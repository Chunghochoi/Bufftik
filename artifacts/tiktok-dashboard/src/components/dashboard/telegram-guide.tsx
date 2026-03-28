import React from "react"
import { CyberCard } from "@/components/ui/cyber-card"
import { Terminal, Send } from "lucide-react"

export function TelegramGuide() {
  return (
    <CyberCard variant="secondary" className="flex flex-col h-full bg-black/60">
      <div className="flex items-center gap-2 border-b border-border/50 pb-3 mb-4">
        <Terminal className="w-5 h-5 text-secondary" />
        <h2 className="text-lg font-display text-secondary">Telegram Override</h2>
      </div>
      
      <div className="flex-1 font-mono text-xs sm:text-sm space-y-3 text-muted-foreground">
        <p className="text-foreground/80 mb-4">
          Hệ thống có thể được điều khiển từ xa thông qua kết nối Telegram Bot an toàn.
        </p>
        
        <div className="space-y-2">
          <div className="flex gap-3 items-start">
            <span className="text-secondary font-bold shrink-0">/start_bot</span>
            <span className="break-all">&lt;url&gt; Kích hoạt bot với URL mục tiêu</span>
          </div>
          <div className="flex gap-3 items-start">
            <span className="text-primary font-bold shrink-0">/stop_bot</span>
            <span>Dừng tất cả tiến trình đang chạy</span>
          </div>
          <div className="flex gap-3 items-start">
            <span className="text-primary font-bold shrink-0">/stats</span>
            <span>Trích xuất dữ liệu hiệu suất hiện tại</span>
          </div>
          <div className="flex gap-3 items-start">
            <span className="text-primary font-bold shrink-0">/status</span>
            <span>Kiểm tra trạng thái hoạt động của lõi</span>
          </div>
          <div className="flex gap-3 items-start">
            <span className="text-primary font-bold shrink-0">/help</span>
            <span>Hiển thị tài liệu hướng dẫn</span>
          </div>
        </div>
      </div>

      <div className="mt-6 pt-4 border-t border-border/30 flex items-center justify-between text-xs text-secondary/70">
        <span className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-secondary animate-pulse" />
          CONNECTION SECURE
        </span>
        <Send className="w-4 h-4" />
      </div>
    </CyberCard>
  )
}
