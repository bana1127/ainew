"use client";

import { forwardRef, type SelectHTMLAttributes } from "react";

export interface SelectOption {
  value: string;
  label: string;
}

interface SelectProps extends SelectHTMLAttributes<HTMLSelectElement> {
  label?: string;
  error?: string;
  options: SelectOption[];
  placeholder?: string;
}

export const Select = forwardRef<HTMLSelectElement, SelectProps>(function Select(
  { label, error, id, options, placeholder, className = "", style, ...props },
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
      <select
        ref={ref}
        id={inputId}
        className={`rounded-xl px-3 py-2 text-sm transition-all duration-150 focus:outline-none disabled:cursor-not-allowed ${className}`}
        style={{
          background: "var(--surface)",
          color: "var(--text-main)",
          border: error ? "1px solid var(--danger)" : "1px solid var(--border-soft)",
          ...style,
        }}
        {...props}
      >
        {placeholder !== undefined && <option value="">{placeholder}</option>}
        {options.map((opt) => (
          <option key={opt.value} value={opt.value}>
            {opt.label}
          </option>
        ))}
      </select>
      {error && <p className="text-xs" style={{ color: "var(--danger)" }}>{error}</p>}
    </div>
  );
});
