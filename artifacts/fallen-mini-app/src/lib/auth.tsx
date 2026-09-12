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
  refetchIdentity: () => void;
}

const AuthContext = createContext<AuthContextType>({ 
  identity: null, 
  isLoading: true, 
  isPreview: false,
  refetchIdentity: () => {}
});

export function AuthProvider({ children }: { children: ReactNode }) {
  const [identity, setIdentity] = useState<FanIdentity | null>(null);
  const [isPreview, setIsPreview] = useState(false);
  const [isInitializing, setIsInitializing] = useState(true);
  
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
      const initData = window.Telegram?.WebApp?.initData;
      
      if (initData) {
        authMutation.mutate({ data: { initData } }, {
          onSuccess: (data) => {
            setIdentity(data);
            setIsInitializing(false);
          },
          onError: () => {
             finishWithoutTelegram();
          }
        });
      } else {
        finishWithoutTelegram();
      }
    }
  }, [me, isMeLoading, isInitializing]);

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

  const finishWithoutTelegram = () => {
    if (import.meta.env.DEV) {
      enablePreviewFallback();
      return;
    }
    setIdentity(null);
    setIsInitializing(false);
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
      refetchIdentity: handleRefetch
    }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);