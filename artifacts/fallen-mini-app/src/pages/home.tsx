import { useState, useRef, useEffect } from 'react';
import { 
  useGetExperience, 
  useListTracks, 
  useListReleases, 
  useListFanPosts, 
  useCreateFanPost, 
  useHideFanPost,
  useAskAssistant,
  useUpdateSubscription,
  useListVideos
} from '@workspace/api-client-react';
import { getTelegramAuthErrorContent, useAuth } from '@/lib/auth';
import { Play, MessageSquare, Users, Loader2, Send, Flame, Skull, Music2, Bell, BellOff, ArrowRight, Film, Headphones, Search, X, EyeOff, RefreshCw, LogOut } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { cn } from '@/lib/utils';
import { useQueryClient } from '@tanstack/react-query';
import { getGetMeQueryKey } from '@workspace/api-client-react';

type Tab = 'sanctuary' | 'oracle' | 'coven';

export default function Home() {
  const [activeTab, setActiveTab] = useState<Tab>('sanctuary');
  const { identity, isLoading, authError, retryTelegramAuth } = useAuth();

  if (isLoading) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
      </div>
    );
  }

  if (!identity && !import.meta.env.DEV) {
    const initDataWasRejected = authError === 'rejected';
    const authFailureContent = getTelegramAuthErrorContent(authError);

    return (
      <div className="flex-1 flex flex-col items-center justify-center px-8 text-center">
        <Skull className="w-12 h-12 text-primary mb-5" />
        <h1 className="font-serif text-2xl font-bold tracking-widest mb-3">
          {authFailureContent.heading}
        </h1>
        <p className="text-sm text-muted-foreground leading-relaxed max-w-xs">
          {authFailureContent.message}
        </p>
        <div className="mt-6 flex w-full max-w-xs flex-col gap-3">
          {initDataWasRejected && (
            <Button onClick={retryTelegramAuth}>
              <RefreshCw className="w-4 h-4" />
              Спробувати ще раз
            </Button>
          )}
          <Button
            variant={initDataWasRejected ? 'outline' : 'default'}
            onClick={() => {
              // @ts-ignore Telegram injects WebApp into window inside the Mini App.
              window.Telegram?.WebApp?.close();
            }}
          >
            <LogOut className="w-4 h-4" />
            Закрити Mini App
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full w-full pb-20">
      {/* Hero Section */}
      <div className="relative py-12 px-6 flex flex-col items-center justify-center border-b border-border/50 bg-gradient-to-b from-background to-secondary/30 overflow-hidden">
        <div className="absolute inset-0 opacity-20 pointer-events-none">
          <div className="absolute top-[-50%] left-[-50%] w-[200%] h-[200%] bg-[radial-gradient(ellipse_at_center,_var(--tw-gradient-stops))] from-primary/20 via-background/5 to-transparent animate-[pulse_10s_ease-in-out_infinite]" />
        </div>
        <Skull className="w-12 h-12 text-primary mb-4 opacity-80" />
        <h1 className="font-serif text-3xl font-black tracking-[0.3em] text-center text-foreground z-10 drop-shadow-[0_0_10px_rgba(0,0,0,0.8)]">
          GATHERING<br/>
          <span className="text-primary">OF THE</span><br/>
          FALLEN
        </h1>
        {identity && <SubscriptionToggle />}
      </div>

      {/* Navigation */}
      <div className="sticky top-14 z-30 bg-background/95 backdrop-blur border-b border-border/50">
        <div className="flex w-full">
          <TabButton active={activeTab === 'sanctuary'} onClick={() => setActiveTab('sanctuary')} icon={Music2} label="Святилище" />
          <TabButton active={activeTab === 'oracle'} onClick={() => setActiveTab('oracle')} icon={MessageSquare} label="Оракул" />
          <TabButton active={activeTab === 'coven'} onClick={() => setActiveTab('coven')} icon={Users} label="Ковен" />
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 relative">
        {activeTab === 'sanctuary' && <SanctuaryTab />}
        {activeTab === 'oracle' && <OracleTab />}
        {activeTab === 'coven' && <CovenTab />}
      </div>
    </div>
  );
}

function TabButton({ active, onClick, icon: Icon, label }: { active: boolean, onClick: () => void, icon: any, label: string }) {
  return (
    <button 
      onClick={onClick}
      className={cn(
        "flex-1 py-4 flex flex-col items-center gap-1 transition-all duration-300 relative",
        active ? "text-primary" : "text-muted-foreground hover:text-foreground"
      )}
    >
      <Icon className={cn("w-5 h-5", active && "drop-shadow-[0_0_8px_rgba(220,38,38,0.8)]")} />
      <span className="text-[10px] uppercase tracking-[0.2em] font-bold">{label}</span>
      {active && (
        <div className="absolute bottom-0 left-0 w-full h-[2px] bg-primary blood-glow"></div>
      )}
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
      old ? { ...old, subscribed: newState } : old
    );

    updateSub.mutate({ data: { subscribed: newState } }, {
      onSuccess: () => refetchIdentity(),
      onError: () => refetchIdentity() // revert
    });
  };

  return (
    <button 
      onClick={handleToggle}
      className="mt-6 z-10 flex items-center gap-2 text-xs uppercase tracking-widest font-bold bg-secondary/50 border border-primary/20 px-4 py-2 rounded-full transition-all hover:bg-secondary hover:border-primary/50"
    >
      {identity?.subscribed ? (
        <><Bell className="w-4 h-4 text-primary" /> Ви підписані</>
      ) : (
        <><BellOff className="w-4 h-4 text-muted-foreground" /> Отримувати оновлення</>
      )}
    </button>
  );
}

function SanctuaryTab() {
  const [query, setQuery] = useState('');
  const [mood, setMood] = useState('');
  const { data: exp, isLoading: isExpLoading } = useGetExperience();
  const { data: tracks, isLoading: isTracksLoading } = useListTracks({
    query: query.trim() || undefined,
    mood: mood || undefined,
  });
  const { data: releases, isLoading: isReleasesLoading } = useListReleases();
  const { data: videos, isLoading: isVideosLoading } = useListVideos();

  if (isExpLoading || isTracksLoading || isReleasesLoading || isVideosLoading) {
    return <LoadingState />;
  }

  return (
    <div className="p-4 space-y-10 animate-in fade-in slide-in-from-bottom-4 duration-500">
      {/* Featured Track */}
      {exp?.featured && (
        <section>
          <SectionTitle icon={Flame}>Ритуал моменту</SectionTitle>
          <div className="bg-card border border-card-border p-4 relative overflow-hidden group">
            <div className="absolute inset-0 bg-primary/5 opacity-0 group-hover:opacity-100 transition-opacity"></div>
            <h3 className="font-serif text-xl font-bold text-foreground">{exp.featured.title}</h3>
            <div className="flex flex-wrap gap-2 mt-2 mb-6">
              {exp.featured.moods.map(mood => (
                <span key={mood} className="text-[10px] uppercase tracking-wider text-primary border border-primary/30 px-2 py-0.5 rounded-sm">
                  {mood}
                </span>
              ))}
            </div>
            <div className="flex flex-wrap gap-2">
              {exp.featured.youtubeUrl && (
                <Button variant="default" className="flex-1 text-xs min-w-[90px]" asChild>
                  <a href={exp.featured.youtubeUrl} target="_blank" rel="noreferrer">
                    Кліп
                  </a>
                </Button>
              )}
              {exp.featured.youtubeMusicUrl && (
                <Button variant="outline" className="flex-1 text-xs text-foreground border-border min-w-[90px]" asChild>
                  <a href={exp.featured.youtubeMusicUrl} target="_blank" rel="noreferrer">
                    YT Music
                  </a>
                </Button>
              )}
              {exp.featured.spotifyUrl && (
                <Button variant="outline" className="flex-1 text-xs text-foreground border-border min-w-[90px]" asChild>
                  <a href={exp.featured.spotifyUrl} target="_blank" rel="noreferrer">
                    Spotify
                  </a>
                </Button>
              )}
            </div>
          </div>
        </section>
      )}

      {/* Videos */}
      {videos && videos.length > 0 && (
        <section>
          <SectionTitle icon={Film}>Офіційні кліпи</SectionTitle>
          <div className="flex overflow-x-auto gap-4 pb-4 snap-x snap-mandatory -mx-4 px-4 [&::-webkit-scrollbar]:hidden" style={{ scrollbarWidth: 'none' }}>
            {videos.map(video => (
              <div 
                key={video.id} 
                className="relative shrink-0 w-[85%] max-w-[300px] aspect-video rounded-sm overflow-hidden border border-border/50 transition-colors snap-center flex flex-col justify-end bg-secondary group"
              >
                <img 
                  src={video.thumbnailUrl} 
                  alt={video.title} 
                  className="absolute inset-0 w-full h-full object-cover transition-transform duration-700 group-hover:scale-105 opacity-80"
                />
                <div className="absolute inset-0 bg-gradient-to-t from-background/95 via-background/60 to-transparent"></div>
                <div className="absolute top-2 right-2 bg-background/80 backdrop-blur text-[10px] px-2 py-1 rounded-sm text-primary font-mono border border-primary/20 shadow-sm z-10">
                  {video.duration}
                </div>
                
                <div className="relative z-10 p-3 w-full mt-auto">
                  <h3 className="font-serif font-bold text-foreground line-clamp-2 text-sm leading-tight drop-shadow-[0_2px_4px_rgba(0,0,0,0.8)] mb-3">
                    {video.title}
                  </h3>
                  <div className="flex gap-2">
                    {video.youtubeUrl && (
                      <Button variant="default" size="sm" className="h-8 text-[10px] px-3 flex-1" asChild>
                        <a href={video.youtubeUrl} target="_blank" rel="noreferrer">Відео</a>
                      </Button>
                    )}
                    {video.youtubeMusicUrl && (
                      <Button variant="outline" size="sm" className="h-8 text-[10px] px-3 flex-1 border-border bg-background/50 backdrop-blur hover:bg-background/80" asChild>
                        <a href={video.youtubeMusicUrl} target="_blank" rel="noreferrer">YT Music</a>
                      </Button>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Releases */}
      <section>
        <SectionTitle icon={Music2}>Останні маніфестації</SectionTitle>
        <div className="space-y-4">
          {releases?.map(release => (
            <div key={release.id} className="flex gap-4 items-center bg-card p-3 border border-border/50 hover:border-primary/50 transition-colors">
              <div className="w-16 h-16 bg-secondary flex items-center justify-center border border-border shrink-0">
                <Skull className="w-6 h-6 text-muted-foreground opacity-50" />
              </div>
              <div className="flex-1 min-w-0">
                <h4 className="font-bold text-sm truncate">{release.title}</h4>
                <p className="text-xs text-muted-foreground mt-1 line-clamp-2">{release.description}</p>
                <div className="text-[10px] text-primary mt-2 font-mono uppercase tracking-wider">
                  {new Date(release.date).toLocaleDateString('uk-UA', { day: 'numeric', month: 'short', year: 'numeric' })}
                </div>
              </div>
              <Button variant="ghost" size="icon" className="shrink-0 h-10 w-10 text-muted-foreground hover:text-primary" asChild>
                <a href={release.url} target="_blank" rel="noreferrer">
                  <Play className="w-5 h-5" />
                </a>
              </Button>
            </div>
          ))}
        </div>
      </section>
      
      {/* Archive */}
      <section>
        <SectionTitle icon={Skull}>Архіви</SectionTitle>
        <div className="space-y-3 mb-5">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
            <Input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Знайти трек..."
              aria-label="Пошук треків"
              className="h-11 pl-10 pr-10 bg-card border-border focus-visible:ring-primary"
            />
            {query && (
              <button
                type="button"
                onClick={() => setQuery('')}
                aria-label="Очистити пошук"
                className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-primary"
              >
                <X className="w-4 h-4" />
              </button>
            )}
          </div>
          <div className="flex gap-2 overflow-x-auto pb-1 [&::-webkit-scrollbar]:hidden" style={{ scrollbarWidth: 'none' }}>
            <MoodButton active={!mood} onClick={() => setMood('')}>Усі</MoodButton>
            {exp?.moods.map((item) => (
              <MoodButton key={item} active={mood === item} onClick={() => setMood(item)}>
                {item}
              </MoodButton>
            ))}
          </div>
        </div>
        <div className="space-y-2">
          {tracks?.filter(t => t.id !== exp?.featured?.id).map(track => (
            <div key={track.id} className="flex items-center justify-between py-3 border-b border-border/30 hover:bg-secondary/20 px-2 transition-colors">
              <div className="flex flex-col min-w-0 pr-4">
                <span className="text-sm font-medium truncate">{track.title}</span>
                <span className="text-[10px] text-muted-foreground mt-1 tracking-wider uppercase truncate">
                  {track.moods.join(' • ')}
                </span>
              </div>
              <div className="flex items-center shrink-0">
                {track.youtubeMusicUrl && (
                  <Button variant="ghost" size="icon" className="h-10 w-10 text-muted-foreground hover:text-primary" asChild>
                    <a href={track.youtubeMusicUrl} target="_blank" rel="noreferrer" title="YouTube Music">
                      <Headphones className="w-4 h-4" />
                    </a>
                  </Button>
                )}
                {track.youtubeUrl && (
                  <Button variant="ghost" size="icon" className="h-10 w-10 text-muted-foreground hover:text-primary" asChild>
                    <a href={track.youtubeUrl} target="_blank" rel="noreferrer" title="YouTube">
                      <Play className="w-5 h-5" />
                    </a>
                  </Button>
                )}
              </div>
            </div>
          ))}
          {tracks?.filter(t => t.id !== exp?.featured?.id).length === 0 && (
            <div className="py-8 text-center border border-dashed border-border text-sm text-muted-foreground font-serif">
              У цих архівах нічого не знайдено.
            </div>
          )}
        </div>
      </section>
    </div>
  );
}

function MoodButton({ active, onClick, children }: { active: boolean; onClick: () => void; children: React.ReactNode }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "shrink-0 border px-3 py-2 text-[10px] font-bold uppercase tracking-wider transition-colors",
        active
          ? "border-primary bg-primary/15 text-primary"
          : "border-border bg-card text-muted-foreground hover:border-primary/50 hover:text-foreground",
      )}
    >
      {children}
    </button>
  );
}

function OracleTab() {
  const [input, setInput] = useState('');
  const [chatLog, setChatLog] = useState<{id: string, role: 'user' | 'oracle', text: string}[]>([
    { id: 'welcome', role: 'oracle', text: "Промов свою правду в порожнечу. Я — Оракул Полеглих. Питай мене про лор, звучання або сенс." }
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
    setInput('');
    const tempId = Date.now().toString();
    
    setChatLog(prev => [...prev, { id: `u-${tempId}`, role: 'user', text: msg }]);
    
    askMutation.mutate({ data: { message: msg } }, {
      onSuccess: (res) => {
        setChatLog(prev => [...prev, { id: `o-${Date.now()}`, role: 'oracle', text: res.reply }]);
      },
      onError: () => {
        setChatLog(prev => [...prev, { id: `o-err-${Date.now()}`, role: 'oracle', text: "Порожнеча не дає відповіді. Спробуй пізніше." }]);
      }
    });
  };

  return (
    <div className="flex flex-col h-[calc(100vh-140px)] animate-in fade-in duration-500 relative">
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-primary/10 via-background to-background pointer-events-none"></div>
      
      <div className="flex-1 overflow-y-auto p-4 space-y-6 relative z-10" ref={scrollRef}>
        {chatLog.map((msg) => (
          <div key={msg.id} className={cn("flex flex-col max-w-[85%]", msg.role === 'user' ? "ml-auto items-end" : "mr-auto items-start")}>
            <span className="text-[10px] text-muted-foreground uppercase tracking-widest mb-1 px-1">
              {msg.role === 'user' ? 'Ти' : 'Оракул'}
            </span>
            <div className={cn(
              "p-3 text-sm leading-relaxed relative",
              msg.role === 'user' 
                ? "bg-secondary text-secondary-foreground border border-border rounded-tl-xl rounded-bl-xl rounded-tr-xl" 
                : "bg-primary/10 border border-primary/30 text-primary-foreground rounded-tr-xl rounded-br-xl rounded-tl-xl font-serif font-medium tracking-wide"
            )}>
              {msg.text}
            </div>
          </div>
        ))}
        {askMutation.isPending && (
          <div className="mr-auto items-start flex flex-col max-w-[85%]">
            <div className="p-3 bg-primary/5 border border-primary/20 rounded-tr-xl rounded-br-xl rounded-tl-xl flex gap-2">
              <span className="w-1.5 h-1.5 bg-primary/60 rounded-full animate-bounce"></span>
              <span className="w-1.5 h-1.5 bg-primary/60 rounded-full animate-bounce [animation-delay:0.2s]"></span>
              <span className="w-1.5 h-1.5 bg-primary/60 rounded-full animate-bounce [animation-delay:0.4s]"></span>
            </div>
          </div>
        )}
      </div>

      <div className="p-4 bg-background/80 backdrop-blur-md border-t border-border/50 relative z-10">
        <div className="flex gap-2 relative">
          <Input 
            value={input} 
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && handleSend()}
            placeholder="Покликати відповідь..." 
            className="pr-14 bg-card border-primary/20 focus-visible:ring-primary focus-visible:border-primary font-serif h-12"
            disabled={askMutation.isPending}
          />
          <Button 
            size="icon" 
            className="absolute right-1 top-1 bottom-1 h-10 w-10 bg-transparent text-primary hover:bg-primary/20"
            onClick={handleSend}
            disabled={askMutation.isPending || !input.trim()}
          >
            <Send className="w-5 h-5" />
          </Button>
        </div>
      </div>
    </div>
  );
}

function CovenTab() {
  const { identity } = useAuth();
  const { data: posts, isLoading, refetch } = useListFanPosts();
  const createMutation = useCreateFanPost();
  const hideMutation = useHideFanPost();
  const [msg, setMsg] = useState('');
  const [feedback, setFeedback] = useState('');

  const errorMessage = (error: unknown) => {
    const apiError = error as { data?: { error?: string } };
    return apiError.data?.error ?? 'Не вдалося виконати дію. Спробуйте ще раз.';
  };

  const handlePost = () => {
    if (!msg.trim() || msg.length < 2) return;
    createMutation.mutate({ data: { message: msg } }, {
      onSuccess: () => {
        setMsg('');
        setFeedback('Твій допис з’явився на фан-стіні.');
        refetch();
      },
      onError: (error) => setFeedback(errorMessage(error)),
    });
  };

  const handleHide = (id: number) => {
    hideMutation.mutate({ id }, {
      onSuccess: () => {
        setFeedback('Допис приховано.');
        refetch();
      },
      onError: (error) => setFeedback(errorMessage(error)),
    });
  };

  if (isLoading) return <LoadingState />;

  return (
    <div className="p-4 space-y-6 animate-in fade-in slide-in-from-right-4 duration-500">
      <div className="bg-card border border-border p-4 shadow-sm">
        <h3 className="font-serif text-lg font-bold mb-3 flex items-center gap-2">
          <Flame className="w-5 h-5 text-primary" /> Залиш свій слід
        </h3>
        <Textarea 
          placeholder="Що лунає в твоїх думках?" 
          value={msg}
          onChange={(e) => setMsg(e.target.value)}
          className="bg-background mb-3 focus-visible:ring-primary border-primary/20"
        />
        <div className="flex justify-end">
          <Button 
            onClick={handlePost} 
            disabled={createMutation.isPending || msg.length < 2}
            className="gap-2"
          >
            {createMutation.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : "Проявити"}
            {!createMutation.isPending && <ArrowRight className="w-4 h-4" />}
          </Button>
        </div>
        {feedback && (
          <p role="status" className="mt-3 text-xs text-muted-foreground">
            {feedback}
          </p>
        )}
      </div>

      <div className="space-y-4">
        {posts?.map(post => (
          <div key={post.id} className="p-4 border-b border-border/40 hover:bg-secondary/10 transition-colors">
            <div className="flex justify-between items-start mb-2">
              <span className="font-bold text-sm text-primary tracking-wide">{post.author}</span>
              <div className="flex items-center gap-2">
                <span className="text-[10px] text-muted-foreground font-mono uppercase tracking-wider">
                  {new Date(post.createdAt).toLocaleDateString('uk-UA', { day: 'numeric', month: 'short', year: 'numeric' })}
                </span>
                {identity?.isAdmin && (
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon"
                    className="h-7 w-7 text-muted-foreground hover:text-destructive"
                    aria-label="Приховати допис"
                    title="Приховати допис"
                    disabled={hideMutation.isPending}
                    onClick={() => handleHide(post.id)}
                  >
                    <EyeOff className="h-4 w-4" />
                  </Button>
                )}
              </div>
            </div>
            <p className="text-sm text-foreground/90 whitespace-pre-wrap font-serif leading-relaxed">
              {post.message}
            </p>
          </div>
        ))}
        {posts?.length === 0 && (
          <div className="text-center py-10 text-muted-foreground text-sm font-serif">
            Ковен мовчить. Заговори першим.
          </div>
        )}
      </div>
    </div>
  );
}

function SectionTitle({ children, icon: Icon }: { children: React.ReactNode, icon: any }) {
  return (
    <h2 className="flex items-center gap-2 text-sm uppercase tracking-[0.3em] font-bold text-muted-foreground mb-4 pb-2 border-b border-border/50">
      <Icon className="w-4 h-4 text-primary" />
      {children}
    </h2>
  );
}

function LoadingState() {
  return (
    <div className="flex-1 flex items-center justify-center p-10 h-64">
      <Loader2 className="w-8 h-8 animate-spin text-primary opacity-50" />
    </div>
  );
}