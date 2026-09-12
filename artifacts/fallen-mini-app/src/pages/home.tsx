import { useState, useRef, useEffect } from "react";
import {
  useGetExperience,
  useListTracks,
  useListReleases,
  useListFanPosts,
  useCreateFanPost,
  useHideFanPost,
  useAskAssistant,
  useUpdateSubscription,
  useListVideos,
} from "@workspace/api-client-react";
import { getTelegramAuthErrorContent, useAuth } from "@/lib/auth";
import {
  Play,
  MessageSquare,
  Users,
  Loader2,
  Send,
  Flame,
  Skull,
  Music2,
  Bell,
  BellOff,
  Film,
  Search,
  X,
  EyeOff,
  RefreshCw,
  LogOut,
  ChevronLeft,
  Disc,
  Tv,
  Compass,
  Shield,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";
import { useQueryClient } from "@tanstack/react-query";
import { getGetMeQueryKey } from "@workspace/api-client-react";

// Background Assets - Assuming these are generated and available in the provided output path
import heroBg from "@assets/generated_images/hero-bg.jpg";
import navMusic from "@assets/generated_images/nav-music.jpg";
import navVideos from "@assets/generated_images/nav-videos.jpg";
import navOracle from "@assets/generated_images/nav-oracle.jpg";
import navCoven from "@assets/generated_images/nav-coven.jpg";

type View = "home" | "music" | "videos" | "oracle" | "coven";

// Utility to clean emojis from text as requested
const cleanText = (text: string) => {
  return text
    .replace(
      /[\u{1F300}-\u{1F9FF}\u{2700}-\u{27BF}\u{1F600}-\u{1F64F}\u{1F680}-\u{1F6FF}\u{2600}-\u{26FF}]/gu,
      "",
    )
    .trim();
};

export default function Home() {
  const [activeView, setActiveView] = useState<View>("home");
  const { identity, isLoading, authError, retryTelegramAuth } = useAuth();

  if (isLoading) {
    return (
      <div className="flex-1 flex items-center justify-center min-h-[100dvh] bg-background">
        <Loader2 className="w-8 h-8 animate-spin text-primary opacity-50" />
      </div>
    );
  }

  if (!identity && !import.meta.env.DEV) {
    const initDataWasRejected = authError === "rejected";
    const authFailureContent = getTelegramAuthErrorContent(authError);

    return (
      <div className="flex-1 flex flex-col items-center justify-center px-8 text-center min-h-[100dvh]">
        <div className="w-16 h-16 rounded-full border border-primary/30 flex items-center justify-center mb-6 bg-secondary/50 violet-glow">
          <Shield className="w-8 h-8 text-primary opacity-80" />
        </div>
        <h1 className="font-serif text-2xl font-bold tracking-widest mb-3 uppercase">
          {authFailureContent.heading}
        </h1>
        <p className="text-sm text-muted-foreground leading-relaxed max-w-xs mb-8">
          {authFailureContent.message}
        </p>
        <div className="mt-2 flex w-full max-w-xs flex-col gap-4">
          {initDataWasRejected && (
            <Button
              onClick={retryTelegramAuth}
              className="h-12 bg-primary/20 text-primary hover:bg-primary/30 border border-primary/30"
            >
              <RefreshCw className="w-4 h-4 mr-2" />
              Спробувати ще раз
            </Button>
          )}
          <Button
            variant="ghost"
            className="h-12 border border-border hover:bg-secondary"
            onClick={() => {
              // @ts-ignore
              window.Telegram?.WebApp?.close();
            }}
          >
            <LogOut className="w-4 h-4 mr-2" />
            Закрити Mini App
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col min-h-[100dvh] w-full bg-background relative selection:bg-primary/30">
      {/* View Router */}
      <div className="flex-1 flex flex-col w-full h-full relative">
        {activeView === "home" && <HomeView onNavigate={setActiveView} />}
        {activeView === "music" && (
          <MusicView onBack={() => setActiveView("home")} />
        )}
        {activeView === "videos" && (
          <VideosView onBack={() => setActiveView("home")} />
        )}
        {activeView === "oracle" && (
          <OracleView onBack={() => setActiveView("home")} />
        )}
        {activeView === "coven" && (
          <CovenView onBack={() => setActiveView("home")} />
        )}
      </div>
    </div>
  );
}

// ==========================================
// HOME VIEW
// ==========================================
function HomeView({ onNavigate }: { onNavigate: (view: View) => void }) {
  const { identity } = useAuth();

  return (
    <div className="flex-1 flex flex-col w-full min-h-[100dvh] pb-12 animate-in fade-in duration-700">
      {/* Hero Section */}
      <div className="relative pt-24 pb-16 px-6 flex flex-col items-center justify-center min-h-[45vh] overflow-hidden">
        {/* Background Image with Overlays */}
        <div className="absolute inset-0 z-0">
          <img
            src={heroBg}
            alt="Темний гірський краєвид Gathering Of The Fallen"
            className="w-full h-full object-cover opacity-40 scale-105 animate-[pulse_20s_ease-in-out_infinite_alternate]"
          />
          <div className="absolute inset-0 bg-gradient-to-b from-background/40 via-background/60 to-background"></div>
          <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,_transparent_0%,_var(--tw-gradient-stops))] from-transparent to-background"></div>
        </div>

        <div className="relative z-10 flex flex-col items-center mt-auto w-full">
          <h1 className="font-serif text-[2.5rem] leading-[1.1] font-black tracking-[0.25em] text-center text-foreground drop-shadow-[0_0_20px_rgba(168,85,247,0.4)] mb-4">
            GATHERING
            <br />
            <span className="text-primary/90 text-2xl tracking-[0.35em] font-light block my-1">
              OF THE
            </span>
            FALLEN
          </h1>
          <div className="flex items-center gap-4 w-full max-w-[280px] my-6">
            <div className="h-[1px] flex-1 bg-gradient-to-r from-transparent via-primary/50 to-transparent"></div>
            <p className="text-[9px] uppercase tracking-[0.3em] text-muted-foreground/80 font-medium whitespace-nowrap">
              Деякі душі не йдуть
            </p>
            <div className="h-[1px] flex-1 bg-gradient-to-r from-transparent via-primary/50 to-transparent"></div>
          </div>

          {identity && <SubscriptionToggle />}
        </div>
      </div>

      {/* Navigation Grid */}
      <div className="relative z-10 px-4 flex flex-col gap-4 mt-2">
        <div className="grid grid-cols-2 gap-4">
          <NavCard
            title="МУЗИКА"
            image={navMusic}
            icon={Disc}
            onClick={() => onNavigate("music")}
          />
          <NavCard
            title="ВІДЕО"
            image={navVideos}
            icon={Tv}
            onClick={() => onNavigate("videos")}
          />
        </div>
        <div className="grid grid-cols-2 gap-4">
          <NavCard
            title="ОРАКУЛ"
            image={navOracle}
            icon={Compass}
            onClick={() => onNavigate("oracle")}
          />
          <NavCard
            title="КОВЕН"
            image={navCoven}
            icon={Users}
            onClick={() => onNavigate("coven")}
          />
        </div>
      </div>

      {/* Footer Quote */}
      <div className="mt-16 mb-8 px-8 text-center relative z-10">
        <p className="font-serif text-xs leading-loose tracking-[0.15em] text-muted-foreground/60 uppercase">
          <span className="text-primary/40 text-xl leading-none mr-2 font-serif opacity-50 block mb-1">
            "
          </span>
          Різні зламані душі.
          <br />
          Одне небо.
          <span className="text-primary/40 text-xl leading-none ml-2 font-serif opacity-50 block mt-1">
            "
          </span>
        </p>
      </div>
    </div>
  );
}

function NavCard({
  title,
  image,
  icon: Icon,
  onClick,
}: {
  title: string;
  image: string;
  icon: any;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className="nav-card group aspect-[4/3] flex flex-col items-center justify-end p-4 text-left w-full relative"
    >
      <img
        src={image}
        alt={title}
        className="absolute inset-0 w-full h-full object-cover opacity-50 mix-blend-screen transition-transform duration-1000 group-hover:scale-110 group-hover:opacity-70"
      />
      <div className="absolute inset-0 bg-gradient-to-t from-background via-background/40 to-transparent"></div>

      <div className="relative z-10 w-full flex flex-col items-center justify-center gap-3">
        <div className="w-10 h-10 rounded-full border border-primary/20 bg-background/50 backdrop-blur flex items-center justify-center mb-1 group-hover:border-primary/50 transition-colors">
          <Icon className="w-4 h-4 text-primary/80 group-hover:text-primary transition-colors" />
        </div>
        <span className="font-serif text-[11px] uppercase tracking-[0.25em] font-bold text-foreground/90 group-hover:text-primary-foreground transition-colors">
          {title}
        </span>
      </div>
    </button>
  );
}

function SubscriptionToggle() {
  const { identity, refetchIdentity } = useAuth();
  const updateSub = useUpdateSubscription();
  const queryClient = useQueryClient();

  const handleToggle = () => {
    if (!identity) return;
    const newState = !identity.subscribed;

    // Optimistic update
    queryClient.setQueryData(getGetMeQueryKey(), (old: any) =>
      old ? { ...old, subscribed: newState } : old,
    );

    updateSub.mutate(
      { data: { subscribed: newState } },
      {
        onSuccess: () => refetchIdentity(),
        onError: () => refetchIdentity(), // revert
      },
    );
  };

  return (
    <button
      onClick={handleToggle}
      className="flex items-center gap-2 text-[10px] uppercase tracking-[0.2em] font-bold bg-secondary/40 backdrop-blur-sm border border-primary/20 px-5 py-2.5 rounded-full transition-all hover:bg-secondary hover:border-primary/50 group"
    >
      {identity?.subscribed ? (
        <>
          <Bell className="w-3.5 h-3.5 text-primary group-hover:animate-wiggle" />{" "}
          Ви підписані
        </>
      ) : (
        <>
          <BellOff className="w-3.5 h-3.5 text-muted-foreground" /> Отримувати
          новини
        </>
      )}
    </button>
  );
}

// ==========================================
// SHARED VIEW COMPONENTS
// ==========================================
function ViewHeader({ title, onBack }: { title: string; onBack: () => void }) {
  return (
    <div className="sticky top-0 z-40 bg-background/90 backdrop-blur-lg border-b border-border/40 px-4 h-16 flex items-center justify-between w-full">
      <button
        onClick={onBack}
        className="w-10 h-10 flex items-center justify-center rounded-full bg-secondary/50 border border-border/50 hover:bg-secondary hover:border-primary/50 transition-colors text-muted-foreground hover:text-primary shrink-0"
      >
        <ChevronLeft className="w-5 h-5" />
      </button>
      <h2 className="font-serif text-sm uppercase tracking-[0.25em] font-bold text-foreground text-center flex-1 pr-10">
        {title}
      </h2>
    </div>
  );
}

function SectionTitle({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex items-center gap-4 w-full mb-6">
      <h3 className="text-[10px] uppercase tracking-[0.25em] font-bold text-primary/80 whitespace-nowrap">
        {children}
      </h3>
      <div className="h-[1px] flex-1 bg-gradient-to-r from-border to-transparent"></div>
    </div>
  );
}

function LoadingState() {
  return (
    <div className="flex-1 flex items-center justify-center p-10 h-[50vh]">
      <div className="relative flex items-center justify-center">
        <div className="w-16 h-16 border-2 border-primary/20 border-t-primary rounded-full animate-spin"></div>
        <div className="absolute w-8 h-8 border border-muted-foreground/30 border-b-muted-foreground rounded-full animate-spin-reverse"></div>
      </div>
    </div>
  );
}

// ==========================================
// MUSIC VIEW
// ==========================================
function MusicView({ onBack }: { onBack: () => void }) {
  const [query, setQuery] = useState("");
  const [mood, setMood] = useState("");
  const { data: exp, isLoading: isExpLoading } = useGetExperience();
  const { data: tracks, isLoading: isTracksLoading } = useListTracks({
    query: query.trim() || undefined,
    mood: mood || undefined,
  });
  const { data: releases, isLoading: isReleasesLoading } = useListReleases();

  return (
    <div className="flex-1 flex flex-col animate-in fade-in slide-in-from-bottom-8 duration-500 bg-background pb-20">
      <ViewHeader title="Музика й архіви" onBack={onBack} />

      <div className="p-5 space-y-12 mt-2">
        {/* Featured Release / Track */}
        {isExpLoading || isReleasesLoading ? (
          <LoadingState />
        ) : (
          <>
            {releases && releases.length > 0 && (
              <section>
                <SectionTitle>Остання маніфестація</SectionTitle>
                <a
                  href={releases[0].url}
                  target="_blank"
                  rel="noreferrer"
                  className="block relative overflow-hidden rounded-xl border border-primary/20 bg-secondary/30 group transition-all hover:border-primary/50"
                >
                  <div className="absolute inset-0 bg-gradient-to-br from-primary/10 to-transparent opacity-0 group-hover:opacity-100 transition-opacity"></div>
                  <div className="p-6">
                    <div className="w-12 h-12 rounded-full bg-primary/20 flex items-center justify-center mb-4 text-primary group-hover:scale-110 transition-transform">
                      <Play className="w-5 h-5 ml-1" />
                    </div>
                    <div className="text-[10px] text-primary/70 font-mono uppercase tracking-wider mb-2">
                      {new Date(releases[0].date).toLocaleDateString("uk-UA", {
                        year: "numeric",
                      })}
                    </div>
                    <h3 className="font-serif text-2xl font-bold text-foreground mb-2 leading-tight">
                      {releases[0].title}
                    </h3>
                    <p className="text-sm text-muted-foreground line-clamp-2">
                      {releases[0].description}
                    </p>
                  </div>
                </a>
              </section>
            )}

            {/* Archive Search & Filter */}
            <section>
              <SectionTitle>Архів композицій</SectionTitle>
              <div className="space-y-4 mb-6">
                <div className="relative">
                  <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                  <Input
                    value={query}
                    onChange={(event) => setQuery(event.target.value)}
                    placeholder="Знайти композицію..."
                    className="h-12 pl-12 pr-10 bg-secondary/40 border-border/50 focus-visible:ring-primary/50 focus-visible:border-primary rounded-xl font-sans"
                  />
                  {query && (
                    <button
                      type="button"
                      onClick={() => setQuery("")}
                      className="absolute right-4 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-primary transition-colors"
                    >
                      <X className="w-4 h-4" />
                    </button>
                  )}
                </div>
                <div
                  className="flex gap-2 overflow-x-auto pb-2 [&::-webkit-scrollbar]:hidden"
                  style={{ scrollbarWidth: "none" }}
                >
                  <MoodButton active={!mood} onClick={() => setMood("")}>
                    Усі
                  </MoodButton>
                  {exp?.moods.map((item) => (
                    <MoodButton
                      key={item}
                      active={mood === item}
                      onClick={() => setMood(item)}
                    >
                      {cleanText(item)}
                    </MoodButton>
                  ))}
                </div>
              </div>

              {/* Track List */}
              <div className="flex flex-col gap-3">
                {isTracksLoading ? (
                  <div className="py-10 text-center">
                    <Loader2 className="w-6 h-6 animate-spin text-primary/50 mx-auto" />
                  </div>
                ) : tracks?.length === 0 ? (
                  <div className="py-12 text-center border border-dashed border-border/50 rounded-xl text-sm text-muted-foreground font-serif bg-secondary/10">
                    У цьому розділі нічого не знайдено.
                  </div>
                ) : (
                  tracks?.map((track) => {
                    const mainLink =
                      track.youtubeUrl ||
                      track.youtubeMusicUrl ||
                      track.spotifyUrl ||
                      track.appleMusicUrl ||
                      "#";
                    return (
                      <a
                        key={track.id}
                        href={mainLink}
                        target="_blank"
                        rel="noreferrer"
                        className="group flex items-center justify-between p-4 rounded-xl border border-transparent hover:border-primary/20 bg-secondary/20 hover:bg-secondary/40 transition-all cursor-pointer"
                      >
                        <div className="flex items-center gap-4 min-w-0 pr-4">
                          <div className="w-10 h-10 rounded-full bg-background border border-border flex items-center justify-center shrink-0 group-hover:border-primary/50 group-hover:text-primary transition-colors">
                            <Play className="w-4 h-4 ml-0.5" />
                          </div>
                          <div className="flex flex-col min-w-0">
                            <span className="text-base font-medium truncate font-serif">
                              {track.title}
                            </span>
                            <span className="text-[10px] text-primary/60 mt-1 tracking-widest uppercase truncate">
                              {track.moods.map(cleanText).join(" • ")}
                            </span>
                          </div>
                        </div>
                      </a>
                    );
                  })
                )}
              </div>
            </section>
          </>
        )}
      </div>
    </div>
  );
}

function MoodButton({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "shrink-0 rounded-full px-5 py-2 text-[10px] font-bold uppercase tracking-widest transition-all",
        active
          ? "bg-primary/20 text-primary border border-primary/40 shadow-[0_0_15px_rgba(168,85,247,0.15)]"
          : "bg-secondary/40 text-muted-foreground border border-border/50 hover:border-primary/30 hover:text-foreground",
      )}
    >
      {children}
    </button>
  );
}

// ==========================================
// VIDEOS VIEW
// ==========================================
function VideosView({ onBack }: { onBack: () => void }) {
  const { data: videos, isLoading } = useListVideos();

  return (
    <div className="flex-1 flex flex-col animate-in fade-in slide-in-from-bottom-8 duration-500 bg-background pb-20">
      <ViewHeader title="Офіційні відео" onBack={onBack} />

      <div className="p-5">
        {isLoading ? (
          <LoadingState />
        ) : (
          <div className="grid grid-cols-1 gap-6">
            {videos?.map((video) => (
              <a
                key={video.id}
                href={video.youtubeUrl}
                target="_blank"
                rel="noreferrer"
                className="group flex flex-col bg-secondary/20 rounded-xl overflow-hidden border border-border/50 hover:border-primary/40 transition-all cursor-pointer"
              >
                <div className="relative aspect-video w-full overflow-hidden bg-black">
                  <img
                    src={video.thumbnailUrl}
                    alt={video.title}
                    className="w-full h-full object-cover opacity-80 group-hover:scale-105 group-hover:opacity-100 transition-all duration-700"
                  />
                  <div className="absolute inset-0 bg-gradient-to-t from-background/90 via-background/20 to-transparent"></div>

                  {/* Play Button Overlay */}
                  <div className="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity duration-300">
                    <div className="w-16 h-16 rounded-full bg-primary/20 backdrop-blur-md border border-primary/50 flex items-center justify-center text-primary violet-glow">
                      <Play className="w-6 h-6 ml-1" />
                    </div>
                  </div>

                  <div className="absolute bottom-3 right-3 bg-black/70 backdrop-blur text-[10px] px-2 py-1 rounded text-primary/90 font-mono border border-white/10">
                    {video.duration}
                  </div>
                </div>

                <div className="p-4">
                  <h3 className="font-serif text-lg font-bold text-foreground line-clamp-2 leading-tight group-hover:text-primary transition-colors">
                    {video.title}
                  </h3>
                </div>
              </a>
            ))}
            {videos?.length === 0 && (
              <div className="py-12 text-center border border-dashed border-border/50 rounded-xl text-sm text-muted-foreground font-serif bg-secondary/10">
                Відео ще не додані.
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

// ==========================================
// ORACLE VIEW
// ==========================================
function OracleView({ onBack }: { onBack: () => void }) {
  const [input, setInput] = useState("");
  const [chatLog, setChatLog] = useState<
    { id: string; role: "user" | "oracle"; text: string }[]
  >([
    {
      id: "welcome",
      role: "oracle",
      text: "Speak your truth into the void. I am the Oracle of the Fallen. Ask me of the lore, the sound, or the meaning.",
    },
  ]);
  const scrollRef = useRef<HTMLDivElement>(null);

  const askMutation = useAskAssistant();

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [chatLog, askMutation.isPending]);

  const handleSend = () => {
    if (!input.trim() || askMutation.isPending) return;
    const msg = input.trim();
    setInput("");
    const tempId = Date.now().toString();

    setChatLog((prev) => [
      ...prev,
      { id: `u-${tempId}`, role: "user", text: msg },
    ]);

    askMutation.mutate(
      { data: { message: msg } },
      {
        onSuccess: (res) => {
          setChatLog((prev) => [
            ...prev,
            { id: `o-${Date.now()}`, role: "oracle", text: res.reply },
          ]);
        },
        onError: () => {
          setChatLog((prev) => [
            ...prev,
            {
              id: `o-err-${Date.now()}`,
              role: "oracle",
              text: "Порожнеча не дає відповіді. Спробуйте ще раз пізніше.",
            },
          ]);
        },
      },
    );
  };

  return (
    <div className="flex flex-col h-full animate-in fade-in slide-in-from-bottom-8 duration-500 relative">
      <ViewHeader title="Оракул" onBack={onBack} />

      {/* Background Effect */}
      <div className="absolute inset-0 top-16 bg-[radial-gradient(circle_at_top,_var(--tw-gradient-stops))] from-primary/5 via-background to-background pointer-events-none z-0"></div>

      <div
        className="flex-1 overflow-y-auto p-5 space-y-8 relative z-10"
        ref={scrollRef}
      >
        <div className="flex justify-center mb-8">
          <div className="w-16 h-16 rounded-full border border-primary/20 bg-secondary/50 flex items-center justify-center violet-glow mt-4">
            <Compass className="w-8 h-8 text-primary/70 animate-[pulse_4s_ease-in-out_infinite]" />
          </div>
        </div>

        {chatLog.map((msg) => (
          <div
            key={msg.id}
            className={cn(
              "flex flex-col max-w-[85%]",
              msg.role === "user" ? "ml-auto items-end" : "mr-auto items-start",
            )}
          >
            <span className="text-[9px] text-muted-foreground/60 uppercase tracking-[0.2em] mb-2 px-2">
              {msg.role === "user" ? "You" : "Oracle"}
            </span>
            <div
              className={cn(
                "p-4 text-[15px] leading-relaxed relative rounded-2xl",
                msg.role === "user"
                  ? "bg-secondary border border-border/50 text-foreground rounded-tr-sm"
                  : "bg-primary/10 border border-primary/20 text-primary-foreground font-serif tracking-wide rounded-tl-sm violet-glow",
              )}
            >
              {msg.text}
            </div>
          </div>
        ))}

        {askMutation.isPending && (
          <div className="mr-auto items-start flex flex-col max-w-[85%]">
            <div className="p-5 bg-primary/5 border border-primary/20 rounded-2xl rounded-tl-sm flex gap-2">
              <span className="w-1.5 h-1.5 bg-primary/60 rounded-full animate-bounce"></span>
              <span className="w-1.5 h-1.5 bg-primary/60 rounded-full animate-bounce [animation-delay:0.2s]"></span>
              <span className="w-1.5 h-1.5 bg-primary/60 rounded-full animate-bounce [animation-delay:0.4s]"></span>
            </div>
          </div>
        )}
      </div>

      <div className="p-4 bg-background/90 backdrop-blur-xl border-t border-border/40 relative z-20 pb-8">
        <div className="flex gap-3 relative max-w-md mx-auto">
          <Input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleSend()}
            placeholder="Покликати відповідь..."
            className="pr-14 bg-secondary/50 border-border/50 focus-visible:ring-primary/50 focus-visible:border-primary font-serif h-14 rounded-full text-base"
            disabled={askMutation.isPending}
          />
          <Button
            size="icon"
            className="absolute right-1.5 top-1.5 bottom-1.5 h-11 w-11 rounded-full bg-primary text-primary-foreground hover:bg-primary/90 hover:scale-105 transition-all"
            onClick={handleSend}
            disabled={askMutation.isPending || !input.trim()}
          >
            <Send className="w-5 h-5 ml-1" />
          </Button>
        </div>
      </div>
    </div>
  );
}

// ==========================================
// COVEN VIEW
// ==========================================
function CovenView({ onBack }: { onBack: () => void }) {
  const { identity } = useAuth();
  const { data: posts, isLoading, refetch } = useListFanPosts();
  const createMutation = useCreateFanPost();
  const hideMutation = useHideFanPost();
  const [msg, setMsg] = useState("");
  const [feedback, setFeedback] = useState("");

  const errorMessage = (error: unknown): string => {
    if (typeof error !== "object" || error === null || !("data" in error))
      return "Failed to manifest. Try again.";
    const data = error.data as any;
    return typeof data?.error === "string" && data.error.length > 0
      ? data.error
      : "Failed to manifest. Try again.";
  };

  const handlePost = () => {
    if (!msg.trim() || msg.length < 2) return;
    createMutation.mutate(
      { data: { message: msg } },
      {
        onSuccess: () => {
          setMsg("");
          setFeedback("Your mark has been left.");
          refetch();
        },
        onError: (error) => setFeedback(errorMessage(error)),
      },
    );
  };

  const handleHide = (id: number) => {
    hideMutation.mutate(
      { id },
      {
        onSuccess: () => {
          setFeedback("Post banished.");
          refetch();
        },
        onError: (error) => setFeedback(errorMessage(error)),
      },
    );
  };

  return (
    <div className="flex-1 flex flex-col animate-in fade-in slide-in-from-bottom-8 duration-500 bg-background pb-20">
      <ViewHeader title="Ковен" onBack={onBack} />

      <div className="p-5 space-y-8">
        {/* Composer */}
        <div className="bg-secondary/30 border border-primary/20 rounded-2xl p-5 relative overflow-hidden group">
          <div className="absolute inset-0 bg-gradient-to-br from-primary/5 to-transparent pointer-events-none"></div>
          <h3 className="font-serif text-sm uppercase tracking-[0.2em] font-bold mb-4 flex items-center gap-3 text-primary/90">
            <Flame className="w-4 h-4" /> Leave your mark
          </h3>
          <Textarea
            placeholder="Що відлунює у ваших думках?"
            value={msg}
            onChange={(e) => setMsg(e.target.value)}
            className="bg-background/50 border-border/50 focus-visible:ring-primary/30 rounded-xl min-h-[100px] text-base resize-none font-serif mb-4"
          />
          <div className="flex items-center justify-between">
            <div className="text-[10px] text-muted-foreground/60 max-w-[60%]">
              {feedback}
            </div>
            <Button
              onClick={handlePost}
              disabled={createMutation.isPending || msg.length < 2}
              className="rounded-full px-6 h-10 bg-primary/20 text-primary hover:bg-primary hover:text-primary-foreground border border-primary/30 transition-all font-bold tracking-widest text-[10px] uppercase"
            >
              {createMutation.isPending ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                "Опублікувати"
              )}
            </Button>
          </div>
        </div>

        {/* Feed */}
        <div className="space-y-4 relative">
          <div className="absolute left-6 top-0 bottom-0 w-[1px] bg-gradient-to-b from-primary/30 via-primary/10 to-transparent -z-10 hidden sm:block"></div>

          {isLoading ? (
            <LoadingState />
          ) : posts?.length === 0 ? (
            <div className="text-center py-16 text-muted-foreground/60 text-sm font-serif border border-dashed border-border/40 rounded-2xl">
              The coven is silent. Speak first.
            </div>
          ) : (
            posts?.map((post, i) => (
              <div
                key={post.id}
                className="bg-secondary/10 border border-border/30 rounded-2xl p-5 transition-all hover:bg-secondary/20 hover:border-primary/20 group"
              >
                <div className="flex justify-between items-start mb-3">
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded-full bg-background border border-primary/20 flex items-center justify-center text-[10px] font-bold font-serif text-primary">
                      {post.author.charAt(0).toUpperCase()}
                    </div>
                    <div>
                      <span className="font-bold text-sm text-foreground tracking-wide block">
                        {post.author}
                      </span>
                      <span className="text-[9px] text-muted-foreground/60 font-mono uppercase tracking-widest">
                        {new Date(post.createdAt).toLocaleDateString("en-US", {
                          day: "numeric",
                          month: "short",
                          year: "numeric",
                        })}
                      </span>
                    </div>
                  </div>

                  {identity?.isAdmin && (
                    <Button
                      type="button"
                      variant="ghost"
                      size="icon"
                      className="h-8 w-8 text-muted-foreground/50 hover:text-destructive hover:bg-destructive/10 rounded-full opacity-0 group-hover:opacity-100 transition-opacity"
                      disabled={hideMutation.isPending}
                      onClick={() => handleHide(post.id)}
                    >
                      <EyeOff className="h-4 w-4" />
                    </Button>
                  )}
                </div>
                <p className="text-[15px] text-foreground/80 whitespace-pre-wrap font-serif leading-relaxed pl-11">
                  {post.message}
                </p>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
