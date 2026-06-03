"use client";

import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";
import Image from "next/image";
import { ChevronDown, ChevronUp, Upload, X } from "lucide-react";
import { nanoid } from "nanoid";

import { AppShell } from "@/components/layout/AppShell";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { ErrorState } from "@/components/ui/ErrorState";
import { AssistantResultCard, type RunStatus } from "@/components/assistant/AssistantResultCard";
import { ApplyConfirmDialog } from "@/components/assistant/ApplyConfirmDialog";
import {
  executeAssistant,
  confirmAssistantAction,
  applyPaymentMatching,
  importTransactions,
  applyFormImport,
  createActivity,
  getActivities,
  type AssistantExecuteResponse,
  type ActivitySummary,
  type ActivityCreate,
  type FormImportRow,
} from "@/lib/api";

// ─── types ────────────────────────────────────────────────────────────────────

type AssistantRun = {
  id: string;
  createdAt: string;
  requestMessage: string;
  response: AssistantExecuteResponse;
  status: RunStatus;
  files: File[];
  period: string;
  paymentType: string;
  requiredAmount: number;
  activityId: string;
  activityMode: string;
};

// ─── constants ────────────────────────────────────────────────────────────────

const EXAMPLE_CHIPS = [
  "이 영수증 활동비로 정리해줘",
  "이 거래내역서에서 회비 납부 확인해줘",
  "이번 달 미납자 확인해줘",
  "이 사진과 메모로 활동 보고서 초안 만들어줘",
  "참여자 기준으로 활동비 10000원 납부 대상 만들어줘",
];

const INTENT_OPTIONS = [
  { value: "auto", label: "자동 감지" },
  { value: "receipt_analysis", label: "영수증 분석" },
  { value: "bank_statement_import", label: "거래내역서 분석" },
  { value: "payment_matching", label: "납부 매칭" },
  { value: "activity_report_generate", label: "활동 보고서 생성" },
  { value: "activity_fee_generate", label: "활동비 납부 대상 생성" },
];

const ACTIVITY_MODE_OPTIONS = [
  { value: "auto", label: "자동 감지" },
  { value: "link_existing", label: "기존 활동 선택" },
  { value: "create_new", label: "새 활동으로 만들기" },
  { value: "none", label: "활동에 연결하지 않음" },
];

const PAYMENT_TYPE_OPTIONS = [
  { value: "membership_fee", label: "회비" },
  { value: "event_fee", label: "행사비" },
  { value: "other", label: "기타" },
];

const inputStyle: React.CSSProperties = {
  background: "var(--surface)",
  color: "var(--text-main)",
  border: "1px solid var(--border-soft)",
  borderRadius: "12px",
  padding: "8px 12px",
  fontSize: "14px",
  width: "100%",
  outline: "none",
};

// ─── page ─────────────────────────────────────────────────────────────────────

export default function AssistantPage() {
  const fileRef = useRef<HTMLInputElement>(null);
  const resultsRef = useRef<HTMLDivElement>(null);

  const [files, setFiles] = useState<File[]>([]);
  const [message, setMessage] = useState("");
  const [intent, setIntent] = useState("auto");
  const [autoApply, setAutoApply] = useState(false);
  const [period, setPeriod] = useState("2026-1");
  const [paymentType, setPaymentType] = useState("membership_fee");
  const [requiredAmount, setRequiredAmount] = useState(0);
  const [showAdvanced, setShowAdvanced] = useState(false);

  // Activity mode state
  const [activityMode, setActivityMode] = useState("auto");
  const [selectedActivityId, setSelectedActivityId] = useState("");
  const [activities, setActivities] = useState<ActivitySummary[]>([]);
  const [loadingActivities, setLoadingActivities] = useState(false);

  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [runs, setRuns] = useState<AssistantRun[]>([]);

  const [confirmRunId, setConfirmRunId] = useState<string | null>(null);
  const [applying, setApplying] = useState(false);

  // Load activities when mode = link_existing
  useEffect(() => {
    if (activityMode === "link_existing" && activities.length === 0) {
      setLoadingActivities(true);
      getActivities({ limit: 100 })
        .then((data) => setActivities(data.filter((a) => a.status !== "archived")))
        .catch(() => {})
        .finally(() => setLoadingActivities(false));
    }
  }, [activityMode, activities.length]);

  useEffect(() => {
    if (runs.length > 0) {
      setTimeout(() => resultsRef.current?.scrollIntoView({ behavior: "smooth", block: "start" }), 120);
    }
  }, [runs.length]);

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    setFiles((prev) => [...prev, ...Array.from(e.target.files ?? [])]);
    e.target.value = "";
  }

  function removeFile(idx: number) {
    setFiles((prev) => prev.filter((_, i) => i !== idx));
  }

  async function executeWithActivity(
    msg: string,
    fs: File[],
    actId: string,
    actMode: string,
    createIfMissing: boolean = false,
  ): Promise<AssistantExecuteResponse> {
    const fd = new FormData();
    if (msg) fd.append("message", msg);
    fd.append("requested_intent", intent);
    fd.append("auto_apply", autoApply ? "true" : "false");
    fd.append("period", period);
    fd.append("payment_type", paymentType);
    fd.append("required_amount", String(requiredAmount));
    fd.append("activity_mode", actMode);
    if (actId) fd.append("activity_id", actId);
    if (createIfMissing) fd.append("create_activity_if_missing", "true");
    for (const f of fs) fd.append("files", f);
    return executeAssistant(fd);
  }

  async function handleRun() {
    if (!message.trim() && files.length === 0) {
      setError("파일을 첨부하거나 요청을 입력해 주세요.");
      return;
    }
    setRunning(true);
    setError(null);

    const actId = activityMode === "link_existing" ? selectedActivityId : "";
    try {
      const res = await executeWithActivity(message, files, actId, activityMode);
      const newRun: AssistantRun = {
        id: nanoid(),
        createdAt: new Date().toISOString(),
        requestMessage: message || files.map((f) => f.name).join(", "),
        response: res,
        status: res.result_type === "error" ? "failed" : res.requires_confirmation ? "preview" : "applied",
        files: [...files],
        period,
        paymentType,
        requiredAmount,
        activityId: actId,
        activityMode,
      };
      setRuns((prev) => [newRun, ...prev]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "요청 처리 중 오류가 발생했습니다.");
    } finally {
      setRunning(false);
    }
  }

  // Handle candidate selection: re-run with selected activity_id
  async function handleSelectCandidate(runId: string, candidateId: string) {
    const run = runs.find((r) => r.id === runId);
    if (!run) return;
    setRunning(true);
    setError(null);
    try {
      const res = await executeWithActivity(
        run.requestMessage,
        run.files,
        candidateId,
        "link_existing",
      );
      const newRun: AssistantRun = {
        id: nanoid(),
        createdAt: new Date().toISOString(),
        requestMessage: run.requestMessage,
        response: res,
        status: res.result_type === "error" ? "failed" : res.requires_confirmation ? "preview" : "applied",
        files: run.files,
        period: run.period,
        paymentType: run.paymentType,
        requiredAmount: run.requiredAmount,
        activityId: candidateId,
        activityMode: "link_existing",
      };
      setRuns((prev) => [newRun, ...prev]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "재실행 중 오류가 발생했습니다.");
    } finally {
      setRunning(false);
    }
  }

  // Handle "새 활동 생성 후 계속" from draft card
  async function handleCreateActivityAndContinue(runId: string, draft: { title: string; activity_date: string | null; location: string | null; description: string | null }) {
    const run = runs.find((r) => r.id === runId);
    if (!run) return;
    setRunning(true);
    setError(null);
    try {
      const payload: ActivityCreate = {
        title: draft.title,
        activity_date: draft.activity_date || null,
        location: draft.location || null,
        description: draft.description || null,
        status: "draft",
      };
      const newActivity = await createActivity(payload);
      // Re-run with new activity_id
      const res = await executeWithActivity(
        run.requestMessage,
        run.files,
        newActivity.id,
        "link_existing",
      );
      const newRun: AssistantRun = {
        id: nanoid(),
        createdAt: new Date().toISOString(),
        requestMessage: run.requestMessage,
        response: res,
        status: res.result_type === "error" ? "failed" : res.requires_confirmation ? "preview" : "applied",
        files: run.files,
        period: run.period,
        paymentType: run.paymentType,
        requiredAmount: run.requiredAmount,
        activityId: newActivity.id,
        activityMode: "link_existing",
      };
      setRuns((prev) => [newRun, ...prev]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "활동 생성 중 오류가 발생했습니다.");
    } finally {
      setRunning(false);
    }
  }

  const handleApplyClick = useCallback((runId: string) => {
    setConfirmRunId(runId);
  }, []);

  const handleConfirmApply = useCallback(async () => {
    const run = runs.find((r) => r.id === confirmRunId);
    if (!run) return;
    setApplying(true);
    try {
      const { response } = run;
      const actionId = response.apply_payload?.action_id as string | undefined;

      if (actionId) {
        // Task 25: use proposal confirm endpoint — no DB change until this call
        const result = await confirmAssistantAction(actionId);
        setRuns((prev) => prev.map((r) =>
          r.id === run.id
            ? { ...r, response: { ...r.response, result: { ...r.response.result, applied_result: result.result, action_status: result.status } }, status: "applied" as RunStatus }
            : r
        ));
      } else {
        // Legacy fallback for intents that don't have action_id yet
        const { files: rf, period: p, paymentType: pt, requiredAmount: ra, activityId, activityMode: am } = run;
        if (response.result_type === "payment_matching_preview") {
          await applyPaymentMatching({ period: p, payment_type: pt, required_amount: ra });
          setRuns((prev) => prev.map((r) => r.id === run.id ? { ...r, status: "applied" as RunStatus } : r));
        } else if (response.result_type === "bank_statement_preview") {
          if (rf[0]) await importTransactions(rf[0]);
          setRuns((prev) => prev.map((r) => r.id === run.id ? { ...r, status: "applied" as RunStatus } : r));
        } else if (response.apply_payload?.intent === "google_form_import") {
          await applyFormImport({
            import_id: (response.apply_payload.import_id as string | undefined) ?? null,
            activity_id: response.apply_payload.activity_id as string,
            form_type: response.apply_payload.form_type as string,
            rows: response.apply_payload.rows as FormImportRow[],
          });
          setRuns((prev) => prev.map((r) => r.id === run.id ? { ...r, status: "applied" as RunStatus } : r));
        } else {
          setRuns((prev) => prev.map((r) => r.id === run.id ? { ...r, status: "failed" as RunStatus } : r));
          setError("확인 후 반영할 수 있는 제안이 없습니다.");
          return;
        }
      }
    } catch (err) {
      setRuns((prev) => prev.map((r) => r.id === run.id ? { ...r, status: "failed" as RunStatus } : r));
      setError(err instanceof Error ? err.message : "반영 중 오류가 발생했습니다.");
    } finally {
      setApplying(false);
      setConfirmRunId(null);
    }
  }, [runs, confirmRunId]);

  const handleCancelRun = useCallback((runId: string) => {
    setRuns((prev) => prev.map((r) => r.id === runId ? { ...r, status: "cancelled" as RunStatus } : r));
  }, []);

  const confirmingRun = runs.find((r) => r.id === confirmRunId);

  return (
    <AppShell>
      <div className="space-y-6" style={{ maxWidth: 800, margin: "0 auto" }}>
        {/* Hero */}
        <div className="flex flex-col items-center text-center py-3 gap-3">
          <div
            className="rounded-full overflow-hidden"
            style={{
              width: 56,
              height: 56,
              border: "1px solid var(--border-soft)",
              background: "var(--surface)",
            }}
          >
            <Image
              src="/brand/oui-parfum.png"
              alt="ClubAgent"
              width={56}
              height={56}
              className="object-cover w-full h-full"
            />
          </div>
          <div>
            <h1 className="text-xl font-semibold" style={{ color: "var(--text-main)" }}>
              ClubAgent Assistant
            </h1>
            <p className="text-sm mt-1 max-w-sm mx-auto" style={{ color: "var(--text-muted)" }}>
              파일을 올리거나 요청을 입력하면 적절한 작업을 실행합니다.
            </p>
          </div>
        </div>

        {/* Input Card */}
        <Card padding="lg">
          {/* 1. File upload */}
          <div
            className="flex flex-col items-center justify-center gap-3 rounded-2xl p-5 text-center cursor-pointer transition-opacity hover:opacity-80"
            style={{ border: "2px dashed var(--border-soft)", background: "var(--surface-soft)" }}
            onClick={() => fileRef.current?.click()}
          >
            <div className="rounded-2xl p-2.5" style={{ background: "var(--primary-soft)" }}>
              <Upload className="h-4 w-4" style={{ color: "var(--primary)" }} />
            </div>
            <div>
              <p className="text-sm font-medium" style={{ color: "var(--text-main)" }}>
                파일 선택 (다중 가능)
              </p>
              <p className="text-xs mt-0.5" style={{ color: "var(--text-muted)" }}>
                영수증 이미지 · 거래내역서 Excel/CSV · 활동 자료 PDF
              </p>
            </div>
          </div>
          <input
            ref={fileRef}
            type="file"
            multiple
            accept="image/*,.xls,.xlsx,.csv,.pdf"
            capture={undefined}
            className="hidden"
            onChange={handleFileChange}
          />

          {files.length > 0 && (
            <div className="mt-3 flex flex-wrap gap-2">
              {files.map((f, i) => (
                <div
                  key={i}
                  className="flex items-center gap-1.5 rounded-lg px-2.5 py-1 text-xs font-medium"
                  style={{ background: "var(--primary-soft)", color: "var(--primary)" }}
                >
                  {f.name}
                  <button onClick={() => removeFile(i)} className="hover:opacity-60 transition-opacity ml-0.5">
                    <X className="h-3 w-3" />
                  </button>
                </div>
              ))}
            </div>
          )}

          {/* 2. Message */}
          <div className="mt-4">
            <textarea
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              placeholder="예: 이 거래내역서 분석해서 2026-1 회비 납부 상태에 반영해줘"
              rows={3}
              className="w-full rounded-xl px-3 py-2 text-sm resize-none focus:outline-none"
              style={{ minHeight: 100, fontSize: 16, background: "var(--surface)", color: "var(--text-main)", border: "1px solid var(--border-soft)" }}
              onFocus={(e) => { e.currentTarget.style.borderColor = "var(--primary)"; e.currentTarget.style.boxShadow = "0 0 0 3px rgba(124,108,242,0.1)"; }}
              onBlur={(e) => { e.currentTarget.style.borderColor = "var(--border-soft)"; e.currentTarget.style.boxShadow = "none"; }}
            />
          </div>

          {/* 3. Example chips */}
          <div className="mt-3 flex flex-wrap gap-1.5">
            {EXAMPLE_CHIPS.map((chip) => (
              <button
                key={chip}
                onClick={() => setMessage(chip)}
                className="rounded-full px-2.5 py-1 text-xs transition-opacity hover:opacity-75"
                style={{ background: "var(--surface-soft)", color: "var(--text-muted)", border: "1px solid var(--border-soft)" }}
              >
                {chip}
              </button>
            ))}
          </div>

          {/* 4. Activity mode selector */}
          <div className="mt-4 rounded-xl p-3"
            style={{ background: "var(--surface-soft)", border: "1px solid var(--border-soft)" }}>
            <label className="block text-xs font-medium mb-2" style={{ color: "var(--text-muted)" }}>
              활동 연결
            </label>
            <div className="flex flex-wrap gap-1.5">
              {ACTIVITY_MODE_OPTIONS.map((opt) => (
                <button
                  key={opt.value}
                  type="button"
                  onClick={() => setActivityMode(opt.value)}
                  className="rounded-lg px-3 py-1.5 text-xs font-medium transition-all min-h-[36px]"
                  style={
                    activityMode === opt.value
                      ? { background: "var(--primary)", color: "#fff" }
                      : { background: "var(--surface)", color: "var(--text-muted)", border: "1px solid var(--border-soft)" }
                  }
                >
                  {opt.label}
                </button>
              ))}
            </div>

            {/* Activity select (when link_existing) */}
            {activityMode === "link_existing" && (
              <div className="mt-3">
                <label className="block text-xs font-medium mb-1.5" style={{ color: "var(--text-muted)" }}>
                  활동 선택
                </label>
                {loadingActivities ? (
                  <p className="text-xs" style={{ color: "var(--text-muted)" }}>활동 목록 로딩 중...</p>
                ) : (
                  <select
                    style={inputStyle}
                    className="min-h-[44px]"
                    value={selectedActivityId}
                    onChange={(e) => setSelectedActivityId(e.target.value)}
                  >
                    <option value="">-- 활동 선택 --</option>
                    {activities.map((a) => (
                      <option key={a.id} value={a.id}>
                        {a.title}{a.activity_date ? ` (${a.activity_date})` : ""}
                      </option>
                    ))}
                  </select>
                )}
                {selectedActivityId && (
                  <Link href={`/activities/${selectedActivityId}`}>
                    <button className="mt-1.5 text-xs hover:opacity-75 transition-opacity"
                      style={{ color: "var(--primary)" }}>
                      활동 상세 보기 →
                    </button>
                  </Link>
                )}
              </div>
            )}
          </div>

          {/* 5. Advanced options (collapsible) */}
          <button
            type="button"
            onClick={() => setShowAdvanced((v) => !v)}
            className="mt-4 flex items-center gap-1.5 text-xs font-medium transition-opacity hover:opacity-75"
            style={{ color: "var(--text-muted)" }}
          >
            {showAdvanced ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
            {showAdvanced ? "상세 옵션 닫기" : "상세 옵션 열기"}
          </button>

          {showAdvanced && (
            <div className="mt-3 rounded-xl p-4 space-y-4"
              style={{ background: "var(--surface-soft)", border: "1px solid var(--border-soft)" }}>
              <div className="grid gap-3 sm:grid-cols-2">
                <div>
                  <label className="block text-xs font-medium mb-1.5" style={{ color: "var(--text-muted)" }}>처리 유형</label>
                  <select style={inputStyle} value={intent} onChange={(e) => setIntent(e.target.value)}>
                    {INTENT_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-medium mb-1.5" style={{ color: "var(--text-muted)" }}>납부 기간</label>
                  <input style={inputStyle} value={period} onChange={(e) => setPeriod(e.target.value)} placeholder="예: 2026-1" />
                </div>
                <div>
                  <label className="block text-xs font-medium mb-1.5" style={{ color: "var(--text-muted)" }}>납부 유형</label>
                  <select style={inputStyle} value={paymentType} onChange={(e) => setPaymentType(e.target.value)}>
                    {PAYMENT_TYPE_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-medium mb-1.5" style={{ color: "var(--text-muted)" }}>기준 금액 (원)</label>
                  <input type="number" style={inputStyle} value={requiredAmount} onChange={(e) => setRequiredAmount(Number(e.target.value))} />
                </div>
              </div>

              {/* Task 25: auto_apply is permanently disabled — all actions require confirmation */}
              <div className="flex items-start gap-2.5 pt-1 rounded-xl px-3 py-2"
                style={{ background: "var(--warning-soft)", border: "1px solid rgba(185,130,43,0.15)" }}>
                <p className="text-xs" style={{ color: "var(--warning)" }}>
                  모든 AI 작업은 확인 후 반영됩니다. 확인 버튼을 누르기 전까지 DB가 변경되지 않습니다.
                </p>
              </div>
            </div>
          )}

          {error && (
            <div className="mt-4">
              <ErrorState message={error} onRetry={() => setError(null)} />
            </div>
          )}

          {/* 6. Run */}
          <div className="mt-5 flex flex-col sm:flex-row gap-3">
            <Button className="w-full sm:w-auto min-h-[44px]" onClick={handleRun} loading={running} disabled={running}>
              {running ? "처리 중..." : "실행"}
            </Button>
            {(files.length > 0 || message) && !running && (
              <Button variant="ghost" className="w-full sm:w-auto min-h-[44px]"
                onClick={() => { setFiles([]); setMessage(""); setError(null); }}>
                초기화
              </Button>
            )}
          </div>
        </Card>

        {/* Results */}
        {runs.length > 0 && (
          <div className="space-y-4" ref={resultsRef}>
            <div className="flex items-center justify-between">
              <h2 className="text-sm font-semibold" style={{ color: "var(--text-muted)" }}>
                실행 결과 ({runs.length}건)
              </h2>
              <button
                onClick={() => setRuns([])}
                className="text-xs hover:opacity-70 transition-opacity"
                style={{ color: "var(--text-muted)" }}
              >
                모두 지우기
              </button>
            </div>
            {runs.map((run) => (
              <AssistantResultCard
                key={run.id}
                response={run.response}
                status={run.status}
                requestMessage={run.requestMessage}
                onApplyClick={run.status === "preview" ? () => handleApplyClick(run.id) : undefined}
                onCancel={run.status === "preview" ? () => handleCancelRun(run.id) : undefined}
                applying={applying && confirmRunId === run.id}
                onSelectCandidate={(candidateId) => handleSelectCandidate(run.id, candidateId)}
                onCreateActivityAndContinue={(draft) => handleCreateActivityAndContinue(run.id, draft)}
              />
            ))}
          </div>
        )}
      </div>

      <ApplyConfirmDialog
        isOpen={confirmRunId !== null}
        intent={confirmingRun?.response.intent ?? ""}
        onConfirm={handleConfirmApply}
        onClose={() => setConfirmRunId(null)}
        loading={applying}
      />
    </AppShell>
  );
}
