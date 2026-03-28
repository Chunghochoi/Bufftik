import * as React from "react"
import { cn } from "@/lib/utils"
import { motion } from "framer-motion"

interface CyberCardProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: "default" | "primary" | "secondary" | "destructive";
  glow?: boolean;
}

export const CyberCard = React.forwardRef<HTMLDivElement, CyberCardProps>(
  ({ className, variant = "default", glow = false, children, ...props }, ref) => {
    
    const borders = {
      default: "border-border/50",
      primary: "border-primary/50",
      secondary: "border-secondary/50",
      destructive: "border-destructive/50",
    }

    const glows = {
      default: "",
      primary: "shadow-[0_0_15px_hsl(var(--primary)/0.15)]",
      secondary: "shadow-[0_0_15px_hsl(var(--secondary)/0.15)]",
      destructive: "shadow-[0_0_15px_hsl(var(--destructive)/0.15)]",
    }

    return (
      <motion.div
        ref={ref}
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className={cn(
          "relative bg-card/80 backdrop-blur-md p-6 border",
          borders[variant],
          glow ? glows[variant] : "",
          "before:content-[''] before:absolute before:top-0 before:left-0 before:w-2 before:h-2 before:border-t-2 before:border-l-2",
          "after:content-[''] after:absolute after:bottom-0 after:right-0 after:w-2 after:h-2 after:border-b-2 after:border-r-2",
          variant === "primary" ? "before:border-primary after:border-primary" : 
          variant === "secondary" ? "before:border-secondary after:border-secondary" :
          variant === "destructive" ? "before:border-destructive after:border-destructive" :
          "before:border-border after:border-border",
          className
        )}
        {...props}
      >
        {/* Subtle decorative background element */}
        <div className="absolute top-0 right-0 w-32 h-32 bg-gradient-to-bl from-white/[0.02] to-transparent pointer-events-none" />
        {children}
      </motion.div>
    )
  }
)
CyberCard.displayName = "CyberCard"
