"use client";

import type { ReactNode } from "react";

type Variant = "default" | "success" | "warning" | "danger" | "info" | "primary";

interface BadgeProps {
  children: ReactNode;
  variant?: Variant;
}

const variantStyles: Record<Variant, React.CSSProperties> = {
  default: {
    background: "var(--border-soft)",
    color: "var(--text-muted)",
  },
  success: {
    background: "var(--success-soft)",
    color: "var(--success)",
  },
  warning: {
    background: "var(--warning-soft)",
    color: "var(--warning)",
  },
  danger: {
    background: "var(--danger-soft)",
    color: "var(--danger)",
  },
  info: {
    background: "var(--primary-soft)",
    color: "var(--primary)",
  },
  primary: {
    background: "var(--primary-soft)",
    color: "var(--primary)",
  },
};

export function Badge({ children, variant = "default" }: BadgeProps) {
  return (
    <span
      className="inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium"
      style={variantStyles[variant]}
    >
      {children}
    </span>
  );
}
