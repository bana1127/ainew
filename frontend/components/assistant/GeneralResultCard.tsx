import { AlertCircle, MessageCircle } from "lucide-react";

interface Props {
  result: Record<string, unknown>;
  resultType: string;
  message: string;
}

export function GeneralResultCard({ result, resultType, message }: Props) {
  const isError = resultType === "error";
  const errorMsg = result.error != null ? String(result.error) : null;

  return (
    <div className="flex items-start gap-3">
      <div className="rounded-xl p-2.5 shrink-0"
        style={{ background: isError ? "var(--danger-soft)" : "var(--primary-soft)" }}>
        {isError
          ? <AlertCircle className="h-4 w-4" style={{ color: "var(--danger)" }} />
          : <MessageCircle className="h-4 w-4" style={{ color: "var(--primary)" }} />
        }
      </div>
      <div>
        <p className="text-sm" style={{ color: isError ? "var(--danger)" : "var(--text-main)" }}>
          {errorMsg ?? message}
        </p>
        {isError && (
          <p className="mt-1 text-xs" style={{ color: "var(--text-muted)" }}>
            처리 유형을 수동으로 선택하거나 파일을 첨부하여 다시 시도해 주세요.
          </p>
        )}
      </div>
    </div>
  );
}
