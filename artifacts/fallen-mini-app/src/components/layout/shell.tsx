import { Link, useLocation } from "wouter";
import { useAuth } from "@/lib/auth";
import { ShieldAlert, Shield } from "lucide-react";

export function Shell({ children }: { children: React.ReactNode }) {
  const { identity, isPreview } = useAuth();
  const [location] = useLocation();

  return (
    <div className="min-h-[100dvh] w-full flex flex-col relative bg-background text-foreground overflow-x-hidden">
      <div className="noise-overlay" />

      {isPreview && (
        <div className="bg-primary/20 backdrop-blur-md text-primary-foreground text-[10px] py-1 px-4 text-center flex items-center justify-center gap-2 uppercase tracking-[0.2em] font-bold z-50 fixed top-0 w-full border-b border-primary/30 shadow-[0_0_15px_rgba(168,85,247,0.3)]">
          <ShieldAlert className="w-3 h-3 text-primary" />
          Режим попереднього перегляду
        </div>
      )}

      {/* Absolute Header - completely transparent, floating above content */}
      <header
        className={`absolute top-0 w-full z-40 transition-all duration-300 ${isPreview ? "mt-6" : "mt-0"}`}
      >
        <div className="max-w-md mx-auto px-4 h-16 flex items-center justify-end">
          <div className="flex items-center gap-3 shrink-0 overflow-hidden">
            {identity?.isAdmin && (
              <Link
                href="/admin"
                className={`p-2 transition-colors shrink-0 bg-background/30 backdrop-blur-md rounded-full border border-primary/20 shadow-sm ${location === "/admin" ? "text-primary" : "text-muted-foreground hover:text-foreground"}`}
              >
                <Shield className="w-4 h-4" />
              </Link>
            )}
            {identity && (
              <div className="flex items-center gap-2 bg-background/30 backdrop-blur-md rounded-full border border-border/50 py-1 pl-3 pr-1 shadow-sm">
                <div className="text-right hidden sm:block truncate max-w-[120px]">
                  <div className="text-xs font-bold truncate">
                    {identity.displayName}
                  </div>
                </div>
                {identity.avatarUrl ? (
                  <img
                    src={identity.avatarUrl}
                    alt="Avatar"
                    className="w-7 h-7 rounded-full border border-primary/40 shrink-0"
                  />
                ) : (
                  <div className="w-7 h-7 rounded-full bg-secondary border border-primary/30 flex items-center justify-center text-xs font-serif font-bold shrink-0">
                    {identity.displayName.charAt(0)}
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </header>

      {/* Main content takes full screen, no top padding */}
      <main className="flex-1 flex flex-col relative z-10 w-full max-w-md mx-auto">
        {children}
      </main>
    </div>
  );
}
