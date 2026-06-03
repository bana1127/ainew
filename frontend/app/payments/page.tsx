"use client";

import React, { useCallback, useEffect, useRef, useState, Suspense } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import {
  ManualPaymentRecordPayload,
  Member,
  MembershipFeePreview,
  MembershipPaymentHistoryItem,
  PaymentMatchingPreview,
  PaymentMatchingResult,
  PaymentRecord,
  PaymentSummary,
  TransactionMatchItem,
  applyPaymentMatching,
  confirmPaymentTransaction,
  excludePaymentTransaction,
  getPaymentRecords,
  getPaymentSummary,
  getMembershipHistory,
  getMembersFiltered,
  patchMembershipPaymentRecord,
  previewMembershipFees,
  previewPaymentMatching,
  confirmAssistantAction,
  unmatchPaymentRecord,
  setRefundRequired,
  setRefundPending,
  setMarkRefunded,
  setRefundCancel,
} from "@/lib/api";

import { AppShell } from "@/components/layout/AppShell";
import { MembershipBulkUpdateModal } from "@/components/payments/MembershipBulkUpdateModal";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorState } from "@/components/ui/ErrorState";
import { PageHeader } from "@/components/ui/PageHeader";
import { StatusBadge } from "@/components/ui/StatusBadge";

function fmt(n: number | null | undefined): string {
  if (n == null) return "-";
  return n.toLocaleString("ko-KR");
}

function fmtDt(s: string | null | undefined): string {
  if (!s) return "-";
  return s.replace("T", " ").slice(0, 16);
}

function feeTierLabel(tier: string | null | undefined): string {
  if (tier === "new") return "신규";
  if (tier === "existing") return "기존";
  if (tier === "executive") return "임원";
  return "-";
}

const inputStyle: React.CSSProperties = {
  background: "var(--surface)",
  color: "var(--text-main)",
  border: "1px solid var(--border-soft)",
  borderRadius: "12px",
  padding: "8px 12px",
  fontSize: "14px",
  width: "100%",
};

function BulkActionBar({
  selectedCount,
  onClear,
  onOpen,
}: {
  selectedCount: number;
  onClear: () => void;
  onOpen: () => void;
}) {
  if (selectedCount === 0) return null;
  return (
    <div
      className="flex flex-col gap-3 px-5 py-3 sm:flex-row sm:items-center sm:justify-between"
      style={{ background: "var(--primary-soft)", borderBottom: "1px solid var(--border-soft)" }}
    >
      <p className="text-sm font-medium" style={{ color: "var(--text-main)" }}>
        {selectedCount}건 선택됨
      </p>
      <div className="flex flex-wrap gap-2">
        <Button size="sm" variant="secondary" onClick={onClear}>
          선택 해제
        </Button>
        <Button size="sm" onClick={onOpen}>
          일괄 변경
        </Button>
      </div>
    </div>
  );
}

// ─── Membership Fee Tab ───────────────────────────────────────────────────────

function MembershipFeeTab() {
  const [period, setPeriod] = useState("2026-1");
  const [requiredAmount, setRequiredAmount] = useState(0);
  const [newMemberFee, setNewMemberFee] = useState(15000);
  const [existingMemberFee, setExistingMemberFee] = useState(10000);
  const [executiveFee, setExecutiveFee] = useState(0);
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [matchMode, setMatchMode] = useState("membership_fee");
  const [unmatching, setUnmatching] = useState<string | null>(null);

  const [previewing, setPreviewing] = useState(false);
  const [applying, setApplying] = useState(false);
  const [preview, setPreview] = useState<PaymentMatchingPreview | null>(null);
  const [applyResult, setApplyResult] = useState<PaymentMatchingResult | null>(null);
  const [feePreview, setFeePreview] = useState<MembershipFeePreview | null>(null);
  const [feePreviewing, setFeePreviewing] = useState(false);
  const [feeApplying, setFeeApplying] = useState(false);
  const [feeApplyResult, setFeeApplyResult] = useState<Record<string, unknown> | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  const [summary, setSummary] = useState<PaymentSummary | null>(null);
  const [records, setRecords] = useState<PaymentRecord[]>([]);
  const [history, setHistory] = useState<MembershipPaymentHistoryItem[]>([]);
  const [selectedRecordIds, setSelectedRecordIds] = useState<string[]>([]);
  const lastSelectionIndexRef = useRef<number | null>(null);
  const [statusFilter, setStatusFilter] = useState("all");
  const [tierFilter, setTierFilter] = useState("all");
  const [sourceFilter, setSourceFilter] = useState("all");
  const [recordSearch, setRecordSearch] = useState("");
  const [bulkModalOpen, setBulkModalOpen] = useState(false);
  const [loadingData, setLoadingData] = useState(false);
  const [memberPageSize, setMemberPageSize] = useState<number | "all">("all");
  const [memberPage, setMemberPage] = useState(1);

  const [confirmTarget, setConfirmTarget] = useState<TransactionMatchItem | null>(null);
  const [members, setMembers] = useState<Member[]>([]);
  const [confirmMemberId, setConfirmMemberId] = useState("");
  const [confirming, setConfirming] = useState(false);
  const [excluding, setExcluding] = useState<string | null>(null);

  const [manualTarget, setManualTarget] = useState<PaymentRecord | null>(null);
  const [manualForm, setManualForm] = useState<ManualPaymentRecordPayload>({
    member_id: "", period: "2026-1", payment_type: "membership_fee",
    required_amount: 0, paid_amount: 0, status: "paid",
  });
  const [manualSaving, setManualSaving] = useState(false);
  const [manualError, setManualError] = useState<string | null>(null);

  async function loadData(p = period) {
    setLoadingData(true);
    try {
      const [s, r, h] = await Promise.all([
        getPaymentSummary({ period: p, payment_type: "membership_fee" }),
        getPaymentRecords({ period: p, payment_type: "membership_fee" }),
        getMembershipHistory({ period: p, limit: 100 }),
      ]);
      setSummary(s);
      setRecords(r);
      setHistory(h);
      setSelectedRecordIds((current) => current.filter((id) => r.some((record) => record.id === id)));
    } catch { /* silently ignore */ }
    finally { setLoadingData(false); }
  }

  useEffect(() => { loadData(); }, []);

  async function handleFeePreview() {
    setActionError(null);
    setFeeApplyResult(null);
    setFeePreviewing(true);
    try {
      const result = await previewMembershipFees({
        period,
        new_member_fee: newMemberFee,
        existing_member_fee: existingMemberFee,
        executive_fee: executiveFee,
      });
      setFeePreview(result);
      setPeriod(result.current_term);
      await loadData(result.current_term);
    } catch (e: unknown) {
      setActionError(e instanceof Error ? e.message : String(e));
    } finally {
      setFeePreviewing(false);
    }
  }

  async function handleFeeConfirm() {
    if (!feePreview?.action_id) return;
    setActionError(null);
    setFeeApplying(true);
    try {
      const result = await confirmAssistantAction(feePreview.action_id);
      setFeeApplyResult(result.result ?? {});
      await loadData(feePreview.current_term);
    } catch (e: unknown) {
      setActionError(e instanceof Error ? e.message : String(e));
    } finally {
      setFeeApplying(false);
    }
  }

  async function handleUnmatchRecord(recordId: string) {
    if (!confirm("이 거래내역 매칭을 취소하시겠습니까?\n납부 상태가 미납 또는 부분 납부로 되돌아갈 수 있습니다.")) return;
    setUnmatching(recordId);
    try {
      await unmatchPaymentRecord(recordId);
      await loadData(period);
    } catch (e: unknown) {
      setActionError(e instanceof Error ? e.message : String(e));
    } finally { setUnmatching(null); }
  }

  async function handlePreview() {
    setActionError(null);
    setApplyResult(null);
    setPreviewing(true);
    try {
      const result = await previewPaymentMatching({
        period, payment_type: "membership_fee",
        required_amount: requiredAmount || null,
        start_date: startDate || null, end_date: endDate || null,
        match_mode: matchMode,
      });
      setPreview(result);
    } catch (e: unknown) {
      setActionError(e instanceof Error ? e.message : String(e));
    } finally { setPreviewing(false); }
  }

  async function handleApply() {
    setActionError(null);
    setApplying(true);
    try {
      const result = await applyPaymentMatching({
        period, payment_type: "membership_fee",
        required_amount: requiredAmount || null,
        start_date: startDate || null, end_date: endDate || null,
        match_mode: matchMode,
      });
      setApplyResult(result);
      setPreview(result);
      await loadData();
    } catch (e: unknown) {
      setActionError(e instanceof Error ? e.message : String(e));
    } finally { setApplying(false); }
  }

  function handleConfirm(item: TransactionMatchItem) {
    setConfirmTarget(item);
    setConfirmMemberId(item.matched_member_id ?? "");
    getMembersFiltered({ status: "active" }).then(setMembers).catch(() => {});
  }

  async function submitConfirm() {
    if (!confirmTarget || !confirmMemberId) return;
    setConfirming(true);
    try {
      await confirmPaymentTransaction(confirmTarget.transaction_id, {
        member_id: confirmMemberId, period,
        payment_type: "membership_fee",
        required_amount: requiredAmount, status: "paid",
      });
      setConfirmTarget(null);
      await handlePreview();
      await loadData();
    } catch (e: unknown) {
      setActionError(e instanceof Error ? e.message : String(e));
    } finally { setConfirming(false); }
  }

  async function handleExclude(transactionId: string) {
    setExcluding(transactionId);
    try {
      await excludePaymentTransaction(transactionId, { payment_type: "other", reason: "manual_exclude" });
      await handlePreview();
    } catch (e: unknown) {
      setActionError(e instanceof Error ? e.message : String(e));
    } finally { setExcluding(null); }
  }

  function openManualEdit(item: PaymentRecord) {
    const initStatus = (item.status as ManualPaymentRecordPayload["status"]) ?? "unpaid";
    const initPaid = initStatus === "paid" ? (item.paid_amount || item.required_amount) : item.paid_amount;
    setManualTarget(item);
    setManualForm({
      member_id: item.member_id,
      period,
      payment_type: "membership_fee",
      required_amount: item.required_amount || requiredAmount,
      paid_amount: initPaid,
      status: initStatus,
      manual_note: item.manual_note ?? null,
    });
    setManualError(null);
  }

  async function handleManualSave() {
    setManualSaving(true);
    setManualError(null);
    try {
      if (!manualTarget) throw new Error("수정할 납부 기록을 찾을 수 없습니다.");
      await patchMembershipPaymentRecord(manualTarget.id, {
        required_amount: manualForm.required_amount,
        paid_amount: manualForm.paid_amount,
        status: manualForm.status,
        manual_note: manualForm.manual_note ?? null,
      });
      setManualTarget(null);
      await loadData(period);
    } catch (err: unknown) {
      setManualError(err instanceof Error ? err.message : "저장에 실패했습니다.");
    } finally { setManualSaving(false); }
  }

  function handleStatusChange(newStatus: string) {
    let newPaid = manualForm.paid_amount;
    if (newStatus === "paid") newPaid = manualForm.required_amount;
    else if (newStatus === "unpaid" || newStatus === "exempt") newPaid = 0;
    setManualForm((f) => ({ ...f, status: newStatus as ManualPaymentRecordPayload["status"], paid_amount: newPaid }));
  }

  function toggleRecordSelection(recordId: string, checked: boolean, shiftKey = false) {
    const currentIndex = filteredRecords.findIndex((record) => record.id === recordId);
    setSelectedRecordIds((current) => {
      if (shiftKey && lastSelectionIndexRef.current !== null && currentIndex >= 0) {
        const start = Math.min(lastSelectionIndexRef.current, currentIndex);
        const end = Math.max(lastSelectionIndexRef.current, currentIndex);
        const rangeIds = filteredRecords.slice(start, end + 1).map((record) => record.id);
        if (checked) return Array.from(new Set([...current, ...rangeIds]));
        return current.filter((id) => !rangeIds.includes(id));
      }
      if (checked) return current.includes(recordId) ? current : [...current, recordId];
      return current.filter((id) => id !== recordId);
    });
    if (currentIndex >= 0) lastSelectionIndexRef.current = currentIndex;
  }

  function toggleAllRecords(checked: boolean) {
    const filteredIds = filteredRecords.map((record) => record.id);
    setSelectedRecordIds((current) => {
      if (checked) return Array.from(new Set([...current, ...filteredIds]));
      return current.filter((id) => !filteredIds.includes(id));
    });
  }

  function sourceLabel(record: PaymentRecord): string {
    if (record.payment_source === "transaction_match" || record.transaction_id) return "거래매칭";
    if (record.payment_source === "manual") return "수동";
    if (record.payment_source === "imported") return "가져오기";
    return "없음";
  }

  const filteredRecords = records.filter((record) => {
    if (statusFilter !== "all" && record.status !== statusFilter) return false;
    if (tierFilter !== "all" && (record.fee_tier ?? "") !== tierFilter) return false;
    const source = sourceLabel(record);
    if (sourceFilter !== "all" && source !== sourceFilter) return false;
    const q = recordSearch.trim().toLowerCase();
    if (q) {
      const haystack = [
        record.member_name,
        record.student_id,
        record.department,
        record.manual_note,
        record.fee_rule_reason,
      ].filter(Boolean).join(" ").toLowerCase();
      if (!haystack.includes(q)) return false;
    }
    return true;
  });

  const pagedRecords = memberPageSize === "all"
    ? filteredRecords
    : filteredRecords.slice((memberPage - 1) * (memberPageSize as number), memberPage * (memberPageSize as number));
  const totalMemberPages = memberPageSize === "all" ? 1 : Math.ceil(filteredRecords.length / (memberPageSize as number));

  const statusFilterLabel =
    statusFilter === "unpaid" ? "미납" :
    statusFilter === "paid" ? "납부완료" :
    statusFilter === "partial" ? "부분납부" :
    statusFilter === "need_check" ? "확인필요" :
    statusFilter === "exempt" ? "면제" :
    statusFilter === "overpaid" ? "초과납부" : "전체";

  const selectedRecordIdSet = new Set(selectedRecordIds);
  const selectedRecords = records.filter((record) => selectedRecordIdSet.has(record.id));
  const allRecordsSelected = filteredRecords.length > 0 && filteredRecords.every((record) => selectedRecordIdSet.has(record.id));

  const tblHeader = (labels: string[]) => (
    <tr style={{ background: "var(--surface-soft)", borderBottom: "1px solid var(--border-soft)" }}>
      {labels.map((h) => (
        <th key={h} className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide"
          style={{ color: "var(--text-muted)" }}>{h}</th>
      ))}
    </tr>
  );

  return (
    <div className="space-y-6">
      <Card padding="lg">
        <div className="flex flex-col gap-1 mb-5">
          <h2 className="text-base font-semibold" style={{ color: "var(--text-main)" }}>회비 대상 생성/갱신</h2>
          <p className="text-sm" style={{ color: "var(--text-muted)" }}>
            가입 학기와 임원 직위를 기준으로 신규 15,000원, 기존 10,000원, 임원 0원을 계산합니다.
          </p>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4">
          <div>
            <label className="block text-xs font-medium mb-1.5" style={{ color: "var(--text-muted)" }}>현재 학기</label>
            <input style={inputStyle} className="focus:outline-none min-h-[44px]" value={period}
              onChange={(e) => setPeriod(e.target.value)} placeholder="예: 2026-1" />
          </div>
          <div>
            <label className="block text-xs font-medium mb-1.5" style={{ color: "var(--text-muted)" }}>신규 부원 회비</label>
            <input type="number" style={inputStyle} className="focus:outline-none min-h-[44px]"
              value={newMemberFee} onChange={(e) => setNewMemberFee(Number(e.target.value))} />
          </div>
          <div>
            <label className="block text-xs font-medium mb-1.5" style={{ color: "var(--text-muted)" }}>기존 부원 회비</label>
            <input type="number" style={inputStyle} className="focus:outline-none min-h-[44px]"
              value={existingMemberFee} onChange={(e) => setExistingMemberFee(Number(e.target.value))} />
          </div>
          <div>
            <label className="block text-xs font-medium mb-1.5" style={{ color: "var(--text-muted)" }}>임원 회비</label>
            <input type="number" style={inputStyle} className="focus:outline-none min-h-[44px]"
              value={executiveFee} onChange={(e) => setExecutiveFee(Number(e.target.value))} />
          </div>
        </div>
        <div className="flex flex-wrap gap-3 mt-5">
          <Button className="flex-1 sm:flex-none" variant="secondary" onClick={handleFeePreview}
            disabled={feePreviewing || feeApplying} loading={feePreviewing}>회비 미리보기</Button>
          <Button className="flex-1 sm:flex-none" onClick={handleFeeConfirm}
            disabled={!feePreview?.action_id || feePreviewing || feeApplying} loading={feeApplying}>확정 생성/갱신</Button>
        </div>
        {feePreview && (
          <div className="mt-5 space-y-4">
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              {[
                { label: "현재 학기", value: feePreview.current_term },
                { label: "신규", value: `${feePreview.summary.new_member_count}명 / ${fmt(feePreview.new_member_fee)}원` },
                { label: "기존", value: `${feePreview.summary.existing_member_count}명 / ${fmt(feePreview.existing_member_fee)}원` },
                { label: "임원", value: `${feePreview.summary.executive_count}명 / ${fmt(feePreview.executive_fee)}원` },
                { label: "생성 예정", value: `${feePreview.summary.created_count}건` },
                { label: "갱신 예정", value: `${feePreview.summary.updated_count}건` },
                { label: "납부금 유지", value: `${feePreview.summary.preserved_paid_count}건` },
                { label: "총 필요 금액", value: `${fmt(feePreview.summary.total_required_amount)}원` },
              ].map((item) => (
                <div key={item.label} className="rounded-xl p-3"
                  style={{ background: "var(--surface-soft)", border: "1px solid var(--border-soft)" }}>
                  <p className="text-xs mb-1" style={{ color: "var(--text-muted)" }}>{item.label}</p>
                  <p className="text-sm font-semibold" style={{ color: "var(--text-main)" }}>{item.value}</p>
                </div>
              ))}
            </div>
            <div className="overflow-x-auto rounded-xl" style={{ border: "1px solid var(--border-soft)" }}>
              <table className="w-full text-sm">
                <thead>{tblHeader(["부원명", "가입 시기", "직위", "구분", "필요", "납부", "상태", "결정 사유"])}</thead>
                <tbody>
                  {feePreview.rows.map((row) => (
                    <tr key={row.member_id} style={{ borderBottom: "1px solid var(--border-soft)" }}>
                      <td className="px-4 py-2.5 font-medium" style={{ color: "var(--text-main)" }}>{row.member_name}</td>
                      <td className="px-4 py-2.5 text-xs" style={{ color: "var(--text-muted)" }}>
                        {row.joined_term ?? "-"}{row.term_code ? ` (${row.term_code})` : ""}
                      </td>
                      <td className="px-4 py-2.5 text-xs" style={{ color: "var(--text-main)" }}>{row.role_label}</td>
                      <td className="px-4 py-2.5 text-xs font-medium" style={{ color: "var(--text-main)" }}>{feeTierLabel(row.fee_tier)}</td>
                      <td className="px-4 py-2.5 text-right" style={{ color: "var(--text-main)" }}>{fmt(row.required_amount)}원</td>
                      <td className="px-4 py-2.5 text-right" style={{ color: "var(--text-main)" }}>{fmt(row.paid_amount)}원</td>
                      <td className="px-4 py-2.5"><StatusBadge status={row.status} /></td>
                      <td className="px-4 py-2.5 text-xs min-w-[240px]" style={{ color: "var(--text-muted)" }}>{row.fee_rule_reason}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
        {feeApplyResult && (
          <div className="mt-4 rounded-xl px-4 py-3 text-sm"
            style={{ background: "var(--success-soft)", color: "var(--success)", border: "1px solid rgba(63,125,88,0.15)" }}>
            회비 기록 생성/갱신 완료
          </div>
        )}
      </Card>

      {/* Matching config */}
      <Card padding="lg">
        <h2 className="text-base font-semibold mb-5" style={{ color: "var(--text-main)" }}>거래내역 매칭</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4">
          <div>
            <label className="block text-xs font-medium mb-1.5" style={{ color: "var(--text-muted)" }}>납부 기간</label>
            <input style={inputStyle} className="focus:outline-none min-h-[44px]" value={period}
              onChange={(e) => setPeriod(e.target.value)} placeholder="예: 2026-1" />
          </div>
          <div>
            <label className="block text-xs font-medium mb-1.5" style={{ color: "var(--text-muted)" }}>매칭 대상</label>
            <select style={inputStyle} className="focus:outline-none min-h-[44px]"
              value={matchMode} onChange={(e) => setMatchMode(e.target.value)}>
              <option value="auto">자동 판단</option>
              <option value="membership_fee">회비</option>
              <option value="activity_fee">활동비 (전체)</option>
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium mb-1.5" style={{ color: "var(--text-muted)" }}>납부 기준 금액 (원)</label>
            <input type="number" style={inputStyle} className="focus:outline-none min-h-[44px]"
              value={requiredAmount} onChange={(e) => setRequiredAmount(Number(e.target.value))} />
          </div>
          <div>
            <label className="block text-xs font-medium mb-1.5" style={{ color: "var(--text-muted)" }}>시작일</label>
            <input type="date" style={inputStyle} className="focus:outline-none min-h-[44px]" value={startDate}
              onChange={(e) => setStartDate(e.target.value)} />
          </div>
          <div>
            <label className="block text-xs font-medium mb-1.5" style={{ color: "var(--text-muted)" }}>종료일</label>
            <input type="date" style={inputStyle} className="focus:outline-none min-h-[44px]" value={endDate}
              onChange={(e) => setEndDate(e.target.value)} />
          </div>
        </div>
        <div className="flex flex-wrap gap-3 mt-5">
          <Button className="flex-1 sm:flex-none" variant="secondary" onClick={handlePreview} disabled={previewing || applying} loading={previewing}>미리보기</Button>
          <Button className="flex-1 sm:flex-none" onClick={handleApply} disabled={previewing || applying} loading={applying}>매칭 적용</Button>
          <Button className="flex-1 sm:flex-none" variant="ghost" onClick={() => loadData(period)} disabled={loadingData}>새로고침</Button>
        </div>
        {actionError && <div className="mt-4"><ErrorState message={actionError} /></div>}
        {applyResult && (
          <div className="mt-4 rounded-xl px-4 py-3 text-sm"
            style={{ background: "var(--success-soft)", color: "var(--success)", border: "1px solid rgba(63,125,88,0.15)" }}>
            매칭 적용 완료 — 생성 {applyResult.created_payment_records}건 / 수정 {applyResult.updated_payment_records}건
          </div>
        )}
      </Card>

      {/* Summary cards */}
      {summary && (
        <section>
          <h2 className="text-base font-semibold mb-4" style={{ color: "var(--text-main)" }}>납부 현황 요약</h2>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            {[
              { label: "전체 대상자", value: fmt(summary.total_members), style: {} },
              { label: "납부 완료", value: fmt(summary.paid_count), style: { background: "var(--success-soft)", border: "1px solid rgba(63,125,88,0.15)" } },
              { label: "부분 납부", value: fmt(summary.partial_count), style: { background: "var(--warning-soft)", border: "1px solid rgba(185,130,43,0.15)" } },
              { label: "미납", value: fmt(summary.unpaid_count), style: { background: "var(--danger-soft)", border: "1px solid rgba(185,74,72,0.15)" } },
              { label: "확인 필요", value: fmt(summary.need_check_count), style: { background: "var(--warning-soft)", border: "1px solid rgba(185,130,43,0.15)" } },
              { label: "면제", value: fmt(summary.exempt_count ?? 0), style: {} },
              { label: "초과 납부", value: fmt(summary.overpaid_count ?? 0), style: {} },
              { label: "총 예정 금액", value: `${fmt(summary.total_required_amount)}원`, style: {} },
              { label: "총 납부 금액", value: `${fmt(summary.total_paid_amount)}원`, style: { background: "var(--success-soft)", border: "1px solid rgba(63,125,88,0.15)" } },
            ].map((card) => (
              <div key={card.label} className="rounded-2xl p-4"
                style={{ background: "var(--surface)", border: "1px solid var(--border-soft)", ...card.style }}>
                <p className="text-xs mb-1.5" style={{ color: "var(--text-muted)" }}>{card.label}</p>
                <p className="text-xl font-semibold" style={{ color: "var(--text-main)" }}>{card.value}</p>
              </div>
            ))}
          </div>
          {(summary.missing_record_count ?? 0) > 0 && (
            <div className="mt-4 rounded-xl px-4 py-3 text-sm"
              style={{ background: "var(--warning-soft)", color: "var(--warning)", border: "1px solid rgba(185,130,43,0.15)" }}>
              회비 대상 기록이 아직 생성되지 않은 부원이 {fmt(summary.missing_record_count)}명 있습니다. 상단의 회비 대상 생성/동기화를 실행하세요.
            </div>
          )}
        </section>
      )}

      {/* Preview */}
      {preview && (
        <div className="space-y-5">
          <h2 className="text-base font-semibold" style={{ color: "var(--text-main)" }}>
            매칭 미리보기 ({preview.period} | {fmt(preview.required_amount)}원)
          </h2>
          {preview.matched_items.length > 0 && (
            <Card padding="none">
              <div className="p-4" style={{ borderBottom: "1px solid var(--border-soft)" }}>
                <h3 className="text-sm font-semibold" style={{ color: "var(--text-main)" }}>매칭 성공 ({preview.matched_items.length}건)</h3>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>{tblHeader(["거래일시", "적요", "입금액", "필요 금액", "차액", "매칭 부원", "상태"])}</thead>
                  <tbody>
                    {preview.matched_items.map((item) => (
                      <tr key={item.transaction_id} style={{ borderBottom: "1px solid var(--border-soft)" }}
                        onMouseEnter={(e) => (e.currentTarget.style.background = "var(--surface-soft)")}
                        onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}>
                        <td className="px-4 py-2.5 text-xs whitespace-nowrap" style={{ color: "var(--text-muted)" }}>{fmtDt(item.transaction_datetime)}</td>
                        <td className="px-4 py-2.5 max-w-[160px] truncate" title={item.memo ?? ""} style={{ color: "var(--text-main)" }}>{item.memo ?? "-"}</td>
                        <td className="px-4 py-2.5 text-right font-medium whitespace-nowrap" style={{ color: "var(--success)" }}>{fmt(item.deposit_amount)}원</td>
                        <td className="px-4 py-2.5 text-right whitespace-nowrap" style={{ color: "var(--text-main)" }}>{fmt(item.expected_amount)}원</td>
                        <td className="px-4 py-2.5 text-right" style={{ color: "var(--text-muted)" }}>
                          {item.amount_difference == null ? "-" : `${item.amount_difference > 0 ? "+" : ""}${fmt(item.amount_difference)}원`}
                        </td>
                        <td className="px-4 py-2.5" style={{ color: "var(--text-main)" }}>{item.matched_member_name ?? "-"}</td>
                        <td className="px-4 py-2.5"><StatusBadge status={item.match_status} /></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Card>
          )}
          {preview.need_check_items.length > 0 && (
            <Card padding="none">
              <div className="p-4" style={{ background: "var(--warning-soft)", borderBottom: "1px solid var(--border-soft)" }}>
                <h3 className="text-sm font-semibold" style={{ color: "var(--warning)" }}>확인 필요 ({preview.need_check_items.length}건)</h3>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>{tblHeader(["거래일시", "적요", "추정 부원", "필요 금액", "입금액", "차액", "상태", "사유", "수동 처리"])}</thead>
                  <tbody>
                    {preview.need_check_items.map((item) => (
                      <tr key={item.transaction_id} style={{ borderBottom: "1px solid var(--border-soft)" }}
                        onMouseEnter={(e) => (e.currentTarget.style.background = "var(--surface-soft)")}
                        onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}>
                        <td className="px-4 py-2.5 text-xs whitespace-nowrap" style={{ color: "var(--text-muted)" }}>{fmtDt(item.transaction_datetime)}</td>
                        <td className="px-4 py-2.5 max-w-[140px] truncate" title={item.memo ?? ""} style={{ color: "var(--text-main)" }}>{item.memo ?? "-"}</td>
                        <td className="px-4 py-2.5" style={{ color: "var(--text-main)" }}>{item.matched_member_name ?? "-"}</td>
                        <td className="px-4 py-2.5 text-right" style={{ color: "var(--text-main)" }}>{fmt(item.expected_amount)}원</td>
                        <td className="px-4 py-2.5 text-right font-medium" style={{ color: "var(--text-main)" }}>{fmt(item.deposit_amount)}원</td>
                        <td className="px-4 py-2.5 text-right" style={{ color: item.amount_difference ? "var(--danger)" : "var(--text-muted)" }}>
                          {item.amount_difference == null ? "-" : `${item.amount_difference > 0 ? "+" : ""}${fmt(item.amount_difference)}원`}
                        </td>
                        <td className="px-4 py-2.5"><StatusBadge status={item.amount_status ?? item.match_status} /></td>
                        <td className="px-4 py-2.5 text-xs min-w-[180px]" style={{ color: "var(--text-muted)" }}>{item.reason ?? "-"}</td>
                        <td className="px-4 py-2.5">
                          <div className="flex gap-2">
                            <Button size="sm" variant="primary" onClick={() => handleConfirm(item)}>확정</Button>
                            <Button size="sm" variant="ghost" onClick={() => handleExclude(item.transaction_id)} disabled={excluding === item.transaction_id}>
                              {excluding === item.transaction_id ? "..." : "제외"}
                            </Button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Card>
          )}
        </div>
      )}

      {/* Records */}
      <Card padding="none">
        <div className="p-5" style={{ borderBottom: "1px solid var(--border-soft)" }}>
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <h2 className="text-base font-semibold" style={{ color: "var(--text-main)" }}>회비 납부 현황</h2>
              <p className="text-xs mt-0.5" style={{ color: "var(--text-muted)" }}>
                {statusFilter !== "all" ? `${statusFilterLabel} ${filteredRecords.length}명` : `전체 ${records.length}명`} 중{" "}
                {pagedRecords.length}명 표시
                {selectedRecords.length > 0 && ` · ${selectedRecords.length}명 선택됨`}
              </p>
            </div>
            <div className="flex items-center gap-2">
              <label className="text-xs whitespace-nowrap" style={{ color: "var(--text-muted)" }}>표시 개수</label>
              <select
                className="rounded-xl px-2 py-1 text-sm focus:outline-none"
                style={{ background: "var(--surface)", color: "var(--text-main)", border: "1px solid var(--border-soft)" }}
                value={String(memberPageSize)}
                onChange={(e) => {
                  const v = e.target.value;
                  setMemberPageSize(v === "all" ? "all" : Number(v));
                  setMemberPage(1);
                }}
              >
                <option value="50">50명</option>
                <option value="100">100명</option>
                <option value="all">전체</option>
              </select>
            </div>
          </div>
        </div>
        <div className="grid grid-cols-1 gap-3 p-5 sm:grid-cols-2 lg:grid-cols-4"
          style={{ borderBottom: "1px solid var(--border-soft)" }}>
          <div>
            <label className="mb-1 block text-xs font-medium" style={{ color: "var(--text-muted)" }}>상태</label>
            <select style={inputStyle} className="min-h-[44px] focus:outline-none" value={statusFilter}
              onChange={(event) => { setStatusFilter(event.target.value); setMemberPage(1); }}>
              <option value="all">전체</option>
              <option value="unpaid">미납</option>
              <option value="paid">납부 완료</option>
              <option value="partial">부분 납부</option>
              <option value="need_check">확인 필요</option>
              <option value="exempt">면제</option>
              <option value="overpaid">초과 납부</option>
            </select>
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium" style={{ color: "var(--text-muted)" }}>검색</label>
            <input style={inputStyle} className="min-h-[44px] focus:outline-none"
              value={recordSearch}
              onChange={(event) => { setRecordSearch(event.target.value); setMemberPage(1); }}
              placeholder="이름 / 학번 / 학과" />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium" style={{ color: "var(--text-muted)" }}>구분</label>
            <select style={inputStyle} className="min-h-[44px] focus:outline-none" value={tierFilter}
              onChange={(event) => { setTierFilter(event.target.value); setMemberPage(1); }}>
              <option value="all">전체</option>
              <option value="new">신규</option>
              <option value="existing">기존</option>
              <option value="executive">임원</option>
            </select>
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium" style={{ color: "var(--text-muted)" }}>확인 방식</label>
            <select style={inputStyle} className="min-h-[44px] focus:outline-none" value={sourceFilter}
              onChange={(event) => { setSourceFilter(event.target.value); setMemberPage(1); }}>
              <option value="all">전체</option>
              <option value="거래매칭">거래매칭</option>
              <option value="수동">수동</option>
              <option value="없음">없음</option>
            </select>
          </div>
        </div>
        <BulkActionBar
          selectedCount={selectedRecords.length}
          onClear={() => setSelectedRecordIds([])}
          onOpen={() => setBulkModalOpen(true)}
        />
        {filteredRecords.length === 0 ? (
          <EmptyState message="표시할 회비 납부 현황이 없습니다." description="필터를 조정하거나 회비 대상 생성/동기화를 실행하세요." />
        ) : (
          <>
            <div className="hidden md:block overflow-x-auto">
              <table className="w-full text-sm" style={{ minWidth: 1080 }}>
                <thead>
                  <tr style={{ background: "var(--surface-soft)", borderBottom: "1px solid var(--border-soft)" }}>
                    <th className="w-12 px-4 py-3 text-left">
                      <input
                        type="checkbox"
                        className="h-4 w-4"
                        checked={allRecordsSelected}
                        onChange={(event) => toggleAllRecords(event.target.checked)}
                        aria-label="전체 납부 기록 선택"
                      />
                    </th>
                    {["부원명", "학번", "학과", "구분", "필요 금액", "납부 금액", "상태", "확인 방식", "메모", "작업"].map((h) => (
                      <th key={h} className="whitespace-nowrap px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide"
                        style={{ color: "var(--text-muted)" }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {pagedRecords.map((r) => (
                    <tr key={r.id} style={{ borderBottom: "1px solid var(--border-soft)" }}
                      onMouseEnter={(e) => (e.currentTarget.style.background = "var(--surface-soft)")}
                      onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}>
                      <td className="px-4 py-3">
                        <input
                          type="checkbox"
                          className="h-4 w-4"
                          checked={selectedRecordIdSet.has(r.id)}
                          onChange={(event) => toggleRecordSelection(
                            r.id,
                            event.target.checked,
                            (event.nativeEvent as MouseEvent).shiftKey,
                          )}
                          aria-label={`${r.member_name ?? "부원"} 납부 기록 선택`}
                        />
                      </td>
                      <td className="whitespace-nowrap px-4 py-3 font-medium" style={{ color: "var(--text-main)" }}>
                        <Link href={`/members/${r.member_id}`} className="hover:underline">
                          {r.member_name ?? "알 수 없는 부원"}
                        </Link>
                      </td>
                      <td className="whitespace-nowrap px-4 py-3 text-xs" style={{ color: "var(--text-muted)" }}>{r.student_id ?? "-"}</td>
                      <td className="whitespace-nowrap px-4 py-3 text-xs" style={{ color: "var(--text-muted)" }}>{r.department ?? "-"}</td>
                      <td className="whitespace-nowrap px-4 py-3 text-xs font-medium" style={{ color: "var(--text-main)" }}>{feeTierLabel(r.fee_tier)}</td>
                      <td className="whitespace-nowrap px-4 py-3 text-right" style={{ color: "var(--text-main)" }}>{fmt(r.required_amount)}원</td>
                      <td className="whitespace-nowrap px-4 py-3 text-right font-medium" style={{ color: "var(--text-main)" }}>{fmt(r.paid_amount)}원</td>
                      <td className="whitespace-nowrap px-4 py-3"><StatusBadge status={r.status} /></td>
                      <td className="whitespace-nowrap px-4 py-3 text-xs" style={{ color: "var(--text-main)" }}>{sourceLabel(r)}</td>
                      <td className="px-4 py-3 text-xs min-w-[180px]" style={{ color: "var(--text-muted)" }}>{r.manual_note ?? r.fee_rule_reason ?? "-"}</td>
                      <td className="whitespace-nowrap px-4 py-3">
                        <div className="flex gap-2">
                          <Button size="sm" variant="ghost" onClick={() => openManualEdit(r)}>직접 수정</Button>
                          {r.transaction_id && (
                            <Button size="sm" variant="ghost" disabled={unmatching === r.id}
                              onClick={() => handleUnmatchRecord(r.id)}>
                              {unmatching === r.id ? "..." : "매칭 취소"}
                            </Button>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="md:hidden divide-y" style={{ borderTop: "1px solid var(--border-soft)" }}>
              {pagedRecords.map((r) => (
                <div key={r.id} className="p-4 space-y-1">
                  <div className="flex items-start justify-between gap-3">
                    <label className="flex min-w-0 items-start gap-3">
                      <input
                        type="checkbox"
                        className="mt-1 h-4 w-4 shrink-0"
                        checked={selectedRecordIdSet.has(r.id)}
                        onChange={(event) => toggleRecordSelection(
                          r.id,
                          event.target.checked,
                          (event.nativeEvent as MouseEvent).shiftKey,
                        )}
                        aria-label={`${r.member_name ?? "부원"} 납부 기록 선택`}
                      />
                      <Link href={`/members/${r.member_id}`} className="min-w-0">
                        <p className="truncate font-medium text-sm hover:underline" style={{ color: "var(--text-main)" }}>
                          {r.member_name ?? "알 수 없는 부원"}
                        </p>
                      </Link>
                    </label>
                    <div className="shrink-0"><StatusBadge status={r.status} /></div>
                  </div>
                  <p className="text-xs" style={{ color: "var(--text-muted)" }}>
                    {r.period} · 필요 {fmt(r.required_amount)}원 / 납부 {fmt(r.paid_amount)}원
                  </p>
                  <p className="text-xs" style={{ color: "var(--text-muted)" }}>
                    {r.department ?? "-"} · {feeTierLabel(r.fee_tier)} · {sourceLabel(r)}
                  </p>
                  {(r.manual_note || r.fee_rule_reason) && (
                    <p className="text-xs" style={{ color: "var(--text-muted)" }}>
                      {r.manual_note ?? r.fee_rule_reason}
                    </p>
                  )}
                  <div className="flex flex-wrap gap-2 pt-2">
                    <Button size="sm" variant="ghost" onClick={() => openManualEdit(r)}>직접 수정</Button>
                    {r.transaction_id && (
                      <Button size="sm" variant="ghost" disabled={unmatching === r.id}
                        onClick={() => handleUnmatchRecord(r.id)}>
                        {unmatching === r.id ? "..." : "매칭 취소"}
                      </Button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </>
        )}
        {memberPageSize !== "all" && totalMemberPages > 1 && (
          <div className="flex items-center justify-center gap-3 p-4" style={{ borderTop: "1px solid var(--border-soft)" }}>
            <Button size="sm" variant="ghost" disabled={memberPage <= 1} onClick={() => setMemberPage((p) => p - 1)}>이전</Button>
            <span className="text-sm" style={{ color: "var(--text-muted)" }}>
              {memberPage} / {totalMemberPages} 페이지 (필터 결과 {filteredRecords.length}명)
            </span>
            <Button size="sm" variant="ghost" disabled={memberPage >= totalMemberPages} onClick={() => setMemberPage((p) => p + 1)}>다음</Button>
            <Button size="sm" variant="ghost" onClick={() => { setMemberPageSize("all"); setMemberPage(1); }}>전체 보기</Button>
          </div>
        )}
      </Card>

      <MembershipBulkUpdateModal
        isOpen={bulkModalOpen}
        period={period}
        selectedRecords={selectedRecords}
        onClose={() => setBulkModalOpen(false)}
        onCompleted={async () => {
          await loadData(period);
          setSelectedRecordIds([]);
        }}
      />

      <Card padding="none">
        <div className="p-5" style={{ borderBottom: "1px solid var(--border-soft)" }}>
          <h2 className="text-base font-semibold" style={{ color: "var(--text-main)" }}>납부 기록 / 변경 이력</h2>
          <p className="mt-1 text-xs" style={{ color: "var(--text-muted)" }}>
            거래내역 매칭, 수동 처리, 일괄 수정으로 발생한 상태 변경을 확인합니다.
          </p>
        </div>
        {history.length === 0 ? (
          <EmptyState message="변경 이력이 없습니다." description="수동 수정 또는 일괄 수정 후 이력이 표시됩니다." />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm" style={{ minWidth: 920 }}>
              <thead>{tblHeader(["처리 일시", "대상자", "작업 유형", "변경 전 상태", "변경 후 상태", "변경 전 금액", "변경 후 금액", "처리 방식", "메모"])}</thead>
              <tbody>
                {history.map((item) => (
                  <tr key={item.id} style={{ borderBottom: "1px solid var(--border-soft)" }}>
                    <td className="whitespace-nowrap px-4 py-3 text-xs" style={{ color: "var(--text-muted)" }}>{fmtDt(item.created_at)}</td>
                    <td className="whitespace-nowrap px-4 py-3 font-medium" style={{ color: "var(--text-main)" }}>
                      {item.member_name}
                      {item.student_id ? <span className="ml-1 text-xs" style={{ color: "var(--text-muted)" }}>({item.student_id})</span> : null}
                    </td>
                    <td className="whitespace-nowrap px-4 py-3 text-xs" style={{ color: "var(--text-main)" }}>{item.action}</td>
                    <td className="whitespace-nowrap px-4 py-3">{item.previous_status ? <StatusBadge status={item.previous_status} /> : "-"}</td>
                    <td className="whitespace-nowrap px-4 py-3">{item.new_status ? <StatusBadge status={item.new_status} /> : "-"}</td>
                    <td className="whitespace-nowrap px-4 py-3 text-right" style={{ color: "var(--text-main)" }}>{fmt(item.previous_paid_amount)}원</td>
                    <td className="whitespace-nowrap px-4 py-3 text-right" style={{ color: "var(--text-main)" }}>{fmt(item.new_paid_amount)}원</td>
                    <td className="whitespace-nowrap px-4 py-3 text-xs" style={{ color: "var(--text-main)" }}>
                      {item.payment_source === "transaction_match" ? "거래매칭" : item.payment_source === "manual" ? "수동" : item.action.includes("bulk") ? "일괄수정" : "없음"}
                    </td>
                    <td className="px-4 py-3 text-xs min-w-[180px]" style={{ color: "var(--text-muted)" }}>
                      {item.manual_note ?? item.reason ?? "-"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      {/* Manual edit modal */}
      {manualTarget && (
        <div className="fixed inset-0 flex items-end sm:items-center justify-center z-50"
          style={{ background: "rgba(31,31,36,0.4)" }}>
          <div className="rounded-t-2xl sm:rounded-2xl w-full sm:max-w-md p-6 space-y-4 shadow-soft"
            style={{ background: "var(--surface)", border: "1px solid var(--border-soft)" }}>
            <h3 className="text-base font-semibold" style={{ color: "var(--text-main)" }}>납부 상태 직접 수정</h3>
            <div className="rounded-xl p-3 text-sm"
              style={{ background: "var(--surface-soft)", border: "1px solid var(--border-soft)" }}>
              <p className="font-medium" style={{ color: "var(--text-main)" }}>{manualTarget.member_name ?? "이름 없는 부원"}</p>
              <p className="text-xs mt-0.5" style={{ color: "var(--text-muted)" }}>{manualTarget.student_id ?? "-"} · {manualTarget.department ?? "-"}</p>
              <p className="text-xs mt-0.5" style={{ color: "var(--text-muted)" }}>거래내역 매칭 없이 납부 상태를 직접 기록합니다.</p>
            </div>
            <div className="space-y-3">
              <div>
                <label className="block text-xs font-medium mb-1" style={{ color: "var(--text-muted)" }}>납부 상태</label>
                <select className="min-h-[44px] w-full rounded-xl px-3 py-2 text-sm focus:outline-none"
                  style={{ background: "var(--surface)", color: "var(--text-main)", border: "1px solid var(--border-soft)", fontSize: 16 }}
                  value={manualForm.status ?? "unpaid"}
                  onChange={(e) => handleStatusChange(e.target.value)}>
                  <option value="unpaid">미납</option>
                  <option value="paid">납부 완료</option>
                  <option value="partial">부분 납부</option>
                  <option value="need_check">확인 필요</option>
                  <option value="exempt">면제</option>
                  <option value="overpaid">초과 납부</option>
                </select>
              </div>
              <div>
                <label className="block text-xs font-medium mb-1" style={{ color: "var(--text-muted)" }}>필요 금액 (원)</label>
                <input type="number" className="min-h-[44px] w-full rounded-xl px-3 py-2 text-sm focus:outline-none"
                  style={{ background: "var(--surface)", color: "var(--text-main)", border: "1px solid var(--border-soft)", fontSize: 16 }}
                  value={manualForm.required_amount}
                  onChange={(e) => setManualForm((f) => ({ ...f, required_amount: Number(e.target.value) }))} />
              </div>
              <div>
                <label className="block text-xs font-medium mb-1" style={{ color: "var(--text-muted)" }}>납부 금액 (원)</label>
                <input type="number" className="min-h-[44px] w-full rounded-xl px-3 py-2 text-sm focus:outline-none"
                  style={{ background: "var(--surface)", color: "var(--text-main)", border: "1px solid var(--border-soft)", fontSize: 16 }}
                  value={manualForm.paid_amount}
                  onChange={(e) => setManualForm((f) => ({ ...f, paid_amount: Number(e.target.value) }))} />
              </div>
              <div>
                <label className="block text-xs font-medium mb-1" style={{ color: "var(--text-muted)" }}>메모</label>
                <textarea className="min-h-[72px] w-full rounded-xl px-3 py-2 text-sm focus:outline-none"
                  style={{ background: "var(--surface)", color: "var(--text-main)", border: "1px solid var(--border-soft)", fontSize: 16 }}
                  value={manualForm.manual_note ?? ""}
                  onChange={(e) => setManualForm((f) => ({ ...f, manual_note: e.target.value }))} />
              </div>
            </div>
            {manualError && <p className="text-sm" style={{ color: "var(--danger)" }}>{manualError}</p>}
            <div className="flex gap-3 pt-1">
              <Button className="flex-1 min-h-[44px]" onClick={handleManualSave} loading={manualSaving}>저장</Button>
              <Button className="flex-1 min-h-[44px]" variant="secondary" onClick={() => setManualTarget(null)} disabled={manualSaving}>취소</Button>
            </div>
          </div>
        </div>
      )}

      {/* Transaction confirm modal */}
      {confirmTarget && (
        <div className="fixed inset-0 flex items-center justify-center z-50"
          style={{ background: "rgba(31,31,36,0.4)" }}>
          <div className="rounded-2xl w-full max-w-md p-6 space-y-4 shadow-soft"
            style={{ background: "var(--surface)", border: "1px solid var(--border-soft)" }}>
            <h3 className="text-lg font-semibold" style={{ color: "var(--text-main)" }}>거래 수동 확정</h3>
            <div className="rounded-xl p-4 space-y-2"
              style={{ background: "var(--surface-soft)", border: "1px solid var(--border-soft)" }}>
              <p className="text-sm" style={{ color: "var(--text-muted)" }}>
                <span className="font-medium" style={{ color: "var(--text-main)" }}>적요:</span> {confirmTarget.memo ?? "-"}
              </p>
              <p className="text-sm" style={{ color: "var(--text-muted)" }}>
                <span className="font-medium" style={{ color: "var(--text-main)" }}>입금액:</span> {fmt(confirmTarget.deposit_amount)}원
              </p>
            </div>
            <div>
              <label className="block text-xs font-medium mb-1.5" style={{ color: "var(--text-muted)" }}>부원 선택</label>
              <select className="w-full rounded-xl px-3 py-2 text-sm focus:outline-none min-h-[44px]"
                style={{ background: "var(--surface)", color: "var(--text-main)", border: "1px solid var(--border-soft)", fontSize: 16 }}
                value={confirmMemberId} onChange={(e) => setConfirmMemberId(e.target.value)}>
                <option value="">-- 부원 선택 --</option>
                {members.map((m) => (
                  <option key={m.id} value={m.id}>{m.name} {m.student_id ? `(${m.student_id})` : ""}</option>
                ))}
              </select>
            </div>
            <div className="flex gap-3 pt-2">
              <Button className="flex-1 min-h-[44px]" onClick={submitConfirm} disabled={confirming || !confirmMemberId} loading={confirming}>확정</Button>
              <Button className="flex-1 min-h-[44px]" variant="secondary" onClick={() => setConfirmTarget(null)} disabled={confirming}>취소</Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// ─── Inner Page (uses useSearchParams) ───────────────────────────────────────

function PaymentsPageInner() {
  // Task 29: Payments page is membership_fee only.
  // Activity fee is managed inside each activity's detail page (fees tab).
  void useSearchParams();

  return (
    <AppShell>
      <div className="space-y-5">
        <PageHeader
          title="회비 관리"
          description="학기별 부원 회비 납부 현황을 관리합니다. 활동비는 각 활동 상세에서 관리하세요."
        />
        <MembershipFeeTab />
      </div>
    </AppShell>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function PaymentsPage() {
  return (
    <Suspense fallback={<AppShell><div className="p-8 text-center" style={{ color: "var(--text-muted)" }}>로딩 중...</div></AppShell>}>
      <PaymentsPageInner />
    </Suspense>
  );
}
