import assert from 'node:assert/strict';
import test from 'node:test';

import {
  getTelegramAuthErrorContent,
  invokeTelegramAuthRetry,
  resolveTelegramAuthFailure,
} from './auth.tsx';

test('shows a distinct message when Telegram rejects initData', () => {
  const rejected = getTelegramAuthErrorContent('rejected');
  const missing = getTelegramAuthErrorContent('missing-init-data');

  assert.equal(rejected.heading, 'НЕ ВДАЛОСЯ УВІЙТИ');
  assert.match(rejected.message, /Telegram не підтвердив ваші дані входу/);
  assert.notDeepEqual(rejected, missing);
  assert.equal(missing.heading, 'ВІДКРИЙТЕ У TELEGRAM');
});

test('retrying Telegram authentication invokes the authentication request again', () => {
  let authenticationAttempts = 0;
  const authenticate = () => {
    authenticationAttempts += 1;
  };

  invokeTelegramAuthRetry(false, authenticate);
  assert.equal(authenticationAttempts, 1);

  invokeTelegramAuthRetry(true, authenticate);
  assert.equal(authenticationAttempts, 1);
});

test('creates the preview user only in development', () => {
  const productionResult = resolveTelegramAuthFailure('rejected', false);
  assert.equal(productionResult.identity, null);
  assert.equal(productionResult.isPreview, false);
  assert.equal(productionResult.authError, 'rejected');

  const developmentResult = resolveTelegramAuthFailure('rejected', true);
  assert.equal(developmentResult.identity?.id, 'preview-user');
  assert.equal(developmentResult.isPreview, true);
  assert.equal(developmentResult.authError, null);
});