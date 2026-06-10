"use client";

import Link from "next/link";
import { ExternalLink, ChevronDown, ChevronUp } from "lucide-react";
import { useState } from "react";
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
  payment_manual_update_result: { label: "활동비 납부 현황", href: "/payments?tab=activity_fee" },
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

  if (ctx.mode === "linked" || ctx.mode === "created") {
    return (
      <div className="mb-4 flex items-center gap-2 rounded-xl px-3 py-2 text-sm"
        style={{ background: "var(--success-soft)", border: "1px solid rgba(63,125,88,0.15)", color: "var(--success)" }}>
        <span>✓</span>
        <span className="font-medium">{ctx.mode === "created" ? "생성된 활동:" : "연결된 활동:"}</span>
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

function ActivityImportResultCard({ result }: { result: Record<string, unknown> }) {
  const activity = result.activity as { id?: string; title?: string; activity_date?: string | null } | undefined;
  const summary = result.import_summary as Record<string, number> | undefined;
  const files = (result.files as Array<{ original_filename?: string; file_category?: string | null }> | undefined) ?? [];
  const risks = (result.risk_reasons as string[] | undefined) ?? [];
  const fee = result.activity_fee_result as { amount?: number; created_count?: number; updated_count?: number; payment_type?: string } | null | undefined;

  return (
    <div className="space-y-3">
      {activity && (
        <div className="rounded-xl p-4"
          style={{ background: "var(--success-soft)", border: "1px solid rgba(63,125,88,0.15)" }}>
          <p className="text-sm font-semibold" style={{ color: "var(--success)" }}>
            생성된 활동: {activity.title ?? activity.id}
          </p>
          {activity.activity_date && (
            <p className="text-xs mt-1" style={{ color: "var(--success)" }}>{activity.activity_date}</p>
          )}
        </div>
      )}
      {summary && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
          {[
            ["신규 부원", summary.created_members],
            ["업데이트", summary.updated_members],
            ["신규 참여", summary.created_participants],
            ["참여 갱신", summary.updated_participants],
          ].map(([label, value]) => (
            <div key={label} className="rounded-xl p-3 text-center"
              style={{ background: "var(--surface-soft)", border: "1px solid var(--border-soft)" }}>
              <p className="text-xs mb-1" style={{ color: "var(--text-muted)" }}>{label}</p>
              <p className="text-sm font-semibold" style={{ color: "var(--text-main)" }}>{Number(value ?? 0)}</p>
            </div>
          ))}
        </div>
      )}
      {files.length > 0 && (
        <div className="space-y-1">
          {files.map((file, idx) => (
            <p key={`${file.original_filename}-${idx}`} className="text-xs" style={{ color: "var(--text-muted)" }}>
              {file.original_filename} {file.file_category ? `· ${file.file_category}` : ""}
            </p>
          ))}
        </div>
      )}
      {fee && (
        <div className="rounded-xl p-3"
          style={{ background: "var(--surface-soft)", border: "1px solid var(--border-soft)" }}>
          <p className="text-xs mb-1" style={{ color: "var(--text-muted)" }}>활동비 생성 결과</p>
          <p className="text-sm font-semibold" style={{ color: "var(--text-main)" }}>
            {(fee.amount ?? 0).toLocaleString("ko-KR")}원 · 대상 {(fee.created_count ?? 0) + (fee.updated_count ?? 0)}명
          </p>
        </div>
      )}
      {risks.length > 0 && (
        <p className="text-xs" style={{ color: "var(--warning)" }}>
          확인 필요: {risks.join(", ")}
        </p>
      )}
    </div>
  );
}

function ParticipantImportPreviewCard({ result }: { result: Record<string, unknown> }) {
  const summary = result.summary as Record<string, number> | undefined;
  const warnings = (result.warnings as string[] | undefined) ?? [];
  const rows = (result.rows as Array<{
    row_index?: number;
    name?: string | null;
    student_id?: string | null;
    department?: string | null;
    match_status?: string;
    action?: string;
    reason?: string;
  }> | undefined) ?? [];

  const matchLabels: Record<string, string> = {
    matched_member: "기존 부원",
    needs_review: "확인 필요",
    duplicate_candidate: "중복 후보",
    unregistered_candidate: "미등록 후보",
    already_participant: "이미 참가자",
  };
  const actionLabels: Record<string, string> = {
    link_existing_member: "기존 부원 연결",
    create_new_member: "새 부원 등록",
    mark_external: "외부인 유지",
    ignore: "무시",
    needs_user_selection: "선택 필요",
    already_exists: "이미 등록됨",
  };

  return (
    <div className="space-y-3">
      {warnings.length > 0 && (
        <div className="rounded-xl p-3"
          style={{ background: "var(--warning-soft, #fef3c7)", border: "1px solid rgba(180,83,9,0.2)" }}>
          {warnings.map((warning) => (
            <p key={warning} className="text-xs font-medium" style={{ color: "var(--warning, #b45309)" }}>
              {warning}
            </p>
          ))}
        </div>
      )}
      {summary && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
          {[
            ["전체 행", summary.total_rows],
            ["기존 부원", summary.matched_members],
            ["미등록 후보", summary.unregistered_candidates],
            ["중복 후보", summary.duplicate_candidates],
            ["확인 필요", summary.needs_review],
            ["이미 참가자", summary.already_participants],
            ["생성 예정", summary.will_create_participants],
            ["무효 행", summary.invalid_rows],
          ].map(([label, value]) => (
            <div key={label} className="rounded-xl p-3 text-center"
              style={{ background: "var(--surface-soft)", border: "1px solid var(--border-soft)" }}>
              <p className="text-xs mb-1" style={{ color: "var(--text-muted)" }}>{label}</p>
              <p className="text-sm font-semibold" style={{ color: "var(--text-main)" }}>{Number(value ?? 0)}</p>
            </div>
          ))}
        </div>
      )}
      {rows.length > 0 && (
        <div className="overflow-x-auto">
          <table className="w-full text-xs" style={{ borderCollapse: "collapse" }}>
            <thead>
              <tr style={{ borderBottom: "1px solid var(--border-soft)" }}>
                {["#", "이름", "학번", "학과", "매칭", "처리"].map((h) => (
                  <th key={h} className="text-left py-1.5 px-2 font-medium" style={{ color: "var(--text-muted)" }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.slice(0, 8).map((row) => (
                <tr key={row.row_index ?? row.name} style={{ borderBottom: "1px solid var(--border-soft)" }}>
                  <td className="py-1.5 px-2" style={{ color: "var(--text-muted)" }}>{row.row_index ?? "-"}</td>
                  <td className="py-1.5 px-2 font-medium" style={{ color: "var(--text-main)" }}>{row.name ?? "-"}</td>
                  <td className="py-1.5 px-2" style={{ color: "var(--text-muted)" }}>{row.student_id ?? "-"}</td>
                  <td className="py-1.5 px-2" style={{ color: "var(--text-muted)" }}>{row.department ?? "-"}</td>
                  <td className="py-1.5 px-2" style={{ color: "var(--text-muted)" }}>{matchLabels[row.match_status ?? ""] ?? row.match_status ?? "-"}</td>
                  <td className="py-1.5 px-2" style={{ color: "var(--text-muted)" }}>{actionLabels[row.action ?? ""] ?? row.action ?? "-"}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {rows.length > 8 && (
            <p className="text-xs mt-2" style={{ color: "var(--text-muted)" }}>
              +{rows.length - 8}행 더 있습니다. 활동 상세의 Import 탭에서 전체 행을 확인할 수 있습니다.
            </p>
          )}
        </div>
      )}
    </div>
  );
}

// ─── Payment Manual Update Result Card (Task 23) ────────────────────────────

function PaymentManualUpdateResultCard({ result, activityId }: {
  result: Record<string, unknown>;
  activityId?: string;
}) {
  const memberName = result.member_name as string | null;
  const newStatus = result.new_status as string | null;
  const prevStatus = result.previous_status as string | null;
  const newPaid = result.new_paid_amount as number | null;
  const prevPaid = result.previous_paid_amount as number | null;
  const required = result.required_amount as number | null;
  const activityTitle = result.activity_title as string | null;
  const proposalStatus = result.proposal_status as string | null;
  const paymentType = result.payment_type as string | null;
  const paymentTypeLabel = paymentType === "membership_fee" ? "회비" : "활동비";
  const candidates = result.candidates as Array<{ member_id: string; name: string; student_id: string | null }> | null;

  const STATUS_LABEL: Record<string, string> = {
    paid: "납부 완료", partial: "부분 납부", unpaid: "미납",
    overpaid: "오납", exempt: "면제", cancelled: "취소",
  };

  const fmt = (n: number | null | undefined) =>
    n != null ? n.toLocaleString("ko-KR") + "원" : "-";

  if (candidates && candidates.length > 0) {
    return (
      <div className="rounded-xl p-4 space-y-2"
        style={{ background: "var(--warning-soft)", border: "1px solid rgba(185,130,43,0.15)" }}>
        <p className="text-sm font-semibold" style={{ color: "var(--warning)" }}>같은 이름 후보 여러 명</p>
        <div className="space-y-1">
          {candidates.map((c) => (
            <p key={c.member_id} className="text-xs" style={{ color: "var(--text-main)" }}>
              {c.name} {c.student_id ? `(${c.student_id})` : ""}
            </p>
          ))}
        </div>
        <p className="text-xs" style={{ color: "var(--warning)" }}>학번을 함께 입력해 주세요.</p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <div className="rounded-xl p-4"
        style={{ background: "var(--success-soft)", border: "1px solid rgba(63,125,88,0.15)" }}>
        <p className="text-sm font-semibold" style={{ color: "var(--success)" }}>
          {proposalStatus === "pending"
            ? `${paymentTypeLabel} 납부 상태 변경 예정`
            : `${paymentTypeLabel} 납부 상태 변경 완료`}
        </p>
        {activityTitle && (
          <p className="text-xs mt-0.5" style={{ color: "var(--success)" }}>활동: {activityTitle}</p>
        )}
      </div>
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
        {[
          { label: "부원명", value: memberName ?? "-" },
          { label: "납부 유형", value: paymentTypeLabel },
          { label: "이전 상태", value: STATUS_LABEL[prevStatus ?? ""] ?? prevStatus ?? "-" },
          { label: "변경 상태", value: STATUS_LABEL[newStatus ?? ""] ?? newStatus ?? "-" },
          { label: "반영 금액", value: fmt(newPaid) },
          { label: "필요 금액", value: fmt(required) },
          { label: "이전 납부", value: fmt(prevPaid) },
        ].map((item) => (
          <div key={item.label} className="rounded-xl p-3 text-center"
            style={{ background: "var(--surface-soft)", border: "1px solid var(--border-soft)" }}>
            <p className="text-xs mb-1" style={{ color: "var(--text-muted)" }}>{item.label}</p>
            <p className="text-sm font-semibold" style={{ color: "var(--text-main)" }}>{item.value}</p>
          </div>
        ))}
      </div>
      {(result.activity_id || activityId) && (
        <Link href={`/activities/${result.activity_id ?? activityId}?tab=fees`}>
          <Button size="sm" variant="secondary">
            <ExternalLink className="h-3.5 w-3.5" />
            활동비 납부 현황 보기
          </Button>
        </Link>
      )}
    </div>
  );
}

// ─── Bulk Membership Fee Mark Paid Preview Card (Task 28) ───────────────────

function BulkMembershipFeeMarkPaidCard({ result }: { result: Record<string, unknown> }) {
  const summary = result.summary as Record<string, number> | undefined;
  const period = result.period as string | undefined;
  const fmt = (n: number | null | undefined) =>
    n != null ? n.toLocaleString("ko-KR") + "원" : "-";

  return (
    <div className="space-y-3">
      <div className="rounded-xl p-3"
        style={{ background: "var(--primary-soft)", border: "1px solid rgba(99,102,241,0.15)" }}>
        <p className="text-sm font-semibold" style={{ color: "var(--primary)" }}>
          회비 일괄 완납 처리 미리보기
        </p>
        {period && (
          <p className="text-xs mt-0.5" style={{ color: "var(--primary)" }}>학기: {period}</p>
        )}
      </div>
      {summary && (
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
          {[
            ["전체 대상", summary.total_records + "명"],
            ["신규 부원", summary.new_member_count + "명"],
            ["기존 부원", summary.existing_member_count + "명"],
            ["임원", summary.executive_count + "명"],
            ["변경 대상", summary.will_change_count + "명"],
            ["총 예정 금액", fmt(summary.total_amount)],
          ].map(([label, val]) => (
            <div key={label} className="rounded-xl p-3 text-center"
              style={{ background: "var(--surface-soft)", border: "1px solid var(--border-soft)" }}>
              <p className="text-xs mb-1" style={{ color: "var(--text-muted)" }}>{label}</p>
              <p className="text-sm font-semibold" style={{ color: "var(--text-main)" }}>{val}</p>
            </div>
          ))}
        </div>
      )}
      <p className="text-xs" style={{ color: "var(--text-muted)" }}>
        각 부원의 회비 기준 금액으로 완납 처리됩니다. 30,000원 단일 기준을 사용하지 않습니다.
      </p>
    </div>
  );
}

// ─── Activity Fee Transaction Match Preview Card (Task 30) ──────────────────

function ActivityFeeTransactionMatchPreviewCard({ result }: { result: Record<string, unknown> }) {
  const summary = result.summary as Record<string, number> | undefined;
  const rows = (result.rows as Array<{
    memo?: string | null;
    deposit_amount?: number;
    matched_member_name?: string | null;
    required_amount?: number | null;
    match_status?: string;
    reason?: string;
  }> | undefined) ?? [];

  const statusLabel: Record<string, string> = {
    auto_match_candidate: "자동 후보",
    amount_mismatch: "금액 불일치",
    name_check_required: "이름 확인 필요",
    already_paid: "이미 납부",
    already_matched: "이미 매칭",
    unmatched: "미매칭",
  };
  const fmt = (n: number | null | undefined) => n != null ? n.toLocaleString("ko-KR") + "원" : "-";

  return (
    <div className="space-y-3">
      <p className="text-sm font-semibold" style={{ color: "var(--text-main)" }}>
        활동비 거래내역 매칭 미리보기
      </p>
      {summary && (
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
          {[
            ["자동 후보", summary.auto_match_candidates, "var(--success)"],
            ["금액 불일치", summary.amount_mismatch, "var(--danger)"],
            ["이름 확인 필요", summary.name_check_required, "var(--warning, #b45309)"],
            ["이미 납부", summary.already_paid, "var(--text-muted)"],
            ["미매칭", summary.unmatched, "var(--text-muted)"],
          ].map(([label, val, color]) => (
            <div key={String(label)} className="rounded-xl p-3 text-center"
              style={{ background: "var(--surface-soft)", border: "1px solid var(--border-soft)" }}>
              <p className="text-xs mb-1" style={{ color: "var(--text-muted)" }}>{label}</p>
              <p className="text-sm font-semibold" style={{ color: String(color) }}>{String(val ?? 0)}</p>
            </div>
          ))}
        </div>
      )}
      {rows.length > 0 && (
        <div className="overflow-x-auto">
          <table className="w-full text-xs" style={{ borderCollapse: "collapse" }}>
            <thead>
              <tr style={{ borderBottom: "1px solid var(--border-soft)" }}>
                {["적요", "참가자", "필요", "입금", "상태"].map((h) => (
                  <th key={h} className="text-left py-1.5 px-2 font-medium" style={{ color: "var(--text-muted)" }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((row, i) => (
                <tr key={i} style={{ borderBottom: "1px solid var(--border-soft)" }}>
                  <td className="py-1.5 px-2" style={{ color: "var(--text-muted)" }}>{row.memo ?? "-"}</td>
                  <td className="py-1.5 px-2 font-medium" style={{ color: "var(--text-main)" }}>{row.matched_member_name ?? "-"}</td>
                  <td className="py-1.5 px-2" style={{ color: "var(--text-muted)" }}>{fmt(row.required_amount)}</td>
                  <td className="py-1.5 px-2" style={{ color: "var(--text-main)" }}>{fmt(row.deposit_amount)}</td>
                  <td className="py-1.5 px-2" style={{ color: row.match_status === "auto_match_candidate" ? "var(--success)" : "var(--text-muted)" }}>
                    {statusLabel[row.match_status ?? ""] ?? row.match_status ?? "-"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

// ─── Diagnostics Panel ───────────────────────────────────────────────────────

function _inferDomain(intent: string): string {
  if (["bulk_membership_fee_mark_paid", "membership_fee_generate", "payment_matching"].includes(intent)) return "membership_fee";
  if (["activity_fee_generate", "activity_fee_transaction_match", "payment_manual_update"].includes(intent)) return "activity_fee";
  if (["receipt_analysis"].includes(intent)) return "receipt";
  if (["bank_statement_import"].includes(intent)) return "bank";
  if (["activity_report_generate", "activity_create", "activity_create_with_roster", "activity_create_with_file", "activity_create_with_application_form", "participant_import"].includes(intent)) return "activity";
  return "general";
}

function _inferScope(intent: string, activityId?: string | null): string {
  if (activityId) return `activity:${activityId.slice(0, 8)}`;
  if (["activity_fee_generate", "activity_fee_transaction_match", "payment_manual_update", "participant_import"].includes(intent)) return "activity (not linked)";
  if (["bulk_membership_fee_mark_paid", "membership_fee_generate", "payment_matching"].includes(intent)) return "global/membership";
  return "global";
}

function DiagnosticsPanel({ response }: { response: AssistantExecuteResponse }) {
  const [open, setOpen] = useState(false);

  const activityId = response.activity_context?.activity_id ?? null;
  const actionId = (response.apply_payload?.action_id as string | undefined)
    ?? (response.result?.action_id as string | undefined)
    ?? null;
  const paymentType = (response.result?.payment_type as string | undefined) ?? null;
  const serviceCalled = response.agent_flow.length > 0 ? response.agent_flow[response.agent_flow.length - 1] : null;

  const rows: Array<[string, string | null]> = [
    ["intent", response.intent],
    ["domain", _inferDomain(response.intent)],
    ["scope", _inferScope(response.intent, activityId)],
    ["activity_id", activityId],
    ["payment_type", paymentType],
    ["requires_confirmation", String(response.requires_confirmation)],
    ["action_id", actionId ? actionId.slice(0, 16) + "…" : null],
    ["service_called", serviceCalled],
  ];

  return (
    <div className="mt-4 border-t" style={{ borderColor: "var(--border-soft)" }}>
      <button
        className="w-full flex items-center justify-between pt-2 pb-1 text-xs"
        style={{ color: "var(--text-muted)", background: "transparent", border: "none", cursor: "pointer" }}
        onClick={() => setOpen((v) => !v)}
      >
        <span>진단 정보</span>
        {open ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
      </button>
      {open && (
        <div className="rounded-xl p-2 mt-1" style={{ background: "var(--surface-soft)", border: "1px solid var(--border-soft)" }}>
          <table className="w-full text-xs" style={{ borderCollapse: "collapse" }}>
            <tbody>
              {rows.map(([key, val]) => (
                <tr key={key}>
                  <td className="py-0.5 pr-3 font-mono" style={{ color: "var(--text-muted)", whiteSpace: "nowrap" }}>{key}</td>
                  <td className="py-0.5 font-mono" style={{ color: val ? "var(--text-main)" : "var(--text-muted)" }}>
                    {val ?? "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
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
  if (result_type === "payment_manual_update_result") {
    const actId = response.activity_context?.activity_id;
    return <PaymentManualUpdateResultCard result={result} activityId={actId} />;
  }
  if (result_type === "activity_import_result" || result_type === "google_form_import_preview") {
    return <ActivityImportResultCard result={result} />;
  }
  if (result_type === "participant_import_preview") {
    return <ParticipantImportPreviewCard result={result} />;
  }
  if (result_type === "bulk_membership_fee_mark_paid_preview") {
    return <BulkMembershipFeeMarkPaidCard result={result} />;
  }
  if (result_type === "activity_fee_transaction_match_preview") {
    return <ActivityFeeTransactionMatchPreviewCard result={result} />;
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

      {/* Task 25: Human-in-the-loop banner */}
      {response.requires_confirmation && status === "preview" && !isError && (
        <div className="mb-3 rounded-xl px-3 py-2 text-xs"
          style={{ background: "var(--warning-soft)", color: "var(--warning)", border: "1px solid rgba(185,130,43,0.15)" }}>
          AI가 다음 작업을 제안했습니다. 확인 후 반영을 누르기 전까지 데이터는 변경되지 않습니다.
        </div>
      )}
      <p className="text-sm mb-4"
        style={{ color: isError ? "var(--danger)" : "var(--text-main)" }}>
        {response.message}
      </p>

      {/* Result body */}
      {!isCancelled && renderBody(response)}

      {/* Actions */}
      {!isCancelled && (
        <div className="mt-5 flex flex-col sm:flex-row sm:flex-wrap sm:items-center gap-2">
          {canApply && onApplyClick && (
            <Button onClick={onApplyClick} loading={applying}>
              확인 후 반영
            </Button>
          )}
          {canApply && onCancel && (
            <Button variant="ghost" onClick={onCancel}>
              취소
            </Button>
          )}
          {detailHref && (
            <Link href={detailHref} className="sm:ml-auto">
              <Button variant="secondary">
                <ExternalLink className="h-3.5 w-3.5" />
                {detailLabel}
              </Button>
            </Link>
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

      {/* Diagnostics panel */}
      <DiagnosticsPanel response={response} />
    </Card>
  );
}
