import type { AssistantIntent } from "@/lib/api";

const INTENT_LABELS: Record<string, string> = {
  receipt_analysis: "영수증 분석",
  bank_statement_import: "거래내역서",
  payment_matching: "납부 매칭",
  activity_report_generate: "활동 보고서",
  activity_fee_generate: "활동비 생성",
  activity_link: "활동 연결",
  activity_create: "활동 생성",
  unknown: "알 수 없음",
};

const INTENT_STYLES: Record<string, React.CSSProperties> = {
  receipt_analysis: { background: "var(--success-soft)", color: "var(--success)" },
  bank_statement_import: { background: "var(--primary-soft)", color: "var(--primary)" },
  payment_matching: { background: "var(--warning-soft)", color: "var(--warning)" },
  activity_report_generate: { background: "var(--primary-soft)", color: "var(--primary)" },
  activity_fee_generate: { background: "var(--warning-soft)", color: "var(--warning)" },
  activity_link: { background: "var(--success-soft)", color: "var(--success)" },
  activity_create: { background: "var(--primary-soft)", color: "var(--primary)" },
  unknown: { background: "var(--border-soft)", color: "var(--text-muted)" },
};

export function IntentBadge({ intent }: { intent: string }) {
  const label = INTENT_LABELS[intent] ?? intent;
  const style = INTENT_STYLES[intent] ?? INTENT_STYLES.unknown;
  return (
    <span className="inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium" style={style}>
      {label}
    </span>
  );
}
