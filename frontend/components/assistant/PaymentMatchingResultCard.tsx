import { ResultSummaryGrid } from "./ResultSummaryGrid";

interface Props {
  result: Record<string, unknown>;
  resultType: string;
}

export function PaymentMatchingResultCard({ result, resultType }: Props) {
  const isPreview = resultType === "payment_matching_preview";
  const unpaidSample: string[] = Array.isArray(result.unpaid_sample) ? result.unpaid_sample.map(String) : [];
  const unpaidCount = Number(result.unpaid_count ?? 0);
  const needCheckCount = Number(result.need_check_count ?? 0);

  function n(v: unknown): number { return v != null ? Number(v) : 0; }
  function s(v: unknown): string { return v != null ? String(v) : "-"; }

  const items = [
    { label: "전체 대상자", value: n(result.total_active_members) },
    { label: "매칭 성공", value: n(result.matched_count), tone: "success" as const },
    { label: "확인 필요", value: needCheckCount, tone: needCheckCount > 0 ? ("warning" as const) : ("default" as const) },
    { label: "미납", value: unpaidCount, tone: unpaidCount > 0 ? ("danger" as const) : ("default" as const) },
  ];

  const metaItems: Array<[string, string]> = [
    ["납부 기간", s(result.period)],
    ["납부 유형", s(result.payment_type)],
    ["기준 금액", result.required_amount != null ? `${Number(result.required_amount).toLocaleString("ko-KR")}원` : "-"],
    ["제외 거래", s(result.excluded_count)],
  ];

  const created = result.created_payment_records;
  const updated = result.updated_payment_records;

  return (
    <div className="space-y-4">
      <ResultSummaryGrid items={items} cols={4} />

      <div className="space-y-0">
        {metaItems.map(([k, v]) => (
          <div key={k} className="flex items-center justify-between py-1.5"
            style={{ borderBottom: "1px solid var(--border-soft)" }}>
            <span className="text-sm" style={{ color: "var(--text-muted)" }}>{k}</span>
            <span className="text-sm font-medium" style={{ color: "var(--text-main)" }}>{v}</span>
          </div>
        ))}
      </div>

      {!isPreview && created != null && (
        <div className="rounded-xl px-4 py-3 text-sm"
          style={{ background: "var(--success-soft)", color: "var(--success)", border: "1px solid rgba(63,125,88,0.15)" }}>
          납부 기록 생성 {String(created)}건 / 수정 {String(updated)}건
        </div>
      )}

      {isPreview && unpaidSample.length > 0 && (
        <div className="rounded-xl px-4 py-3 text-sm"
          style={{ background: "var(--danger-soft)", color: "var(--danger)", border: "1px solid rgba(185,74,72,0.15)" }}>
          <p className="font-medium mb-1">미납자 미리보기</p>
          <p>{unpaidSample.join(", ")}{unpaidCount > unpaidSample.length ? ` 외 ${unpaidCount - unpaidSample.length}명` : ""}</p>
        </div>
      )}
    </div>
  );
}
