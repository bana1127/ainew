import { ResultSummaryGrid } from "./ResultSummaryGrid";

interface Props {
  result: Record<string, unknown>;
  saved: boolean;
}

const PAYMENT_METHOD_LABELS: Record<string, string> = {
  card: "카드",
  online_card: "온라인 카드",
  transfer_student: "계좌이체 (학생)",
  transfer_company: "계좌이체 (단체)",
  cash_withdrawal: "현금 인출",
  personal_card_reimbursement: "개인카드 후정산",
  recurring_payment: "정기 결제",
  unknown: "알 수 없음",
};

const EVIDENCE_TONE: Record<string, "success" | "warning" | "danger" | "default"> = {
  valid: "success",
  need_check: "warning",
  invalid: "danger",
  pending: "default",
};

export function ReceiptResultCard({ result, saved }: Props) {
  const evidenceStatus = String(result.evidence_status ?? "pending");
  const needCheck = Boolean(result.need_check);
  const paymentMethod = String(result.payment_method ?? "unknown");
  const requiredEvidence = (result.required_evidence as string[] | null) ?? [];
  const reason = result.reason ? String(result.reason) : null;

  const rows: Array<[string, string]> = [
    ["날짜", String(result.receipt_date ?? "-")],
    ["가맹점", String(result.store_name ?? "-")],
    ["금액", result.amount != null ? `${Number(result.amount).toLocaleString("ko-KR")}원` : "-"],
    ["결제 방식", PAYMENT_METHOD_LABELS[paymentMethod] ?? paymentMethod],
    ["지출 분류", String(result.category ?? "-")],
    ["신뢰도", result.confidence != null ? `${Math.round(Number(result.confidence) * 100)}%` : "-"],
  ];

  return (
    <div className="space-y-4">
      {/* Status banner */}
      <div className="rounded-xl px-4 py-3 flex items-center justify-between"
        style={{
          background: evidenceStatus === "valid" ? "var(--success-soft)" : evidenceStatus === "need_check" ? "var(--warning-soft)" : evidenceStatus === "invalid" ? "var(--danger-soft)" : "var(--border-soft)",
          border: `1px solid ${evidenceStatus === "valid" ? "rgba(63,125,88,0.2)" : evidenceStatus === "need_check" ? "rgba(185,130,43,0.2)" : evidenceStatus === "invalid" ? "rgba(185,74,72,0.2)" : "var(--border-soft)"}`,
        }}>
        <span className="text-sm font-medium" style={{
          color: evidenceStatus === "valid" ? "var(--success)" : evidenceStatus === "need_check" ? "var(--warning)" : evidenceStatus === "invalid" ? "var(--danger)" : "var(--text-muted)",
        }}>
          증빙 상태: {evidenceStatus === "valid" ? "적합" : evidenceStatus === "need_check" ? "확인 필요" : evidenceStatus === "invalid" ? "부적합" : "대기"}
        </span>
        {needCheck && (
          <span className="text-xs font-medium px-2 py-0.5 rounded-full"
            style={{ background: "var(--warning)", color: "#fff" }}>
            확인 필요
          </span>
        )}
        {saved && (
          <span className="text-xs font-medium px-2 py-0.5 rounded-full"
            style={{ background: "var(--success-soft)", color: "var(--success)" }}>
            저장 완료
          </span>
        )}
      </div>

      {/* Key-value grid */}
      <div className="space-y-0">
        {rows.map(([k, v]) => (
          <div key={k} className="flex items-center justify-between py-2"
            style={{ borderBottom: "1px solid var(--border-soft)" }}>
            <span className="text-sm" style={{ color: "var(--text-muted)" }}>{k}</span>
            <span className="text-sm font-medium" style={{ color: "var(--text-main)" }}>{v}</span>
          </div>
        ))}
      </div>

      {/* Required evidence */}
      {requiredEvidence.length > 0 && (
        <div className="rounded-xl px-4 py-3 text-sm"
          style={{ background: "var(--warning-soft)", color: "var(--warning)", border: "1px solid rgba(185,130,43,0.15)" }}>
          <p className="font-medium mb-1">필요 증빙</p>
          <p>{requiredEvidence.join(", ")}</p>
        </div>
      )}

      {/* Reason */}
      {reason && (
        <div className="text-sm" style={{ color: "var(--text-muted)" }}>
          <span className="font-medium" style={{ color: "var(--text-main)" }}>판단 사유: </span>
          {reason}
        </div>
      )}

    </div>
  );
}
