import { ResultSummaryGrid } from "./ResultSummaryGrid";

interface Props {
  result: Record<string, unknown>;
  resultType: string;
}

export function BankStatementResultCard({ result, resultType }: Props) {
  const isPreview = resultType === "bank_statement_preview";
  const warnings: string[] = Array.isArray(result.warnings) ? result.warnings.map(String) : [];
  const errors: string[] = Array.isArray(result.errors) ? result.errors.map(String) : [];
  const fileName = result.file_name != null ? String(result.file_name) : null;

  function n(v: unknown): number {
    return v != null ? Number(v) : 0;
  }

  const items = isPreview
    ? [
        { label: "전체 행", value: n(result.total_rows) },
        { label: "파싱 성공", value: n(result.parsed_rows) },
        { label: "스킵", value: n(result.skipped_rows) },
        { label: "경고", value: warnings.length, tone: warnings.length > 0 ? ("warning" as const) : ("default" as const) },
      ]
    : [
        { label: "전체 행", value: n(result.total_rows) },
        { label: "파싱 성공", value: n(result.parsed_rows) },
        { label: "저장됨", value: n(result.inserted_rows), tone: "success" as const },
        { label: "중복 스킵", value: n(result.duplicate_rows) },
      ];

  return (
    <div className="space-y-4">
      <ResultSummaryGrid items={items} cols={4} />

      {errors.length > 0 && (
        <div className="rounded-xl px-4 py-3 text-sm"
          style={{ background: "var(--danger-soft)", color: "var(--danger)", border: "1px solid rgba(185,74,72,0.15)" }}>
          <p className="font-medium mb-1">오류 ({errors.length}건)</p>
          {errors.slice(0, 3).map((e, i) => <p key={i}>{e}</p>)}
          {errors.length > 3 && <p>...외 {errors.length - 3}건</p>}
        </div>
      )}

      {warnings.length > 0 && (
        <div className="rounded-xl px-4 py-3 text-sm"
          style={{ background: "var(--warning-soft)", color: "var(--warning)", border: "1px solid rgba(185,130,43,0.15)" }}>
          <p className="font-medium mb-1">경고 ({warnings.length}건)</p>
          {warnings.slice(0, 3).map((w, i) => <p key={i}>{w}</p>)}
          {warnings.length > 3 && <p>...외 {warnings.length - 3}건</p>}
        </div>
      )}

      {fileName != null && (
        <p className="text-xs" style={{ color: "var(--text-muted)" }}>
          파일: {fileName}
        </p>
      )}
    </div>
  );
}
