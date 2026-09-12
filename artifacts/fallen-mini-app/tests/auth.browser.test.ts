import assert from 'node:assert/strict';
import { createReadStream, existsSync, statSync } from 'node:fs';
import { readFile } from 'node:fs/promises';
import { createServer, type IncomingMessage, type ServerResponse } from 'node:http';
import { extname, join, normalize } from 'node:path';
import { fileURLToPath } from 'node:url';
import test from 'node:test';
import { chromium, type Browser, type Page } from 'playwright-core';

const publicDirectory = fileURLToPath(new URL('../dist/public/', import.meta.url));
const chromiumPath = process.env.CHROMIUM_PATH ?? '/repl/tools/bin/chromium';

function contentTypeFor(path: string): string {
  switch (extname(path)) {
    case '.css':
      return 'text/css; charset=utf-8';
    case '.js':
      return 'text/javascript; charset=utf-8';
    case '.json':
      return 'application/json; charset=utf-8';
    case '.svg':
      return 'image/svg+xml';
    case '.jpg':
    case '.jpeg':
      return 'image/jpeg';
    case '.png':
      return 'image/png';
    case '.woff':
    case '.woff2':
      return 'font/woff2';
    default:
      return 'text/html; charset=utf-8';
  }
}

async function serveProductionBuild(
  request: IncomingMessage,
  response: ServerResponse,
  serverState: {
    authRequestCount: { value: number };
    meResponse: Promise<void>;
  },
): Promise<void> {
  const requestPath = new URL(request.url ?? '/', 'http://localhost').pathname;

  if (requestPath === '/api/me') {
    await serverState.meResponse;
    response.writeHead(401, { 'Content-Type': 'application/json' });
    response.end(JSON.stringify({ message: 'Not authenticated' }));
    return;
  }

  if (requestPath === '/api/auth/telegram' && request.method === 'POST') {
    serverState.authRequestCount.value += 1;
    response.writeHead(401, { 'Content-Type': 'application/json' });
    response.end(JSON.stringify({ message: 'Invalid Telegram authentication' }));
    return;
  }

  const relativePath = normalize(requestPath).replace(/^(\.\.(\/|\\|$))+/, '');
  const requestedFile = join(publicDirectory, relativePath === '/' ? 'index.html' : relativePath);
  const filePath = existsSync(requestedFile) && statSync(requestedFile).isFile()
    ? requestedFile
    : join(publicDirectory, 'index.html');

  if (filePath === join(publicDirectory, 'index.html')) {
    const index = await readFile(filePath, 'utf8');
    response.writeHead(200, { 'Content-Type': contentTypeFor(filePath) });
    response.end(index.replace(
      '<script src="https://telegram.org/js/telegram-web-app.js"></script>',
      '',
    ));
    return;
  }

  response.writeHead(200, { 'Content-Type': contentTypeFor(filePath) });
  createReadStream(filePath).pipe(response);
}

async function waitForAuthRequestCount(
  authRequestCount: { value: number },
  expectedCount: number,
): Promise<void> {
  const deadline = Date.now() + 3_000;

  while (authRequestCount.value < expectedCount && Date.now() < deadline) {
    await new Promise((resolve) => setTimeout(resolve, 25));
  }

  assert.equal(authRequestCount.value, expectedCount);
}

test('production build shows rejected Telegram auth and retries the request', async () => {
  assert.ok(existsSync(join(publicDirectory, 'index.html')), 'production build is missing');
  assert.ok(existsSync(chromiumPath), `Chromium executable is missing at ${chromiumPath}`);

  const authRequestCount = { value: 0 };
  let releaseMeResponse!: () => void;
  const meResponse = new Promise<void>((resolve) => {
    releaseMeResponse = resolve;
  });
  const serverState = { authRequestCount, meResponse };
  const server = createServer((request, response) => {
    void serveProductionBuild(request, response, serverState);
  });
  await new Promise<void>((resolve) => server.listen(0, '127.0.0.1', resolve));

  const address = server.address();
  assert.ok(address && typeof address !== 'string');
  const browser: Browser = await chromium.launch({
    executablePath: chromiumPath,
    headless: true,
    args: ['--no-sandbox'],
  });

  try {
    const page: Page = await browser.newPage();

    await page.goto(`http://127.0.0.1:${address.port}/`, { waitUntil: 'domcontentloaded' });
    await page.evaluate(`
      Object.defineProperty(window, 'Telegram', {
        configurable: true,
        value: {
          WebApp: {
            initData: 'invalid-production-init-data',
            ready: function () {},
          },
        },
      });
    `);
    releaseMeResponse();

    try {
      await page.getByRole('heading', { name: 'НЕ ВДАЛОСЯ УВІЙТИ' }).waitFor({ timeout: 5_000 });
    } catch (error) {
      console.error('Unexpected production auth page:', {
        url: page.url(),
        body: await page.locator('body').textContent(),
        telegram: await page.evaluate(() => (window as unknown as { Telegram?: unknown }).Telegram),
        authRequestCount: authRequestCount.value,
      });
      throw error;
    }

    const bodyText = await page.locator('body').textContent();
    assert.match(bodyText ?? '', /Telegram не підтвердив ваші дані входу/);
    assert.doesNotMatch(bodyText ?? '', /Mini App не отримав дані входу від Telegram/);
    await waitForAuthRequestCount(authRequestCount, 1);

    const retryButton = page.getByRole('button', { name: 'Спробувати ще раз' });
    await retryButton.click();
    await waitForAuthRequestCount(authRequestCount, 2);
  } finally {
    await browser.close();
    await new Promise<void>((resolve, reject) => {
      server.close((error) => (error ? reject(error) : resolve()));
    });
  }
});