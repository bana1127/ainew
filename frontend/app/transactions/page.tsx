"use client";

import React, { useEffect, useRef, useState, useCallback } from "react";
import { Upload, MoreHorizontal } from "lucide-react";
import {
  BankStatementImportResponse,
  BankStatementPreviewResponse,
  BankTransaction,
  TransactionQueryParams,
  getTransactionsTyped,
  importTransactions,
  parseTransactionPreview,
  unmatchTransaction,
  matchRefundTransaction,
  unmatchRefundTransaction,
  getRefundRecords,
  budgetExcludeTransaction,
  budgetIncludeTransaction,
  type RefundRecord,
} from "@/lib/api";
import { QuarterFilter } from "@/components/budget/QuarterFilter";

import { AppShell } from "@/components/layout/AppShell";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorState } from "@/components/ui/ErrorState";
import { LoadingState } from "@/components/ui/LoadingState";
import { PageHeader } from "@/components/ui/PageHeader";
import { StatusBadge } from "@/components/ui/StatusBadge";

const menuItemStyle: React.CSSProperties = {
  display: "block", width: "100%", textAlign: "left",
  padding: "8px 14px", fontSize: 13, cursor: "pointer",
  background: "none", border: "none", color: "var(--text-main)",
  transition: "background 0.1s",
};

function fmt(n: number | null | undefined): string {
  if (n == null) return "-";
  return n.toLocaleString("ko-KR");
}

function fmtDate(s: string | null | undefined): string {
  if (!s) return "-";
  return s.replace("T", " ").slice(0, 16);
}

export default function TransactionsPage() {
  const fileRef = useRef<HTMLInputElement>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [previewing, setPreviewing] = useState(false);
  const [importing, setImporting] = useState(false);
  const [preview, setPreview] = useState<BankStatementPreviewResponse | null>(null);
  const [importResult, setImportResult] = useState<BankStatementImportResponse | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);

  const [transactions, setTransactions] = useState<BankTransaction[]>([]);
  const [loading, setLoading] = useState(false);
  const [listError, setListError] = useState<string | null>(null);
  const [unmatching, setUnmatching] = useState<string | null>(null);
  const [refundMatchTarget, setRefundMatchTarget] = useState<BankTransaction | null>(null);
  const [refundRecords, setRefundRecords] = useState<RefundRecord[]>([]);
  const [selectedRefundRecordId, setSelectedRefundRecordId] = useState("");
  const [refundMatchBusy, setRefundMatchBusy] = useState(false);
  const [refundMatchError, setRefundMatchError] = useState<string | null>(null);
  const [filters, setFilters] = useState<TransactionQueryParams>({
    q: "", match_status: "", payment_type: "", start_date: "", end_date: "",
  });
  const [operatingQuarter, setOperatingQuarter] = useState<string>("");
  const [txPageSize, setTxPageSize] = useState<number | "all">("all");
  const [txPage, setTxPage] = useState(1);
  const [excludeBusy, setExcludeBusy] = useState<string | null>(null);
  const [excludeModal, setExcludeModal] = useState<BankTransaction | null>(null);
  const [excludeReason, setExcludeReason] = useState<string>("");
  const [excludeType, setExcludeType] = useState<"income" | "expense" | "both">("both");
  const [openMenuId, setOpenMenuId] = useState<string | null>(null);

  const loadTransactions = async (f: TransactionQueryParams = filters, quarter: string = operatingQuarter) => {
    setLoading(true);
    setListError(null);
    setTxPage(1);
    try {
      const params: TransactionQueryParams = {};
      if (f.q) params.q = f.q;
      if (f.match_status) params.match_status = f.match_status;
      if (f.payment_type) params.payment_type = f.payment_type;
      if (quarter) {
        params.operating_quarter = quarter;
      } else {
        if (f.start_date) params.start_date = f.start_date;
        if (f.end_date) params.end_date = f.end_date;
      }
      setTransactions(await getTransactionsTyped(params));
    } catch (e: unknown) {
      setListError(e instanceof Error ? e.message : "불러오기 실패");
    } finally {
      setLoading(false);
    }
  };

  const handleExclude = async (txn: BankTransaction) => {
    setExcludeModal(txn);
    setExcludeReason("");
    setExcludeType("both");
  };

  const confirmExclude = async () => {
    if (!excludeModal) return;
    setExcludeBusy(excludeModal.id);
    try {
      await budgetExcludeTransaction(excludeModal.id, {
        exclude_from_budget: excludeType === "both",
        exclude_from_income: excludeType === "income" || excludeType === "both",
        exclude_from_expense: excludeType === "expense" || excludeType === "both",
        reason: excludeReason,
      });
      setExcludeModal(null);
      await loadTransactions();
    } catch (e: unknown) {
      alert(e instanceof Error ? e.message : "제외 처리 실패");
    } finally {
      setExcludeBusy(null);
    }
  };

  const handleInclude = async (txn: BankTransaction) => {
    if (!confirm("예산 제외를 해제하시겠습니까?")) return;
    setExcludeBusy(txn.id);
    try {
      await budgetIncludeTransaction(txn.id);
      await loadTransactions();
    } catch (e: unknown) {
      alert(e instanceof Error ? e.message : "해제 실패");
    } finally {
      setExcludeBusy(null);
    }
  };

  useEffect(() => { loadTransactions(); }, []);

  const openRefundMatch = async (txn: BankTransaction) => {
    setRefundMatchTarget(txn);
    setRefundMatchError(null);
    setSelectedRefundRecordId("");
    try {
      const recs = await getRefundRecords({ refund_status: "refund_required" });
      setRefundRecords(recs);
    } catch { setRefundRecords([]); }
  };

  const handleRefundMatch = async () => {
    if (!refundMatchTarget || !selectedRefundRecordId) return;
    setRefundMatchBusy(true);
    setRefundMatchError(null);
    try {
      await matchRefundTransaction(refundMatchTarget.id, { payment_record_id: selectedRefundRecordId });
      setRefundMatchTarget(null);
      await loadTransactions();
    } catch (e: unknown) {
      setRefundMatchError(e instanceof Error ? e.message : "환불 매칭 실패");
    } finally { setRefundMatchBusy(false); }
  };

  const handleUnmatchRefund = async (transactionId: string) => {
    if (!confirm("환불 매칭을 취소하시겠습니까?")) return;
    setUnmatching(transactionId);
    try {
      await unmatchRefundTransaction(transactionId);
      await loadTransactions();
    } catch (e: unknown) {
      setListError(e instanceof Error ? e.message : "환불 매칭 취소 실패");
    } finally { setUnmatching(null); }
  };

  const handleUnmatch = async (transactionId: string) => {
    if (!confirm("이 거래내역 매칭을 취소하시겠습니까?\n납부 상태가 미납 또는 부분 납부로 되돌아갈 수 있습니다.")) return;
    setUnmatching(transactionId);
    try {
      await unmatchTransaction(transactionId);
      await loadTransactions();
    } catch (e: unknown) {
      setListError(e instanceof Error ? e.message : "매칭 취소 실패");
    } finally {
      setUnmatching(null);
    }
  };

  const handlePreview = async () => {
    if (!selectedFile) return;
    setPreviewing(true);
    setUploadError(null);
    setPreview(null);
    setImportResult(null);
    try {
      setPreview(await parseTransactionPreview(selectedFile));
    } catch (e: unknown) {
      setUploadError(e instanceof Error ? e.message : "미리보기 실패");
    } finally {
      setPreviewing(false);
    }
  };

  const handleImport = async () => {
    if (!selectedFile) return;
    setImporting(true);
    setUploadError(null);
    setImportResult(null);
    try {
      const result = await importTransactions(selectedFile);
      setImportResult(result);
      await loadTransactions();
    } catch (e: unknown) {
      setUploadError(e instanceof Error ? e.message : "가져오기 실패");
    } finally {
      setImporting(false);
    }
  };

  const pagedTransactions = txPageSize === "all"
    ? transactions
    : transactions.slice((txPage - 1) * (txPageSize as number), txPage * (txPageSize as number));
  const txTotalPages = txPageSize === "all" ? 1 : Math.ceil(transactions.length / (txPageSize as number));

  return (
    <AppShell>
      <div className="space-y-6">
        <PageHeader
          title="거래내역"
          description="거래내역서를 업로드하여 입출금 내역을 관리합니다."
        />

        {/* Upload Section */}
        <Card padding="lg">
          <h2 className="text-base font-semibold mb-4" style={{ color: "var(--text-main)" }}>
            거래내역서 업로드
          </h2>
          <p className="text-sm mb-5" style={{ color: "var(--text-muted)" }}>
            지원 파일: .xls, .xlsx, .csv
          </p>

          {/* File dropzone */}
          <div
            className="flex flex-col items-center justify-center gap-3 rounded-2xl p-8 text-center cursor-pointer transition-colors hover:opacity-80"
            style={{ border: "2px dashed var(--border-soft)", background: "var(--surface-soft)" }}
            onClick={() => fileRef.current?.click()}
          >
            <div className="rounded-2xl p-3" style={{ background: "var(--primary-soft)" }}>
              <Upload className="h-5 w-5" style={{ color: "var(--primary)" }} />
            </div>
            <div>
              <p className="text-sm font-medium" style={{ color: "var(--text-main)" }}>
                {selectedFile ? selectedFile.name : "클릭하여 거래내역서 선택"}
              </p>
              <p className="text-xs mt-0.5" style={{ color: "var(--text-muted)" }}>
                Excel(.xls, .xlsx) 또는 CSV 파일
              </p>
            </div>
          </div>
          <input
            ref={fileRef}
            type="file"
            accept=".xls,.xlsx,.csv"
            className="hidden"
            onChange={(e) => {
              const f = e.target.files?.[0] ?? null;
              setSelectedFile(f);
              setPreview(null);
              setImportResult(null);
              setUploadError(null);
            }}
          />

          <div className="mt-5 flex flex-wrap gap-3">
            <Button
              variant="secondary"
              onClick={handlePreview}
              disabled={!selectedFile || previewing}
              loading={previewing}
            >
              {previewing ? "미리보기 중..." : "미리보기"}
            </Button>
            <Button
              onClick={handleImport}
              disabled={!selectedFile || importing}
              loading={importing}
            >
              {importing ? "가져오는 중..." : "가져오기"}
            </Button>
          </div>

          {uploadError && (
            <div className="mt-4">
              <ErrorState message={uploadError} />
            </div>
          )}

          {/* Preview result summary */}
          {preview && (
            <div className="mt-6 space-y-4">
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                {[
                  { label: "전체 행", value: preview.total_rows },
                  { label: "파싱 성공", value: preview.parsed_rows },
                  { label: "스킵", value: preview.skipped_rows },
                  {
                    label: "경고",
                    value: preview.warnings.length +
                      preview.transactions.reduce((s, t) => s + t.warnings.length, 0),
                  },
                ].map(({ label, value }) => (
                  <div key={label} className="rounded-2xl p-4 text-center"
                    style={{ background: "var(--surface-soft)", border: "1px solid var(--border-soft)" }}>
                    <div className="text-2xl font-semibold" style={{ color: "var(--text-main)" }}>{value}</div>
                    <div className="text-xs mt-1" style={{ color: "var(--text-muted)" }}>{label}</div>
                  </div>
                ))}
              </div>
              {preview.errors.length > 0 && (
                <ErrorState message={preview.errors.join(", ")} />
              )}
              {preview.warnings.length > 0 && (
                <div className="rounded-xl px-4 py-3 text-sm"
                  style={{ background: "var(--warning-soft)", color: "var(--warning)", border: "1px solid rgba(185,130,43,0.15)" }}>
                  {preview.warnings.map((w, i) => <div key={i}>{w}</div>)}
                </div>
              )}
              <div className="overflow-x-auto rounded-xl"
                style={{ border: "1px solid var(--border-soft)" }}>
                <table className="w-full text-sm">
                  <thead>
                    <tr style={{ background: "var(--surface-soft)", borderBottom: "1px solid var(--border-soft)" }}>
                      {["거래일시", "구분", "적요", "출금액", "입금액", "잔액", "거래점", "경고"].map((h) => (
                        <th key={h}
                          className="px-3 py-2.5 text-left text-xs font-semibold uppercase tracking-wide"
                          style={{ color: "var(--text-muted)" }}>
                          {h}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {preview.transactions.map((t, i) => (
                      <tr key={i}
                        style={{ borderBottom: "1px solid var(--border-soft)" }}
                        onMouseEnter={(e) => (e.currentTarget.style.background = "var(--surface-soft)")}
                        onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}>
                        <td className="px-3 py-2.5 whitespace-nowrap text-xs"
                          style={{ color: "var(--text-muted)" }}>
                          {fmtDate(t.transaction_datetime)}
                        </td>
                        <td className="px-3 py-2.5" style={{ color: "var(--text-main)" }}>
                          {t.transaction_type ?? "-"}
                        </td>
                        <td className="px-3 py-2.5 max-w-[200px] truncate" style={{ color: "var(--text-main)" }}>
                          {t.memo ?? "-"}
                        </td>
                        <td className="px-3 py-2.5 text-right font-medium" style={{ color: t.withdraw_amount ? "var(--danger)" : "var(--text-muted)" }}>
                          {t.withdraw_amount ? fmt(t.withdraw_amount) : "-"}
                        </td>
                        <td className="px-3 py-2.5 text-right font-medium" style={{ color: t.deposit_amount ? "var(--success)" : "var(--text-muted)" }}>
                          {t.deposit_amount ? fmt(t.deposit_amount) : "-"}
                        </td>
                        <td className="px-3 py-2.5 text-right" style={{ color: "var(--text-main)" }}>
                          {fmt(t.balance)}
                        </td>
                        <td className="px-3 py-2.5" style={{ color: "var(--text-muted)" }}>
                          {t.branch ?? "-"}
                        </td>
                        <td className="px-3 py-2.5 text-xs" style={{ color: "var(--warning)" }}>
                          {t.warnings.join(", ") || "-"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Import result */}
          {importResult && (
            <div className="mt-6 space-y-4">
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                {[
                  { label: "전체 행", value: importResult.total_rows },
                  { label: "파싱 성공", value: importResult.parsed_rows },
                  { label: "저장됨", value: importResult.inserted_rows },
                  { label: "중복 스킵", value: importResult.duplicate_rows },
                ].map(({ label, value }) => (
                  <div key={label} className="rounded-2xl p-4 text-center"
                    style={{ background: "var(--success-soft)", border: "1px solid rgba(63,125,88,0.15)" }}>
                    <div className="text-2xl font-semibold" style={{ color: "var(--success)" }}>{value}</div>
                    <div className="text-xs mt-1" style={{ color: "var(--success)" }}>{label}</div>
                  </div>
                ))}
              </div>
              <p className="text-sm font-medium" style={{ color: "var(--success)" }}>
                가져오기 완료: {importResult.inserted_rows}건 저장, {importResult.duplicate_rows}건 중복 스킵
              </p>
              {importResult.errors.length > 0 && (
                <ErrorState message={importResult.errors.join(", ")} />
              )}
            </div>
          )}
        </Card>

        {/* Saved transactions */}
        <Card padding="none">
          <div className="flex flex-col gap-3 p-5 sm:flex-row sm:items-center sm:justify-between"
            style={{ borderBottom: "1px solid var(--border-soft)" }}>
            <div>
              <h2 className="text-base font-semibold" style={{ color: "var(--text-main)" }}>저장된 거래내역</h2>
              <p className="text-xs mt-0.5" style={{ color: "var(--text-muted)" }}>
                전체 {transactions.length}건 중 {pagedTransactions.length}건 표시
              </p>
            </div>
            <div className="flex items-center gap-2">
              <label className="text-xs whitespace-nowrap" style={{ color: "var(--text-muted)" }}>표시 개수</label>
              <select
                className="rounded-xl px-2 py-1 text-sm focus:outline-none"
                style={{ background: "var(--surface)", color: "var(--text-main)", border: "1px solid var(--border-soft)" }}
                value={String(txPageSize)}
                onChange={(e) => {
                  const v = e.target.value;
                  setTxPageSize(v === "all" ? "all" : Number(v));
                  setTxPage(1);
                }}
              >
                <option value="50">50건</option>
                <option value="100">100건</option>
                <option value="all">전체</option>
              </select>
              <Button variant="ghost" size="sm" onClick={() => loadTransactions()}>새로고침</Button>
            </div>
          </div>

          {/* Filters */}
          <div className="flex flex-wrap gap-3 p-5"
            style={{ borderBottom: "1px solid var(--border-soft)" }}>
            {/* 분기 필터 */}
            <QuarterFilter
              value={operatingQuarter}
              onChange={(q) => {
                setOperatingQuarter(q);
                loadTransactions(filters, q);
              }}
              label="분기"
            />
            <input
              type="text"
              placeholder="검색 (적요/구분/거래점)"
              value={filters.q ?? ""}
              onChange={(e) => setFilters((f) => ({ ...f, q: e.target.value }))}
              className="rounded-xl px-3 py-2 text-sm focus:outline-none w-48"
              style={{
                background: "var(--surface)",
                color: "var(--text-main)",
                border: "1px solid var(--border-soft)",
              }}
            />
            <select
              value={filters.match_status ?? ""}
              onChange={(e) => setFilters((f) => ({ ...f, match_status: e.target.value }))}
              className="rounded-xl px-3 py-2 text-sm focus:outline-none"
              style={{
                background: "var(--surface)",
                color: "var(--text-main)",
                border: "1px solid var(--border-soft)",
              }}
            >
              <option value="">매칭상태 전체</option>
              <option value="unmatched">미매칭</option>
              <option value="matched">매칭됨</option>
              <option value="need_check">확인필요</option>
              <option value="ignored">무시</option>
            </select>
            <select
              value={filters.payment_type ?? ""}
              onChange={(e) => setFilters((f) => ({ ...f, payment_type: e.target.value }))}
              className="rounded-xl px-3 py-2 text-sm focus:outline-none"
              style={{
                background: "var(--surface)",
                color: "var(--text-main)",
                border: "1px solid var(--border-soft)",
              }}
            >
              <option value="">납부유형 전체</option>
              <option value="membership_fee">회비</option>
              <option value="activity_fee">활동비</option>
            </select>
            {!operatingQuarter && (
              <>
                <input
                  type="date"
                  value={filters.start_date ?? ""}
                  onChange={(e) => setFilters((f) => ({ ...f, start_date: e.target.value }))}
                  className="rounded-xl px-3 py-2 text-sm focus:outline-none"
                  style={{
                    background: "var(--surface)",
                    color: "var(--text-main)",
                    border: "1px solid var(--border-soft)",
                  }}
                />
                <input
                  type="date"
                  value={filters.end_date ?? ""}
                  onChange={(e) => setFilters((f) => ({ ...f, end_date: e.target.value }))}
                  className="rounded-xl px-3 py-2 text-sm focus:outline-none"
                  style={{
                    background: "var(--surface)",
                    color: "var(--text-main)",
                    border: "1px solid var(--border-soft)",
                  }}
                />
              </>
            )}
            <Button variant="primary" size="sm" onClick={() => loadTransactions()}>
              검색
            </Button>
          </div>

          {/* Budget Exclusion Modal */}
          {excludeModal && (
            <div style={{
              position: "fixed", inset: 0, zIndex: 9999,
              background: "rgba(0,0,0,0.5)",
              display: "flex", alignItems: "center", justifyContent: "center",
            }}>
              <div style={{
                background: "var(--surface)", borderRadius: 16, padding: 24,
                minWidth: 340, maxWidth: 480, boxShadow: "0 8px 32px rgba(0,0,0,0.2)",
              }}>
                <h3 style={{ fontWeight: 600, marginBottom: 12 }}>예산 집계 제외</h3>
                <p style={{ fontSize: 13, color: "var(--text-sub)", marginBottom: 16 }}>
                  <b>{excludeModal.memo ?? "(적요 없음)"}</b><br />
                  {excludeModal.deposit_amount > 0
                    ? `입금 ${excludeModal.deposit_amount.toLocaleString()}원`
                    : `출금 ${excludeModal.withdraw_amount.toLocaleString()}원`}
                </p>
                <div style={{ marginBottom: 12 }}>
                  <label style={{ fontSize: 13, fontWeight: 500, display: "block", marginBottom: 6 }}>제외 유형</label>
                  <select value={excludeType} onChange={(e) => setExcludeType(e.target.value as "income" | "expense" | "both")}
                    style={{ width: "100%", padding: "8px 10px", borderRadius: 8, border: "1px solid var(--border-soft)", background: "var(--surface)", color: "var(--text-main)", fontSize: 13 }}>
                    <option value="both">예산 집계 전체 제외</option>
                    <option value="income">수입에서만 제외</option>
                    <option value="expense">지출에서만 제외</option>
                  </select>
                </div>
                <div style={{ marginBottom: 16 }}>
                  <label style={{ fontSize: 13, fontWeight: 500, display: "block", marginBottom: 6 }}>사유</label>
                  <input type="text" value={excludeReason} onChange={(e) => setExcludeReason(e.target.value)}
                    placeholder="제외 사유를 입력하세요"
                    style={{ width: "100%", padding: "8px 10px", borderRadius: 8, border: "1px solid var(--border-soft)", background: "var(--surface)", color: "var(--text-main)", fontSize: 13, boxSizing: "border-box" }}
                  />
                </div>
                <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
                  <Button variant="ghost" size="sm" onClick={() => setExcludeModal(null)}>취소</Button>
                  <Button variant="primary" size="sm" onClick={confirmExclude} disabled={excludeBusy !== null}>
                    {excludeBusy ? "처리중..." : "제외 확정"}
                  </Button>
                </div>
              </div>
            </div>
          )}

          {listError && (
            <div className="p-5">
              <ErrorState message={listError} onRetry={() => loadTransactions()} />
            </div>
          )}

          {loading ? (
            <LoadingState />
          ) : transactions.length === 0 ? (
            <EmptyState
              message="거래내역이 없습니다."
              description="거래내역서를 업로드하여 데이터를 추가하세요."
            />
          ) : (
            <>
            {/* Mobile cards */}
            <div className="md:hidden divide-y" style={{ borderTop: "1px solid var(--border-soft)" }}>
              {pagedTransactions.map((t) => {
                const isExcluded = t.exclude_from_budget || t.exclude_from_income || t.exclude_from_expense;
                return (
                <div key={t.id} className="p-4 space-y-1.5">
                  <div className="flex items-center justify-between gap-2">
                    <div className="flex items-center gap-1.5 flex-1 min-w-0">
                      <p className="text-sm font-medium truncate" style={{ color: "var(--text-main)" }}>{t.memo ?? "-"}</p>
                      {isExcluded && (
                        <span className="shrink-0 text-xs rounded px-1.5 py-0.5"
                          style={{ background: "#fef3c7", color: "#92400e", fontSize: 10, fontWeight: 600 }}>
                          {t.exclude_from_budget ? "전체제외" : t.exclude_from_income ? "수입제외" : "지출제외"}
                        </span>
                      )}
                    </div>
                    <StatusBadge status={t.match_status} />
                  </div>
                  <p className="text-xs" style={{ color: "var(--text-muted)" }}>{fmtDate(t.transaction_datetime)}</p>
                  <div className="flex items-center gap-3 text-sm">
                    {t.deposit_amount > 0 && <span className="font-medium" style={{ color: "var(--success)" }}>+{fmt(t.deposit_amount)}원</span>}
                    {t.withdraw_amount > 0 && <span className="font-medium" style={{ color: "var(--danger)" }}>-{fmt(t.withdraw_amount)}원</span>}
                    <span className="text-xs" style={{ color: "var(--text-muted)" }}>잔 {fmt(t.balance)}원</span>
                    <span className="flex-1" />
                    {isExcluded ? (
                      <button
                        className="text-xs"
                        style={{ color: "#d97706", fontWeight: 500 }}
                        disabled={excludeBusy === t.id}
                        onClick={() => handleInclude(t)}>
                        {excludeBusy === t.id ? "..." : "제외 해제"}
                      </button>
                    ) : (
                      <button
                        className="text-xs"
                        style={{ color: "var(--text-muted)" }}
                        onClick={() => handleExclude(t)}>
                        예산제외
                      </button>
                    )}
                  </div>
                </div>
                );
              })}
            </div>
            {/* Desktop table */}
            <div className="hidden md:block overflow-x-auto">
              <table className="w-full text-sm" style={{ minWidth: 860 }}>
                <thead>
                  <tr style={{ background: "var(--surface-soft)", borderBottom: "1px solid var(--border-soft)" }}>
                    {["거래일시", "구분", "적요", "출금액", "입금액", "잔액", "거래점", "매칭상태", "납부유형", ""].map((h) => (
                      <th key={h}
                        className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide"
                        style={{ color: "var(--text-muted)" }}>
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {pagedTransactions.map((t) => {
                    const isExcluded = !!(t.exclude_from_budget || t.exclude_from_income || t.exclude_from_expense);
                    const menuOpen = openMenuId === t.id;
                    return (
                    <tr key={t.id}
                      style={{ borderBottom: "1px solid var(--border-soft)", position: "relative" }}
                      onMouseEnter={(e) => (e.currentTarget.style.background = "var(--surface-soft)")}
                      onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}>
                      <td className="px-4 py-3 whitespace-nowrap text-xs" style={{ color: "var(--text-muted)" }}>
                        {fmtDate(t.transaction_datetime)}
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap text-xs" style={{ color: "var(--text-main)" }}>
                        {t.transaction_type ?? "-"}
                      </td>
                      <td className="px-4 py-3 max-w-[220px] truncate" title={t.memo ?? ""} style={{ color: "var(--text-main)" }}>
                        {t.memo ?? "-"}
                        {isExcluded && (
                          <span className="ml-1 text-xs rounded px-1"
                            style={{ background: "#fef3c7", color: "#92400e", fontSize: 10 }}>
                            {t.exclude_from_budget ? "전체제외" : t.exclude_from_income ? "수입제외" : "지출제외"}
                          </span>
                        )}
                      </td>
                      <td className="px-4 py-3 text-right font-medium whitespace-nowrap"
                        style={{ color: t.withdraw_amount ? "var(--danger)" : "var(--text-muted)" }}>
                        {t.withdraw_amount ? fmt(t.withdraw_amount) : "-"}
                      </td>
                      <td className="px-4 py-3 text-right font-medium whitespace-nowrap"
                        style={{ color: t.deposit_amount ? "var(--success)" : "var(--text-muted)" }}>
                        {t.deposit_amount ? fmt(t.deposit_amount) : "-"}
                      </td>
                      <td className="px-4 py-3 text-right whitespace-nowrap" style={{ color: "var(--text-main)" }}>
                        {fmt(t.balance)}
                      </td>
                      <td className="px-4 py-3 max-w-[100px] truncate" title={t.branch ?? ""} style={{ color: "var(--text-muted)" }}>
                        {t.branch ?? "-"}
                      </td>
                      <td className="px-4 py-3">
                        <StatusBadge status={t.match_status} />
                      </td>
                      <td className="px-4 py-3 text-xs whitespace-nowrap" style={{ color: "var(--text-muted)" }}>
                        {t.payment_type ?? "-"}
                      </td>
                      {/* ⋯ 액션 드롭다운 */}
                      <td className="px-3 py-3" style={{ position: "relative" }}>
                        <button
                          onClick={() => setOpenMenuId(menuOpen ? null : t.id)}
                          style={{
                            width: 28, height: 28, borderRadius: 8, border: "1px solid var(--border-soft)",
                            background: menuOpen ? "var(--surface-soft)" : "transparent",
                            cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center",
                            color: "var(--text-muted)",
                          }}
                        >
                          <MoreHorizontal size={15} />
                        </button>
                        {menuOpen && (
                          <>
                            {/* 바깥 클릭 닫기 오버레이 */}
                            <div
                              style={{ position: "fixed", inset: 0, zIndex: 40 }}
                              onClick={() => setOpenMenuId(null)}
                            />
                            <div style={{
                              position: "absolute", right: 0, top: 32, zIndex: 50,
                              background: "var(--surface)", border: "1px solid var(--border-soft)",
                              borderRadius: 12, boxShadow: "0 8px 24px rgba(0,0,0,0.15)",
                              minWidth: 156, padding: "4px 0", overflow: "hidden",
                            }}>
                              {/* 매칭 취소 */}
                              {t.match_status === "matched" && (
                                <button onClick={() => { setOpenMenuId(null); handleUnmatch(t.id); }}
                                  style={menuItemStyle} disabled={unmatching === t.id}>
                                  {unmatching === t.id ? "처리 중..." : "매칭 취소"}
                                </button>
                              )}
                              {/* 환불 취소 */}
                              {t.match_status === "refund_matched" && (
                                <button onClick={() => { setOpenMenuId(null); handleUnmatchRefund(t.id); }}
                                  style={menuItemStyle} disabled={unmatching === t.id}>
                                  환불 취소
                                </button>
                              )}
                              {/* 환불로 매칭 */}
                              {t.withdraw_amount > 0 && t.match_status !== "matched" && t.match_status !== "refund_matched" && (
                                <button onClick={() => { setOpenMenuId(null); openRefundMatch(t); }}
                                  style={menuItemStyle}>
                                  환불로 매칭
                                </button>
                              )}
                              {/* 구분선 */}
                              {(t.match_status === "matched" || t.match_status === "refund_matched" ||
                                (t.withdraw_amount > 0 && t.match_status !== "matched")) && (
                                <div style={{ height: 1, background: "var(--border-soft)", margin: "4px 0" }} />
                              )}
                              {/* 예산 제외 관련 */}
                              {isExcluded ? (
                                <>
                                  <button onClick={() => { setOpenMenuId(null); handleInclude(t); }}
                                    style={{ ...menuItemStyle, color: "#d97706" }}
                                    disabled={excludeBusy === t.id}>
                                    {excludeBusy === t.id ? "처리 중..." : "제외 해제"}
                                  </button>
                                  {t.exclude_reason && (
                                    <div style={{ padding: "4px 14px 6px", fontSize: 11, color: "var(--text-muted)" }}>
                                      사유: {t.exclude_reason}
                                    </div>
                                  )}
                                </>
                              ) : (
                                <>
                                  {t.deposit_amount > 0 && (
                                    <button onClick={() => { setOpenMenuId(null); setExcludeType("income"); handleExclude(t); }}
                                      style={menuItemStyle}>
                                      수입에서 제외
                                    </button>
                                  )}
                                  {t.withdraw_amount > 0 && (
                                    <button onClick={() => { setOpenMenuId(null); setExcludeType("expense"); handleExclude(t); }}
                                      style={menuItemStyle}>
                                      지출에서 제외
                                    </button>
                                  )}
                                  <button onClick={() => { setOpenMenuId(null); setExcludeType("both"); handleExclude(t); }}
                                    style={menuItemStyle}>
                                    예산 전체 제외
                                  </button>
                                </>
                              )}
                            </div>
                          </>
                        )}
                      </td>
                    </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
            </>
          )}
          {txPageSize !== "all" && txTotalPages > 1 && (
            <div className="flex items-center justify-center gap-3 p-4" style={{ borderTop: "1px solid var(--border-soft)" }}>
              <Button size="sm" variant="ghost" disabled={txPage <= 1} onClick={() => setTxPage((p) => p - 1)}>이전</Button>
              <span className="text-sm" style={{ color: "var(--text-muted)" }}>
                {txPage} / {txTotalPages} 페이지 (전체 {transactions.length}건)
              </span>
              <Button size="sm" variant="ghost" disabled={txPage >= txTotalPages} onClick={() => setTxPage((p) => p + 1)}>다음</Button>
              <Button size="sm" variant="ghost" onClick={() => { setTxPageSize("all"); setTxPage(1); }}>전체 보기</Button>
            </div>
          )}
        </Card>
      </div>

      {/* Refund match modal */}
      {refundMatchTarget && (
        <div className="fixed inset-0 flex items-center justify-center z-50"
          style={{ background: "rgba(31,31,36,0.5)" }}>
          <div className="rounded-2xl p-6 w-full max-w-md space-y-4"
            style={{ background: "var(--surface)", border: "1px solid var(--border-soft)" }}>
            <h3 className="text-base font-semibold" style={{ color: "var(--text-main)" }}>환불 거래내역 매칭</h3>
            <p className="text-xs" style={{ color: "var(--text-muted)" }}>
              출금: {fmt(refundMatchTarget.withdraw_amount)}원 — {refundMatchTarget.memo ?? ""}
            </p>
            <div>
              <label className="text-xs mb-1 block" style={{ color: "var(--text-muted)" }}>환불 대상 납부기록 선택</label>
              <select
                className="w-full rounded-xl px-3 py-2 text-sm min-h-[44px]"
                style={{ background: "var(--surface)", color: "var(--text-main)", border: "1px solid var(--border-soft)" }}
                value={selectedRefundRecordId}
                onChange={(e) => setSelectedRefundRecordId(e.target.value)}
              >
                <option value="">-- 선택 --</option>
                {refundRecords.map((r) => (
                  <option key={r.payment_record_id} value={r.payment_record_id}>
                    {r.member_name ?? "-"} — {r.activity_title ?? "-"} — 납부 {fmt(r.paid_amount)}원
                  </option>
                ))}
              </select>
              {refundRecords.length === 0 && (
                <p className="text-xs mt-1" style={{ color: "var(--text-muted)" }}>환불 필요 상태인 납부 기록이 없습니다.</p>
              )}
            </div>
            {refundMatchError && <p className="text-sm" style={{ color: "var(--danger)" }}>{refundMatchError}</p>}
            <div className="flex gap-2">
              <Button onClick={handleRefundMatch} loading={refundMatchBusy} disabled={!selectedRefundRecordId}>환불 매칭</Button>
              <Button variant="secondary" onClick={() => setRefundMatchTarget(null)} disabled={refundMatchBusy}>취소</Button>
            </div>
          </div>
        </div>
      )}
    </AppShell>
  );
}
