"use client";

import { forwardRef, type TextareaHTMLAttributes } from "react";

interface TextareaProps extends TextareaHTMLAttributes<HTMLTextAreaElement> {
  label?: string;
  error?: string;
}

export const Textarea = forwardRef<HTMLTextAreaElement, TextareaProps>(function Textarea(
  { label, error, id, className = "", style, ...props },
  ref,
) {
  const inputId = id ?? (label ? label.toLowerCase().replace(/\s+/g, "-") : undefined);
  return (
    <div className="flex flex-col gap-1">
      {label && (
        <label htmlFor={inputId} className="text-sm font-medium"
          style={{ color: "var(--text-main)" }}>
          {label}
        </label>
      )}
      <textarea
        ref={ref}
        id={inputId}
        className={`resize-vertical rounded-xl px-3 py-2 text-sm transition-all duration-150 focus:outline-none disabled:cursor-not-allowed ${className}`}
        style={{
          background: "var(--surface)",
          color: "var(--text-main)",
          border: error ? "1px solid var(--danger)" : "1px solid var(--border-soft)",
          ...style,
        }}
        onFocus={(e) => {
          e.currentTarget.style.borderColor = "var(--primary)";
          e.currentTarget.style.boxShadow = "0 0 0 3px rgba(124,108,242,0.12)";
          props.onFocus?.(e);
        }}
        onBlur={(e) => {
          e.currentTarget.style.borderColor = error ? "var(--danger)" : "var(--border-soft)";
          e.currentTarget.style.boxShadow = "none";
          props.onBlur?.(e);
        }}
        {...props}
      />
      {error && <p className="text-xs" style={{ color: "var(--danger)" }}>{error}</p>}
    </div>
  );
});
