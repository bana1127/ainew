"use client";

import type { ButtonHTMLAttributes } from "react";

type Variant = "primary" | "secondary" | "danger" | "ghost" | "outline";
type Size = "sm" | "md" | "lg";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: Size;
  loading?: boolean;
}

const variantStyles: Record<Variant, React.CSSProperties> = {
  primary: {
    background: "var(--primary)",
    color: "#FFFFFF",
    border: "1px solid transparent",
  },
  secondary: {
    background: "var(--surface)",
    color: "var(--text-main)",
    border: "1px solid var(--border-soft)",
  },
  danger: {
    background: "var(--danger)",
    color: "#FFFFFF",
    border: "1px solid transparent",
  },
  ghost: {
    background: "transparent",
    color: "var(--text-muted)",
    border: "1px solid transparent",
  },
  outline: {
    background: "transparent",
    color: "var(--primary)",
    border: "1px solid var(--primary)",
  },
};

const variantHoverClass: Record<Variant, string> = {
  primary: "hover:opacity-85",
  secondary: "hover:bg-mist",
  danger: "hover:opacity-85",
  ghost: "hover:bg-mist hover:text-ink",
  outline: "hover:bg-primary-soft",
};

const sizeClass: Record<Size, string> = {
  sm: "px-3 py-1.5 text-xs rounded-lg gap-1.5",
  md: "px-4 py-2 text-sm rounded-xl gap-2",
  lg: "px-5 py-2.5 text-sm rounded-xl gap-2",
};

export function Button({
  variant = "primary",
  size = "md",
  loading,
  disabled,
  children,
  className = "",
  style,
  ...props
}: ButtonProps) {
  return (
    <button
      disabled={disabled || loading}
      className={`inline-flex items-center justify-center font-medium transition-all duration-150 disabled:cursor-not-allowed disabled:opacity-50 ${variantHoverClass[variant]} ${sizeClass[size]} ${className}`}
      style={{ ...variantStyles[variant], ...style }}
      {...props}
    >
      {loading && (
        <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-current border-t-transparent" />
      )}
      {children}
    </button>
  );
}
