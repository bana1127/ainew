import type { LucideIcon } from "lucide-react";

type Tone = "success" | "warning" | "danger" | "neutral" | "primary";

const toneIconStyles: Record<Tone, React.CSSProperties> = {
  success: { background: "var(--success-soft)", color: "var(--success)" },
  warning: { background: "var(--warning-soft)", color: "var(--warning)" },
  danger: { background: "var(--danger-soft)", color: "var(--danger)" },
  neutral: { background: "var(--border-soft)", color: "var(--text-muted)" },
  primary: { background: "var(--primary-soft)", color: "var(--primary)" },
};

export function StatCard({
  icon: Icon,
  label,
  value,
  tone = "neutral",
}: {
  icon: LucideIcon;
  label: string;
  value: string;
  tone?: Tone;
}) {
  return (
    <div className="rounded-2xl p-5 transition-shadow hover:shadow-card-hover"
      style={{
        background: "var(--surface)",
        border: "1px solid var(--border-soft)",
        boxShadow: "0 1px 4px 0 rgba(31,31,36,0.05)",
      }}>
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-xs font-medium truncate" style={{ color: "var(--text-muted)" }}>
            {label}
          </p>
          <p className="mt-2 text-2xl font-semibold tracking-tight" style={{ color: "var(--text-main)" }}>
            {value}
          </p>
        </div>
        <div className="rounded-xl p-2.5 shrink-0" style={toneIconStyles[tone]}>
          <Icon className="h-4 w-4" aria-hidden="true" />
        </div>
      </div>
    </div>
  );
}
