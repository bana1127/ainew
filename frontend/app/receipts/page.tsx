"use client";

import React, { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { Trash2, Upload } from "lucide-react";
import {
  ActivityReport,
  ActivitySummary,
  Receipt,
  ReceiptAnalyzeResponse,
  ReceiptQueryParams,
  analyzeReceipt,
  deleteReceipt,
  getActivities,
  getActivityReportsFiltered,
  getReceiptsTyped,
  linkReceiptToActivity,
} from "@/lib/api";

import { AppShell } from "@/components/layout/AppShell";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorState } from "@/components/ui/ErrorState";
import { LoadingState } from "@/components/ui/LoadingState";
import { Modal } from "@/components/ui/Modal";
import { PageHeader } from "@/components/ui/PageHeader";
import { Select } from "@/components/ui/Select";
import { StatusBadge } from "@/components/ui/StatusBadge";

const PAYMENT_METHOD_OPTIONS = [
  { value: "unknown", label: "알 수 없음" },
  { value: "card", label: "카드" },
  { value: "online_card", label: "온라인 카드" },
  { value: "transfer_student", label: "계좌이체 (학생)" },
  { value: "transfer_company", label: "계좌이체 (단체)" },
  { value: "cash_withdrawal", label: "현금 인출" },
  { value: "personal_card_reimbursement", label: "개인카드 후정산" },
  { value: "recurring_payment", label: "정기 결제" },
];

const EVIDENCE_STATUS_OPTIONS = [
  { value: "", label: "전체" },
  { value: "valid", label: "적합" },
  { value: "need_check", label: "확인 필요" },
  { value: "invalid", label: "부적합" },
  { value: "pending", label: "대기" },
];

const PAYMENT_METHOD_ALL_OPTIONS = [
  { value: "", label: "전체 결제방식" },
  ...PAYMENT_METHOD_OPTIONS,
];

function paymentMethodLabel(val: string | null | undefined): string {
  return PAYMENT_METHOD_OPTIONS.find((o) => o.value === val)?.label ?? val ?? "-";
}

const inputStyle: React.CSSProperties = {
  background: "var(--surface)",
  color: "var(--text-main)",
  border: "1px solid var(--border-soft)",
  borderRadius: 12,
  padding: "8px 12px",
  fontSize: 14,
  width: "100%",
};

export default function ReceiptsPage() {
  const fileRef = useRef<HTMLInputElement>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [activityReportId, setActivityReportId] = useState("");
  const [manualPaymentMethod, setManualPaymentMethod] = useState("unknown");
  const [manualCategory, setManualCategory] = useState("");
  const [saveToDb, setSaveToDb] = useState(true);

  const [analyzing, setAnalyzing] = useState(false);
  const [analysisResult, setAnalysisResult] = useState<ReceiptAnalyzeResponse | null>(null);
  const [analyzeError, setAnalyzeError] = useState<string | null>(null);

  const [receipts, setReceipts] = useState<Receipt[]>([]);
  const [loadingList, setLoadingList] = useState(false);
  const [listError, setListError] = useState<string | null>(null);
  const [filters, setFilters] = useState<ReceiptQueryParams>({ evidence_status: "", payment_method: "", q: "" });
  const [filterDraft, setFilterDraft] = useState<ReceiptQueryParams>({ evidence_status: "", payment_method: "", q: "" });

  const [activityReports, setActivityReports] = useState<ActivityReport[]>([]);
  const [activities, setActivities] = useState<ActivitySummary[]>([]);
  const [deleteTarget, setDeleteTarget] = useState<Receipt | null>(null);
  const [deleting, setDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  // Activity link modal state
  const [linkTarget, setLinkTarget] = useState<Receipt | null>(null);
  const [linkActivityId, setLinkActivityId] = useState("");
  const [linking, setLinking] = useState(false);
  const [linkError, setLinkError] = useState<string | null>(null);

  // Map: activity_report_id → title (for display)
  const activityTitleMap = Object.fromEntries([
    ...activityReports.map((r) => [r.id, r.title]),
    ...activities.map((a) => [a.id, a.title]),
  ]);

  const activityReportOptions = [
    { value: "", label: "-- 연결 안 함 --" },
    ...activityReports.map((r) => ({
      value: r.id,
      label: `${r.title}${r.activity_date ? ` (${r.activity_date})` : ""}`,
    })),
  ];

  const activityLinkOptions = activities
    .filter((a) => a.status !== "archived")
    .map((a) => ({
      value: a.id,
      label: `${a.title}${a.activity_date ? ` (${a.activity_date})` : ""}`,
    }));

  async function loadReceipts(f: ReceiptQueryParams = filters) {
    setLoadingList(true);
    setListError(null);
    try {
      setReceipts(await getReceiptsTyped(f));
    } catch (err) {
      setListError(err instanceof Error ? err.message : "목록 불러오기 실패");
    } finally {
      setLoadingList(false);
    }
  }

  async function handleAnalyze() {
    if (!selectedFile || analyzing) return;
    setAnalyzing(true);
    setAnalyzeError(null);
    setAnalysisResult(null);
    try {
      const formData = new FormData();
      formData.append("file", selectedFile);
      if (activityReportId) formData.append("activity_report_id", activityReportId);
      if (manualPaymentMethod && manualPaymentMethod !== "unknown")
        formData.append("manual_payment_method", manualPaymentMethod);
      if (manualCategory) formData.append("manual_category", manualCategory);
      formData.append("save_to_db", saveToDb ? "true" : "false");
      const result = await analyzeReceipt(formData);
      setAnalysisResult(result);
      await loadReceipts(filters);
    } catch (err) {
      setAnalyzeError(err instanceof Error ? err.message : "분석 중 오류 발생");
    } finally {
      setAnalyzing(false);
    }
  }

  function handleSearch() {
    const f = { ...filterDraft };
    setFilters(f);
    loadReceipts(f);
  }

  async function handleDeleteConfirm() {
    if (!deleteTarget) return;
    setDeleting(true);
    setDeleteError(null);
    try {
      await deleteReceipt(deleteTarget.id);
      setDeleteTarget(null);
      await loadReceipts(filters);
    } catch (err) {
      setDeleteError(err instanceof Error ? err.message : "삭제에 실패했습니다.");
    } finally {
      setDeleting(false);
    }
  }

  async function handleLink() {
    if (!linkTarget || !linkActivityId) return;
    setLinking(true);
    setLinkError(null);
    try {
      await linkReceiptToActivity(linkTarget.id, linkActivityId);
      setLinkTarget(null);
      setLinkActivityId("");
      await loadReceipts(filters);
    } catch (err) {
      setLinkError(err instanceof Error ? err.message : "활동 연결에 실패했습니다.");
    } finally {
      setLinking(false);
    }
  }

  async function handleUnlink(receipt: Receipt) {
    try {
      await linkReceiptToActivity(receipt.id, null);
      await loadReceipts(filters);
    } catch { /* ignore */ }
  }

  useEffect(() => {
    getActivityReportsFiltered().then(setActivityReports).catch(() => {});
    getActivities({ limit: 100 }).then(setActivities).catch(() => {});
    loadReceipts(filters);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const extracted = analysisResult?.extracted;
  const policy = analysisResult?.policy;

  return (
    <AppShell>
      <div className="space-y-6">
        <PageHeader
          title="영수증 분석"
          description="영수증을 업로드하고 AI로 증빙 적합성을 분석합니다."
        />

        {/* Upload & Analyze */}
        <Card padding="lg">
          <h2 className="text-base font-semibold mb-5" style={{ color: "var(--text-main)" }}>
            영수증 업로드 및 분석
          </h2>

          {/* Dropzone area */}
          <div
            className="flex flex-col items-center justify-center gap-3 rounded-2xl p-8 text-center cursor-pointer transition-colors hover:opacity-80"
            style={{
              border: "2px dashed var(--border-soft)",
              background: "var(--surface-soft)",
            }}
            onClick={() => fileRef.current?.click()}
          >
            <div className="rounded-2xl p-3" style={{ background: "var(--primary-soft)" }}>
              <Upload className="h-5 w-5" style={{ color: "var(--primary)" }} />
            </div>
            <div>
              <p className="text-sm font-medium" style={{ color: "var(--text-main)" }}>
                {selectedFile ? selectedFile.name : "클릭하여 영수증 파일 선택"}
              </p>
              <p className="text-xs mt-0.5" style={{ color: "var(--text-muted)" }}>
                이미지(JPG, PNG) 또는 PDF 지원
              </p>
            </div>
          </div>
          <input
            ref={fileRef}
            type="file"
            accept="image/*,application/pdf"
            className="hidden"
            onChange={(e) => setSelectedFile(e.target.files?.[0] ?? null)}
          />

          {/* Options */}
          <div className="mt-5 grid gap-4 sm:grid-cols-2">
            <Select
              label="활동 보고서 연결 (선택)"
              options={activityReportOptions}
              value={activityReportId}
              onChange={(e) => setActivityReportId(e.target.value)}
            />
            <Select
              label="결제 방식 수동 선택"
              options={PAYMENT_METHOD_OPTIONS}
              value={manualPaymentMethod}
              onChange={(e) => setManualPaymentMethod(e.target.value)}
            />
            <div className="flex flex-col gap-1">
              <label className="text-sm font-medium" style={{ color: "var(--text-main)" }}>
                지출 분류 (선택)
              </label>
              <input
                type="text"
                value={manualCategory}
                onChange={(e) => setManualCategory(e.target.value)}
                placeholder="예: 식비, 교통비, 행사비..."
                className="rounded-xl px-3 py-2 text-sm focus:outline-none"
                style={{
                  background: "var(--surface)",
                  color: "var(--text-main)",
                  border: "1px solid var(--border-soft)",
                }}
              />
            </div>
            <div className="flex items-end pb-1">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  id="save-to-db"
                  type="checkbox"
                  checked={saveToDb}
                  onChange={(e) => setSaveToDb(e.target.checked)}
                  className="h-4 w-4 rounded"
                  style={{ accentColor: "var(--primary)" }}
                />
                <span className="text-sm" style={{ color: "var(--text-main)" }}>
                  분석 결과를 DB에 저장
                </span>
              </label>
            </div>
          </div>

          <div className="mt-5">
            <Button
              onClick={handleAnalyze}
              disabled={!selectedFile || analyzing}
              loading={analyzing}
            >
              {analyzing ? "분석 중..." : "영수증 분석"}
            </Button>
          </div>

          {analyzeError && (
            <div className="mt-4">
              <ErrorState message={analyzeError} />
            </div>
          )}
        </Card>

        {/* Analysis Result */}
        {analysisResult && extracted && policy && (
          <Card padding="lg">
            <div className="flex items-center gap-3 mb-5 flex-wrap">
              <h2 className="text-base font-semibold" style={{ color: "var(--text-main)" }}>
                분석 결과
              </h2>
              <span className="inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium"
                style={{ background: "var(--primary-soft)", color: "var(--primary)" }}>
                {analysisResult.model !== "mock" ? analysisResult.model : "AI 분석"}
              </span>
              <StatusBadge status={policy.evidence_status} />
            </div>

            <div className="grid sm:grid-cols-2 gap-6">
              {/* Extracted info */}
              <div className="space-y-2">
                <h3 className="text-xs font-semibold uppercase tracking-wider mb-3"
                  style={{ color: "var(--text-muted)" }}>
                  추출된 정보
                </h3>
                {[
                  { label: "날짜", value: extracted.receipt_date ?? "-" },
                  { label: "가맹점", value: extracted.store_name ?? "-" },
                  {
                    label: "금액",
                    value: extracted.amount != null
                      ? `${extracted.amount.toLocaleString("ko-KR")}원`
                      : "-",
                  },
                  { label: "결제 방식", value: paymentMethodLabel(extracted.payment_method) },
                  { label: "지출 분류", value: extracted.category ?? "-" },
                  {
                    label: "신뢰도",
                    value: extracted.confidence != null
                      ? `${Math.round(extracted.confidence * 100)}%`
                      : "-",
                  },
                ].map(({ label, value }) => (
                  <div key={label} className="flex items-center justify-between py-1.5"
                    style={{ borderBottom: "1px solid var(--border-soft)" }}>
                    <span className="text-sm" style={{ color: "var(--text-muted)" }}>{label}</span>
                    <span className="text-sm font-medium" style={{ color: "var(--text-main)" }}>
                      {value}
                    </span>
                  </div>
                ))}
              </div>

              {/* Policy result */}
              <div>
                <h3 className="text-xs font-semibold uppercase tracking-wider mb-3"
                  style={{ color: "var(--text-muted)" }}>
                  감사 규정 검토
                </h3>
                <div className="space-y-2">
                  <div className="flex items-center justify-between py-1.5"
                    style={{ borderBottom: "1px solid var(--border-soft)" }}>
                    <span className="text-sm" style={{ color: "var(--text-muted)" }}>증빙 상태</span>
                    <StatusBadge status={policy.evidence_status} />
                  </div>
                  <div className="flex items-center justify-between py-1.5"
                    style={{ borderBottom: "1px solid var(--border-soft)" }}>
                    <span className="text-sm" style={{ color: "var(--text-muted)" }}>확인 필요</span>
                    <span className="text-sm font-medium"
                      style={{ color: policy.need_check ? "var(--warning)" : "var(--text-muted)" }}>
                      {policy.need_check ? "예" : "아니오"}
                    </span>
                  </div>
                  {policy.required_evidence && policy.required_evidence.length > 0 && (
                    <div className="py-1.5"
                      style={{ borderBottom: "1px solid var(--border-soft)" }}>
                      <span className="text-sm" style={{ color: "var(--text-muted)" }}>필요 증빙</span>
                      <p className="text-sm font-medium mt-0.5" style={{ color: "var(--text-main)" }}>
                        {policy.required_evidence.join(", ")}
                      </p>
                    </div>
                  )}
                  {policy.reason && (
                    <div className="py-1.5">
                      <span className="text-sm" style={{ color: "var(--text-muted)" }}>판단 사유</span>
                      <p className="text-sm mt-0.5" style={{ color: "var(--text-main)" }}>
                        {policy.reason}
                      </p>
                    </div>
                  )}
                </div>

                {/* Activity link for analysis result */}
                {analysisResult.receipt_id && (
                  <div className="mt-4 pt-4" style={{ borderTop: "1px solid var(--border-soft)" }}>
                    <p className="text-xs font-medium mb-2" style={{ color: "var(--text-muted)" }}>활동에 연결</p>
                    {analysisResult.activity_report_id ? (
                      <div className="flex items-center gap-2">
                        <span className="text-xs rounded-full px-2.5 py-1"
                          style={{ background: "var(--success-soft)", color: "var(--success)" }}>
                          {activityTitleMap[analysisResult.activity_report_id] ?? "연결된 활동"}
                        </span>
                        <Link href={`/activities/${analysisResult.activity_report_id}`}>
                          <Button size="sm" variant="ghost">활동 상세에서 보기</Button>
                        </Link>
                      </div>
                    ) : (
                      <Button
                        size="sm"
                        variant="secondary"
                        onClick={() => {
                          const receipt = receipts.find((r) => r.id === analysisResult.receipt_id);
                          if (receipt) {
                            setLinkTarget(receipt);
                            setLinkActivityId("");
                          }
                        }}
                      >
                        활동에 연결
                      </Button>
                    )}
                  </div>
                )}
              </div>
            </div>
          </Card>
        )}

        {/* Saved Receipts List */}
        <Card padding="none">
          <div className="flex items-center justify-between p-5"
            style={{ borderBottom: "1px solid var(--border-soft)" }}>
            <h2 className="text-base font-semibold" style={{ color: "var(--text-main)" }}>
              저장된 영수증 목록
            </h2>
            <Button variant="ghost" size="sm" onClick={() => loadReceipts(filters)}>
              새로고침
            </Button>
          </div>

          {/* Filters */}
          <div className="flex flex-wrap items-end gap-3 p-5"
            style={{ borderBottom: "1px solid var(--border-soft)" }}>
            <Select
              options={EVIDENCE_STATUS_OPTIONS}
              value={filterDraft.evidence_status ?? ""}
              onChange={(e) => setFilterDraft((f) => ({ ...f, evidence_status: e.target.value }))}
              className="w-36"
            />
            <Select
              options={PAYMENT_METHOD_ALL_OPTIONS}
              value={filterDraft.payment_method ?? ""}
              onChange={(e) => setFilterDraft((f) => ({ ...f, payment_method: e.target.value }))}
              className="w-44"
            />
            <input
              type="text"
              value={filterDraft.q ?? ""}
              onChange={(e) => setFilterDraft((f) => ({ ...f, q: e.target.value }))}
              onKeyDown={(e) => e.key === "Enter" && handleSearch()}
              placeholder="가맹점 / 분류 검색..."
              className="rounded-xl px-3 py-2 text-sm focus:outline-none w-44"
              style={{
                background: "var(--surface)",
                color: "var(--text-main)",
                border: "1px solid var(--border-soft)",
              }}
            />
            <Button variant="primary" size="sm" onClick={handleSearch}>검색</Button>
          </div>

          {listError && (
            <div className="p-5">
              <ErrorState message={listError} onRetry={() => loadReceipts(filters)} />
            </div>
          )}

          {loadingList ? (
            <LoadingState />
          ) : receipts.length === 0 ? (
            <EmptyState
              message="저장된 영수증이 없습니다."
              description="위에서 영수증을 업로드하고 분석해 보세요."
            />
          ) : (
            <>
              {/* Mobile cards */}
              <div className="md:hidden divide-y" style={{ borderTop: "1px solid var(--border-soft)" }}>
                {receipts.map((r) => (
                  <div key={r.id} className="p-4 space-y-2">
                    <div className="flex items-start justify-between gap-2">
                      <div>
                        <p className="font-medium text-sm" style={{ color: "var(--text-main)" }}>{r.store_name ?? "-"}</p>
                        <p className="text-xs" style={{ color: "var(--text-muted)" }}>{r.receipt_date ?? "-"} · {paymentMethodLabel(r.payment_method)}</p>
                      </div>
                      <div className="flex items-center gap-2 shrink-0">
                        <StatusBadge status={r.evidence_status} />
                        <button onClick={() => setDeleteTarget(r)} className="rounded-lg p-1.5 hover:bg-mist" type="button">
                          <Trash2 className="h-3.5 w-3.5" style={{ color: "var(--danger)" }} />
                        </button>
                      </div>
                    </div>
                    <div className="flex items-center justify-between text-sm">
                      <span style={{ color: "var(--text-muted)" }}>{r.category ?? "-"}</span>
                      <span className="font-medium" style={{ color: "var(--text-main)" }}>
                        {r.amount != null ? `${r.amount.toLocaleString("ko-KR")}원` : "-"}
                      </span>
                    </div>
                    {/* Activity link */}
                    <div className="flex items-center gap-2 flex-wrap">
                      {r.activity_report_id ? (
                        <>
                          <span className="text-xs rounded-full px-2 py-0.5"
                            style={{ background: "var(--success-soft)", color: "var(--success)" }}>
                            {activityTitleMap[r.activity_report_id] ?? "연결된 활동"}
                          </span>
                          <Link href={`/activities/${r.activity_report_id}`}>
                            <button className="text-xs" style={{ color: "var(--primary)" }}>상세 보기</button>
                          </Link>
                          <button className="text-xs" style={{ color: "var(--text-muted)" }}
                            onClick={() => handleUnlink(r)}>
                            연결 해제
                          </button>
                        </>
                      ) : (
                        <button
                          className="text-xs rounded-full px-2 py-0.5"
                          style={{ background: "var(--surface-soft)", color: "var(--primary)", border: "1px solid var(--border-soft)" }}
                          onClick={() => { setLinkTarget(r); setLinkActivityId(""); }}
                        >
                          + 활동에 연결
                        </button>
                      )}
                    </div>
                    {r.reason && <p className="text-xs truncate" style={{ color: "var(--text-muted)" }}>{r.reason}</p>}
                  </div>
                ))}
              </div>

              {/* Desktop table */}
              <div className="hidden md:block overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr style={{ borderBottom: "1px solid var(--border-soft)", background: "var(--surface-soft)" }}>
                      {["날짜", "가맹점", "금액", "결제방식", "분류", "증빙상태", "확인필요", "연결된 활동", "생성일", ""].map((h) => (
                        <th key={h}
                          className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide"
                          style={{ color: "var(--text-muted)" }}>
                          {h}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {receipts.map((r) => (
                      <tr key={r.id}
                        className="transition-colors"
                        style={{ borderBottom: "1px solid var(--border-soft)" }}
                        onMouseEnter={(e) => (e.currentTarget.style.background = "var(--surface-soft)")}
                        onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}>
                        <td className="px-4 py-3 whitespace-nowrap text-xs"
                          style={{ color: "var(--text-muted)" }}>
                          {r.receipt_date ?? "-"}
                        </td>
                        <td className="px-4 py-3 font-medium max-w-[140px] truncate" title={r.store_name ?? ""} style={{ color: "var(--text-main)" }}>
                          {r.store_name ?? "-"}
                        </td>
                        <td className="px-4 py-3 text-right font-medium whitespace-nowrap"
                          style={{ color: "var(--text-main)" }}>
                          {r.amount != null ? `${r.amount.toLocaleString("ko-KR")}원` : "-"}
                        </td>
                        <td className="px-4 py-3 whitespace-nowrap"
                          style={{ color: "var(--text-muted)" }}>
                          {paymentMethodLabel(r.payment_method)}
                        </td>
                        <td className="px-4 py-3" style={{ color: "var(--text-muted)" }}>
                          {r.category ?? "-"}
                        </td>
                        <td className="px-4 py-3">
                          <StatusBadge status={r.evidence_status} />
                        </td>
                        <td className="px-4 py-3 text-center">
                          <span className="text-xs font-medium"
                            style={{ color: r.need_check ? "var(--warning)" : "var(--text-muted)" }}>
                            {r.need_check ? "요" : "—"}
                          </span>
                        </td>
                        {/* Activity link column */}
                        <td className="px-4 py-3">
                          {r.activity_report_id ? (
                            <div className="flex items-center gap-1.5 flex-wrap">
                              <span className="text-xs rounded-full px-2 py-0.5"
                                style={{ background: "var(--success-soft)", color: "var(--success)" }}>
                                {activityTitleMap[r.activity_report_id] ?? "연결됨"}
                              </span>
                              <Link href={`/activities/${r.activity_report_id}`}>
                                <button className="text-xs" style={{ color: "var(--primary)" }}>→ 상세</button>
                              </Link>
                              <button
                                className="text-xs"
                                style={{ color: "var(--text-muted)" }}
                                onClick={() => handleUnlink(r)}
                                title="연결 해제"
                              >
                                ×
                              </button>
                            </div>
                          ) : (
                            <button
                              className="text-xs rounded-full px-2 py-0.5 hover:opacity-80"
                              style={{ background: "var(--surface-soft)", color: "var(--primary)", border: "1px solid var(--border-soft)" }}
                              onClick={() => { setLinkTarget(r); setLinkActivityId(""); setLinkError(null); }}
                            >
                              + 연결
                            </button>
                          )}
                        </td>
                        <td className="px-4 py-3 whitespace-nowrap text-xs"
                          style={{ color: "var(--text-muted)" }}>
                          {r.created_at ? r.created_at.slice(0, 10) : "-"}
                        </td>
                        <td className="px-4 py-3">
                          <button
                            onClick={() => setDeleteTarget(r)}
                            className="rounded-lg p-1.5 transition-colors hover:bg-mist"
                            title="영수증 삭제"
                            type="button"
                          >
                            <Trash2 className="h-3.5 w-3.5" style={{ color: "var(--danger)" }} />
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}
        </Card>

        {/* Delete error */}
        {deleteError && (
          <div className="mt-2">
            <ErrorState message={deleteError} onRetry={() => setDeleteError(null)} />
          </div>
        )}
      </div>

      {/* Delete confirm dialog */}
      <ConfirmDialog
        isOpen={deleteTarget !== null}
        onClose={() => { setDeleteTarget(null); setDeleteError(null); }}
        onConfirm={handleDeleteConfirm}
        title="영수증 삭제"
        message={`이 영수증 분석 결과를 삭제하시겠습니까? 업로드된 원본 파일은 삭제되지 않습니다.`}
        confirmLabel="삭제"
        confirmVariant="danger"
        loading={deleting}
      />

      {/* Activity link modal */}
      {linkTarget && (
        <Modal
          isOpen
          onClose={() => { setLinkTarget(null); setLinkActivityId(""); setLinkError(null); }}
          title="활동에 연결"
        >
          <div className="space-y-4">
            <div className="rounded-xl p-3" style={{ background: "var(--surface-soft)", border: "1px solid var(--border-soft)" }}>
              <p className="text-sm font-medium" style={{ color: "var(--text-main)" }}>
                {linkTarget.store_name ?? "(상호명 없음)"}
              </p>
              <p className="text-xs mt-0.5" style={{ color: "var(--text-muted)" }}>
                {linkTarget.receipt_date ?? "-"} · {linkTarget.amount != null ? `${linkTarget.amount.toLocaleString("ko-KR")}원` : "-"}
              </p>
            </div>
            <div>
              <label className="block text-xs font-medium mb-1.5" style={{ color: "var(--text-muted)" }}>
                연결할 활동 선택
              </label>
              <select
                className="w-full rounded-xl px-3 py-2 text-sm focus:outline-none min-h-[44px]"
                style={inputStyle}
                value={linkActivityId}
                onChange={(e) => setLinkActivityId(e.target.value)}
              >
                <option value="">-- 활동 선택 --</option>
                {activityLinkOptions.map((opt) => (
                  <option key={opt.value} value={opt.value}>{opt.label}</option>
                ))}
              </select>
            </div>
            <p className="text-xs" style={{ color: "var(--text-muted)" }}>
              연결 시 영수증과 원본 파일이 해당 활동의 증빙/파일함에 추가됩니다.
            </p>
            {linkError && <p className="text-sm" style={{ color: "var(--danger)" }}>{linkError}</p>}
            <div className="flex gap-2">
              <Button
                className="flex-1 min-h-[44px]"
                onClick={handleLink}
                loading={linking}
                disabled={!linkActivityId}
              >
                연결
              </Button>
              <Button
                className="flex-1 min-h-[44px]"
                variant="secondary"
                onClick={() => { setLinkTarget(null); setLinkActivityId(""); setLinkError(null); }}
                disabled={linking}
              >
                취소
              </Button>
            </div>
          </div>
        </Modal>
      )}
    </AppShell>
  );
}
