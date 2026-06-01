"use client";

import Link from "next/link";
import { ExternalLink } from "lucide-react";
import type { AssistantExecuteResponse, ActivityCandidateInfo, ActivityDraftInfo } from "@/lib/api";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { AgentFlow } from "./AgentFlow";
import { IntentBadge } from "./IntentBadge";
import { ReceiptResultCard } from "./ReceiptResultCard";
import { BankStatementResultCard } from "./BankStatementResultCard";
import { PaymentMatchingResultCard } from "./PaymentMatchingResultCard";
import { ActivityReportResultCard } from "./ActivityReportResultCard";
import { GeneralResultCard } from "./GeneralResultCard";

export type RunStatus = "preview" | "applied" | "failed" | "cancelled";

const STATUS_LABELS: Record<RunStatus, { label: string; style: React.CSSProperties }> = {
  preview: { label: "미리보기", style: { background: "var(--primary-soft)", color: "var(--primary)" } },
  applied: { label: "반영 완료", style: { background: "var(--success-soft)", color: "var(--success)" } },
  failed: { label: "실패", style: { background: "var(--danger-soft)", color: "var(--danger)" } },
  cancelled: { label: "취소됨", style: { background: "var(--border-soft)", color: "var(--text-muted)" } },
};

const DETAIL_LINK_MAP: Record<string, { label: string; href: string }> = {
  receipt_analysis: { label: "영수증 목록에서 보기", href: "/receipts" },
  bank_statement_preview: { label: "거래내역 페이지에서 보기", href: "/transactions" },
  bank_statement_import_result: { label: "거래내역 목록에서 보기", href: "/transactions" },
  payment_matching_preview: { label: "납부 페이지에서 보기", href: "/payments" },
  payment_matching_result: { label: "납부 현황 보기", href: "/payments" },
  activity_report_draft: { label: "보고서 작성 화면", href: "/reports" },
  activity_fee_generation_result: { label: "활동비 납부 현황", href: "/payments?tab=activity_fee" },
  general_message: { label: "대시보드", href: "/dashboard" },
};

interface Props {
  response: AssistantExecuteResponse;
  status: RunStatus;
  onApplyClick?: () => void;
  onCancel?: () => void;
  applying?: boolean;
  requestMessage?: string;
  onSelectCandidate?: (activityId: string) => void;
  onCreateActivityAndContinue?: (draft: ActivityDraftInfo) => void;
}

// ─── Activity Context Banner ──────────────────────────────────────────────────

function ActivityContextBanner({
  response,
  onSelectCandidate,
  onCreateActivityAndContinue,
}: {
  response: AssistantExecuteResponse;
  onSelectCandidate?: (id: string) => void;
  onCreateActivityAndContinue?: (draft: ActivityDraftInfo) => void;
}) {
  const ctx = response.activity_context;
  if (!ctx || ctx.mode === "none") return null;

  if (ctx.mode === "linked") {
    return (
      <div className="mb-4 flex items-center gap-2 rounded-xl px-3 py-2 text-sm"
        style={{ background: "var(--success-soft)", border: "1px solid rgba(63,125,88,0.15)", color: "var(--success)" }}>
        <span>✓</span>
        <span className="font-medium">연결된 활동:</span>
        <span>{ctx.activity_title ?? ctx.activity_id}</span>
        {ctx.activity_id && (
          <Link href={`/activities/${ctx.activity_id}`}
            className="ml-auto text-xs font-medium hover:opacity-75 transition-opacity"
            style={{ color: "var(--success)" }}>
            활동 상세 →
          </Link>
        )}
      </div>
    );
  }

  if (ctx.mode === "needs_confirmation" && response.activity_candidates && response.activity_candidates.length > 0) {
    return (
      <div className="mb-4 rounded-xl p-3 space-y-2"
        style={{ background: "var(--warning-soft)", border: "1px solid rgba(185,130,43,0.15)" }}>
        <p className="text-sm font-medium" style={{ color: "var(--warning)" }}>
          연결할 활동을 선택해 주세요
        </p>
        <div className="flex flex-wrap gap-2">
          {response.activity_candidates.map((c: ActivityCandidateInfo) => (
            <button
              key={c.id}
              onClick={() => onSelectCandidate?.(c.id)}
              className="rounded-lg px-3 py-1.5 text-xs font-medium transition-all hover:opacity-85"
              style={{ background: "var(--surface)", border: "1px solid var(--border-soft)", color: "var(--text-main)" }}
            >
              {c.title}
              {c.activity_date && <span className="ml-1" style={{ color: "var(--text-muted)" }}>({c.activity_date})</span>}
            </button>
          ))}
        </div>
      </div>
    );
  }

  if (ctx.mode === "create_draft" && response.activity_draft) {
    const draft = response.activity_draft;
    return (
      <div className="mb-4 rounded-xl p-4 space-y-3"
        style={{ background: "var(--primary-soft)", border: "1px solid rgba(124,108,242,0.15)" }}>
        <p className="text-sm font-medium" style={{ color: "var(--primary)" }}>
          새 활동으로 생성할까요?
        </p>
        <div className="space-y-1 text-sm" style={{ color: "var(--text-main)" }}>
          <p><span className="font-medium">활동명:</span> {draft.title}</p>
          {draft.activity_date && <p><span className="font-medium">활동일:</span> {draft.activity_date}</p>}
          {draft.location && <p><span className="font-medium">장소:</span> {draft.location}</p>}
          {draft.description && (
            <p className="text-xs" style={{ color: "var(--text-muted)" }}>{draft.description.slice(0, 100)}</p>
          )}
        </div>
        <Button
          size="sm"
          onClick={() => onCreateActivityAndContinue?.(draft)}
        >
          새 활동 생성 후 계속
        </Button>
      </div>
    );
  }

  return null;
}

// ─── Activity Fee Result Card ─────────────────────────────────────────────────

function ActivityFeeResultCard({ result }: { result: Record<string, unknown> }) {
  const amount = result.fee_amount as number;
  const created = result.created_count as number;
  const total = result.total_participants as number;
  const activityTitle = result.activity_title as string | null;

  return (
    <div className="space-y-3">
      <div className="rounded-xl p-4"
        style={{ background: "var(--success-soft)", border: "1px solid rgba(63,125,88,0.15)" }}>
        <p className="text-sm font-semibold" style={{ color: "var(--success)" }}>
          활동비 납부 대상 생성 완료
        </p>
        {activityTitle && (
          <p className="text-xs mt-1" style={{ color: "var(--success)" }}>활동: {activityTitle}</p>
        )}
      </div>
      <div className="grid grid-cols-3 gap-3">
        {[
          { label: "참여자 수", value: `${total}명` },
          { label: "신규 생성", value: `${created}건` },
          { label: "1인당 금액", value: `${(amount || 0).toLocaleString("ko-KR")}원` },
        ].map((item) => (
          <div key={item.label} className="rounded-xl p-3 text-center"
            style={{ background: "var(--surface-soft)", border: "1px solid var(--border-soft)" }}>
            <p className="text-xs mb-1" style={{ color: "var(--text-muted)" }}>{item.label}</p>
            <p className="text-sm font-semibold" style={{ color: "var(--text-main)" }}>{item.value}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

// ─── renderBody ───────────────────────────────────────────────────────────────

function renderBody(response: AssistantExecuteResponse) {
  const { result_type, result } = response;
  if (result_type === "receipt_analysis") {
    return <ReceiptResultCard result={result} saved={Boolean(result.saved)} />;
  }
  if (result_type === "bank_statement_preview" || result_type === "bank_statement_import_result") {
    return <BankStatementResultCard result={result} resultType={result_type} />;
  }
  if (result_type === "payment_matching_preview" || result_type === "payment_matching_result") {
    return <PaymentMatchingResultCard result={result} resultType={result_type} />;
  }
  if (result_type === "activity_report_draft") {
    return <ActivityReportResultCard result={result} />;
  }
  if (result_type === "activity_fee_generation_result") {
    return <ActivityFeeResultCard result={result} />;
  }
  if (result_type === "activity_candidate" || result_type === "activity_draft") {
    // Context banner already shown above; no additional body needed
    return null;
  }
  return <GeneralResultCard result={result} resultType={result_type} message={response.message} />;
}

export function AssistantResultCard({
  response,
  status,
  onApplyClick,
  onCancel,
  applying,
  requestMessage,
  onSelectCandidate,
  onCreateActivityAndContinue,
}: Props) {
  const isError = response.result_type === "error";
  const isCancelled = status === "cancelled";
  const isApplied = status === "applied";
  const canApply = response.requires_confirmation && !isCancelled && !isApplied && !isError
    && !["activity_candidate", "activity_draft"].includes(response.result_type);

  const detailHref = response.detail_url ?? DETAIL_LINK_MAP[response.result_type]?.href ?? null;
  const detailLabel = DETAIL_LINK_MAP[response.result_type]?.label ?? "상세 페이지에서 보기";

  const statusInfo = STATUS_LABELS[status] ?? STATUS_LABELS.preview;

  return (
    <Card padding="lg">
      {/* Header row */}
      <div className="flex items-start justify-between gap-3 mb-4">
        <div className="flex items-center gap-2 flex-wrap">
          <IntentBadge intent={response.intent} />
          <span className="text-xs px-2.5 py-0.5 rounded-full font-medium" style={statusInfo.style}>
            {statusInfo.label}
          </span>
          <span className="text-xs px-2 py-0.5 rounded-full font-medium"
            style={{ background: "var(--border-soft)", color: "var(--text-muted)" }}>
            신뢰도 {Math.round(response.confidence * 100)}%
          </span>
        </div>
      </div>

      {/* Request message */}
      {requestMessage && (
        <p className="text-xs mb-3 px-3 py-2 rounded-xl"
          style={{ background: "var(--surface-soft)", color: "var(--text-muted)", border: "1px solid var(--border-soft)" }}>
          요청: {requestMessage}
        </p>
      )}

      {/* Agent flow */}
      {response.agent_flow.length > 0 && (
        <div className="mb-4">
          <AgentFlow steps={response.agent_flow} />
        </div>
      )}

      {/* Activity context banner (Task 17) */}
      <ActivityContextBanner
        response={response}
        onSelectCandidate={onSelectCandidate}
        onCreateActivityAndContinue={onCreateActivityAndContinue}
      />

      {/* Summary message */}
      <p className="text-sm mb-4"
        style={{ color: isError ? "var(--danger)" : "var(--text-main)" }}>
        {response.message}
      </p>

      {/* Result body */}
      {!isCancelled && renderBody(response)}

      {/* Actions */}
      {!isCancelled && (
        <div className="mt-5 flex flex-wrap items-center gap-3">
          {canApply && onApplyClick && (
            <Button onClick={onApplyClick} loading={applying}>
              {response.result_type.includes("bank") ? "거래내역 반영" :
               response.result_type.includes("payment_matching") ? "납부 상태 반영" :
               response.result_type.includes("receipt") ? "영수증 저장" :
               response.result_type.includes("report") ? "보고서 저장" :
               "확인 후 반영"}
            </Button>
          )}
          {detailHref && (
            <Link href={detailHref}>
              <Button variant="secondary">
                <ExternalLink className="h-3.5 w-3.5" />
                {detailLabel}
              </Button>
            </Link>
          )}
          {canApply && onCancel && (
            <Button variant="ghost" onClick={onCancel}>
              취소
            </Button>
          )}
          {isApplied && detailHref && (
            <Link href={detailHref}>
              <Button variant="secondary">
                <ExternalLink className="h-3.5 w-3.5" />
                결과 확인하기
              </Button>
            </Link>
          )}
        </div>
      )}
    </Card>
  );
}
