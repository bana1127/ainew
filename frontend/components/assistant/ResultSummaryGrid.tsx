interface GridItem {
  label: string;
  value: string | number | null | undefined;
  tone?: "default" | "success" | "warning" | "danger";
}

const TONE_STYLES: Record<string, React.CSSProperties> = {
  default: { background: "var(--surface-soft)", color: "var(--text-main)" },
  success: { background: "var(--success-soft)", color: "var(--success)" },
  warning: { background: "var(--warning-soft)", color: "var(--warning)" },
  danger: { background: "var(--danger-soft)", color: "var(--danger)" },
};

export function ResultSummaryGrid({ items, cols = 4 }: { items: GridItem[]; cols?: 2 | 3 | 4 }) {
  const colClass = { 2: "sm:grid-cols-2", 3: "sm:grid-cols-3", 4: "sm:grid-cols-4" }[cols];
  return (
    <div className={`grid grid-cols-2 ${colClass} gap-3`}>
      {items.map(({ label, value, tone = "default" }) => (
        <div
          key={label}
          className="rounded-xl p-3 text-center"
          style={{ border: "1px solid var(--border-soft)", ...TONE_STYLES[tone] }}
        >
          <div className="text-xl font-semibold" style={{ color: TONE_STYLES[tone].color }}>
            {value ?? "-"}
          </div>
          <div className="text-xs mt-0.5" style={{ color: "var(--text-muted)" }}>
            {label}
          </div>
        </div>
      ))}
    </div>
  );
}
