import { createContext, useContext, useEffect, useState, ReactNode } from 'react';
import {
  getGetMeQueryKey,
  useAuthenticateTelegram,
  useGetMe,
  type FanIdentity,
} from '@workspace/api-client-react';

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

  const authenticateWithTelegram = () => {
    const initData = getTelegramInitData();

    if (!initData) {
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