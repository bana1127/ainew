interface Props {
  result: Record<string, unknown>;
}

export function ActivityReportResultCard({ result }: Props) {
  const title = String(result.title ?? "");
  const summary = result.summary != null ? String(result.summary) : null;
  const content = String(result.content ?? "");
  const model = String(result.model ?? "");
  const confidence = result.confidence != null ? Math.round(Number(result.confidence) * 100) : null;
  const missingFields = (result.missing_fields as string[]) ?? [];
  const saved = Boolean(result.saved);

  return (
    <div className="space-y-4">
      {/* Status */}
      {saved && (
        <div className="rounded-xl px-4 py-2 text-sm"
          style={{ background: "var(--success-soft)", color: "var(--success)", border: "1px solid rgba(63,125,88,0.15)" }}>
          저장 완료 — 활동 보고서 목록에서 확인하세요.
        </div>
      )}

      {/* Title + summary */}
      <div>
        <h4 className="text-sm font-semibold mb-1" style={{ color: "var(--text-main)" }}>{title}</h4>
        {summary && (
          <p className="text-xs italic" style={{ color: "var(--text-muted)" }}>{summary}</p>
        )}
      </div>

      {/* Content preview */}
      <pre className="whitespace-pre-wrap text-xs rounded-xl p-4 max-h-48 overflow-y-auto"
        style={{ background: "var(--surface-soft)", border: "1px solid var(--border-soft)", color: "var(--text-main)" }}>
        {content.slice(0, 600)}{content.length > 600 ? "..." : ""}
      </pre>

      {/* Meta */}
      <div className="flex flex-wrap gap-4 text-xs" style={{ color: "var(--text-muted)" }}>
        {model && <span>모델: {model}</span>}
        {confidence !== null && <span>신뢰도: {confidence}%</span>}
      </div>

      {/* Missing fields */}
      {missingFields.length > 0 && (
        <div className="rounded-xl px-4 py-3 text-sm"
          style={{ background: "var(--warning-soft)", color: "var(--warning)", border: "1px solid rgba(185,130,43,0.15)" }}>
          <p className="font-medium mb-0.5">누락된 필드</p>
          <p>{missingFields.join(", ")}</p>
        </div>
      )}
    </div>
  );
}
