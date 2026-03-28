import React from "react"
import { useGetBotStatus, useGetBotStats } from "@workspace/api-client-react"
import { StatsGrid } from "@/components/dashboard/stats-grid"
import { ControlPanel } from "@/components/dashboard/control-panel"
import { TelegramGuide } from "@/components/dashboard/telegram-guide"
import { motion } from "framer-motion"
import { ShieldAlert, ShieldCheck } from "lucide-react"

export default function Dashboard() {
  // Poll status every 2 seconds to know if we should poll stats
  const { data: statusData, isLoading: isStatusLoading } = useGetBotStatus({
    query: { refetchInterval: 2000 }
  });

  const isRunning = statusData?.isRunning || false;

  // Poll stats only if running, otherwise just fetch once
  const { data: statsData, isLoading: isStatsLoading } = useGetBotStats({
    query: { refetchInterval: isRunning ? 2000 : false }
  });

  const bgImage = `${import.meta.env.BASE_URL}images/cyber-bg.png`;

  return (
    <div className="min-h-screen relative overflow-hidden bg-background selection:bg-primary/30 selection:text-primary">
      {/* Background with scanlines */}
      <div 
        className="absolute inset-0 z-0 opacity-20 bg-cover bg-center bg-no-repeat mix-blend-luminosity"
        style={{ backgroundImage: `url(${bgImage})` }}
      />
      <div className="absolute inset-0 z-0 scanlines opacity-30" />
      
      {/* Subtle vignette/vignette shadow */}
      <div className="absolute inset-0 z-0 shadow-[inset_0_0_150px_rgba(0,0,0,0.9)] pointer-events-none" />

      <div className="relative z-10 container mx-auto px-4 py-8 max-w-7xl">
        
        {/* Header Section */}
        <header className="flex flex-col md:flex-row justify-between items-center mb-8 pb-6 border-b border-border/50 gap-6">
          <motion.div 
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            className="flex items-center gap-4"
          >
            <div className="w-12 h-12 bg-primary/10 border-2 border-primary flex items-center justify-center neon-border-primary">
              <ShieldAlert className="w-6 h-6 text-primary" />
            </div>
            <div>
              <h1 className="text-3xl font-display font-black tracking-widest text-white glitch-wrapper" data-text="SPY VIEW BOT PRO">
                SPY VIEW BOT PRO
              </h1>
              <p className="text-primary font-mono text-sm tracking-[0.2em] opacity-80 uppercase">
                Tactical Engagement Protocol
              </p>
            </div>
          </motion.div>

          <motion.div 
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            className="flex items-center gap-4 bg-black/40 border border-border px-6 py-3"
          >
            <div className="flex flex-col items-end">
              <span className="text-xs text-muted-foreground font-display uppercase tracking-widest">
                System Status
              </span>
              <span className={`font-mono font-bold text-lg ${isRunning ? 'text-primary neon-text-primary' : 'text-destructive neon-text-destructive'}`}>
                {isStatusLoading ? "SCANNING..." : (isRunning ? "ONLINE / ACTIVE" : "OFFLINE / STANDBY")}
              </span>
            </div>
            {isRunning ? (
              <ShieldCheck className="w-8 h-8 text-primary animate-pulse" />
            ) : (
              <div className="w-8 h-8 border-2 border-destructive rounded-full flex items-center justify-center">
                <div className="w-2 h-2 bg-destructive rounded-full" />
              </div>
            )}
          </motion.div>
        </header>

        {/* Target Info Bar (shows when running) */}
        {isRunning && statusData?.videoId && (
          <motion.div 
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            className="mb-6 bg-primary/5 border border-primary/30 p-4 flex flex-col sm:flex-row justify-between items-center gap-4 font-mono text-sm"
          >
            <div className="flex items-center gap-2">
              <span className="text-primary">TARGET ID:</span>
              <span className="text-foreground tracking-widest">{statusData.videoId}</span>
            </div>
            <div className="flex items-center gap-2 text-muted-foreground truncate max-w-xl">
              <span>URL:</span>
              <a href={statusData.videoUrl} target="_blank" rel="noreferrer" className="hover:text-primary transition-colors truncate">
                {statusData.videoUrl}
              </a>
            </div>
          </motion.div>
        )}

        {/* Main Dashboard Layout */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          
          {/* Left Column: Controls & Telegram */}
          <motion.div 
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
            className="lg:col-span-4 flex flex-col gap-6"
          >
            <ControlPanel 
              isRunning={isRunning} 
              activeVideoUrl={statusData?.videoUrl}
              activeWorkers={statsData?.workers}
            />
            <div className="flex-grow">
              <TelegramGuide />
            </div>
          </motion.div>

          {/* Right Column: Real-time Stats */}
          <motion.div 
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
            className="lg:col-span-8"
          >
            <StatsGrid stats={statsData} isLoading={isStatsLoading} />
          </motion.div>
          
        </div>

      </div>
    </div>
  )
}
