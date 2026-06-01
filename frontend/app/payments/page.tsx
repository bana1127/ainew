"use client";

import React, { useCallback, useEffect, useRef, useState, Suspense } from "react";
import Link from "next/link";
import { useSearchParams, useRouter } from "next/navigation";
import {
  ManualPaymentRecordPayload,
  Member,
  PaymentMatchingPreview,
  PaymentMatchingResult,
  PaymentRecord,
  PaymentSummary,
  TransactionMatchItem,
  UnpaidPaymentItem,
  applyPaymentMatching,
  confirmPaymentTransaction,
  excludePaymentTransaction,
  getPaymentRecords,
  getPaymentSummary,
  getUnpaidPayments,
  getMembersFiltered,
  previewPaymentMatching,
  upsertManualPaymentRecord,
  getActivityFeePaymentRecords,
  getActivities,
  type ActivitySummary,
} from "@/lib/api";

import { AppShell } from "@/components/layout/AppShell";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorState } from "@/components/ui/ErrorState";
import { PageHeader } from "@/components/ui/PageHeader";
import { StatusBadge } from "@/components/ui/StatusBadge";

type TabKey = "membership_fee" | "activity_fee";

function fmt(n: number | null | undefined): string {
  if (n == null) return "-";
  return n.toLocaleString("ko-KR");
}

function fmtDt(s: string | null | undefined): string {
  if (!s) return "-";
  return s.replace("T", " ").slice(0, 16);
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

// ─── Membership Fee Tab ───────────────────────────────────────────────────────

function MembershipFeeTab() {
  const [period, setPeriod] = useState("2026-1");
  const [requiredAmount, setRequiredAmount] = useState(30000);
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");

  const [previewing, setPreviewing] = useState(false);
  const [applying, setApplying] = useState(false);
  const [preview, setPreview] = useState<PaymentMatchingPreview | null>(null);
  const [applyResult, setApplyResult] = useState<PaymentMatchingResult | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  const [summary, setSummary] = useState<PaymentSummary | null>(null);
  const [unpaid, setUnpaid] = useState<UnpaidPaymentItem[]>([]);
  const [records, setRecords] = useState<PaymentRecord[]>([]);
  const [loadingData, setLoadingData] = useState(false);

  const [confirmTarget, setConfirmTarget] = useState<TransactionMatchItem | null>(null);
  const [members, setMembers] = useState<Member[]>([]);
  const [confirmMemberId, setConfirmMemberId] = useState("");
  const [confirming, setConfirming] = useState(false);
  const [excluding, setExcluding] = useState<string | null>(null);

  const [manualTarget, setManualTarget] = useState<UnpaidPaymentItem | null>(null);
  const [manualForm, setManualForm] = useState<ManualPaymentRecordPayload>({
    member_id: "", period: "2026-1", payment_type: "membership_fee",
    required_amount: 30000, paid_amount: 0, status: "paid",
  });
  const [manualSaving, setManualSaving] = useState(false);
  const [manualError, setManualError] = useState<string | null>(null);

  async function loadData(p = period) {
    setLoadingData(true);
    try {
      const [s, u, r] = await Promise.all([
        getPaymentSummary({ period: p, payment_type: "membership_fee" }),
        getUnpaidPayments({ period: p, payment_type: "membership_fee" }),
        getPaymentRecords({ period: p, payment_type: "membership_fee" }),
      ]);
      setSummary(s);
      setUnpaid(u);
      setRecords(r);
    } catch { /* silently ignore */ }
    finally { setLoadingData(false); }
  }

  useEffect(() => { loadData(); }, []);

  async function handlePreview() {
    setActionError(null);
    setApplyResult(null);
    setPreviewing(true);
    try {
      const result = await previewPaymentMatching({
        period, payment_type: "membership_fee",
        required_amount: requiredAmount || null,
        start_date: startDate || null, end_date: endDate || null,
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

  function openManualEdit(item: UnpaidPaymentItem) {
    const initStatus = (item.status as ManualPaymentRecordPayload["status"]) ?? "unpaid";
    const initPaid = initStatus === "paid" ? (item.paid_amount || requiredAmount) : item.paid_amount;
    setManualTarget(item);
    setManualForm({
      member_id: item.member_id,
      period,
      payment_type: "membership_fee",
      required_amount: item.required_amount || requiredAmount,
      paid_amount: initPaid,
      status: initStatus,
    });
    setManualError(null);
  }

  async function handleManualSave() {
    setManualSaving(true);
    setManualError(null);
    try {
      await upsertManualPaymentRecord(manualForm);
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
                  <thead>{tblHeader(["거래일시", "적요", "입금액", "매칭 부원", "상태"])}</thead>
                  <tbody>
                    {preview.matched_items.map((item) => (
                      <tr key={item.transaction_id} style={{ borderBottom: "1px solid var(--border-soft)" }}
                        onMouseEnter={(e) => (e.currentTarget.style.background = "var(--surface-soft)")}
                        onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}>
                        <td className="px-4 py-2.5 text-xs whitespace-nowrap" style={{ color: "var(--text-muted)" }}>{fmtDt(item.transaction_datetime)}</td>
                        <td className="px-4 py-2.5 max-w-[160px] truncate" style={{ color: "var(--text-main)" }}>{item.memo ?? "-"}</td>
                        <td className="px-4 py-2.5 text-right font-medium" style={{ color: "var(--success)" }}>{fmt(item.deposit_amount)}원</td>
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
                  <thead>{tblHeader(["거래일시", "적요", "입금액", "추정 부원", "수동 처리"])}</thead>
                  <tbody>
                    {preview.need_check_items.map((item) => (
                      <tr key={item.transaction_id} style={{ borderBottom: "1px solid var(--border-soft)" }}
                        onMouseEnter={(e) => (e.currentTarget.style.background = "var(--surface-soft)")}
                        onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}>
                        <td className="px-4 py-2.5 text-xs whitespace-nowrap" style={{ color: "var(--text-muted)" }}>{fmtDt(item.transaction_datetime)}</td>
                        <td className="px-4 py-2.5 max-w-[140px] truncate" style={{ color: "var(--text-main)" }}>{item.memo ?? "-"}</td>
                        <td className="px-4 py-2.5 text-right font-medium" style={{ color: "var(--text-main)" }}>{fmt(item.deposit_amount)}원</td>
                        <td className="px-4 py-2.5" style={{ color: "var(--text-main)" }}>{item.matched_member_name ?? "-"}</td>
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

      {/* Unpaid */}
      {unpaid.length > 0 && (
        <Card padding="none">
          <div className="p-5" style={{ background: "var(--danger-soft)", borderBottom: "1px solid var(--border-soft)" }}>
            <h2 className="text-base font-semibold" style={{ color: "var(--danger)" }}>미납자 목록 ({unpaid.length}명)</h2>
          </div>
          {/* Desktop */}
          <div className="hidden md:block overflow-x-auto">
            <table className="w-full text-sm">
              <thead>{tblHeader(["이름", "학번", "학과", "필요 금액", "납부 금액", "상태", "직접 수정"])}</thead>
              <tbody>
                {unpaid.map((item) => (
                  <tr key={item.member_id} style={{ borderBottom: "1px solid var(--border-soft)" }}
                    onMouseEnter={(e) => (e.currentTarget.style.background = "var(--surface-soft)")}
                    onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}>
                    <td className="px-4 py-3 font-medium" style={{ color: "var(--text-main)" }}>
                      <Link href={`/members/${item.member_id}`} className="hover:underline">{item.name}</Link>
                    </td>
                    <td className="px-4 py-3 text-xs" style={{ color: "var(--text-muted)" }}>{item.student_id ?? "-"}</td>
                    <td className="px-4 py-3 text-xs" style={{ color: "var(--text-muted)" }}>{item.department ?? "-"}</td>
                    <td className="px-4 py-3 text-right" style={{ color: "var(--text-main)" }}>{fmt(item.required_amount)}원</td>
                    <td className="px-4 py-3 text-right" style={{ color: "var(--text-main)" }}>{fmt(item.paid_amount)}원</td>
                    <td className="px-4 py-3"><StatusBadge status={item.status} /></td>
                    <td className="px-4 py-3">
                      <Button size="sm" variant="ghost" onClick={() => openManualEdit(item)}>직접 수정</Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {/* Mobile */}
          <div className="md:hidden divide-y" style={{ borderTop: "1px solid var(--border-soft)" }}>
            {unpaid.map((item) => (
              <div key={item.member_id} className="p-4 space-y-2">
                <div className="flex items-center justify-between">
                  <div>
                    <Link href={`/members/${item.member_id}`}>
                      <p className="font-medium text-sm hover:underline" style={{ color: "var(--text-main)" }}>{item.name}</p>
                    </Link>
                    {item.student_id && <p className="text-xs" style={{ color: "var(--text-muted)" }}>{item.student_id} · {item.department ?? ""}</p>}
                  </div>
                  <StatusBadge status={item.status} />
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm" style={{ color: "var(--text-muted)" }}>
                    필요: {fmt(item.required_amount)}원 / 납부: {fmt(item.paid_amount)}원
                  </span>
                  <Button size="sm" variant="ghost" onClick={() => openManualEdit(item)}>직접 수정</Button>
                </div>
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* Records */}
      <Card padding="none">
        <div className="p-5" style={{ borderBottom: "1px solid var(--border-soft)" }}>
          <h2 className="text-base font-semibold" style={{ color: "var(--text-main)" }}>납부 기록</h2>
        </div>
        {records.length === 0 ? (
          <EmptyState message="납부 기록이 없습니다." description="매칭 적용 후 납부 기록이 생성됩니다." />
        ) : (
          <>
            <div className="hidden md:block overflow-x-auto">
              <table className="w-full text-sm">
                <thead>{tblHeader(["부원명", "학번", "기간", "필요 금액", "납부 금액", "상태", "생성일"])}</thead>
                <tbody>
                  {records.map((r) => (
                    <tr key={r.id} style={{ borderBottom: "1px solid var(--border-soft)" }}
                      onMouseEnter={(e) => (e.currentTarget.style.background = "var(--surface-soft)")}
                      onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}>
                      <td className="px-4 py-3 font-medium" style={{ color: "var(--text-main)" }}>
                        <Link href={`/members/${r.member_id}`} className="hover:underline">
                          {r.member_name ?? "알 수 없는 부원"}
                        </Link>
                      </td>
                      <td className="px-4 py-3 text-xs" style={{ color: "var(--text-muted)" }}>{r.student_id ?? "-"}</td>
                      <td className="px-4 py-3" style={{ color: "var(--text-main)" }}>{r.period}</td>
                      <td className="px-4 py-3 text-right" style={{ color: "var(--text-main)" }}>{fmt(r.required_amount)}원</td>
                      <td className="px-4 py-3 text-right font-medium" style={{ color: "var(--text-main)" }}>{fmt(r.paid_amount)}원</td>
                      <td className="px-4 py-3"><StatusBadge status={r.status} /></td>
                      <td className="px-4 py-3 text-xs whitespace-nowrap" style={{ color: "var(--text-muted)" }}>{fmtDt(r.created_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="md:hidden divide-y" style={{ borderTop: "1px solid var(--border-soft)" }}>
              {records.map((r) => (
                <div key={r.id} className="p-4 space-y-1">
                  <div className="flex items-center justify-between">
                    <Link href={`/members/${r.member_id}`}>
                      <p className="font-medium text-sm hover:underline" style={{ color: "var(--text-main)" }}>
                        {r.member_name ?? "알 수 없는 부원"}
                      </p>
                    </Link>
                    <StatusBadge status={r.status} />
                  </div>
                  <p className="text-xs" style={{ color: "var(--text-muted)" }}>
                    {r.period} · 필요 {fmt(r.required_amount)}원 / 납부 {fmt(r.paid_amount)}원
                  </p>
                </div>
              ))}
            </div>
          </>
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
              <p className="font-medium" style={{ color: "var(--text-main)" }}>{manualTarget.name}</p>
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

// ─── Activity Fee Tab ─────────────────────────────────────────────────────────

function ActivityFeeTab({ initialActivityId }: { initialActivityId?: string }) {
  const [activities, setActivities] = useState<ActivitySummary[]>([]);
  const [selectedActivityId, setSelectedActivityId] = useState(initialActivityId ?? "");
  const [records, setRecords] = useState<PaymentRecord[]>([]);
  const [loadingActivities, setLoadingActivities] = useState(true);
  const [loadingRecords, setLoadingRecords] = useState(false);
  const [manualTarget, setManualTarget] = useState<PaymentRecord | null>(null);
  const [manualStatus, setManualStatus] = useState("unpaid");
  const [manualPaid, setManualPaid] = useState(0);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  useEffect(() => {
    getActivities({ limit: 100 })
      .then((data) => setActivities(data.filter((a) => a.status !== "archived")))
      .catch(() => {})
      .finally(() => setLoadingActivities(false));
  }, []);

  useEffect(() => {
    if (!selectedActivityId) {
      // load all activity_fee records
      setLoadingRecords(true);
      getActivityFeePaymentRecords()
        .then(setRecords)
        .catch(() => {})
        .finally(() => setLoadingRecords(false));
    } else {
      const activity = activities.find((a) => a.id === selectedActivityId);
      if (!activity) return;
      const period = `act-${selectedActivityId.slice(0, 8)}`;
      setLoadingRecords(true);
      getActivityFeePaymentRecords({ period })
        .then(setRecords)
        .catch(() => {})
        .finally(() => setLoadingRecords(false));
    }
  }, [selectedActivityId, activities]);

  function openEdit(r: PaymentRecord) {
    setManualTarget(r);
    setManualStatus(r.status);
    setManualPaid(r.paid_amount);
    setSaveError(null);
  }

  async function handleSave() {
    if (!manualTarget) return;
    setSaving(true);
    setSaveError(null);
    try {
      await upsertManualPaymentRecord({
        member_id: manualTarget.member_id,
        period: manualTarget.period,
        payment_type: "activity_fee",
        required_amount: manualTarget.required_amount,
        paid_amount: manualPaid,
        status: manualStatus as ManualPaymentRecordPayload["status"],
      });
      setManualTarget(null);
      // reload
      setSelectedActivityId((v) => v);
    } catch (err: unknown) {
      setSaveError(err instanceof Error ? err.message : "저장에 실패했습니다.");
    } finally {
      setSaving(false);
    }
  }

  const paidCount = records.filter((r) => r.status === "paid").length;
  const unpaidCount = records.filter((r) => r.status === "unpaid").length;

  return (
    <div className="space-y-5">
      <Card padding="lg">
        <h2 className="text-base font-semibold mb-4" style={{ color: "var(--text-main)" }}>활동비 현황</h2>
        <p className="text-sm mb-4" style={{ color: "var(--text-muted)" }}>
          활동비 생성은 각 활동 상세 페이지에서 합니다.
          여기서는 전체 현황 확인 및 직접 수정이 가능합니다.
        </p>

        <div className="flex items-end gap-3">
          <div className="flex-1">
            <label className="block text-xs font-medium mb-1.5" style={{ color: "var(--text-muted)" }}>활동 선택</label>
            <select
              className="w-full rounded-xl px-3 py-2 text-sm focus:outline-none min-h-[44px]"
              style={{ background: "var(--surface)", color: "var(--text-main)", border: "1px solid var(--border-soft)" }}
              value={selectedActivityId}
              onChange={(e) => setSelectedActivityId(e.target.value)}
            >
              <option value="">전체 활동비</option>
              {activities.map((a) => (
                <option key={a.id} value={a.id}>
                  {a.title} {a.activity_date ? `(${a.activity_date})` : ""}
                </option>
              ))}
            </select>
          </div>
          {selectedActivityId && (
            <Link href={`/activities/${selectedActivityId}`}>
              <Button variant="secondary" size="sm">활동 상세 이동</Button>
            </Link>
          )}
        </div>
      </Card>

      {records.length > 0 && (
        <Card padding="none">
          <div className="p-4 flex items-center justify-between" style={{ borderBottom: "1px solid var(--border-soft)" }}>
            <h3 className="text-sm font-semibold" style={{ color: "var(--text-main)" }}>
              활동비 납부 현황 ({records.length}명)
            </h3>
            <div className="flex gap-2">
              <span className="text-xs rounded-full px-2.5 py-1"
                style={{ background: "var(--success-soft)", color: "var(--success)" }}>
                납부 {paidCount}명
              </span>
              <span className="text-xs rounded-full px-2.5 py-1"
                style={{ background: "var(--danger-soft)", color: "var(--danger)" }}>
                미납 {unpaidCount}명
              </span>
            </div>
          </div>
          {/* Desktop */}
          <div className="hidden md:block overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr style={{ background: "var(--surface-soft)", borderBottom: "1px solid var(--border-soft)" }}>
                  {["부원명", "학번", "활동 기간", "필요 금액", "납부 금액", "상태", "수정"].map((h) => (
                    <th key={h} className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide"
                      style={{ color: "var(--text-muted)" }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {records.map((r) => (
                  <tr key={r.id} style={{ borderBottom: "1px solid var(--border-soft)" }}
                    onMouseEnter={(e) => (e.currentTarget.style.background = "var(--surface-soft)")}
                    onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}>
                    <td className="px-4 py-3 font-medium" style={{ color: "var(--text-main)" }}>
                      <Link href={`/members/${r.member_id}`} className="hover:underline">
                        {r.member_name ?? "-"}
                      </Link>
                    </td>
                    <td className="px-4 py-3 text-xs" style={{ color: "var(--text-muted)" }}>{r.student_id ?? "-"}</td>
                    <td className="px-4 py-3 text-xs" style={{ color: "var(--text-muted)" }}>{r.period}</td>
                    <td className="px-4 py-3 text-right" style={{ color: "var(--text-main)" }}>{fmt(r.required_amount)}원</td>
                    <td className="px-4 py-3 text-right" style={{ color: "var(--text-main)" }}>{fmt(r.paid_amount)}원</td>
                    <td className="px-4 py-3"><StatusBadge status={r.status} /></td>
                    <td className="px-4 py-3">
                      <Button size="sm" variant="ghost" onClick={() => openEdit(r)}>직접 수정</Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {/* Mobile */}
          <div className="md:hidden divide-y" style={{ borderTop: "1px solid var(--border-soft)" }}>
            {records.map((r) => (
              <div key={r.id} className="p-4 space-y-2">
                <div className="flex items-center justify-between">
                  <div>
                    <Link href={`/members/${r.member_id}`}>
                      <p className="font-medium text-sm hover:underline" style={{ color: "var(--text-main)" }}>
                        {r.member_name ?? "-"}
                      </p>
                    </Link>
                    {r.student_id && <p className="text-xs" style={{ color: "var(--text-muted)" }}>{r.student_id}</p>}
                  </div>
                  <StatusBadge status={r.status} />
                </div>
                <div className="flex items-center justify-between">
                  <p className="text-xs" style={{ color: "var(--text-muted)" }}>
                    {r.period} · 필요 {fmt(r.required_amount)}원 / 납부 {fmt(r.paid_amount)}원
                  </p>
                  <Button size="sm" variant="ghost" onClick={() => openEdit(r)}>수정</Button>
                </div>
              </div>
            ))}
          </div>
        </Card>
      )}

      {!loadingRecords && records.length === 0 && (
        <EmptyState
          message="활동비 납부 기록이 없습니다."
          description="활동 상세 페이지에서 활동비 대상을 생성하세요."
          action={
            <Link href="/activities">
              <Button size="sm">활동 목록으로</Button>
            </Link>
          }
        />
      )}

      {/* Edit modal */}
      {manualTarget && (
        <div className="fixed inset-0 flex items-end sm:items-center justify-center z-50"
          style={{ background: "rgba(31,31,36,0.4)" }}>
          <div className="rounded-t-2xl sm:rounded-2xl w-full sm:max-w-md p-6 space-y-4"
            style={{ background: "var(--surface)", border: "1px solid var(--border-soft)" }}>
            <h3 className="text-base font-semibold" style={{ color: "var(--text-main)" }}>납부 상태 직접 수정</h3>
            <div className="space-y-3">
              <div>
                <label className="block text-xs font-medium mb-1" style={{ color: "var(--text-muted)" }}>납부 상태</label>
                <select className="w-full rounded-xl px-3 py-2 text-sm focus:outline-none min-h-[44px]"
                  style={{ background: "var(--surface)", color: "var(--text-main)", border: "1px solid var(--border-soft)", fontSize: 16 }}
                  value={manualStatus} onChange={(e) => setManualStatus(e.target.value)}>
                  <option value="unpaid">미납</option>
                  <option value="paid">납부 완료</option>
                  <option value="partial">부분 납부</option>
                  <option value="exempt">면제</option>
                  <option value="need_check">확인 필요</option>
                </select>
              </div>
              <div>
                <label className="block text-xs font-medium mb-1" style={{ color: "var(--text-muted)" }}>납부 금액 (원)</label>
                <input type="number" className="w-full rounded-xl px-3 py-2 text-sm focus:outline-none min-h-[44px]"
                  style={{ background: "var(--surface)", color: "var(--text-main)", border: "1px solid var(--border-soft)", fontSize: 16 }}
                  value={manualPaid} onChange={(e) => setManualPaid(Number(e.target.value))} />
              </div>
            </div>
            {saveError && <p className="text-sm" style={{ color: "var(--danger)" }}>{saveError}</p>}
            <div className="flex gap-3">
              <Button className="flex-1 min-h-[44px]" onClick={handleSave} loading={saving}>저장</Button>
              <Button className="flex-1 min-h-[44px]" variant="secondary" onClick={() => setManualTarget(null)} disabled={saving}>취소</Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// ─── Inner Page (uses useSearchParams) ───────────────────────────────────────

function PaymentsPageInner() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const tabParam = searchParams?.get("tab") as TabKey | null;
  const activityIdParam = searchParams?.get("activity_id") ?? undefined;

  const [activeTab, setActiveTab] = useState<TabKey>(
    tabParam === "activity_fee" ? "activity_fee" : "membership_fee",
  );

  function switchTab(tab: TabKey) {
    setActiveTab(tab);
    router.push(`/payments?tab=${tab}`);
  }

  const tabs: { key: TabKey; label: string }[] = [
    { key: "membership_fee", label: "회비" },
    { key: "activity_fee", label: "활동비" },
  ];

  return (
    <AppShell>
      <div className="space-y-5">
        <PageHeader
          title="납부 현황"
          description="회비 및 활동비 납부 현황을 확인하고 관리합니다."
        />

        {/* Tab bar */}
        <div className="flex gap-1 rounded-xl p-1" style={{ background: "var(--surface-soft)", border: "1px solid var(--border-soft)", width: "fit-content" }}>
          {tabs.map((tab) => (
            <button
              key={tab.key}
              onClick={() => switchTab(tab.key)}
              className="px-4 py-2 rounded-lg text-sm font-medium transition-all min-h-[36px]"
              style={
                activeTab === tab.key
                  ? { background: "var(--surface)", color: "var(--text-main)", boxShadow: "0 1px 3px rgba(31,31,36,0.1)" }
                  : { color: "var(--text-muted)" }
              }
            >
              {tab.label}
            </button>
          ))}
        </div>

        {activeTab === "membership_fee" && <MembershipFeeTab />}
        {activeTab === "activity_fee" && <ActivityFeeTab initialActivityId={activityIdParam} />}
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
