import React from "react"
import { CyberCard } from "@/components/ui/cyber-card"
import { Activity, Eye, Zap, Target, TrendingUp, Clock, AlertTriangle, CheckCircle2 } from "lucide-react"
import { BotStats } from "@workspace/api-client-react"

interface StatsGridProps {
  stats?: BotStats;
  isLoading: boolean;
}

export function StatsGrid({ stats, isLoading }: StatsGridProps) {
  
  const defaultStats = {
    totalViews: 0,
    viewsPerSecond: 0,
    peakSpeed: 0,
    viewsPerMinute: 0,
    viewsPerHour: 0,
    successRate: 0,
    successfulRequests: 0,
    failedRequests: 0,
    elapsedTime: 0,
  }

  const s = stats || defaultStats;

  const formatTime = (seconds: number) => {
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    const sec = Math.floor(seconds % 60);
    return `${h.toString().padStart(2, '0')}:${m.toString().padStart(2, '0')}:${sec.toString().padStart(2, '0')}`;
  };

  const StatItem = ({ label, value, icon: Icon, colorClass, highlight = false }: any) => (
    <CyberCard glow={highlight} variant={highlight ? "primary" : "default"} className="flex flex-col justify-between overflow-hidden relative">
      <div className="flex justify-between items-start mb-4 relative z-10">
        <span className="text-sm font-display text-muted-foreground uppercase tracking-wider">{label}</span>
        <Icon className={`w-5 h-5 ${colorClass}`} />
      </div>
      <div className="relative z-10">
        <span className={`text-3xl font-bold ${highlight ? 'neon-text-primary text-primary' : 'text-foreground'}`}>
          {isLoading ? "---" : value}
        </span>
      </div>
      {highlight && (
        <div className="absolute inset-0 bg-primary/5 pattern-dots pointer-events-none" />
      )}
    </CyberCard>
  );

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      {/* Primary Highlight Card */}
      <div className="sm:col-span-2 lg:col-span-2">
        <CyberCard variant="primary" glow className="h-full flex flex-col justify-center items-center text-center py-8">
          <Eye className="w-12 h-12 text-primary mb-4 animate-pulse opacity-80" />
          <h3 className="text-sm font-display text-primary uppercase tracking-[0.3em] mb-2">Tổng View Đã Gửi</h3>
          <div className="text-6xl md:text-7xl font-bold text-primary neon-text-primary tracking-tight">
            {isLoading ? "0" : s.totalViews.toLocaleString()}
          </div>
          
          <div className="mt-6 flex items-center gap-6 text-sm text-muted-foreground font-display">
            <span className="flex items-center gap-2">
              <Clock className="w-4 h-4 text-primary" />
              {formatTime(s.elapsedTime)}
            </span>
            <span className="flex items-center gap-2">
              <Target className="w-4 h-4 text-secondary" />
              {s.successRate.toFixed(1)}% SUCCESS
            </span>
          </div>
        </CyberCard>
      </div>

      <StatItem 
        label="Tốc Độ Hiện Tại" 
        value={`${s.viewsPerSecond.toFixed(1)} /s`} 
        icon={Activity} 
        colorClass="text-primary"
      />
      
      <StatItem 
        label="Tốc Độ Đỉnh" 
        value={`${s.peakSpeed.toFixed(1)} /s`} 
        icon={Zap} 
        colorClass="text-secondary"
      />
      
      <StatItem 
        label="Dự Kiến / Phút" 
        value={s.viewsPerMinute.toFixed(0)} 
        icon={TrendingUp} 
        colorClass="text-foreground"
      />
      
      <StatItem 
        label="Dự Kiến / Giờ" 
        value={s.viewsPerHour.toFixed(0)} 
        icon={TrendingUp} 
        colorClass="text-foreground"
      />

      <StatItem 
        label="Request Thành Công" 
        value={s.successfulRequests.toLocaleString()} 
        icon={CheckCircle2} 
        colorClass="text-primary"
      />
      
      <StatItem 
        label="Request Thất Bại" 
        value={s.failedRequests.toLocaleString()} 
        icon={AlertTriangle} 
        colorClass="text-destructive"
      />
    </div>
  )
}
