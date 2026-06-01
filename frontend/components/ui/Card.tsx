import type { ReactNode } from "react";

interface CardProps {
  children: ReactNode;
  className?: string;
  padding?: "none" | "sm" | "md" | "lg";
}

const paddingClass = {
  none: "",
  sm: "p-4",
  md: "p-5",
  lg: "p-6",
};

export function Card({ children, className = "", padding = "md" }: CardProps) {
  return (
    <div
      className={`rounded-2xl ${paddingClass[padding]} ${className}`}
      style={{
        background: "var(--surface)",
        border: "1px solid var(--border-soft)",
        boxShadow: "0 1px 4px 0 rgba(31,31,36,0.05)",
      }}
    >
      {children}
    </div>
  );
}
