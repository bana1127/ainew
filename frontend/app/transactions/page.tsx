"use client";

import { useEffect, useRef, useState } from "react";
import { Upload } from "lucide-react";
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
  type RefundRecord,
} from "@/lib/api";

import { AppShell } from "@/components/layout/AppShell";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorState } from "@/components/ui/ErrorState";
import { LoadingState } from "@/components/ui/LoadingState";
import { PageHeader } from "@/components/ui/PageHeader";
import { StatusBadge } from "@/components/ui/StatusBadge";

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

  const loadTransactions = async (f: TransactionQueryParams = filters) => {
    setLoading(true);
    setListError(null);
    try {
      const params: TransactionQueryParams = {};
      if (f.q) params.q = f.q;
      if (f.match_status) params.match_status = f.match_status;
      if (f.payment_type) params.payment_type = f.payment_type;
      if (f.start_date) params.start_date = f.start_date;
      if (f.end_date) params.end_date = f.end_date;
      setTransactions(await getTransactionsTyped(params));
    } catch (e: unknown) {
      setListError(e instanceof Error ? e.message : "불러오기 실패");
    } finally {
      setLoading(false);
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
          <div className="flex items-center justify-between p-5"
            style={{ borderBottom: "1px solid var(--border-soft)" }}>
            <h2 className="text-base font-semibold" style={{ color: "var(--text-main)" }}>
              저장된 거래내역
            </h2>
            <Button variant="ghost" size="sm" onClick={() => loadTransactions()}>
              새로고침
            </Button>
          </div>

          {/* Filters */}
          <div className="flex flex-wrap gap-3 p-5"
            style={{ borderBottom: "1px solid var(--border-soft)" }}>
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
            <Button variant="primary" size="sm" onClick={() => loadTransactions()}>
              검색
            </Button>
          </div>

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
              {transactions.map((t) => (
                <div key={t.id} className="p-4 space-y-1.5">
                  <div className="flex items-center justify-between">
                    <p className="text-sm font-medium truncate max-w-[180px]" style={{ color: "var(--text-main)" }}>{t.memo ?? "-"}</p>
                    <StatusBadge status={t.match_status} />
                  </div>
                  <p className="text-xs" style={{ color: "var(--text-muted)" }}>{fmtDate(t.transaction_datetime)}</p>
                  <div className="flex items-center gap-3 text-sm">
                    {t.deposit_amount > 0 && <span className="font-medium" style={{ color: "var(--success)" }}>+{fmt(t.deposit_amount)}원</span>}
                    {t.withdraw_amount > 0 && <span className="font-medium" style={{ color: "var(--danger)" }}>-{fmt(t.withdraw_amount)}원</span>}
                    <span className="text-xs" style={{ color: "var(--text-muted)" }}>잔 {fmt(t.balance)}원</span>
                  </div>
                </div>
              ))}
            </div>
            {/* Desktop table */}
            <div className="hidden md:block overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr style={{ background: "var(--surface-soft)", borderBottom: "1px solid var(--border-soft)" }}>
                    {["거래일시", "구분", "적요", "출금액", "입금액", "잔액", "거래점", "매칭상태", "납부유형", "생성일", "매칭 취소", "환불 매칭"].map((h) => (
                      <th key={h}
                        className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide"
                        style={{ color: "var(--text-muted)" }}>
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {transactions.map((t) => (
                    <tr key={t.id}
                      style={{ borderBottom: "1px solid var(--border-soft)" }}
                      onMouseEnter={(e) => (e.currentTarget.style.background = "var(--surface-soft)")}
                      onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}>
                      <td className="px-4 py-3 whitespace-nowrap text-xs"
                        style={{ color: "var(--text-muted)" }}>
                        {fmtDate(t.transaction_datetime)}
                      </td>
                      <td className="px-4 py-3" style={{ color: "var(--text-main)" }}>
                        {t.transaction_type ?? "-"}
                      </td>
                      <td className="px-4 py-3 max-w-[200px] truncate" style={{ color: "var(--text-main)" }}>
                        {t.memo ?? "-"}
                      </td>
                      <td className="px-4 py-3 text-right font-medium"
                        style={{ color: t.withdraw_amount ? "var(--danger)" : "var(--text-muted)" }}>
                        {t.withdraw_amount ? fmt(t.withdraw_amount) : "-"}
                      </td>
                      <td className="px-4 py-3 text-right font-medium"
                        style={{ color: t.deposit_amount ? "var(--success)" : "var(--text-muted)" }}>
                        {t.deposit_amount ? fmt(t.deposit_amount) : "-"}
                      </td>
                      <td className="px-4 py-3 text-right" style={{ color: "var(--text-main)" }}>
                        {fmt(t.balance)}
                      </td>
                      <td className="px-4 py-3" style={{ color: "var(--text-muted)" }}>
                        {t.branch ?? "-"}
                      </td>
                      <td className="px-4 py-3">
                        <StatusBadge status={t.match_status} />
                      </td>
                      <td className="px-4 py-3 text-xs" style={{ color: "var(--text-muted)" }}>
                        {t.payment_type ?? "-"}
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap text-xs"
                        style={{ color: "var(--text-muted)" }}>
                        {fmtDate(t.created_at)}
                      </td>
                      <td className="px-4 py-3">
                        {t.match_status === "matched" && (
                          <Button size="sm" variant="ghost" disabled={unmatching === t.id}
                            onClick={() => handleUnmatch(t.id)}>
                            {unmatching === t.id ? "..." : "매칭 취소"}
                          </Button>
                        )}
                      </td>
                      <td className="px-4 py-3">
                        {t.match_status === "refund_matched" ? (
                          <Button size="sm" variant="ghost" disabled={unmatching === t.id}
                            onClick={() => handleUnmatchRefund(t.id)}>
                            {unmatching === t.id ? "..." : "환불취소"}
                          </Button>
                        ) : t.withdraw_amount > 0 && t.match_status !== "matched" ? (
                          <Button size="sm" variant="ghost"
                            onClick={() => openRefundMatch(t)}>
                            환불로 매칭
                          </Button>
                        ) : null}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            </>
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
