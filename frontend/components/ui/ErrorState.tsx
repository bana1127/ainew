"use client";

import { AlertCircle, RefreshCw } from "lucide-react";

interface ErrorStateProps {
  message: string;
  onRetry?: () => void;
}

export function ErrorState({ message, onRetry }: ErrorStateProps) {
  return (
    <div className="flex items-start gap-3 rounded-xl p-4"
      style={{
        background: "var(--danger-soft)",
        border: "1px solid rgba(185,74,72,0.15)",
      }}>
      <AlertCircle className="h-4 w-4 flex-shrink-0 mt-0.5" style={{ color: "var(--danger)" }} />
      <div className="flex-1 min-w-0">
        <p className="text-sm" style={{ color: "var(--danger)" }}>{message}</p>
        {onRetry && (
          <button
            onClick={onRetry}
            className="mt-2 flex items-center gap-1 text-xs font-medium hover:opacity-75 transition-opacity"
            style={{ color: "var(--danger)" }}
          >
            <RefreshCw className="h-3 w-3" />
            다시 시도
          </button>
        )}
      </div>
    </div>
  );
}
