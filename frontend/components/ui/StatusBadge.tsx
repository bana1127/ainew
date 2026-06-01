"use client";

type StatusKey =
  | "active" | "inactive" | "graduated" | "paused"
  | "draft" | "generated" | "confirmed" | "archived"
  | "pending" | "valid" | "need_check" | "invalid"
  | "unmatched" | "matched" | "excluded"
  | "paid" | "partial" | "unpaid";

interface StatusConfig {
  label: string;
  style: React.CSSProperties;
}

const STATUS_MAP: Record<StatusKey, StatusConfig> = {
  active:    { label: "활동중",    style: { background: "var(--success-soft)", color: "var(--success)" } },
  inactive:  { label: "비활성",   style: { background: "var(--border-soft)",  color: "var(--text-muted)" } },
  graduated: { label: "졸업",     style: { background: "var(--border-soft)",  color: "var(--text-muted)" } },
  paused:    { label: "휴면",     style: { background: "var(--border-soft)",  color: "var(--text-muted)" } },

  draft:     { label: "초안",     style: { background: "var(--border-soft)",  color: "var(--text-muted)" } },
  generated: { label: "생성됨",   style: { background: "var(--primary-soft)", color: "var(--primary)" } },
  confirmed: { label: "확정",     style: { background: "var(--success-soft)", color: "var(--success)" } },
  archived:  { label: "보관",     style: { background: "var(--border-soft)",  color: "var(--text-muted)" } },

  pending:   { label: "대기",     style: { background: "var(--border-soft)",  color: "var(--text-muted)" } },
  valid:     { label: "적합",     style: { background: "var(--success-soft)", color: "var(--success)" } },
  need_check:{ label: "확인 필요", style: { background: "var(--warning-soft)", color: "var(--warning)" } },
  invalid:   { label: "부적합",   style: { background: "var(--danger-soft)",  color: "var(--danger)" } },

  unmatched: { label: "미매칭",   style: { background: "var(--border-soft)",  color: "var(--text-muted)" } },
  matched:   { label: "매칭됨",   style: { background: "var(--success-soft)", color: "var(--success)" } },
  excluded:  { label: "제외",     style: { background: "var(--border-soft)",  color: "var(--text-muted)" } },

  paid:      { label: "납부 완료", style: { background: "var(--success-soft)", color: "var(--success)" } },
  partial:   { label: "부분 납부", style: { background: "var(--warning-soft)", color: "var(--warning)" } },
  unpaid:    { label: "미납",     style: { background: "var(--danger-soft)",  color: "var(--danger)" } },
};

const DEFAULT_STYLE: React.CSSProperties = {
  background: "var(--border-soft)",
  color: "var(--text-muted)",
};

interface StatusBadgeProps {
  status: string;
  customLabel?: string;
}

export function StatusBadge({ status, customLabel }: StatusBadgeProps) {
  const config = STATUS_MAP[status as StatusKey];
  const displayLabel = customLabel ?? config?.label ?? status;
  const style = config?.style ?? DEFAULT_STYLE;

  return (
    <span
      className="inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium"
      style={style}
    >
      {displayLabel}
    </span>
  );
}
