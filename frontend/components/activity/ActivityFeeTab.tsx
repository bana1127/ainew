"use client";

import React, { useEffect, useRef, useState } from "react";
import { MoreHorizontal } from "lucide-react";

import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Modal } from "@/components/ui/Modal";
import {
  type ActivityDetail,
  type ActivityFeeMatchTransactionsConfirmResult,
  type ActivityFeeMatchTransactionsPreview,
  type ActivityFeeRecord,
  type ExcludedTransactionItem,
  cancelActivityFeeMatchTransactions,
  confirmActivityFeeMatchTransactions,
  excludeActivityFeeTransaction,
  includeActivityFeeTransaction,
  getExcludedActivityFeeTransactions,
  generateActivityFees,
  previewActivityFeeMatchTransactions,
  setMarkRefunded,
  setRefundRequired,
  unmatchActivityFeeRecord,
  updateActivityFeeRecord,
} from "@/lib/api";

// ─── Helpers ───────────────────────────────────────────────────────────────────

function fmt(n: number): string {
  return n.toLocaleString("ko-KR");
}

const PAYMENT_STATUS_LABEL: Record<string, string> = {
  unpaid: "미납",
  partial: "부분 납부",
  paid: "납부 완료",
  overpaid: "초과 납부",
  need_check: "확인 필요",
  exempt: "면제",
  refunded: "환불 완료",
  cancelled: "취소",
};

const REFUND_STATUS_LABEL: Record<string, string> = {
  none: "없음",
  refund_required: "환불 필요",
  refund_pending: "환불 대기",
  refunded: "환불 완료",
};

const PAYMENT_STATUS_STYLE: Record<string, { bg: string; text: string }> = {
  paid: { bg: "var(--success-soft)", text: "var(--success)" },
  unpaid: { bg: "var(--danger-soft)", text: "var(--danger)" },
  partial: { bg: "var(--warning-soft)", text: "var(--warning)" },
  overpaid: { bg: "var(--warning-soft)", text: "var(--warning)" },
  need_check: { bg: "var(--surface-soft)", text: "var(--text-muted)" },
  exempt: { bg: "var(--surface-soft)", text: "var(--text-muted)" },
};

const REFUND_STATUS_STYLE: Record<string, string> = {
  refund_required: "var(--danger)",
  refund_pending: "var(--warning)",
  refunded: "var(--success)",
};

function autoStatus(paid: number, required: number): string {
  if (paid === 0) return "unpaid";
  if (paid < required) return "partial";
  if (paid === required) return "paid";
  return "overpaid";
}

// ─── 1. 활동비 설정 패널 ──────────────────────────────────────────────────────

function ActivityFeeSettingsPanel({
  activityId,
  defaultAmount,
  onUpdated,
}: {
  activityId: string;
  defaultAmount: number;
  onUpdated: () => void;
}) {
  const [feeAmount, setFeeAmount] = useState(defaultAmount || 10000);
  const [generating, setGenerating] = useState(false);
  const [genResult, setGenResult] = useState<string | null>(null);
  const [genError, setGenError] = useState<string | null>(null);

  async function handleGenerate() {
    setGenerating(true);
    setGenError(null);
    setGenResult(null);
    try {
      const result = await generateActivityFees(activityId, feeAmount);
      setGenResult(`완료: ${result.created}건 생성, ${result.updated}건 갱신 (총 ${result.total}명 기준)`);
      onUpdated();
    } catch (err: unknown) {
      setGenError(err instanceof Error ? err.message : "생성에 실패했습니다.");
    } finally {
      setGenerating(false);
    }
  }

  return (
    <Card padding="lg">
      <h3 className="text-sm font-semibold mb-3" style={{ color: "var(--text-main)" }}>
        활동비 설정
      </h3>
      <div className="flex flex-wrap items-end gap-3">
        <div>
          <label className="block text-xs font-medium mb-1.5" style={{ color: "var(--text-muted)" }}>
            1인당 활동비 (원)
          </label>
          <input
            type="number"
            className="rounded-xl px-3 py-2 text-sm focus:outline-none min-h-[44px] w-40"
            style={{ background: "var(--surface)", color: "var(--text-main)", border: "1px solid var(--border-soft)" }}
            value={feeAmount}
            onChange={(e) => setFeeAmount(Number(e.target.value))}
          />
        </div>
        <Button onClick={handleGenerate} loading={generating}>
          활동비 대상 생성/갱신
        </Button>
      </div>
      <p className="mt-2 text-xs" style={{ color: "var(--text-muted)" }}>
        현재 활동 참가자를 기준으로 활동비 납부 대상을 생성합니다. 기존 납부 금액은 유지됩니다.
      </p>
      {genResult && <p className="mt-2 text-sm" style={{ color: "var(--success)" }}>{genResult}</p>}
      {genError && <p className="mt-2 text-sm" style={{ color: "var(--danger)" }}>{genError}</p>}
    </Card>
  );
}

// ─── 2. 활동비 요약 카드 ──────────────────────────────────────────────────────

function ActivityFeeSummaryCards({ records }: { records: ActivityFeeRecord[] }) {
  // Exclude cancelled records from summary calculations
  const activeRecords = records.filter((r) => r.status !== "cancelled");
  const paid = activeRecords.filter((r) => r.status === "paid").length;
  const unpaid = activeRecords.filter((r) => r.status === "unpaid").length;
  const partial = activeRecords.filter((r) => r.status === "partial").length;
  const overpaid = activeRecords.filter((r) => r.status === "overpaid").length;
  const refundNeeded = activeRecords.filter(
    (r) => r.refund_status === "refund_required" || r.refund_status === "refund_pending",
  ).length;
  const totalRequired = activeRecords.reduce((s, r) => s + r.required_amount, 0);
  const totalPaid = activeRecords.reduce((s, r) => s + r.paid_amount, 0);

  const cards = [
    { label: "참가자", value: `${activeRecords.length}명`, color: "var(--text-main)" },
    { label: "납부 완료", value: `${paid}명`, color: "var(--success)" },
    { label: "미납", value: `${unpaid}명`, color: unpaid > 0 ? "var(--danger)" : "var(--text-muted)" },
    { label: "부분 납부", value: `${partial}명`, color: partial > 0 ? "var(--warning)" : "var(--text-muted)" },
    { label: "초과 납부", value: `${overpaid}명`, color: overpaid > 0 ? "var(--warning)" : "var(--text-muted)" },
    { label: "환불 필요", value: `${refundNeeded}명`, color: refundNeeded > 0 ? "var(--danger)" : "var(--text-muted)" },
    { label: "총 예정", value: `${fmt(totalRequired)}원`, color: "var(--text-main)" },
    { label: "총 납부", value: `${fmt(totalPaid)}원`, color: "var(--primary)" },
  ];

  return (
    <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
      {cards.map((card) => (
        <div
          key={card.label}
          className="rounded-xl p-3 text-center"
          style={{ background: "var(--surface-soft)", border: "1px solid var(--border-soft)" }}
        >
          <p className="text-xs mb-0.5" style={{ color: "var(--text-muted)" }}>{card.label}</p>
          <p className="text-sm font-semibold" style={{ color: card.color }}>{card.value}</p>
        </div>
      ))}
    </div>
  );
}

// ─── 3. 거래내역 매칭 ─────────────────────────────────────────────────────────

function ActivityFeeMatchSection({
  activityId,
  onUpdated,
}: {
  activityId: string;
  onUpdated: () => void;
}) {
  const [previewing, setPreviewing] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const [preview, setPreview] = useState<ActivityFeeMatchTransactionsPreview | null>(null);
  const [result, setResult] = useState<ActivityFeeMatchTransactionsConfirmResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [excludingId, setExcludingId] = useState<string | null>(null);
  const [showExcluded, setShowExcluded] = useState(false);
  const [excludedList, setExcludedList] = useState<ExcludedTransactionItem[]>([]);
  const [loadingExcluded, setLoadingExcluded] = useState(false);
  const [confirmExcludeId, setConfirmExcludeId] = useState<string | null>(null);

  async function handlePreview() {
    setPreviewing(true);
    setError(null);
    setPreview(null);
    setResult(null);
    try {
      const r = await previewActivityFeeMatchTransactions(activityId);
      setPreview(r);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "매칭 분석 실패");
    } finally {
      setPreviewing(false);
    }
  }

  async function handleConfirm() {
    if (!preview) return;
    setConfirming(true);
    setError(null);
    try {
      const r = await confirmActivityFeeMatchTransactions(activityId, preview.confirm_payload.action_id);
      setResult(r);
      setPreview(null);
      onUpdated();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "매칭 적용 실패");
    } finally {
      setConfirming(false);
    }
  }

  async function handleCancel() {
    if (!preview) return;
    try {
      await cancelActivityFeeMatchTransactions(activityId, preview.confirm_payload.action_id);
    } catch { /* ignore */ }
    setPreview(null);
    setError(null);
  }

  async function handleExclude(transactionId: string) {
    setExcludingId(transactionId);
    setConfirmExcludeId(null);
    try {
      await excludeActivityFeeTransaction(activityId, transactionId);
      // Re-run preview to refresh
      const r = await previewActivityFeeMatchTransactions(activityId);
      setPreview(r);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "제외 처리 실패");
    } finally {
      setExcludingId(null);
    }
  }

  async function handleLoadExcluded() {
    setLoadingExcluded(true);
    try {
      const list = await getExcludedActivityFeeTransactions(activityId);
      setExcludedList(list);
      setShowExcluded(true);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "제외 목록 조회 실패");
    } finally {
      setLoadingExcluded(false);
    }
  }

  async function handleInclude(transactionId: string) {
    try {
      await includeActivityFeeTransaction(activityId, transactionId);
      const list = await getExcludedActivityFeeTransactions(activityId);
      setExcludedList(list);
      // Re-run preview if open
      if (preview) {
        const r = await previewActivityFeeMatchTransactions(activityId);
        setPreview(r);
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "제외 해제 실패");
    }
  }

  const MATCH_STATUS_LABELS: Record<string, string> = {
    auto_match_candidate: "자동 후보",
    amount_mismatch: "금액 불일치",
    name_check_required: "이름 확인 필요",
    already_paid: "이미 납부",
    already_matched: "이미 매칭",
    unmatched: "미매칭",
  };
  const MATCH_STATUS_COLORS: Record<string, string> = {
    auto_match_candidate: "var(--success)",
    amount_mismatch: "var(--danger)",
    name_check_required: "var(--warning)",
    already_paid: "var(--text-muted)",
    already_matched: "var(--text-muted)",
    unmatched: "var(--text-muted)",
  };

  return (
    <>
    {/* 제외 확인 모달 */}
    {confirmExcludeId && (
      <Modal isOpen onClose={() => setConfirmExcludeId(null)} title="거래 제외">
        <div className="space-y-4">
          <p className="text-sm" style={{ color: "var(--text-main)" }}>
            이 거래를 현재 활동의 활동비 매칭 후보에서 제외하시겠습니까?
          </p>
          <p className="text-xs" style={{ color: "var(--text-muted)" }}>
            이 작업은 현재 활동의 활동비 매칭에만 적용됩니다. 회비 매칭 및 다른 활동에는 영향 없습니다.
          </p>
          <div className="flex gap-2 justify-end">
            <Button size="sm" variant="secondary" onClick={() => setConfirmExcludeId(null)}>취소</Button>
            <Button
              size="sm"
              variant="danger"
              onClick={() => handleExclude(confirmExcludeId)}
              loading={excludingId === confirmExcludeId}
            >
              제외
            </Button>
          </div>
        </div>
      </Modal>
    )}

    <Card padding="lg">
      <div className="flex items-start justify-between gap-3 mb-2">
        <h3 className="text-sm font-semibold" style={{ color: "var(--text-main)" }}>
          거래내역 매칭
        </h3>
        {preview && (
          <div className="flex gap-2">
            <Button size="sm" variant="secondary" onClick={handleCancel} disabled={confirming}>
              취소
            </Button>
            <Button
              size="sm"
              onClick={handleConfirm}
              disabled={confirming || preview.summary.auto_match_candidates === 0}
              loading={confirming}
            >
              확인 후 반영 ({preview.summary.auto_match_candidates}건)
            </Button>
          </div>
        )}
      </div>
      <p className="text-xs mb-3" style={{ color: "var(--text-muted)" }}>
        이 활동의 활동비만 매칭합니다. 금액 exact match만 자동 후보입니다. 회비는 절대 수정되지 않습니다.
      </p>

      <div className="flex gap-2 flex-wrap">
        {!preview && (
          <Button size="sm" onClick={handlePreview} disabled={previewing} loading={previewing}>
            거래내역에서 이 활동 활동비 매칭
          </Button>
        )}
        <Button
          size="sm"
          variant="secondary"
          onClick={handleLoadExcluded}
          loading={loadingExcluded}
        >
          제외된 거래 보기
        </Button>
      </div>

      {error && <p className="mt-2 text-xs" style={{ color: "var(--danger)" }}>{error}</p>}

      {result && (
        <div className="rounded-xl p-3 mt-2" style={{ background: "var(--success-soft)", border: "1px solid rgba(63,125,88,0.15)" }}>
          <p className="text-xs font-semibold" style={{ color: "var(--success)" }}>활동비 매칭 완료</p>
          <p className="text-xs mt-0.5" style={{ color: "var(--success)" }}>
            {result.matched_count}건 납부 완료 처리 · {result.skipped_count}건 건너뜀
          </p>
        </div>
      )}

      {/* 제외된 거래 목록 */}
      {showExcluded && (
        <div className="mt-3 rounded-xl p-3" style={{ background: "var(--surface-soft)", border: "1px solid var(--border-soft)" }}>
          <div className="flex items-center justify-between mb-2">
            <p className="text-xs font-semibold" style={{ color: "var(--text-main)" }}>
              제외된 거래 ({excludedList.length}건)
            </p>
            <button
              className="text-xs"
              style={{ color: "var(--text-muted)" }}
              onClick={() => setShowExcluded(false)}
            >
              닫기
            </button>
          </div>
          {excludedList.length === 0 ? (
            <p className="text-xs" style={{ color: "var(--text-muted)" }}>제외된 거래가 없습니다.</p>
          ) : (
            <div className="space-y-1.5">
              {excludedList.map((item) => (
                <div
                  key={item.exclusion_id}
                  className="flex items-center justify-between gap-2 rounded-lg p-2"
                  style={{ background: "var(--surface)", border: "1px solid var(--border-soft)" }}
                >
                  <div className="text-xs" style={{ color: "var(--text-main)" }}>
                    <span className="font-medium">{item.transaction?.memo ?? "-"}</span>
                    <span className="ml-2" style={{ color: "var(--text-muted)" }}>
                      {item.transaction ? `${item.transaction.deposit_amount.toLocaleString("ko-KR")}원` : ""}
                    </span>
                    {item.reason && (
                      <span className="ml-2" style={{ color: "var(--text-muted)" }}>({item.reason})</span>
                    )}
                  </div>
                  <Button
                    size="sm"
                    variant="secondary"
                    onClick={() => handleInclude(item.transaction_id)}
                  >
                    제외 해제
                  </Button>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {preview && (
        <div className="mt-3 space-y-3">
          {/* Summary mini-cards */}
          <div className="grid grid-cols-3 gap-2">
            {[
              ["자동 후보", preview.summary.auto_match_candidates, "var(--success)"],
              ["금액 불일치", preview.summary.amount_mismatch, "var(--danger)"],
              ["이름 확인", preview.summary.name_check_required, "var(--warning)"],
              ["이미 납부", preview.summary.already_paid, "var(--text-muted)"],
              ["이미 매칭", preview.summary.already_matched, "var(--text-muted)"],
              ["미매칭", preview.summary.unmatched, "var(--text-muted)"],
              ["제외됨", preview.summary.excluded_transactions, "var(--text-muted)"],
            ].map(([label, val, color]) => (
              <div key={String(label)} className="rounded-lg p-2 text-center" style={{ background: "var(--surface-soft)" }}>
                <p className="text-xs" style={{ color: "var(--text-muted)" }}>{label}</p>
                <p className="text-sm font-semibold" style={{ color: String(color) }}>{String(val)}</p>
              </div>
            ))}
          </div>
          {/* Preview table */}
          <div className="overflow-x-auto">
            <table className="w-full text-xs" style={{ borderCollapse: "collapse" }}>
              <thead>
                <tr style={{ borderBottom: "1px solid var(--border-soft)" }}>
                  {["거래일", "적요", "추정 참가자", "필요", "입금", "차액", "상태", "사유", ""].map((h) => (
                    <th key={h} className="text-left py-1.5 px-2 font-medium" style={{ color: "var(--text-muted)" }}>
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {preview.rows
                  .filter((r) => r.match_status !== "unmatched" && r.match_status !== "already_matched")
                  .slice(0, 30)
                  .map((row) => (
                    <tr key={row.transaction_id} style={{ borderBottom: "1px solid var(--border-soft)" }}>
                      <td className="py-1.5 px-2" style={{ color: "var(--text-muted)" }}>
                        {row.transaction_datetime?.slice(0, 10) ?? "-"}
                      </td>
                      <td className="py-1.5 px-2" style={{ color: "var(--text-main)" }}>{row.memo ?? "-"}</td>
                      <td className="py-1.5 px-2 font-medium" style={{ color: "var(--text-main)" }}>
                        {row.matched_member_name ?? "-"}
                      </td>
                      <td className="py-1.5 px-2 text-right" style={{ color: "var(--text-muted)" }}>
                        {row.required_amount != null ? row.required_amount.toLocaleString("ko-KR") : "-"}
                      </td>
                      <td className="py-1.5 px-2 text-right" style={{ color: "var(--text-main)" }}>
                        {row.deposit_amount.toLocaleString("ko-KR")}
                      </td>
                      <td
                        className="py-1.5 px-2 text-right"
                        style={{
                          color: row.amount_difference != null && row.amount_difference !== 0
                            ? "var(--danger)"
                            : "var(--text-muted)",
                        }}
                      >
                        {row.amount_difference != null && row.amount_difference !== 0
                          ? (row.amount_difference > 0 ? "+" : "") + row.amount_difference.toLocaleString("ko-KR")
                          : "-"}
                      </td>
                      <td className="py-1.5 px-2">
                        <span style={{ color: MATCH_STATUS_COLORS[row.match_status] ?? "var(--text-muted)", fontWeight: 500 }}>
                          {MATCH_STATUS_LABELS[row.match_status] ?? row.match_status}
                        </span>
                      </td>
                      <td className="py-1.5 px-2" style={{ color: "var(--text-muted)" }}>{row.reason}</td>
                      <td className="py-1.5 px-2">
                        <button
                          className="text-xs rounded px-1.5 py-0.5"
                          style={{ color: "var(--danger)", border: "1px solid var(--danger)", background: "transparent", cursor: "pointer", opacity: excludingId === row.transaction_id ? 0.5 : 1 }}
                          disabled={excludingId === row.transaction_id}
                          onClick={() => setConfirmExcludeId(row.transaction_id)}
                        >
                          이 거래 제외
                        </button>
                      </td>
                    </tr>
                  ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </Card>
    </>
  );
}

// ─── 수정 모달 ────────────────────────────────────────────────────────────────

function ActivityFeeEditModal({
  activityId,
  record,
  onClose,
  onSaved,
}: {
  activityId: string;
  record: ActivityFeeRecord;
  onClose: () => void;
  onSaved: () => void;
}) {
  const [requiredAmount, setRequiredAmount] = useState(record.required_amount);
  const [paidAmount, setPaidAmount] = useState(record.paid_amount);
  const [status, setStatus] = useState(record.status);
  const [refundStatus, setRefundStatus] = useState(record.refund_status || "none");
  const [autoCalc, setAutoCalc] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (autoCalc) {
      setStatus(autoStatus(paidAmount, requiredAmount));
    }
  }, [paidAmount, requiredAmount, autoCalc]);

  async function handleSave() {
    setSaving(true);
    setError(null);
    try {
      await updateActivityFeeRecord(activityId, record.id, {
        required_amount: requiredAmount,
        paid_amount: paidAmount,
        status,
        refund_status: refundStatus,
      });
      onSaved();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "저장에 실패했습니다.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <Modal isOpen onClose={onClose} title="납부 상태 수정">
      <div className="space-y-4">
        <div
          className="rounded-xl p-3 text-sm"
          style={{ background: "var(--surface-soft)", border: "1px solid var(--border-soft)" }}
        >
          <p className="font-medium" style={{ color: "var(--text-main)" }}>
            {record.member_name}
            {record.student_id && (
              <span className="ml-1.5 text-xs font-normal" style={{ color: "var(--text-muted)" }}>
                ({record.student_id})
              </span>
            )}
          </p>
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="block text-xs font-medium mb-1" style={{ color: "var(--text-muted)" }}>
              필요 금액 (원)
            </label>
            <input
              type="number"
              className="w-full rounded-xl px-3 py-2 text-sm focus:outline-none min-h-[44px]"
              style={{ background: "var(--surface)", color: "var(--text-main)", border: "1px solid var(--border-soft)" }}
              value={requiredAmount}
              onChange={(e) => setRequiredAmount(Number(e.target.value))}
            />
          </div>
          <div>
            <label className="block text-xs font-medium mb-1" style={{ color: "var(--text-muted)" }}>
              납부 금액 (원)
            </label>
            <input
              type="number"
              className="w-full rounded-xl px-3 py-2 text-sm focus:outline-none min-h-[44px]"
              style={{ background: "var(--surface)", color: "var(--text-main)", border: "1px solid var(--border-soft)" }}
              value={paidAmount}
              onChange={(e) => setPaidAmount(Number(e.target.value))}
            />
          </div>
        </div>
        <label className="flex items-center gap-2 text-sm cursor-pointer" style={{ color: "var(--text-main)" }}>
          <input type="checkbox" checked={autoCalc} onChange={(e) => setAutoCalc(e.target.checked)} />
          납부 금액 기반 상태 자동 계산
        </label>
        <div>
          <label className="block text-xs font-medium mb-1" style={{ color: "var(--text-muted)" }}>
            납부 상태
          </label>
          <select
            className="w-full rounded-xl px-3 py-2 text-sm focus:outline-none min-h-[44px]"
            style={{ background: "var(--surface)", color: "var(--text-main)", border: "1px solid var(--border-soft)" }}
            value={status}
            disabled={autoCalc}
            onChange={(e) => { setStatus(e.target.value); setAutoCalc(false); }}
          >
            <option value="unpaid">미납</option>
            <option value="partial">부분 납부</option>
            <option value="paid">납부 완료</option>
            <option value="overpaid">초과 납부</option>
            <option value="need_check">확인 필요</option>
            <option value="exempt">면제</option>
          </select>
        </div>
        <div>
          <label className="block text-xs font-medium mb-1" style={{ color: "var(--text-muted)" }}>
            환불 상태
          </label>
          <select
            className="w-full rounded-xl px-3 py-2 text-sm focus:outline-none min-h-[44px]"
            style={{ background: "var(--surface)", color: "var(--text-main)", border: "1px solid var(--border-soft)" }}
            value={refundStatus}
            onChange={(e) => setRefundStatus(e.target.value)}
          >
            <option value="none">없음</option>
            <option value="refund_required">환불 필요</option>
            <option value="refund_pending">환불 대기</option>
            <option value="refunded">환불 완료</option>
          </select>
        </div>
        {error && <p className="text-sm" style={{ color: "var(--danger)" }}>{error}</p>}
        <div className="flex gap-2">
          <Button className="flex-1 min-h-[44px]" onClick={handleSave} loading={saving}>
            저장
          </Button>
          <Button className="flex-1 min-h-[44px]" variant="secondary" onClick={onClose} disabled={saving}>
            취소
          </Button>
        </div>
      </div>
    </Modal>
  );
}

// ─── 매칭 취소 모달 ───────────────────────────────────────────────────────────

function ActivityFeeUnmatchModal({
  activityId,
  record,
  onClose,
  onDone,
}: {
  activityId: string;
  record: ActivityFeeRecord;
  onClose: () => void;
  onDone: () => void;
}) {
  const [keepPaid, setKeepPaid] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleConfirm() {
    setBusy(true);
    setError(null);
    try {
      await unmatchActivityFeeRecord(activityId, record.id, keepPaid);
      onDone();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "매칭 취소에 실패했습니다.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Modal isOpen onClose={onClose} title="매칭 취소">
      <div className="space-y-4">
        <p className="text-sm" style={{ color: "var(--text-main)" }}>
          <span className="font-medium">{record.member_name}</span>의 거래내역 매칭을 취소하시겠습니까?
        </p>
        <div className="space-y-2">
          <label
            className="flex items-start gap-3 text-sm cursor-pointer rounded-xl p-3"
            style={{
              border: `1px solid ${keepPaid ? "var(--primary)" : "var(--border-soft)"}`,
              background: keepPaid ? "var(--primary-soft)" : "transparent",
            }}
          >
            <input type="radio" className="mt-0.5" checked={keepPaid} onChange={() => setKeepPaid(true)} />
            <div>
              <p className="font-medium" style={{ color: "var(--text-main)" }}>납부 금액 유지</p>
              <p className="text-xs mt-0.5" style={{ color: "var(--text-muted)" }}>
                매칭만 해제하고 납부 금액({fmt(record.paid_amount)}원)은 유지합니다.
              </p>
            </div>
          </label>
          <label
            className="flex items-start gap-3 text-sm cursor-pointer rounded-xl p-3"
            style={{
              border: `1px solid ${!keepPaid ? "var(--danger)" : "var(--border-soft)"}`,
              background: !keepPaid ? "var(--danger-soft)" : "transparent",
            }}
          >
            <input type="radio" className="mt-0.5" checked={!keepPaid} onChange={() => setKeepPaid(false)} />
            <div>
              <p className="font-medium" style={{ color: "var(--text-main)" }}>납부 금액 0원으로 초기화</p>
              <p className="text-xs mt-0.5" style={{ color: "var(--text-muted)" }}>
                매칭 해제 및 납부 금액을 0원으로 되돌립니다.
              </p>
            </div>
          </label>
        </div>
        {error && <p className="text-sm" style={{ color: "var(--danger)" }}>{error}</p>}
        <div className="flex gap-2">
          <Button className="flex-1 min-h-[44px]" onClick={handleConfirm} loading={busy}>
            매칭 취소 확인
          </Button>
          <Button className="flex-1 min-h-[44px]" variant="secondary" onClick={onClose} disabled={busy}>
            닫기
          </Button>
        </div>
      </div>
    </Modal>
  );
}

// ─── 빠른 작업 확인 모달 ──────────────────────────────────────────────────────

function QuickActionModal({
  title,
  message,
  onConfirm,
  onClose,
  danger = false,
}: {
  title: string;
  message: string;
  onConfirm: () => Promise<void>;
  onClose: () => void;
  danger?: boolean;
}) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handle() {
    setBusy(true);
    setError(null);
    try {
      await onConfirm();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "작업에 실패했습니다.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Modal isOpen onClose={onClose} title={title}>
      <div className="space-y-4">
        <p className="text-sm" style={{ color: "var(--text-main)" }}>{message}</p>
        {error && <p className="text-sm" style={{ color: "var(--danger)" }}>{error}</p>}
        <div className="flex gap-2">
          <Button className="flex-1 min-h-[44px]" variant={danger ? "danger" : "primary"} onClick={handle} loading={busy}>
            확인
          </Button>
          <Button className="flex-1 min-h-[44px]" variant="secondary" onClick={onClose} disabled={busy}>
            취소
          </Button>
        </div>
      </div>
    </Modal>
  );
}

// ─── 4. 납부 현황 테이블 ──────────────────────────────────────────────────────

type QuickActionType = "mark_paid" | "mark_partial" | "mark_unpaid" | "refund_needed" | "refund_complete";

const QUICK_ACTION_META: Record<
  QuickActionType,
  { title: string; message: (r: ActivityFeeRecord) => string; danger?: boolean }
> = {
  mark_paid: {
    title: "납부 완료 처리",
    message: (r) =>
      `${r.member_name}의 활동비를 납부 완료 처리합니다. 필요 금액(${fmt(r.required_amount)}원)이 납부된 것으로 처리됩니다.`,
  },
  mark_partial: {
    title: "부분 납부 처리",
    message: (r) => `${r.member_name}의 활동비를 부분 납부 상태로 변경합니다.`,
  },
  mark_unpaid: {
    title: "미납 처리",
    message: (r) => `${r.member_name}의 납부 금액을 0원으로 초기화하고 미납 상태로 변경합니다.`,
    danger: true,
  },
  refund_needed: {
    title: "환불 필요 표시",
    message: (r) => `${r.member_name}의 활동비를 환불 필요 상태로 표시합니다.`,
  },
  refund_complete: {
    title: "환불 완료 처리",
    message: (r) => `${r.member_name}의 활동비 환불이 완료된 것으로 처리합니다.`,
  },
};

function ActivityFeeRecordsTable({
  activityId,
  records,
  onUpdated,
}: {
  activityId: string;
  records: ActivityFeeRecord[];
  onUpdated: () => void;
}) {
  const [editRecord, setEditRecord] = useState<ActivityFeeRecord | null>(null);
  const [unmatchRecord, setUnmatchRecord] = useState<ActivityFeeRecord | null>(null);
  const [confirmAction, setConfirmAction] = useState<{
    record: ActivityFeeRecord;
    type: QuickActionType;
  } | null>(null);
  const [openMenuId, setOpenMenuId] = useState<string | null>(null);
  const menuRef = useRef<HTMLDivElement>(null);
  const [showCancelled, setShowCancelled] = useState(false);

  const activeRecords = records.filter((r) => r.status !== "cancelled");
  const cancelledRecords = records.filter((r) => r.status === "cancelled");
  const displayedRecords = showCancelled ? records : activeRecords;

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setOpenMenuId(null);
      }
    }
    if (openMenuId) document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [openMenuId]);

  async function executeQuickAction(record: ActivityFeeRecord, type: QuickActionType) {
    if (type === "mark_paid") {
      await updateActivityFeeRecord(activityId, record.id, {
        paid_amount: record.required_amount,
        status: "paid",
      });
    } else if (type === "mark_partial") {
      await updateActivityFeeRecord(activityId, record.id, { status: "partial" });
    } else if (type === "mark_unpaid") {
      await updateActivityFeeRecord(activityId, record.id, { paid_amount: 0, status: "unpaid" });
    } else if (type === "refund_needed") {
      await setRefundRequired(record.id, {});
    } else if (type === "refund_complete") {
      await setMarkRefunded(record.id, {});
    }
    onUpdated();
  }

  if (records.length === 0) {
    return (
      <Card padding="lg">
        <h3 className="text-sm font-semibold mb-2" style={{ color: "var(--text-main)" }}>납부 현황</h3>
        <p className="text-sm" style={{ color: "var(--text-muted)" }}>납부 대상이 없습니다. 활동비 설정에서 대상을 생성하세요.</p>
      </Card>
    );
  }

  return (
    <>
      <Card padding="none">
        <div className="p-4 flex flex-wrap items-center justify-between gap-3" style={{ borderBottom: "1px solid var(--border-soft)" }}>
          <h3 className="text-sm font-semibold" style={{ color: "var(--text-main)" }}>
            납부 현황 ({activeRecords.length}명
            {cancelledRecords.length > 0 && <span className="ml-1 text-xs font-normal" style={{ color: "var(--text-muted)" }}>/ 제외 {cancelledRecords.length}명</span>}
            )
          </h3>
          {cancelledRecords.length > 0 && (
            <button
              className="text-xs underline"
              style={{ color: "var(--text-muted)", background: "none", border: "none", cursor: "pointer" }}
              onClick={() => setShowCancelled((v) => !v)}
            >
              {showCancelled ? "제외된 기록 숨기기" : `제외된 기록 보기 (${cancelledRecords.length}명)`}
            </button>
          )}
        </div>
        {/* Desktop table */}
        <div className="hidden md:block overflow-x-auto">
          <table className="w-full text-sm" style={{ minWidth: 820 }}>
            <thead>
              <tr style={{ background: "var(--surface-soft)", borderBottom: "1px solid var(--border-soft)" }}>
                {["이름", "학번", "필요 금액", "납부 금액", "상태", "환불 상태", "매칭 거래", "작업"].map((h) => (
                  <th
                    key={h}
                    className="whitespace-nowrap px-3 py-3 text-left text-xs font-semibold uppercase tracking-wide"
                    style={{ color: "var(--text-muted)" }}
                  >
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {displayedRecords.map((r) => {
                const statusStyle = PAYMENT_STATUS_STYLE[r.status] ?? { bg: "var(--surface-soft)", text: "var(--text-muted)" };
                const refundColor = REFUND_STATUS_STYLE[r.refund_status ?? "none"] ?? "var(--text-muted)";
                const isMenuOpen = openMenuId === r.id;
                return (
                  <tr
                    key={r.id}
                    style={{ borderBottom: "1px solid var(--border-soft)" }}
                    onMouseEnter={(e) => (e.currentTarget.style.background = "var(--surface-soft)")}
                    onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}
                  >
                    <td className="whitespace-nowrap px-3 py-3 font-medium" style={{ color: "var(--text-main)" }}>
                      {r.member_name ?? "-"}
                    </td>
                    <td className="whitespace-nowrap px-3 py-3 text-xs" style={{ color: "var(--text-muted)" }}>
                      {r.student_id ?? "-"}
                    </td>
                    <td className="whitespace-nowrap px-3 py-3 text-right text-xs" style={{ color: "var(--text-main)" }}>
                      {fmt(r.required_amount)}
                    </td>
                    <td className="whitespace-nowrap px-3 py-3 text-right text-xs" style={{ color: "var(--text-main)" }}>
                      {fmt(r.paid_amount)}
                    </td>
                    <td className="whitespace-nowrap px-3 py-2">
                      <span
                        className="whitespace-nowrap text-xs px-2 py-0.5 rounded-full"
                        style={{ background: statusStyle.bg, color: statusStyle.text }}
                      >
                        {PAYMENT_STATUS_LABEL[r.status] ?? r.status}
                      </span>
                    </td>
                    <td className="whitespace-nowrap px-3 py-2">
                      {r.refund_status && r.refund_status !== "none" ? (
                        <span
                          className="whitespace-nowrap text-xs px-2 py-0.5 rounded-full"
                          style={{ background: "var(--surface-soft)", color: refundColor }}
                        >
                          {REFUND_STATUS_LABEL[r.refund_status] ?? r.refund_status}
                        </span>
                      ) : (
                        <span className="text-xs" style={{ color: "var(--text-muted)" }}>-</span>
                      )}
                    </td>
                    <td className="whitespace-nowrap px-3 py-2">
                      {r.transaction_id ? (
                        <span
                          className="whitespace-nowrap text-xs px-2 py-0.5 rounded-full"
                          style={{ background: "var(--success-soft)", color: "var(--success)" }}
                        >
                          매칭됨
                        </span>
                      ) : (
                        <span className="text-xs" style={{ color: "var(--text-muted)" }}>-</span>
                      )}
                    </td>
                    <td className="whitespace-nowrap px-3 py-2">
                      <div
                        className="flex items-center gap-1"
                        ref={isMenuOpen ? menuRef : undefined}
                      >
                        <Button size="sm" variant="ghost" onClick={() => setEditRecord(r)}>
                          수정
                        </Button>
                        <div className="relative">
                          <Button
                            size="sm"
                            variant="ghost"
                            onClick={() => setOpenMenuId(isMenuOpen ? null : r.id)}
                          >
                            <MoreHorizontal className="h-3.5 w-3.5" />
                          </Button>
                          {isMenuOpen && (
                            <div
                              className="absolute right-0 z-50 rounded-xl shadow-lg py-1 min-w-[160px]"
                              style={{
                                background: "var(--surface)",
                                border: "1px solid var(--border-soft)",
                                top: "calc(100% + 4px)",
                              }}
                            >
                              {[
                                { type: "mark_paid" as QuickActionType, label: "납부 완료 처리" },
                                { type: "mark_partial" as QuickActionType, label: "부분 납부 처리" },
                                { type: "mark_unpaid" as QuickActionType, label: "미납 처리", danger: true },
                                null,
                                { type: "refund_needed" as QuickActionType, label: "환불 필요 표시" },
                                { type: "refund_complete" as QuickActionType, label: "환불 완료 처리" },
                                ...(r.transaction_id
                                  ? [null, { type: "unmatch" as const, label: "매칭 취소", danger: true }]
                                  : []),
                              ].map((item, idx) => {
                                if (item === null) {
                                  return (
                                    <div
                                      key={idx}
                                      style={{ height: 1, background: "var(--border-soft)", margin: "4px 0" }}
                                    />
                                  );
                                }
                                const isDanger = (item as { danger?: boolean }).danger === true;
                                return (
                                  <button
                                    key={item.type}
                                    className="w-full text-left px-3 py-2 text-sm transition-colors"
                                    style={{
                                      color: isDanger ? "var(--danger)" : "var(--text-main)",
                                    }}
                                    onMouseEnter={(e) => (e.currentTarget.style.background = "var(--surface-soft)")}
                                    onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}
                                    onClick={() => {
                                      setOpenMenuId(null);
                                      if (item.type === "unmatch") {
                                        setUnmatchRecord(r);
                                      } else {
                                        setConfirmAction({ record: r, type: item.type as QuickActionType });
                                      }
                                    }}
                                  >
                                    {item.label}
                                  </button>
                                );
                              })}
                            </div>
                          )}
                        </div>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
        {/* Mobile cards */}
        <div className="md:hidden divide-y" style={{ borderTop: "1px solid var(--border-soft)" }}>
          {displayedRecords.map((r) => {
            const statusStyle = PAYMENT_STATUS_STYLE[r.status] ?? { bg: "var(--surface-soft)", text: "var(--text-muted)" };
            return (
              <div key={r.id} className="p-4">
                <div className="flex items-center justify-between gap-2">
                  <div>
                    <p className="font-medium text-sm" style={{ color: "var(--text-main)" }}>{r.member_name ?? "-"}</p>
                    {r.student_id && (
                      <p className="text-xs" style={{ color: "var(--text-muted)" }}>{r.student_id}</p>
                    )}
                  </div>
                  <span
                    className="whitespace-nowrap text-xs px-2 py-0.5 rounded-full"
                    style={{ background: statusStyle.bg, color: statusStyle.text }}
                  >
                    {PAYMENT_STATUS_LABEL[r.status] ?? r.status}
                  </span>
                </div>
                <div className="flex items-center justify-between mt-2">
                  <p className="text-xs" style={{ color: "var(--text-muted)" }}>
                    필요: {fmt(r.required_amount)}원 / 납부: {fmt(r.paid_amount)}원
                  </p>
                  <Button size="sm" variant="ghost" onClick={() => setEditRecord(r)}>
                    수정
                  </Button>
                </div>
              </div>
            );
          })}
        </div>
      </Card>

      {editRecord && (
        <ActivityFeeEditModal
          activityId={activityId}
          record={editRecord}
          onClose={() => setEditRecord(null)}
          onSaved={() => { setEditRecord(null); onUpdated(); }}
        />
      )}

      {unmatchRecord && (
        <ActivityFeeUnmatchModal
          activityId={activityId}
          record={unmatchRecord}
          onClose={() => setUnmatchRecord(null)}
          onDone={() => { setUnmatchRecord(null); onUpdated(); }}
        />
      )}

      {confirmAction && (() => {
        const meta = QUICK_ACTION_META[confirmAction.type];
        return (
          <QuickActionModal
            title={meta.title}
            message={meta.message(confirmAction.record)}
            danger={meta.danger}
            onConfirm={async () => {
              await executeQuickAction(confirmAction.record, confirmAction.type);
              setConfirmAction(null);
            }}
            onClose={() => setConfirmAction(null)}
          />
        );
      })()}
    </>
  );
}

// ─── ActivityFeeTab (메인) ────────────────────────────────────────────────────

export function ActivityFeeTab({
  activityId,
  feeInfo,
  onUpdated,
}: {
  activityId: string;
  feeInfo: ActivityDetail["activity_fee"];
  onUpdated: () => void;
}) {
  return (
    <div className="space-y-4">
      {/* 1. 활동비 설정 */}
      <ActivityFeeSettingsPanel
        activityId={activityId}
        defaultAmount={feeInfo.amount}
        onUpdated={onUpdated}
      />

      {/* 2. 활동비 요약 */}
      {feeInfo.records.length > 0 && (
        <Card padding="lg">
          <h3 className="text-sm font-semibold mb-3" style={{ color: "var(--text-main)" }}>
            활동비 요약
          </h3>
          <ActivityFeeSummaryCards records={feeInfo.records} />
        </Card>
      )}

      {/* 3. 거래내역 매칭 */}
      {feeInfo.records.length > 0 && (
        <ActivityFeeMatchSection activityId={activityId} onUpdated={onUpdated} />
      )}

      {/* 4. 납부 현황 */}
      <ActivityFeeRecordsTable activityId={activityId} records={feeInfo.records} onUpdated={onUpdated} />
    </div>
  );
}
