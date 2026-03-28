import React, { useState } from "react"
import { CyberCard } from "@/components/ui/cyber-card"
import { CyberButton } from "@/components/ui/cyber-button"
import { Play, Square, Link as LinkIcon, Cpu } from "lucide-react"
import { useStartBot, useStopBot, getGetBotStatusQueryKey, getGetBotStatsQueryKey } from "@workspace/api-client-react"
import { useQueryClient } from "@tanstack/react-query"
import { useToast } from "@/hooks/use-toast"

interface ControlPanelProps {
  isRunning: boolean;
  activeVideoUrl?: string;
  activeWorkers?: number;
}

export function ControlPanel({ isRunning, activeVideoUrl, activeWorkers }: ControlPanelProps) {
  const [url, setUrl] = useState("")
  const [workers, setWorkers] = useState(300)
  const queryClient = useQueryClient()
  const { toast } = useToast()

  const startMutation = useStartBot({
    mutation: {
      onSuccess: (data) => {
        queryClient.invalidateQueries({ queryKey: getGetBotStatusQueryKey() })
        queryClient.invalidateQueries({ queryKey: getGetBotStatsQueryKey() })
        if (data.success) {
          toast({
            title: "SYSTEM ONLINE",
            description: data.message,
            className: "bg-primary/20 border-primary text-primary",
          })
        } else {
          toast({
            title: "ERROR",
            description: data.message,
            variant: "destructive",
          })
        }
      },
      onError: (err) => {
        toast({
          title: "SYSTEM FAILURE",
          description: err.message,
          variant: "destructive",
        })
      }
    }
  })

  const stopMutation = useStopBot({
    mutation: {
      onSuccess: (data) => {
        queryClient.invalidateQueries({ queryKey: getGetBotStatusQueryKey() })
        queryClient.invalidateQueries({ queryKey: getGetBotStatsQueryKey() })
        toast({
          title: "SYSTEM HALTED",
          description: data.message,
          className: "bg-destructive/20 border-destructive text-destructive",
        })
      }
    }
  })

  const handleStart = () => {
    if (!url) {
      toast({
        title: "INPUT REQUIRED",
        description: "Vui lòng nhập URL TikTok hợp lệ.",
        variant: "destructive",
      })
      return;
    }
    startMutation.mutate({ data: { videoUrl: url, workers } })
  }

  const handleStop = () => {
    stopMutation.mutate()
  }

  const displayUrl = isRunning ? (activeVideoUrl || url) : url;
  const displayWorkers = isRunning ? (activeWorkers || workers) : workers;

  return (
    <CyberCard className="flex flex-col gap-6">
      <div>
        <h2 className="text-xl font-display text-foreground border-b border-border/50 pb-2 mb-4 flex items-center gap-2">
          <Cpu className="w-5 h-5 text-primary" />
          Tham Số Hệ Thống
        </h2>
        
        <div className="space-y-4">
          <div className="space-y-2">
            <label className="text-xs font-display text-primary uppercase tracking-wider flex items-center gap-2">
              <LinkIcon className="w-3 h-3" />
              Target URL
            </label>
            <input
              type="text"
              value={displayUrl}
              onChange={(e) => setUrl(e.target.value)}
              disabled={isRunning}
              placeholder="https://tiktok.com/@user/video/..."
              className="w-full bg-input/50 border border-border text-foreground px-4 py-3 font-mono text-sm focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition-all disabled:opacity-50 disabled:cursor-not-allowed"
            />
          </div>

          <div className="space-y-4">
            <div className="flex justify-between items-end">
              <label className="text-xs font-display text-secondary uppercase tracking-wider">
                Concurrency Threads
              </label>
              <span className="text-xl font-bold font-mono text-secondary neon-text-secondary">
                {displayWorkers}
              </span>
            </div>
            <input
              type="range"
              min="50"
              max="1000"
              step="50"
              value={displayWorkers}
              onChange={(e) => setWorkers(parseInt(e.target.value))}
              disabled={isRunning}
              className="cyber-slider disabled:opacity-50 disabled:cursor-not-allowed"
            />
            <div className="flex justify-between text-xs text-muted-foreground font-mono">
              <span>50 MIN</span>
              <span>1000 MAX</span>
            </div>
          </div>
        </div>
      </div>

      <div className="pt-4 grid grid-cols-2 gap-4">
        {!isRunning ? (
          <CyberButton 
            variant="primary" 
            className="col-span-2"
            onClick={handleStart}
            isLoading={startMutation.isPending}
          >
            <Play className="w-5 h-5" />
            Bắt Đầu Tấn Công
          </CyberButton>
        ) : (
          <CyberButton 
            variant="destructive" 
            className="col-span-2"
            onClick={handleStop}
            isLoading={stopMutation.isPending}
          >
            <Square className="w-5 h-5 fill-current" />
            Hủy Bỏ Chuỗi Lệnh
          </CyberButton>
        )}
      </div>
    </CyberCard>
  )
}
