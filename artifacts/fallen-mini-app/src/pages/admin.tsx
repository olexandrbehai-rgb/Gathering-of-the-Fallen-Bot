import {
  getGetUsageSummaryQueryKey,
  useGetUsageSummary,
} from '@workspace/api-client-react';
import { useAuth } from '@/lib/auth';
import { Redirect } from 'wouter';
import { Loader2, ShieldAlert, Activity, DollarSign, Clock, AlertTriangle } from 'lucide-react';

export default function Admin() {
  const { identity, isLoading } = useAuth();
  
  const { data: usage, isLoading: isUsageLoading } = useGetUsageSummary({
    query: {
      enabled: !!identity?.isAdmin,
      queryKey: getGetUsageSummaryQueryKey(),
    }
  });

  if (isLoading) {
    return (
      <div className="flex-1 flex items-center justify-center h-full">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
      </div>
    );
  }

  if (!identity?.isAdmin) {
    return <Redirect to="/" />;
  }

  return (
    <div className="p-4 space-y-6 animate-in fade-in duration-500">
      <div className="flex items-center gap-3 border-b border-border/50 pb-4">
        <ShieldAlert className="w-8 h-8 text-primary shrink-0" />
        <div>
          <h1 className="font-serif text-2xl font-bold tracking-wider">Контроль Оракула</h1>
          <p className="text-xs text-muted-foreground uppercase tracking-widest">Панель адміністратора</p>
        </div>
      </div>

      {isUsageLoading ? (
        <div className="flex justify-center py-10">
          <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
        </div>
      ) : (
        <div className="grid grid-cols-2 gap-4">
          <StatCard 
            icon={Activity} 
            label="Сьогоднішні запити" 
            value={usage?.todayRequests.toString() || '0'} 
          />
          <StatCard 
            icon={Activity} 
            label="Запити за місяць" 
            value={usage?.monthRequests.toString() || '0'} 
          />
          <StatCard 
            icon={DollarSign} 
            label="Орієнтовна вартість" 
            value={`$${usage?.monthEstimatedUsd.toFixed(2) || '0.00'}`} 
            highlight
          />
          <StatCard 
            icon={Clock} 
            label="Голосові секунди" 
            value={usage?.voiceSeconds.toString() || '0'} 
          />
          <div className="col-span-2">
            <StatCard 
              icon={AlertTriangle} 
              label="Рівень помилок" 
              value={`${((usage?.errorRate || 0) * 100).toFixed(1)}%`} 
              danger={usage && usage.errorRate > 0.05}
            />
          </div>
        </div>
      )}
    </div>
  );
}

function StatCard({ icon: Icon, label, value, highlight, danger }: { icon: any, label: string, value: string, highlight?: boolean, danger?: boolean }) {
  return (
    <div className={`p-4 bg-card border ${danger ? 'border-destructive/50 bg-destructive/10' : highlight ? 'border-primary/50' : 'border-border'} flex flex-col gap-2`}>
      <div className="flex items-center gap-2 text-muted-foreground">
        <Icon className={`w-4 h-4 ${danger ? 'text-destructive' : highlight ? 'text-primary' : ''}`} />
        <span className="text-[10px] uppercase tracking-widest font-bold">{label}</span>
      </div>
      <div className={`font-serif text-2xl font-bold ${danger ? 'text-destructive' : highlight ? 'text-primary' : 'text-foreground'}`}>
        {value}
      </div>
    </div>
  );
}