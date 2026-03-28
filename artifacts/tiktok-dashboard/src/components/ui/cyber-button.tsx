import * as React from "react"
import { cn } from "@/lib/utils"
import { motion, HTMLMotionProps } from "framer-motion"

interface CyberButtonProps extends HTMLMotionProps<"button"> {
  variant?: "primary" | "secondary" | "destructive" | "outline";
  isLoading?: boolean;
}

export const CyberButton = React.forwardRef<HTMLButtonElement, CyberButtonProps>(
  ({ className, variant = "primary", isLoading, children, disabled, ...props }, ref) => {
    
    const variants = {
      primary: "bg-primary/10 border-primary text-primary hover:bg-primary/20 hover:shadow-[0_0_20px_hsl(var(--primary)/0.4)]",
      secondary: "bg-secondary/10 border-secondary text-secondary hover:bg-secondary/20 hover:shadow-[0_0_20px_hsl(var(--secondary)/0.4)]",
      destructive: "bg-destructive/10 border-destructive text-destructive hover:bg-destructive/20 hover:shadow-[0_0_20px_hsl(var(--destructive)/0.4)]",
      outline: "bg-transparent border-border text-foreground hover:bg-white/5 hover:border-primary/50 hover:text-primary",
    }

    return (
      <motion.button
        ref={ref}
        whileHover={{ scale: disabled ? 1 : 1.02 }}
        whileTap={{ scale: disabled ? 1 : 0.98 }}
        disabled={disabled || isLoading}
        className={cn(
          "relative group px-6 py-3 font-display font-bold tracking-widest uppercase border transition-all duration-300",
          "disabled:opacity-50 disabled:cursor-not-allowed",
          variants[variant],
          className
        )}
        {...props}
      >
        {/* Decorative corner cut effect */}
        <div className="absolute top-0 left-0 w-2 h-2 border-t-2 border-l-2 border-current opacity-50 group-hover:w-full group-hover:h-full group-hover:opacity-20 transition-all duration-500 ease-out z-0" />
        <div className="absolute bottom-0 right-0 w-2 h-2 border-b-2 border-r-2 border-current opacity-50 group-hover:w-full group-hover:h-full group-hover:opacity-20 transition-all duration-500 ease-out z-0" />
        
        <span className="relative z-10 flex items-center justify-center gap-2">
          {isLoading ? (
            <span className="flex items-center gap-2">
              <span className="animate-spin h-4 w-4 border-2 border-current border-t-transparent rounded-full" />
              PROCESSING...
            </span>
          ) : children}
        </span>
      </motion.button>
    )
  }
)
CyberButton.displayName = "CyberButton"
