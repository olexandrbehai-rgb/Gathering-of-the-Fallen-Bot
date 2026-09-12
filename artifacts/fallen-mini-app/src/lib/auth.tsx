import { createContext, useContext, useEffect, useState, ReactNode } from 'react';
import {
  getGetMeQueryKey,
  useAuthenticateTelegram,
  useGetMe,
  type FanIdentity,
} from '@workspace/api-client-react';

const TELEGRAM_INIT_DATA_WAIT_MS = 4_000;
const TELEGRAM_INIT_DATA_POLL_MS = 100;

interface AuthContextType {
  identity: FanIdentity | null;
  isLoading: boolean;
  isPreview: boolean;
  authError: 'missing-init-data' | 'rejected' | null;
  retryTelegramAuth: () => void;
  refetchIdentity: () => void;
}

const AuthContext = createContext<AuthContextType>({ 
  identity: null, 
  isLoading: true, 
  isPreview: false,
  authError: null,
  retryTelegramAuth: () => {},
  refetchIdentity: () => {}
});

export function AuthProvider({ children }: { children: ReactNode }) {
  const [identity, setIdentity] = useState<FanIdentity | null>(null);
  const [isPreview, setIsPreview] = useState(false);
  const [isInitializing, setIsInitializing] = useState(true);
  const [authError, setAuthError] = useState<AuthContextType['authError']>(null);
  
  const { data: me, isLoading: isMeLoading, refetch: refetchMe } = useGetMe({
    query: {
      retry: false,
      refetchInterval: 15_000,
      refetchOnWindowFocus: true,
      queryKey: getGetMeQueryKey(),
    }
  });
  
  const authMutation = useAuthenticateTelegram();
  
  useEffect(() => {
    if (me) {
      setIdentity(me);
      setIsInitializing(false);
      return;
    }
    
    if (!isMeLoading && !me && !identity && isInitializing) {
      // @ts-ignore
      authenticateWithTelegram();
    }
  }, [me, isMeLoading, isInitializing]);

  const getTelegramInitData = () => {
    // @ts-ignore Telegram injects WebApp into window inside the Mini App.
    return window.Telegram?.WebApp?.initData as string | undefined;
  };

  const waitForTelegramInitData = async (): Promise<string | undefined> => {
    const startedAt = Date.now();

    while (Date.now() - startedAt < TELEGRAM_INIT_DATA_WAIT_MS) {
      // @ts-ignore Telegram injects WebApp into window inside the Mini App.
      const webApp = window.Telegram?.WebApp;
      // Tell Telegram that the app has loaded before reading its signed data.
      // @ts-ignore Telegram injects WebApp into window inside the Mini App.
      webApp?.ready?.();

      const initData = getTelegramInitData();
      if (initData) return initData;

      await new Promise((resolve) => window.setTimeout(resolve, TELEGRAM_INIT_DATA_POLL_MS));
    }

    return getTelegramInitData();
  };

  const authenticateWithTelegram = async () => {
    const initData = await waitForTelegramInitData();

    if (!initData) {
      console.warn('[Telegram Mini App] initData was not available after waiting for Telegram SDK');
      finishWithoutTelegram('missing-init-data');
      return;
    }

    setAuthError(null);
    authMutation.mutate({ data: { initData } }, {
      onSuccess: (data) => {
        setIdentity(data);
        setIsInitializing(false);
      },
      onError: () => {
        finishWithoutTelegram('rejected');
      }
    });
  };

  const enablePreviewFallback = () => {
    setIsPreview(true);
    setIdentity({
      id: 'preview-user',
      displayName: 'Загублена Душа (Тест)',
      username: 'preview_soul',
      isAdmin: true,
      subscribed: false
    });
    setIsInitializing(false);
  };

  const finishWithoutTelegram = (error: NonNullable<AuthContextType['authError']>) => {
    if (import.meta.env.DEV) {
      enablePreviewFallback();
      return;
    }
    setIdentity(null);
    setAuthError(error);
    setIsInitializing(false);
  };

  const retryTelegramAuth = () => {
    if (authMutation.isPending) return;
    authenticateWithTelegram();
  };

  const handleRefetch = () => {
    if (isPreview) return; // Don't refetch if mock
    refetchMe();
  };

  return (
    <AuthContext.Provider value={{ 
      identity, 
      isLoading: isMeLoading || authMutation.isPending || isInitializing, 
      isPreview,
      authError,
      retryTelegramAuth,
      refetchIdentity: handleRefetch
    }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);