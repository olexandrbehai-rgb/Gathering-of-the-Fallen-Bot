import { Link, useLocation } from 'wouter';
import { useAuth } from '@/lib/auth';
import { ShieldAlert, Home, Shield } from 'lucide-react';

export function Shell({ children }: { children: React.ReactNode }) {
  const { identity, isPreview } = useAuth();
  const [location] = useLocation();

  return (
    <div className="min-h-[100dvh] w-full flex flex-col relative bg-background text-foreground overflow-x-hidden">
      <div className="noise-overlay" />
      
      {isPreview && (
        <div className="bg-primary text-primary-foreground text-[10px] py-1 px-4 text-center flex items-center justify-center gap-2 uppercase tracking-[0.2em] font-bold z-50 fixed top-0 w-full shadow-[0_0_15px_rgba(220,38,38,0.5)]">
          <ShieldAlert className="w-3 h-3" />
          Режим попереднього перегляду
        </div>
      )}
      
      {/* Top Nav / Header */}
      <header className={`fixed top-0 w-full z-40 bg-background/80 backdrop-blur-md border-b border-border/50 transition-all duration-300 ${isPreview ? 'mt-6' : 'mt-0'}`}>
        <div className="max-w-md mx-auto px-4 h-14 flex items-center justify-between">
          <Link href="/" className="font-serif font-black text-lg tracking-widest text-primary hover:text-primary/80 transition-colors shrink-0">
            GOTF
          </Link>
          
          <div className="flex items-center gap-2 sm:gap-4 shrink-0 overflow-hidden ml-4">
            {identity?.isAdmin && (
              <Link href="/admin" className={`p-2 transition-colors shrink-0 ${location === '/admin' ? 'text-primary' : 'text-muted-foreground hover:text-foreground'}`}>
                <Shield className="w-5 h-5" />
              </Link>
            )}
            {identity && (
              <div className="flex items-center gap-2 min-w-0">
                <div className="text-right hidden sm:block truncate max-w-[120px]">
                  <div className="text-xs font-bold truncate">{identity.displayName}</div>
                  <div className="text-[10px] text-muted-foreground truncate">@{identity.username}</div>
                </div>
                {identity.avatarUrl ? (
                  <img src={identity.avatarUrl} alt="Avatar" className="w-8 h-8 rounded-full border border-primary/50 shrink-0" />
                ) : (
                  <div className="w-8 h-8 rounded-full bg-secondary border border-primary/30 flex items-center justify-center text-xs font-serif font-bold shrink-0">
                    {identity.displayName.charAt(0)}
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </header>

      <main className={`flex-1 flex flex-col relative z-10 w-full max-w-md mx-auto ${isPreview ? 'pt-20' : 'pt-14'}`}>
        {children}
      </main>
    </div>
  );
}