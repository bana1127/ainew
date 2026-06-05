"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import React, { useCallback, useEffect, useState } from "react";
import {
  ArrowLeft,
  Calendar,
  CheckCircle2,
  Circle,
  Copy,
  Download,
  MapPin,
  Plus,
  Trash2,
  UserPlus,
  Users,
  X,
} from "lucide-react";

import { AppShell } from "@/components/layout/AppShell";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorState } from "@/components/ui/ErrorState";
import { LoadingState } from "@/components/ui/LoadingState";
import { Modal } from "@/components/ui/Modal";
import { StatusBadge } from "@/components/ui/StatusBadge";
import {
  type ActivityDetail,
  type ActivityParticipantInfo,
  type Member,
  type Receipt,
  type AssistantExecuteResponse,
  type ActivityDraftInfo,
  type ActivityFile,
  type FilePreviewResult,
  type SubmissionPackagePreview,
  type ActivityEvidence,
  addActivityParticipant,
  deleteActivity,
  getActivityDetail,
  getActivityCategoriesTyped,
  getMembersFiltered,
  getReceiptsTyped,
  linkReceiptToActivity,
  removeActivityParticipant,
  updateActivity,
  updateActivityReport,
  generateActivityReportDraft,
  executeAssistant,
  uploadActivityEvidence,
  getActivityEvidence,
  updateReceiptManualData,
  type ActivityReportGenerateRequest,
  type ActivityCategory,
  type FormImportPreview,
  type FormImportRow,
  previewFormImport,
  applyFormImport,
  getActivityFiles,
  uploadActivityFile,
  getFilePreview,
  softDeleteFile,
  patchFileActivity,
  patchFileSubmission,
  getSubmissionPackagePreview,
  generateSubmissionPackage,
  getActivityAuditChecklist,
  type AuditCheckItem,
  type ActivityAuditCheckResult,
  type DocumentTemplate,
  type DocumentPreviewResult,
  type GeneratedDocument,
  getDocumentTemplates,
  uploadDocumentTemplate,
  previewDocument,
  generateDocument,
  getActivityDocuments,
  confirmAssistantAction,
  cancelAssistantAction,
  previewParticipantImport,
  confirmParticipantImport,
  cancelParticipantImport,
} from "@/lib/api";
import { AssistantResultCard } from "@/components/assistant/AssistantResultCard";
import { ActivityFeeTab } from "@/components/activity/ActivityFeeTab";
import { EvidenceDocumentTypeBadge } from "@/components/evidence/EvidenceDocumentTypeBadge";
import { EvidenceDetailEditModal } from "@/components/evidence/EvidenceDetailEditModal";
import { nanoid } from "nanoid";

type TabKey = "ai" | "overview" | "participants" | "report" | "fees" | "receipts" | "files" | "import";

const TABS: { key: TabKey; label: string }[] = [
  { key: "ai", label: "AI 작업" },
  { key: "overview", label: "개요" },
  { key: "participants", label: "참여자" },
  { key: "report", label: "보고서" },
  { key: "fees", label: "활동비" },
  { key: "receipts", label: "증빙" },
  { key: "files", label: "파일함" },
  { key: "import", label: "명단" },
];

function normalizeActivityTab(value: string | null | undefined): TabKey | null {
  if (!value) return null;
  const aliases: Record<string, TabKey> = {
    "activity-fee": "fees",
    activity_fee: "fees",
    fees: "fees",
    evidence: "receipts",
    receipts: "receipts",
    files: "files",
    audit: "ai",
    ai: "ai",
    overview: "overview",
    participants: "participants",
    report: "report",
    import: "import",
  };
  return aliases[value] ?? null;
}

function fmt(n: number): string {
  return n.toLocaleString("ko-KR");
}


function statusLabel(status: string): string {
  const map: Record<string, string> = {
    planned: "예정",
    in_progress: "진행 중",
    done: "완료",
    draft: "초안",
    confirmed: "확정",
    archived: "보관",
    generated: "생성됨",
  };
  return map[status] ?? status;
}

function downloadFile(filename: string, content: string, mime: string) {
  const blob = new Blob([content], { type: mime });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

// ─── Checklist ────────────────────────────────────────────────────────────────

function Checklist({ items }: { items: ActivityDetail["checklist"] }) {
  return (
    <Card padding="md">
      <h3 className="text-sm font-semibold mb-3" style={{ color: "var(--text-main)" }}>
        처리 체크리스트
      </h3>
      <div className="space-y-2">
        {items.map((item) => (
          <div key={item.key} className="flex items-center gap-2">
            {item.done ? (
              <CheckCircle2 className="h-4 w-4 shrink-0" style={{ color: "var(--success)" }} />
            ) : (
              <Circle className="h-4 w-4 shrink-0" style={{ color: "var(--text-muted)" }} />
            )}
            <span
              className="text-sm"
              style={{ color: item.done ? "var(--text-main)" : "var(--text-muted)" }}
            >
              {item.label}
              {item.detail && (
                <span className="ml-1 text-xs" style={{ color: "var(--text-muted)" }}>
                  ({item.detail})
                </span>
              )}
              {item.count !== undefined && item.count > 0 && (
                <span className="ml-1 text-xs" style={{ color: "var(--text-muted)" }}>
                  ({item.count}명)
                </span>
              )}
            </span>
          </div>
        ))}
      </div>
    </Card>
  );
}

// ─── Overview Tab ─────────────────────────────────────────────────────────────

function OverviewTab({
  detail,
  categories,
  onUpdated,
}: {
  detail: ActivityDetail;
  categories: ActivityCategory[];
  onUpdated: () => void;
}) {
  const { activity } = detail;
  const [editing, setEditing] = useState(false);
  const [title, setTitle] = useState(activity.title);
  const [location, setLocation] = useState(activity.location ?? "");
  const [activityDate, setActivityDate] = useState(activity.activity_date ?? "");
  const [categoryId, setCategoryId] = useState(activity.category_id ?? "");
  const [description, setDescription] = useState(activity.input_text ?? "");
  const [activityStatus, setActivityStatus] = useState(activity.status);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  const categoryOptions = [
    { value: "", label: "카테고리 없음" },
    ...categories.map((c) => ({ value: c.id, label: c.name })),
  ];

  async function handleSave() {
    setSaving(true);
    setSaveError(null);
    try {
      await updateActivity(activity.id, {
        title,
        category_id: categoryId || null,
        activity_date: activityDate || null,
        location: location || null,
        description: description || null,
        status: activityStatus,
      });
      setEditing(false);
      onUpdated();
    } catch (err: unknown) {
      setSaveError(err instanceof Error ? err.message : "저장에 실패했습니다.");
    } finally {
      setSaving(false);
    }
  }

  const fields = [
    ["활동일", activity.activity_date ?? "-"],
    ["장소", activity.location ?? "-"],
    ["카테고리", activity.category_name ?? "-"],
    ["상태", statusLabel(activity.status)],
  ];

  if (!editing) {
    return (
      <Card padding="lg">
        <div className="flex items-start justify-between gap-3 mb-4">
          <h2 className="text-base font-semibold" style={{ color: "var(--text-main)" }}>
            {activity.title}
          </h2>
          <Button size="sm" variant="ghost" onClick={() => setEditing(true)}>
            수정
          </Button>
        </div>
        <div className="space-y-2">
          {fields.map(([label, value]) => (
            <div key={label} className="flex items-start gap-3">
              <span
                className="text-xs w-16 shrink-0 pt-0.5"
                style={{ color: "var(--text-muted)" }}
              >
                {label}
              </span>
              <span className="text-sm" style={{ color: "var(--text-main)" }}>
                {value}
              </span>
            </div>
          ))}
          {activity.input_text && (
            <div>
              <p className="text-xs mb-1" style={{ color: "var(--text-muted)" }}>설명</p>
              <p
                className="text-sm rounded-xl p-3 whitespace-pre-wrap"
                style={{
                  background: "var(--surface-soft)",
                  border: "1px solid var(--border-soft)",
                  color: "var(--text-main)",
                }}
              >
                {activity.input_text}
              </p>
            </div>
          )}
        </div>
      </Card>
    );
  }

  return (
    <Card padding="lg">
      <h3 className="text-sm font-semibold mb-4" style={{ color: "var(--text-main)" }}>활동 정보 수정</h3>
      <div className="space-y-3">
        <div>
          <label className="block text-xs font-medium mb-1" style={{ color: "var(--text-muted)" }}>활동명 *</label>
          <input
            className="w-full rounded-xl px-3 py-2 text-sm focus:outline-none min-h-[44px]"
            style={{ background: "var(--surface)", color: "var(--text-main)", border: "1px solid var(--border-soft)" }}
            value={title}
            onChange={(e) => setTitle(e.target.value)}
          />
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="block text-xs font-medium mb-1" style={{ color: "var(--text-muted)" }}>활동일</label>
            <input
              type="date"
              className="w-full rounded-xl px-3 py-2 text-sm focus:outline-none min-h-[44px]"
              style={{ background: "var(--surface)", color: "var(--text-main)", border: "1px solid var(--border-soft)" }}
              value={activityDate}
              onChange={(e) => setActivityDate(e.target.value)}
            />
          </div>
          <div>
            <label className="block text-xs font-medium mb-1" style={{ color: "var(--text-muted)" }}>상태</label>
            <select
              className="w-full rounded-xl px-3 py-2 text-sm focus:outline-none min-h-[44px]"
              style={{ background: "var(--surface)", color: "var(--text-main)", border: "1px solid var(--border-soft)" }}
              value={activityStatus}
              onChange={(e) => setActivityStatus(e.target.value)}
            >
              <option value="planned">예정</option>
              <option value="in_progress">진행 중</option>
              <option value="done">완료</option>
              <option value="draft">초안</option>
              <option value="confirmed">확정</option>
            </select>
          </div>
        </div>
        <div>
          <label className="block text-xs font-medium mb-1" style={{ color: "var(--text-muted)" }}>장소</label>
          <input
            className="w-full rounded-xl px-3 py-2 text-sm focus:outline-none min-h-[44px]"
            style={{ background: "var(--surface)", color: "var(--text-main)", border: "1px solid var(--border-soft)" }}
            value={location}
            onChange={(e) => setLocation(e.target.value)}
            placeholder="활동 장소"
          />
        </div>
        <div>
          <label className="block text-xs font-medium mb-1" style={{ color: "var(--text-muted)" }}>카테고리</label>
          <select
            className="w-full rounded-xl px-3 py-2 text-sm focus:outline-none min-h-[44px]"
            style={{ background: "var(--surface)", color: "var(--text-main)", border: "1px solid var(--border-soft)" }}
            value={categoryId}
            onChange={(e) => setCategoryId(e.target.value)}
          >
            {categoryOptions.map((o) => (
              <option key={o.value} value={o.value}>{o.label}</option>
            ))}
          </select>
        </div>
        <div>
          <label className="block text-xs font-medium mb-1" style={{ color: "var(--text-muted)" }}>설명</label>
          <textarea
            className="w-full rounded-xl px-3 py-2 text-sm focus:outline-none"
            style={{ background: "var(--surface)", color: "var(--text-main)", border: "1px solid var(--border-soft)", minHeight: 72 }}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
          />
        </div>
        {saveError && <p className="text-sm" style={{ color: "var(--danger)" }}>{saveError}</p>}
        <div className="flex gap-2">
          <Button onClick={handleSave} loading={saving}>저장</Button>
          <Button variant="secondary" onClick={() => setEditing(false)} disabled={saving}>취소</Button>
        </div>
      </div>
    </Card>
  );
}

// ─── Participants Tab ─────────────────────────────────────────────────────────

function ParticipantsTab({
  activityId,
  participants,
  onUpdated,
}: {
  activityId: string;
  participants: ActivityParticipantInfo[];
  onUpdated: () => void;
}) {
  const [allMembers, setAllMembers] = useState<Member[]>([]);
  const [showAdd, setShowAdd] = useState(false);
  const [selectedId, setSelectedId] = useState("");
  const [adding, setAdding] = useState(false);
  const [removing, setRemoving] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [memberSearch, setMemberSearch] = useState("");

  useEffect(() => {
    if (showAdd) {
      getMembersFiltered({ status: "active" }).then(setAllMembers).catch(() => {});
    }
  }, [showAdd]);

  const participantMemberIds = new Set(
    participants
      .map((p) => p.member_id)
      .filter((memberId): memberId is string => Boolean(memberId)),
  );
  const availableMembers = allMembers.filter((m) => !participantMemberIds.has(m.id));
  const searchedMembers = memberSearch.trim()
    ? availableMembers.filter((m) => {
        const q = memberSearch.trim().toLowerCase();
        return (
          (m.name ?? "").toLowerCase().includes(q) ||
          (m.student_id ?? "").toLowerCase().includes(q) ||
          (m.department ?? "").toLowerCase().includes(q) ||
          (m.role ?? "").toLowerCase().includes(q)
        );
      })
    : availableMembers;

  async function handleAdd() {
    if (!selectedId) return;
    setAdding(true);
    setActionError(null);
    try {
      await addActivityParticipant(activityId, selectedId);
      setShowAdd(false);
      setSelectedId("");
      onUpdated();
    } catch (err: unknown) {
      setActionError(err instanceof Error ? err.message : "참여자 추가에 실패했습니다.");
    } finally {
      setAdding(false);
    }
  }

  async function handleRemove(memberId: string) {
    setRemoving(memberId);
    setActionError(null);
    try {
      await removeActivityParticipant(activityId, memberId);
      onUpdated();
    } catch (err: unknown) {
      setActionError(err instanceof Error ? err.message : "참여자 제거에 실패했습니다.");
    } finally {
      setRemoving(null);
    }
  }

  return (
    <Card padding="none">
      <div
        className="p-4 flex items-center justify-between"
        style={{ borderBottom: "1px solid var(--border-soft)" }}
      >
        <h3 className="text-sm font-semibold" style={{ color: "var(--text-main)" }}>
          참여자 ({participants.length}명)
        </h3>
        <Button size="sm" variant="secondary" onClick={() => setShowAdd(true)}>
          <UserPlus className="h-3.5 w-3.5" />
          참여자 추가
        </Button>
      </div>

      {actionError && (
        <div className="p-4">
          <ErrorState message={actionError} />
        </div>
      )}

      {participants.length === 0 ? (
        <EmptyState
          message="참여자가 없습니다."
          description="참여자 추가 버튼으로 부원을 등록하세요."
        />
      ) : (
        <>
          {/* Desktop table */}
          <div className="hidden md:block overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr style={{ background: "var(--surface-soft)", borderBottom: "1px solid var(--border-soft)" }}>
                  {["이름", "학번", "학과", "역할", "제거"].map((h) => (
                    <th
                      key={h}
                      className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide"
                      style={{ color: "var(--text-muted)" }}
                    >
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {participants.map((p) => (
                  <tr
                    key={p.id}
                    style={{ borderBottom: "1px solid var(--border-soft)" }}
                    onMouseEnter={(e) => (e.currentTarget.style.background = "var(--surface-soft)")}
                    onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}
                  >
                    <td className="px-4 py-3 font-medium" style={{ color: "var(--text-main)" }}>
                      {p.member_id ? (
                        <Link href={`/members/${p.member_id}`} className="hover:underline">
                          {p.name ?? "-"}
                        </Link>
                      ) : (
                        <span>{p.name ?? "-"}</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-xs" style={{ color: "var(--text-muted)" }}>{p.student_id ?? "-"}</td>
                    <td className="px-4 py-3 text-xs" style={{ color: "var(--text-muted)" }}>{p.department ?? "-"}</td>
                    <td className="px-4 py-3 text-xs" style={{ color: "var(--text-muted)" }}>{p.role ?? "participant"}</td>
                    <td className="px-4 py-3">
                      {p.member_id ? (
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() => handleRemove(p.member_id!)}
                          disabled={removing === p.member_id}
                        >
                          <Trash2 className="h-3.5 w-3.5" />
                        </Button>
                      ) : (
                        <span className="text-xs" style={{ color: "var(--text-muted)" }}>외부</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {/* Mobile cards */}
          <div className="md:hidden divide-y" style={{ borderTop: "1px solid var(--border-soft)" }}>
            {participants.map((p) => (
              <div key={p.id} className="p-4 flex items-center justify-between">
                <div>
                  {p.member_id ? (
                    <Link href={`/members/${p.member_id}`}>
                      <p className="font-medium text-sm hover:underline" style={{ color: "var(--text-main)" }}>
                        {p.name ?? "-"}
                      </p>
                    </Link>
                  ) : (
                    <p className="font-medium text-sm" style={{ color: "var(--text-main)" }}>
                      {p.name ?? "-"}
                    </p>
                  )}
                  <p className="text-xs mt-0.5" style={{ color: "var(--text-muted)" }}>
                    {p.student_id ?? ""} {p.department ? `· ${p.department}` : ""}
                  </p>
                </div>
                {p.member_id ? (
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => handleRemove(p.member_id!)}
                    disabled={removing === p.member_id}
                  >
                    <X className="h-3.5 w-3.5" />
                  </Button>
                ) : (
                  <span className="text-xs" style={{ color: "var(--text-muted)" }}>외부</span>
                )}
              </div>
            ))}
          </div>
        </>
      )}

      {/* Add Participant Modal */}
      {showAdd && (
        <Modal isOpen onClose={() => { setShowAdd(false); setMemberSearch(""); setSelectedId(""); }} title="참여자 추가">
          <div className="space-y-4">
            <div className="rounded-xl px-3 py-2 text-xs" style={{ background: "var(--surface-soft)", color: "var(--text-muted)", border: "1px solid var(--border-soft)" }}>
              전체 부원 {allMembers.length}명 · 현재 참여자 {participantMemberIds.size}명 · 추가 가능 {availableMembers.length}명
            </div>
            {availableMembers.length === 0 ? (
              <p className="text-sm" style={{ color: "var(--text-muted)" }}>
                추가할 수 있는 활동 중인 부원이 없습니다.
              </p>
            ) : (
              <div className="space-y-2">
                <input
                  type="text"
                  placeholder="이름 / 학번 / 학과 / 직위 검색"
                  value={memberSearch}
                  onChange={(e) => { setMemberSearch(e.target.value); setSelectedId(""); }}
                  className="w-full rounded-xl px-3 py-2 text-sm focus:outline-none min-h-[44px]"
                  style={{ background: "var(--surface)", color: "var(--text-main)", border: "1px solid var(--border-soft)" }}
                />
                <label className="block text-xs font-medium" style={{ color: "var(--text-muted)" }}>
                  부원 선택 {memberSearch.trim() ? `(검색 결과 ${searchedMembers.length}명)` : ""}
                </label>
                <select
                  className="w-full rounded-xl px-3 py-2 text-sm focus:outline-none min-h-[44px]"
                  style={{ background: "var(--surface)", color: "var(--text-main)", border: "1px solid var(--border-soft)" }}
                  value={selectedId}
                  onChange={(e) => setSelectedId(e.target.value)}
                  size={Math.min(searchedMembers.length + 1, 8)}
                >
                  <option value="">-- 부원 선택 --</option>
                  {searchedMembers.map((m) => (
                    <option key={m.id} value={m.id}>
                      {m.name} {m.student_id ? `(${m.student_id})` : ""}{m.department ? ` · ${m.department}` : ""}
                    </option>
                  ))}
                </select>
                {memberSearch.trim() && searchedMembers.length === 0 && (
                  <p className="text-xs" style={{ color: "var(--text-muted)" }}>검색 결과가 없습니다.</p>
                )}
              </div>
            )}
            {actionError && <p className="text-sm" style={{ color: "var(--danger)" }}>{actionError}</p>}
            <div className="flex gap-2">
              <Button onClick={handleAdd} loading={adding} disabled={!selectedId}>추가</Button>
              <Button variant="secondary" onClick={() => { setShowAdd(false); setMemberSearch(""); setSelectedId(""); }}>취소</Button>
            </div>
          </div>
        </Modal>
      )}
    </Card>
  );
}

// ─── Report Tab ───────────────────────────────────────────────────────────────

function ReportTab({
  activityId,
  detail,
  onUpdated,
}: {
  activityId: string;
  detail: ActivityDetail;
  onUpdated: () => void;
}) {
  const { activity } = detail;
  const content = activity.final_content ?? activity.generated_content ?? activity.input_text ?? "";
  const [editContent, setEditContent] = useState(content);
  const [editing, setEditing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [saveOk, setSaveOk] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [copied, setCopied] = useState(false);
  const [genError, setGenError] = useState<string | null>(null);
  const [saveError, setSaveError] = useState<string | null>(null);

  async function handleGenerateDraft() {
    if (!activity.category_id) {
      setGenError("카테고리가 설정된 활동에서만 AI 초안을 생성할 수 있습니다.");
      return;
    }
    setGenerating(true);
    setGenError(null);
    try {
      const req: ActivityReportGenerateRequest = {
        activity_report_id: activityId,
        category_id: activity.category_id,
        title: activity.title,
        activity_date: activity.activity_date,
        location: activity.location,
        input_text: activity.input_text,
        participant_ids: detail.participants
          .map((p) => p.member_id)
          .filter((memberId): memberId is string => Boolean(memberId)),
        save_to_db: true,
      };
      await generateActivityReportDraft(req);
      onUpdated();
    } catch (err: unknown) {
      setGenError(err instanceof Error ? err.message : "AI 초안 생성에 실패했습니다.");
    } finally {
      setGenerating(false);
    }
  }

  async function handleSaveContent() {
    setSaving(true);
    setSaveError(null);
    setSaveOk(false);
    try {
      await updateActivityReport(activityId, { final_content: editContent });
      setEditing(false);
      setSaveOk(true);
      setTimeout(() => setSaveOk(false), 3000);
      onUpdated();
    } catch (err: unknown) {
      setSaveError(err instanceof Error ? err.message : "저장에 실패했습니다.");
    } finally {
      setSaving(false);
    }
  }

  async function handleConfirm() {
    setSaving(true);
    try {
      await updateActivityReport(activityId, { status: "confirmed" });
      onUpdated();
    } catch {
      // silently fail
    } finally {
      setSaving(false);
    }
  }

  async function handleCopy() {
    try {
      await navigator.clipboard.writeText(editContent);
      setCopied(true);
      setTimeout(() => setCopied(false), 2500);
    } catch { /* ignore */ }
  }

  function handleMdDownload() {
    const date = activity.activity_date ?? "unknown";
    const slug = activity.title.toLowerCase().replace(/[^a-z0-9가-힣]+/g, "-").slice(0, 40);
    const md = `# ${activity.title}\n\n- 활동일: ${activity.activity_date ?? "-"}\n- 장소: ${activity.location ?? "-"}\n- 카테고리: ${activity.category_name ?? "-"}\n\n## 본문\n\n${editContent}`;
    downloadFile(`activity-report-${date}-${slug}.md`, md, "text/markdown;charset=utf-8");
  }

  function handleTxtDownload() {
    const date = activity.activity_date ?? "unknown";
    const slug = activity.title.toLowerCase().replace(/[^a-z0-9가-힣]+/g, "-").slice(0, 40);
    downloadFile(`activity-report-${date}-${slug}.txt`, editContent, "text/plain;charset=utf-8");
  }

  return (
    <Card padding="lg">
      <div className="flex items-center justify-between mb-4">
        <div>
          <div className="flex items-center gap-2">
            <h3 className="text-sm font-semibold" style={{ color: "var(--text-main)" }}>활동 보고서</h3>
            {saveOk && (
              <span className="text-xs rounded-full px-2 py-0.5"
                style={{ background: "var(--success-soft)", color: "var(--success)" }}>
                저장 완료
              </span>
            )}
          </div>
          <p className="text-xs mt-0.5" style={{ color: "var(--text-muted)" }}>
            상태: {statusLabel(activity.status)}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button size="sm" variant="secondary" onClick={handleGenerateDraft} loading={generating}>
            AI 초안 생성
          </Button>
          {activity.status !== "confirmed" && (
            <Button size="sm" variant="primary" onClick={handleConfirm} loading={saving}>
              보고서 확정
            </Button>
          )}
        </div>
      </div>

      {genError && (
        <div className="mb-4">
          <ErrorState message={genError} />
        </div>
      )}

      {!editing ? (
        <>
          {content ? (
            <pre
              className="whitespace-pre-wrap text-sm leading-relaxed rounded-xl p-4 max-h-[50vh] overflow-y-auto mb-4"
              style={{
                background: "var(--surface-soft)",
                border: "1px solid var(--border-soft)",
                color: "var(--text-main)",
                fontFamily: "inherit",
              }}
            >
              {content}
            </pre>
          ) : (
            <div className="rounded-xl p-4 mb-4 text-center"
              style={{ background: "var(--surface-soft)", border: "1px solid var(--border-soft)" }}>
              <p className="text-sm" style={{ color: "var(--text-muted)" }}>
                보고서 내용이 없습니다. AI 초안 생성 또는 직접 작성하세요.
              </p>
            </div>
          )}
          {copied && (
            <p className="mb-2 text-xs font-medium" style={{ color: "var(--success)" }}>
              클립보드에 복사했습니다.
            </p>
          )}
          <div className="flex flex-wrap gap-2">
            <Button size="sm" variant="secondary" onClick={() => { setEditContent(content); setEditing(true); }}>
              직접 수정
            </Button>
            <Button size="sm" variant="secondary" onClick={handleCopy} disabled={!content}>
              <Copy className="h-3.5 w-3.5" />
              본문 복사
            </Button>
            <Button size="sm" variant="secondary" onClick={handleMdDownload} disabled={!content}>
              <Download className="h-3.5 w-3.5" />
              .md 다운로드
            </Button>
            <Button size="sm" variant="secondary" onClick={handleTxtDownload} disabled={!content}>
              <Download className="h-3.5 w-3.5" />
              .txt 다운로드
            </Button>
          </div>
        </>
      ) : (
        <>
          <textarea
            className="w-full rounded-xl px-3 py-3 text-sm focus:outline-none mb-3"
            style={{
              background: "var(--surface-soft)",
              color: "var(--text-main)",
              border: "1px solid var(--border-soft)",
              minHeight: 240,
              fontFamily: "inherit",
              resize: "vertical",
            }}
            value={editContent}
            onChange={(e) => setEditContent(e.target.value)}
          />
          {saveError && <p className="mb-2 text-sm" style={{ color: "var(--danger)" }}>{saveError}</p>}
          <div className="flex gap-2">
            <Button onClick={handleSaveContent} loading={saving}>저장</Button>
            <Button variant="secondary" onClick={() => setEditing(false)} disabled={saving}>취소</Button>
          </div>
        </>
      )}

      {/* Document generation section */}
      <DocumentGenerationSection
        activityId={activityId}
        reportContent={content}
        onUpdated={onUpdated}
      />
    </Card>
  );
}

// ─── Document Generation Section (Task 20) ───────────────────────────────────

const TEMPLATE_TYPE_LABEL: Record<string, string> = {
  activity_report: "활동 내역서",
  activity_plan: "활동 기획서",
  meeting_report: "회의록",
  mentoring_report: "멘토링 보고서",
  project_report: "프로젝트 보고서",
  exchange_activity: "교류 활동",
  other: "기타",
};

function DocumentGenerationSection({
  activityId,
  reportContent,
  onUpdated,
}: {
  activityId: string;
  reportContent: string;
  onUpdated: () => void;
}) {
  const tplFileRef = React.useRef<HTMLInputElement>(null);
  const [templates, setTemplates] = React.useState<DocumentTemplate[]>([]);
  const [loadingTemplates, setLoadingTemplates] = React.useState(false);
  const [selectedTemplateId, setSelectedTemplateId] = React.useState("");
  const [preview, setPreview] = React.useState<DocumentPreviewResult | null>(null);
  const [previewing, setPreviewing] = React.useState(false);
  const [generating, setGenerating] = React.useState(false);
  const [genResult, setGenResult] = React.useState<{ download_url: string; file_id: string; missing: string[]; mode?: string; replaced_count?: number; participant_count?: number; warnings?: string[] } | null>(null);
  const [genError, setGenError] = React.useState<string | null>(null);
  const [docTitle, setDocTitle] = React.useState("");
  const [bodyText, setBodyText] = React.useState(reportContent);
  const [markSubmission, setMarkSubmission] = React.useState(false);
  const [submissionMonth, setSubmissionMonth] = React.useState("");
  const [docs, setDocs] = React.useState<GeneratedDocument[]>([]);
  const [loadingDocs, setLoadingDocs] = React.useState(false);

  // Template upload state
  const [showTplUpload, setShowTplUpload] = React.useState(false);
  const [tplFile, setTplFile] = React.useState<File | null>(null);
  const [tplName, setTplName] = React.useState("");
  const [tplType, setTplType] = React.useState("activity_report");
  const [uploadingTpl, setUploadingTpl] = React.useState(false);
  const [tplError, setTplError] = React.useState<string | null>(null);

  React.useEffect(() => {
    setBodyText(reportContent);
  }, [reportContent]);

  React.useEffect(() => {
    loadTemplates();
    loadDocs();
  }, [activityId]);

  async function loadTemplates() {
    setLoadingTemplates(true);
    try {
      const data = await getDocumentTemplates();
      setTemplates(data);
    } catch { /* ignore */ }
    setLoadingTemplates(false);
  }

  async function loadDocs() {
    setLoadingDocs(true);
    try {
      const data = await getActivityDocuments(activityId);
      setDocs(data);
    } catch { /* ignore */ }
    setLoadingDocs(false);
  }

  async function handlePreview() {
    if (!selectedTemplateId) return;
    setPreviewing(true);
    setGenError(null);
    try {
      const result = await previewDocument(activityId, {
        template_id: selectedTemplateId,
        overrides: { 활동내용: bodyText, content: bodyText },
      });
      setPreview(result);
    } catch (e: unknown) {
      setGenError(e instanceof Error ? e.message : "미리보기 실패");
    } finally {
      setPreviewing(false);
    }
  }

  async function handleGenerate() {
    if (!selectedTemplateId) return;
    setGenerating(true);
    setGenError(null);
    setGenResult(null);
    try {
      const result = await generateDocument(activityId, {
        template_id: selectedTemplateId,
        document_title: docTitle || undefined,
        overrides: { 활동내용: bodyText, content: bodyText },
        mark_as_submission: markSubmission,
        submission_month: submissionMonth || undefined,
      });
      setGenResult({ download_url: result.download_url, file_id: result.file_id ?? result.generated_file_id, missing: result.missing_fields, mode: result.mode, replaced_count: result.replaced_count, participant_count: result.participant_count, warnings: result.warnings });
      loadDocs();
      onUpdated();
    } catch (e: unknown) {
      setGenError(e instanceof Error ? e.message : "문서 생성 실패");
    } finally {
      setGenerating(false);
    }
  }

  async function handleUploadTemplate() {
    if (!tplFile) return;
    setUploadingTpl(true);
    setTplError(null);
    try {
      const t = await uploadDocumentTemplate(tplFile, { name: tplName || tplFile.name, template_type: tplType });
      setTemplates((prev) => [t, ...prev]);
      setSelectedTemplateId(t.id);
      setShowTplUpload(false);
      setTplFile(null);
      setTplName("");
    } catch (e: unknown) {
      setTplError(e instanceof Error ? e.message : "업로드 실패");
    } finally {
      setUploadingTpl(false);
    }
  }

  const inputSt: React.CSSProperties = {
    background: "var(--surface)", color: "var(--text-main)",
    border: "1px solid var(--border-soft)", borderRadius: 12,
    padding: "8px 12px", fontSize: 14, width: "100%",
  };

  const selectedTemplate = templates.find((t) => t.id === selectedTemplateId);

  return (
    <div className="mt-6 space-y-4">
      <div style={{ borderTop: "1px solid var(--border-soft)", paddingTop: 16 }}>
        <div className="flex items-center justify-between mb-4">
          <h4 className="text-sm font-semibold" style={{ color: "var(--text-main)" }}>제출 문서 생성 (HWPX)</h4>
          <Button size="sm" variant="ghost" onClick={() => setShowTplUpload(!showTplUpload)}>
            템플릿 업로드
          </Button>
        </div>

        {/* Template upload */}
        {showTplUpload && (
          <div className="rounded-xl p-4 mb-4 space-y-3" style={{ background: "var(--surface-soft)", border: "1px solid var(--border-soft)" }}>
            <p className="text-xs font-medium" style={{ color: "var(--text-main)" }}>HWPX 템플릿 업로드</p>
            <input type="file" accept=".hwpx,.hwp" style={inputSt}
              onChange={(e) => setTplFile(e.target.files?.[0] ?? null)} />
            <input type="text" placeholder="템플릿 이름" value={tplName}
              onChange={(e) => setTplName(e.target.value)} style={inputSt} />
            <select value={tplType} onChange={(e) => setTplType(e.target.value)} style={inputSt}>
              {Object.entries(TEMPLATE_TYPE_LABEL).map(([k, v]) => (
                <option key={k} value={k}>{v}</option>
              ))}
            </select>
            {tplError && <p className="text-xs" style={{ color: "var(--danger)" }}>{tplError}</p>}
            <div className="flex gap-2">
              <Button size="sm" onClick={handleUploadTemplate} loading={uploadingTpl} disabled={!tplFile}>업로드</Button>
              <Button size="sm" variant="secondary" onClick={() => setShowTplUpload(false)}>취소</Button>
            </div>
            <p className="text-xs" style={{ color: "var(--text-muted)" }}>
              placeholder 규칙: {"{{활동명}}"} {"{{활동일}}"} {"{{참여자명단}}"} {"{{활동내용}}"} 등
            </p>
          </div>
        )}

        {/* Template select */}
        <div className="space-y-3">
          <div>
            <label className="text-xs mb-1 block" style={{ color: "var(--text-muted)" }}>HWPX 템플릿 선택</label>
            {loadingTemplates ? (
              <p className="text-xs" style={{ color: "var(--text-muted)" }}>불러오는 중...</p>
            ) : templates.length === 0 ? (
              <p className="text-xs" style={{ color: "var(--text-muted)" }}>템플릿을 먼저 업로드해 주세요.</p>
            ) : (
              <select value={selectedTemplateId} onChange={(e) => { setSelectedTemplateId(e.target.value); setPreview(null); setGenResult(null); }} style={inputSt}>
                <option value="">-- 템플릿 선택 --</option>
                {templates.map((t) => (
                  <option key={t.id} value={t.id}>
                    {t.name} ({TEMPLATE_TYPE_LABEL[t.template_type] ?? t.template_type})
                  </option>
                ))}
              </select>
            )}
          </div>

          {/* Placeholder fields display */}
          {selectedTemplate && selectedTemplate.placeholder_fields.length > 0 && (
            <div className="rounded-xl p-3" style={{ background: "var(--surface-soft)", border: "1px solid var(--border-soft)" }}>
              <p className="text-xs font-medium mb-1.5" style={{ color: "var(--text-muted)" }}>템플릿 필드</p>
              <div className="flex flex-wrap gap-1.5">
                {selectedTemplate.placeholder_fields.map((f) => (
                  <span key={f} className="text-xs px-2 py-0.5 rounded-full"
                    style={{ background: "var(--primary-soft)", color: "var(--primary)" }}>
                    {"{{"}{f}{"}}"}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Report body */}
          <div>
            <label className="text-xs mb-1 block" style={{ color: "var(--text-muted)" }}>보고서 본문 ({"{{활동내용}}"} 치환용)</label>
            <textarea
              value={bodyText}
              onChange={(e) => setBodyText(e.target.value)}
              rows={5}
              style={{ ...inputSt, resize: "vertical", minHeight: 100, fontFamily: "inherit" }}
              placeholder="AI 초안 또는 직접 작성한 보고서 본문..."
            />
          </div>

          <div>
            <label className="text-xs mb-1 block" style={{ color: "var(--text-muted)" }}>생성 문서 제목</label>
            <input type="text" value={docTitle} onChange={(e) => setDocTitle(e.target.value)}
              placeholder="예: Oui Parfum_20260530_정기스터디" style={inputSt} />
          </div>

          <div className="flex flex-wrap items-center gap-4">
            <label className="flex items-center gap-2 text-sm cursor-pointer" style={{ color: "var(--text-main)" }}>
              <input type="checkbox" checked={markSubmission} onChange={(e) => setMarkSubmission(e.target.checked)} />
              제출용 파일로 지정
            </label>
            {markSubmission && (
              <div className="flex items-center gap-2">
                <label className="text-xs" style={{ color: "var(--text-muted)" }}>제출 월</label>
                <input type="month" value={submissionMonth} onChange={(e) => setSubmissionMonth(e.target.value)}
                  style={{ ...inputSt, width: "auto" }} />
              </div>
            )}
          </div>

          <div className="flex flex-wrap gap-2">
            <Button size="sm" variant="secondary" onClick={handlePreview}
              disabled={!selectedTemplateId || previewing} loading={previewing}>
              매핑 미리보기
            </Button>
            <Button size="sm" onClick={handleGenerate}
              disabled={!selectedTemplateId || generating} loading={generating}>
              HWPX 생성
            </Button>
          </div>

          {genError && <p className="text-sm" style={{ color: "var(--danger)" }}>{genError}</p>}

          {/* Preview result */}
          {preview && (
            <div className="rounded-xl p-4 space-y-2" style={{ background: "var(--surface-soft)", border: "1px solid var(--border-soft)" }}>
              <div className="flex items-center gap-2">
                <p className="text-xs font-semibold" style={{ color: "var(--text-main)" }}>매핑 미리보기</p>
                {preview.mode && (
                  <span className="text-xs px-2 py-0.5 rounded-full" style={{ background: "var(--primary-soft)", color: "var(--primary)" }}>
                    {preview.mode === "legacy_form" ? "레거시 폼" : preview.mode === "placeholder" ? "플레이스홀더" : "혼합"}
                  </span>
                )}
              </div>
              {/* Warnings */}
              {(preview.warnings ?? []).map((w, i) => (
                <p key={i} className="text-xs" style={{ color: "var(--warning)" }}>⚠ {w}</p>
              ))}
              {/* Mappings list */}
              <div className="max-h-48 overflow-y-auto space-y-1">
                {(preview.mappings ?? []).map((m, i) => (
                  <div key={i} className="flex items-center gap-2 text-xs">
                    <span className="shrink-0 font-medium max-w-[110px] truncate" style={{ color: "var(--text-muted)" }}>{m.source}</span>
                    <span className="text-xs" style={{ color: "var(--text-muted)" }}>→</span>
                    <span className="truncate" style={{ color: "var(--text-main)" }}>{m.target || "(빈 값)"}</span>
                  </div>
                ))}
                {/* Fallback for old API: show mapped_fields if no mappings */}
                {!(preview.mappings ?? []).length && Object.entries(preview.mapped_fields ?? {}).map(([k, v]) => (
                  <div key={k} className="flex gap-2 text-xs">
                    <span className="shrink-0 font-medium" style={{ color: "var(--text-muted)" }}>{"{{"}{k}{"}}"}</span>
                    <span className="truncate" style={{ color: "var(--text-main)" }}>{v || "(빈 값)"}</span>
                  </div>
                ))}
              </div>
              {(preview.missing_fields ?? []).length > 0 && (
                <p className="text-xs" style={{ color: "var(--warning)" }}>
                  누락 필드: {preview.missing_fields.join(", ")}
                </p>
              )}
            </div>
          )}

          {/* Generate result */}
          {genResult && (
            <div className="rounded-xl p-4" style={{ background: "var(--success-soft)", border: "1px solid var(--border-soft)" }}>
              <p className="text-sm font-medium mb-1" style={{ color: "var(--success)" }}>HWPX 문서 생성 완료</p>
              <div className="flex flex-wrap gap-x-4 gap-y-0.5 mb-2">
                {genResult.replaced_count != null && (
                  <p className="text-xs" style={{ color: "var(--success)" }}>치환 필드: {genResult.replaced_count}개</p>
                )}
                {genResult.participant_count != null && (
                  <p className="text-xs" style={{ color: "var(--success)" }}>참여자: {genResult.participant_count}명</p>
                )}
                {genResult.mode && (
                  <p className="text-xs" style={{ color: "var(--success)" }}>모드: {genResult.mode}</p>
                )}
              </div>
              {(genResult.warnings ?? []).map((w, i) => (
                <p key={i} className="text-xs mb-1" style={{ color: "var(--warning)" }}>⚠ {w}</p>
              ))}
              {(genResult.missing ?? []).length > 0 && (
                <p className="text-xs mb-2" style={{ color: "var(--warning)" }}>
                  누락 필드: {genResult.missing.join(", ")}
                </p>
              )}
              <div className="flex flex-wrap gap-2 mt-2">
                <a href={genResult.download_url} download>
                  <Button size="sm">
                    <Download className="h-3.5 w-3.5" />
                    HWPX 다운로드
                  </Button>
                </a>
                <Button size="sm" variant="secondary" onClick={() => {
                  window.history.pushState({}, "", window.location.pathname + "?tab=files");
                  window.dispatchEvent(new CustomEvent("switch-tab", { detail: "files" }));
                }}>
                  파일함에서 보기
                </Button>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Generated documents list */}
      {docs.length > 0 && (
        <div>
          <p className="text-xs font-semibold mb-2" style={{ color: "var(--text-muted)" }}>생성된 문서 목록</p>
          <div className="space-y-2">
            {docs.map((d) => (
              <div key={d.id} className="flex items-center justify-between rounded-xl px-3 py-2"
                style={{ background: "var(--surface-soft)", border: "1px solid var(--border-soft)" }}>
                <div>
                  <p className="text-xs font-medium" style={{ color: "var(--text-main)" }}>{d.document_title || d.title}</p>
                  <p className="text-xs" style={{ color: "var(--text-muted)" }}>
                    {d.template_name}{d.submission_month ? ` · ${d.submission_month}` : ""}
                    {d.is_submission_file && " · 제출용"}
                    {d.created_at ? ` · ${new Date(d.created_at).toLocaleDateString("ko-KR")}` : ""}
                  </p>
                </div>
                <a href={d.download_url} download>
                  <Button size="sm" variant="ghost">
                    <Download className="h-3.5 w-3.5" />
                  </Button>
                </a>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}


// ─── Receipts Tab ─────────────────────────────────────────────────────────────

const DOCUMENT_TYPE_OPTIONS_UPLOAD = [
  { value: "unknown", label: "자동 감지" },
  { value: "receipt", label: "영수증" },
  { value: "business_registration", label: "사업자등록증" },
  { value: "bankbook_copy", label: "통장 사본" },
  { value: "transfer_confirmation", label: "계좌이체 확인서" },
  { value: "invoice", label: "청구서" },
  { value: "quote", label: "견적서" },
  { value: "transaction_statement", label: "거래명세서" },
  { value: "other", label: "기타 증빙" },
];

function ReceiptsTab({
  activityId,
  receipts,
  onUpdated,
}: {
  activityId: string;
  receipts: ActivityDetail["receipts"];
  onUpdated: () => void;
}) {
  const receiptFileRef = React.useRef<HTMLInputElement>(null);
  const [allReceipts, setAllReceipts] = useState<Receipt[]>([]);
  const [evidenceList, setEvidenceList] = useState<ActivityEvidence[]>([]);
  const [showLink, setShowLink] = useState(false);
  const [linking, setLinking] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [previewReceiptId, setPreviewReceiptId] = useState<string | null>(null);
  const [selectedDocType, setSelectedDocType] = useState("unknown");
  const [editTarget, setEditTarget] = useState<ActivityEvidence | null>(null);

  async function loadEvidence() {
    try {
      const data = await getActivityEvidence(activityId);
      setEvidenceList(data);
    } catch { /* ignore */ }
  }

  async function loadAll() {
    try {
      const data = await getReceiptsTyped({ limit: 100 });
      setAllReceipts(data);
    } catch { /* ignore */ }
  }

  useEffect(() => {
    loadEvidence();
  }, [activityId, receipts]);

  useEffect(() => {
    if (showLink) loadAll();
  }, [showLink]);

  const linkedIds = new Set(receipts.map((r) => r.id));
  const unlinkable = allReceipts.filter(
    (r) => r.activity_report_id !== activityId && !linkedIds.has(r.id),
  );

  async function handleLink(receiptId: string) {
    setLinking(receiptId);
    setActionError(null);
    try {
      await linkReceiptToActivity(receiptId, activityId);
      setShowLink(false);
      onUpdated();
      await loadEvidence();
    } catch (err: unknown) {
      setActionError(err instanceof Error ? err.message : "연결에 실패했습니다.");
    } finally {
      setLinking(null);
    }
  }

  async function handleUnlink(receiptId: string) {
    setLinking(receiptId);
    setActionError(null);
    try {
      await linkReceiptToActivity(receiptId, null);
      onUpdated();
      await loadEvidence();
    } catch (err: unknown) {
      setActionError(err instanceof Error ? err.message : "연결 해제에 실패했습니다.");
    } finally {
      setLinking(null);
    }
  }

  // ★ Fixed: use direct evidence upload API instead of AI assistant
  async function handleReceiptUpload() {
    if (!uploadFile) return;
    setUploading(true);
    setUploadError(null);
    try {
      await uploadActivityEvidence(activityId, uploadFile, {
        document_type: selectedDocType,
        save_to_db: true,
      });
      setUploadFile(null);
      setSelectedDocType("unknown");
      if (receiptFileRef.current) receiptFileRef.current.value = "";
      onUpdated();
      await loadEvidence();
    } catch (err: unknown) {
      setUploadError(err instanceof Error ? err.message : "증빙 업로드 실패");
    } finally {
      setUploading(false);
    }
  }

  async function handleSaveEdit(receiptId: string, manualData: Record<string, unknown>, docType: string) {
    await updateReceiptManualData(receiptId, {
      manual_data: manualData,
      document_type: docType,
      title: String(manualData.title || manualData.business_name || manualData.account_holder || ""),
      amount: manualData.amount ? Number(manualData.amount) : undefined,
      receipt_date: String(manualData.receipt_date || manualData.transfer_date || manualData.opening_date || ""),
    });
    setEditTarget(null);
    await loadEvidence();
    onUpdated();
  }

  // Show evidence list (from direct API call) if available, otherwise fall back to receipts prop
  const displayEvidence = evidenceList.length > 0 ? evidenceList : receipts.map((r) => ({
    ...r,
    document_type: (r as unknown as Record<string, unknown>).document_type as string || "unknown",
    title: r.store_name,
    display_data: {},
    transaction_id: null,
    parsed_data: null,
    manual_data: null,
  })) as unknown as ActivityEvidence[];

  return (
    <Card padding="none">
      <div
        className="p-4 flex items-center justify-between"
        style={{ borderBottom: "1px solid var(--border-soft)" }}
      >
        <h3 className="text-sm font-semibold" style={{ color: "var(--text-main)" }}>
          증빙 ({displayEvidence.length}건)
        </h3>
        <div className="flex gap-2">
          <Button size="sm" variant="secondary" onClick={() => setShowLink(true)}>
            <Plus className="h-3.5 w-3.5" />
            기존 증빙 연결
          </Button>
          <Button size="sm" variant="ghost" onClick={() => receiptFileRef.current?.click()}>
            증빙 파일 업로드
          </Button>
          <input
            ref={receiptFileRef}
            type="file"
            accept="image/*,.pdf"
            className="hidden"
            onChange={(e) => setUploadFile(e.target.files?.[0] ?? null)}
          />
        </div>
      </div>

      {/* Upload panel */}
      {uploadFile && (
        <div className="p-3 space-y-2" style={{ borderBottom: "1px solid var(--border-soft)", background: "var(--surface-soft)" }}>
          <div className="flex items-center gap-2">
            <span className="text-xs flex-1 truncate" style={{ color: "var(--text-main)" }}>{uploadFile.name}</span>
          </div>
          <div className="flex items-center gap-2 flex-wrap">
            <select
              value={selectedDocType}
              onChange={(e) => setSelectedDocType(e.target.value)}
              style={{
                padding: "5px 8px", borderRadius: 8, fontSize: 12,
                border: "1px solid var(--border-soft)", background: "var(--surface)", color: "var(--text-main)",
                maxWidth: 180,
              }}
            >
              {DOCUMENT_TYPE_OPTIONS_UPLOAD.map((o) => (
                <option key={o.value} value={o.value}>{o.label}</option>
              ))}
            </select>
            <Button size="sm" onClick={handleReceiptUpload} disabled={uploading}>
              {uploading ? "분석 중..." : "분석 후 저장"}
            </Button>
            <Button size="sm" variant="ghost" onClick={() => { setUploadFile(null); setUploadError(null); }}>취소</Button>
          </div>
          {uploading && <p className="text-xs" style={{ color: "var(--text-muted)" }}>업로드 및 분석 중입니다...</p>}
        </div>
      )}
      {uploadError && (
        <p className="px-4 py-2 text-xs" style={{ color: "var(--danger)" }}>{uploadError}</p>
      )}

      {actionError && (
        <div className="p-4"><ErrorState message={actionError} /></div>
      )}

      {/* 증빙 요약 */}
      {displayEvidence.length > 0 && (
        <div className="px-4 py-3 grid grid-cols-2 sm:grid-cols-4 gap-2" style={{ borderBottom: "1px solid var(--border-soft)" }}>
          {[
            { label: "전체", value: displayEvidence.length, color: "var(--text-main)" },
            { label: "분석 완료", value: displayEvidence.filter(r => r.evidence_status !== "pending").length, color: "var(--success)" },
            { label: "분석 대기", value: displayEvidence.filter(r => r.evidence_status === "pending").length, color: "var(--warning)" },
            { label: "확인 필요", value: displayEvidence.filter(r => r.need_check).length, color: "var(--danger)" },
          ].map(({ label, value, color }) => (
            <div key={label} className="rounded-xl p-2.5 text-center" style={{ background: "var(--surface-soft)", border: "1px solid var(--border-soft)" }}>
              <p className="text-xs" style={{ color: "var(--text-muted)" }}>{label}</p>
              <p className="text-sm font-semibold mt-0.5" style={{ color }}>{value}</p>
            </div>
          ))}
        </div>
      )}

      {displayEvidence.length === 0 ? (
        <EmptyState
          message="연결된 증빙이 없습니다."
          description="증빙 파일을 업로드하거나 기존 증빙을 연결하세요."
        />
      ) : (
        <div className="divide-y" style={{ borderTop: "1px solid var(--border-soft)" }}>
          {displayEvidence.map((r) => {
            const displayTitle = (r.manual_data as Record<string, unknown> | null)?.title
              || (r.manual_data as Record<string, unknown> | null)?.business_name
              || r.title || r.store_name || "(제목 없음)";
            return (
              <div key={r.id} className="p-4">
                <div className="flex items-center justify-between gap-3">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap mb-1">
                      <EvidenceDocumentTypeBadge documentType={r.document_type || "unknown"} size="xs" />
                      <p className="font-medium text-sm" style={{ color: "var(--text-main)" }}>
                        {String(displayTitle)}
                        {r.amount > 0 && (
                          <span className="ml-2 text-xs" style={{ color: "var(--text-muted)" }}>
                            {fmt(r.amount)}원
                          </span>
                        )}
                      </p>
                    </div>
                    <div className="flex flex-wrap items-center gap-2">
                      {r.receipt_date && (
                        <span className="text-xs" style={{ color: "var(--text-muted)" }}>{r.receipt_date}</span>
                      )}
                      <StatusBadge status={r.evidence_status} />
                      {r.need_check && (
                        <span className="text-xs rounded-full px-2 py-0.5"
                          style={{ background: "var(--warning-soft)", color: "var(--warning)" }}>
                          확인 필요
                        </span>
                      )}
                      {r.manual_data && (
                        <span className="text-xs" style={{ color: "var(--primary)", fontWeight: 500 }}>수정됨</span>
                      )}
                      {r.file_id && (
                        <button
                          className="text-xs"
                          style={{ color: "var(--primary)" }}
                          onClick={() => setPreviewReceiptId(previewReceiptId === r.id ? null : r.id)}
                        >
                          {previewReceiptId === r.id ? "이미지 닫기" : "이미지 보기"}
                        </button>
                      )}
                    </div>
                  </div>
                  <div className="flex gap-1 items-center flex-wrap justify-end">
                    <Button size="sm" variant="ghost" style={{ fontSize: 11 }}
                      onClick={() => setEditTarget(r)}>
                      수정
                    </Button>
                    {r.file_id && (
                      <a href={`/api/files/${r.file_id}/download`} download>
                        <Button size="sm" variant="ghost">
                          <Download className="h-3.5 w-3.5" />
                        </Button>
                      </a>
                    )}
                    <Button
                      size="sm"
                      variant="ghost"
                      style={{ fontSize: 11 }}
                      onClick={() => handleUnlink(r.id)}
                      disabled={linking === r.id}
                    >
                      연결 해제
                    </Button>
                  </div>
                </div>
                {r.file_id && previewReceiptId === r.id && (
                  <div className="mt-3">
                    <img
                      src={`/api/files/${r.file_id}/preview/inline`}
                      alt={String(displayTitle)}
                      className="max-w-full rounded-xl"
                      style={{ maxHeight: 320, border: "1px solid var(--border-soft)" }}
                      onError={(e) => {
                        (e.currentTarget as HTMLImageElement).style.display = "none";
                      }}
                    />
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* Link evidence modal */}
      {showLink && (
        <Modal isOpen onClose={() => setShowLink(false)} title="기존 증빙 연결">
          <div className="space-y-3">
            {unlinkable.length === 0 ? (
              <p className="text-sm" style={{ color: "var(--text-muted)" }}>
                연결할 수 있는 증빙이 없습니다. 먼저 증빙을 업로드하세요.
              </p>
            ) : (
              <div className="max-h-64 overflow-y-auto space-y-2">
                {unlinkable.map((r) => (
                  <div
                    key={r.id}
                    className="flex items-center justify-between rounded-xl p-3"
                    style={{ border: "1px solid var(--border-soft)", background: "var(--surface-soft)" }}
                  >
                    <div>
                      <p className="text-sm font-medium" style={{ color: "var(--text-main)" }}>
                        {r.store_name ?? "(상호명 없음)"}
                      </p>
                      <p className="text-xs" style={{ color: "var(--text-muted)" }}>
                        {r.receipt_date ?? ""} · {r.amount > 0 ? `${fmt(r.amount)}원` : "금액 없음"}
                      </p>
                    </div>
                    <Button
                      size="sm"
                      onClick={() => handleLink(r.id)}
                      loading={linking === r.id}
                    >
                      연결
                    </Button>
                  </div>
                ))}
              </div>
            )}
            {actionError && (
              <p className="text-sm" style={{ color: "var(--danger)" }}>{actionError}</p>
            )}
            <Button variant="secondary" onClick={() => setShowLink(false)}>닫기</Button>
          </div>
        </Modal>
      )}

      {/* Evidence edit modal */}
      {editTarget && (
        <EvidenceDetailEditModal
          receipt={editTarget}
          onClose={() => setEditTarget(null)}
          onSaved={handleSaveEdit}
        />
      )}
    </Card>
  );
}

// ─── File Vault Tab (Task 19) ─────────────────────────────────────────────────

const FILE_CATEGORY_LABEL: Record<string, string> = {
  activity_report: "활동 내역서",
  activity_plan: "활동 기획서",
  receipt: "영수증/증빙",
  photo: "사진",
  google_form_application: "신청서(Google Form)",
  google_form_feedback: "피드백(Google Form)",
  bank_statement: "거래내역서",
  attachment: "첨부파일",
  submission_package: "제출 패키지",
  other: "기타",
};

const FILE_ROLE_LABEL: Record<string, string> = {
  source: "원본",
  evidence: "증빙",
  report: "보고",
  plan: "기획",
  attachment: "첨부",
  submission: "제출",
  generated: "생성됨",
};

// ─── File Group definitions ───────────────────────────────────────────────────

const FILE_GROUPS: Array<{ label: string; categories: string[]; roles: string[] }> = [
  { label: "원본 파일", categories: ["bank_statement", "activity_plan", "google_form_application", "google_form_feedback"], roles: ["source"] },
  { label: "증빙 파일", categories: ["receipt", "photo"], roles: ["evidence"] },
  { label: "생성 문서", categories: ["activity_report", "submission_package"], roles: ["generated"] },
  { label: "기타 파일", categories: ["attachment", "other"], roles: ["attachment", "submission", "report", "plan"] },
];

function _fileGroup(file: ActivityFile): string {
  const cat = file.file_category ?? "";
  const role = file.file_role ?? "";
  for (const g of FILE_GROUPS) {
    if (g.categories.includes(cat) || g.roles.includes(role)) return g.label;
  }
  return "기타 파일";
}

function FileGroupedList({
  files,
  previewFileId,
  deletingId,
  onPreview,
  onDownload,
  onToggleSubmission,
  onUnlink,
  onDelete,
}: {
  files: ActivityFile[];
  previewFileId: string | null;
  deletingId: string | null;
  onPreview: (f: ActivityFile) => void;
  onDownload: (f: ActivityFile) => void;
  onToggleSubmission: (f: ActivityFile) => void;
  onUnlink: (fileId: string) => void;
  onDelete: (fileId: string) => void;
}) {
  const grouped = FILE_GROUPS.map((g) => ({
    ...g,
    files: files.filter((f) => _fileGroup(f) === g.label),
  })).filter((g) => g.files.length > 0);

  return (
    <div>
      {grouped.map((group) => (
        <div key={group.label}>
          <div className="px-4 py-2 text-xs font-semibold" style={{ background: "var(--surface-soft)", color: "var(--text-muted)", borderBottom: "1px solid var(--border-soft)" }}>
            {group.label} ({group.files.length})
          </div>
          {group.files.map((f) => (
            <div key={f.id} className="flex items-center gap-3 px-4 py-3"
              style={{ borderBottom: "1px solid var(--border-soft)", transition: "background 0.1s" }}
              onMouseEnter={(e) => (e.currentTarget.style.background = "var(--surface-soft)")}
              onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}>
              <div className="shrink-0 w-9 h-9 rounded-lg flex items-center justify-center text-xs font-bold uppercase"
                style={{ background: "var(--primary-soft, rgba(99,102,241,0.1))", color: "var(--primary)" }}>
                {(f.file_ext ?? "?").slice(0, 4)}
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium truncate" style={{ color: "var(--text-main)" }}>{f.original_filename}</p>
                <div className="flex flex-wrap items-center gap-1.5 mt-0.5">
                  {f.file_category && (
                    <span className="text-xs rounded-full px-2 py-0.5" style={{ background: "var(--primary-soft)", color: "var(--primary)" }}>
                      {FILE_CATEGORY_LABEL[f.file_category] ?? f.file_category}
                    </span>
                  )}
                  {f.is_submission_file && (
                    <span className="text-xs rounded-full px-2 py-0.5" style={{ background: "var(--success-soft)", color: "var(--success)" }}>
                      제출용{f.submission_month ? ` ${f.submission_month}` : ""}
                    </span>
                  )}
                  <span className="text-xs" style={{ color: "var(--text-muted)" }}>
                    {formatBytes(f.size_bytes)}{f.created_at && ` · ${new Date(f.created_at).toLocaleDateString("ko-KR")}`}
                  </span>
                </div>
              </div>
              <div className="flex items-center gap-1 shrink-0">
                {f.preview_available && (
                  <button className="rounded-lg px-2.5 py-1.5 text-xs transition-all hover:opacity-75"
                    style={{ background: "var(--surface-soft)", color: "var(--text-muted)", border: "1px solid var(--border-soft)" }}
                    onClick={() => onPreview(f)}>
                    {previewFileId === f.id ? "닫기" : "미리보기"}
                  </button>
                )}
                <a href={f.download_url} download={f.original_filename}>
                  <button className="p-1.5 rounded-lg transition-all hover:opacity-75" style={{ color: "var(--text-muted)" }} title="다운로드">
                    <Download className="h-4 w-4" />
                  </button>
                </a>
                <button className="p-1.5 rounded-lg transition-all hover:opacity-75"
                  style={{ color: f.is_submission_file ? "var(--warning)" : "var(--text-muted)" }}
                  title={f.is_submission_file ? "제출용 해제" : "제출용 지정"}
                  onClick={() => onToggleSubmission(f)}>
                  {f.is_submission_file ? "★" : "☆"}
                </button>
                <button className="rounded-lg px-2 py-1 text-xs transition-all hover:opacity-75"
                  style={{ color: "var(--text-muted)", border: "1px solid var(--border-soft)", background: "transparent" }}
                  title="연결 해제 (파일 보존)"
                  disabled={deletingId === f.id}
                  onClick={() => onUnlink(f.id)}>
                  해제
                </button>
                <button className="p-1.5 rounded-lg transition-all hover:opacity-75" style={{ color: "var(--danger)" }}
                  title="삭제" disabled={deletingId === f.id} onClick={() => onDelete(f.id)}>
                  <Trash2 className="h-4 w-4" />
                </button>
              </div>
            </div>
          ))}
        </div>
      ))}
    </div>
  );
}

function formatBytes(bytes: number | null): string {
  if (!bytes) return "-";
  if (bytes < 1024) return `${bytes}B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)}KB`;
  return `${(bytes / 1024 / 1024).toFixed(2)}MB`;
}

function FilePreviewPanel({
  file,
  onClose,
}: {
  file: ActivityFile;
  onClose: () => void;
}) {
  const [preview, setPreview] = React.useState<FilePreviewResult | null>(null);
  const [loading, setLoading] = React.useState(true);
  const [previewError, setPreviewError] = React.useState<string | null>(null);

  React.useEffect(() => {
    setLoading(true);
    setPreviewError(null);
    getFilePreview(file.id)
      .then(setPreview)
      .catch((e) => setPreviewError(e instanceof Error ? e.message : "미리보기 실패"))
      .finally(() => setLoading(false));
  }, [file.id]);

  const inputSt: React.CSSProperties = {
    background: "var(--surface-soft)",
    border: "1px solid var(--border-soft)",
    borderRadius: 12,
    padding: "12px 16px",
    fontSize: 13,
    color: "var(--text-main)",
  };

  return (
    <div
      className="rounded-2xl p-4"
      style={{ background: "var(--surface)", border: "1px solid var(--border-soft)" }}
    >
      <div className="flex items-center justify-between mb-3">
        <p className="text-sm font-semibold truncate max-w-[70%]" style={{ color: "var(--text-main)" }}>
          {file.original_filename}
        </p>
        <div className="flex gap-2">
          <a href={file.download_url} download={file.original_filename}>
            <Button size="sm" variant="secondary">
              <Download className="h-3.5 w-3.5" />
              다운로드
            </Button>
          </a>
          <Button size="sm" variant="ghost" onClick={onClose}>
            <X className="h-3.5 w-3.5" />
          </Button>
        </div>
      </div>

      {loading && (
        <p className="text-sm text-center py-8" style={{ color: "var(--text-muted)" }}>미리보기 불러오는 중...</p>
      )}
      {previewError && (
        <p className="text-sm py-4" style={{ color: "var(--danger)" }}>{previewError}</p>
      )}

      {preview && !loading && (
        <>
          {preview.type === "pdf" && (
            <iframe
              src={`/api/files/${file.id}/preview/inline`}
              className="w-full rounded-xl"
              style={{ height: 480, border: "1px solid var(--border-soft)" }}
            />
          )}
          {preview.type === "image" && (
            <img
              src={`/api/files/${file.id}/preview/inline`}
              alt={file.original_filename}
              className="max-w-full rounded-xl"
              style={{ maxHeight: 480, border: "1px solid var(--border-soft)" }}
            />
          )}
          {preview.type === "excel" && (
            <div className="space-y-3 max-h-96 overflow-y-auto">
              {preview.sheets.map((sheet) => (
                <div key={sheet.name}>
                  <p className="text-xs font-medium mb-1" style={{ color: "var(--text-muted)" }}>{sheet.name}</p>
                  <div className="overflow-x-auto">
                    <table className="w-full text-xs" style={{ borderCollapse: "collapse" }}>
                      <thead>
                        <tr style={{ background: "var(--surface-soft)" }}>
                          {sheet.headers.map((h, i) => (
                            <th key={i} className="px-2 py-1 text-left border" style={{ borderColor: "var(--border-soft)", color: "var(--text-muted)" }}>{h}</th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {sheet.rows.slice(0, 15).map((row, ri) => (
                          <tr key={ri}>
                            {row.map((cell, ci) => (
                              <td key={ci} className="px-2 py-1 border" style={{ borderColor: "var(--border-soft)", color: "var(--text-main)" }}>{cell}</td>
                            ))}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                  {sheet.rows.length > 15 && (
                    <p className="text-xs mt-1" style={{ color: "var(--text-muted)" }}>+{sheet.rows.length - 15}행 더 있음</p>
                  )}
                </div>
              ))}
            </div>
          )}
          {preview.type === "zip" && (
            <div className="max-h-72 overflow-y-auto rounded-xl p-3" style={{ background: "var(--surface-soft)", border: "1px solid var(--border-soft)" }}>
              <p className="text-xs font-medium mb-2" style={{ color: "var(--text-muted)" }}>ZIP 내부 파일 ({preview.files.length}개)</p>
              {preview.files.map((f, i) => (
                <div key={i} className="flex items-center justify-between py-1 border-b" style={{ borderColor: "var(--border-soft)" }}>
                  <span className="text-xs truncate" style={{ color: "var(--text-main)" }}>{f.filename}</span>
                  <span className="text-xs ml-2 shrink-0" style={{ color: "var(--text-muted)" }}>{formatBytes(f.size_bytes)}</span>
                </div>
              ))}
            </div>
          )}
          {preview.type === "hwp" && (
            <div className="rounded-xl p-4 text-center" style={{ background: "var(--surface-soft)", border: "1px solid var(--border-soft)" }}>
              {preview.doc_title && (
                <p className="text-sm font-medium mb-2" style={{ color: "var(--text-main)" }}>{preview.doc_title}</p>
              )}
              <p className="text-sm mb-3" style={{ color: "var(--text-muted)" }}>{preview.message}</p>
              <a href={file.download_url} download={file.original_filename}>
                <Button variant="primary" size="sm">
                  <Download className="h-3.5 w-3.5" />
                  원본 다운로드
                </Button>
              </a>
            </div>
          )}
          {(preview.type === "unsupported" || preview.type === "error") && (
            <div className="rounded-xl p-4 text-center" style={{ background: "var(--surface-soft)", border: "1px solid var(--border-soft)" }}>
              <p className="text-sm mb-3" style={{ color: "var(--text-muted)" }}>{preview.message}</p>
              <a href={file.download_url} download={file.original_filename}>
                <Button variant="secondary" size="sm">
                  <Download className="h-3.5 w-3.5" />
                  원본 파일 다운로드
                </Button>
              </a>
            </div>
          )}
        </>
      )}
    </div>
  );
}

function FileVaultTab({
  activityId,
  onUpdated,
}: {
  activityId: string;
  onUpdated: () => void;
}) {
  const fileInputRef = React.useRef<HTMLInputElement>(null);
  const [files, setFiles] = React.useState<ActivityFile[]>([]);
  const [loadingFiles, setLoadingFiles] = React.useState(true);
  const [filterCategory, setFilterCategory] = React.useState("");
  const [filterSubmission, setFilterSubmission] = React.useState(false);
  const [uploading, setUploading] = React.useState(false);
  const [uploadFile, setUploadFile] = React.useState<File | null>(null);
  const [uploadCategory, setUploadCategory] = React.useState("");
  const [uploadRole, setUploadRole] = React.useState("");
  const [uploadIsSubmission, setUploadIsSubmission] = React.useState(false);
  const [uploadMonth, setUploadMonth] = React.useState("");
  const [uploadError, setUploadError] = React.useState<string | null>(null);
  const [deletingId, setDeletingId] = React.useState<string | null>(null);
  const [previewFile, setPreviewFile] = React.useState<ActivityFile | null>(null);
  const [actionError, setActionError] = React.useState<string | null>(null);

  // Submission package state
  const [pkgMonth, setPkgMonth] = React.useState("");
  const [pkgPreview, setPkgPreview] = React.useState<SubmissionPackagePreview | null>(null);
  const [pkgLoading, setPkgLoading] = React.useState(false);
  const [pkgGenerating, setPkgGenerating] = React.useState(false);
  const [pkgResult, setPkgResult] = React.useState<{ download_url: string; file_count: number } | null>(null);
  const [pkgError, setPkgError] = React.useState<string | null>(null);

  async function loadFiles() {
    setLoadingFiles(true);
    try {
      const data = await getActivityFiles(activityId, {
        category: filterCategory || undefined,
      });
      setFiles(filterSubmission ? data.filter((f) => f.is_submission_file) : data);
    } catch {
      // ignore
    } finally {
      setLoadingFiles(false);
    }
  }

  React.useEffect(() => {
    loadFiles();
  }, [activityId, filterCategory, filterSubmission]);

  async function handleUpload() {
    if (!uploadFile) return;
    setUploading(true);
    setUploadError(null);
    try {
      await uploadActivityFile(activityId, uploadFile, {
        file_category: uploadCategory || undefined,
        file_role: uploadRole || undefined,
        is_submission_file: uploadIsSubmission,
        submission_month: uploadMonth || undefined,
      });
      setUploadFile(null);
      setUploadCategory("");
      setUploadRole("");
      setUploadIsSubmission(false);
      setUploadMonth("");
      if (fileInputRef.current) fileInputRef.current.value = "";
      await loadFiles();
      onUpdated();
    } catch (err: unknown) {
      setUploadError(err instanceof Error ? err.message : "업로드 실패");
    } finally {
      setUploading(false);
    }
  }

  async function handleDelete(fileId: string) {
    if (!confirm("이 파일을 삭제하시겠습니까?\n화면에서는 사라지지만 원본 파일은 복구를 위해 서버에 보관될 수 있습니다.")) return;
    setDeletingId(fileId);
    setActionError(null);
    try {
      await softDeleteFile(fileId);
      setFiles((prev) => prev.filter((f) => f.id !== fileId));
      if (previewFile?.id === fileId) setPreviewFile(null);
      onUpdated();
    } catch (err: unknown) {
      setActionError(err instanceof Error ? err.message : "삭제 실패");
    } finally {
      setDeletingId(null);
    }
  }

  async function handleUnlink(fileId: string) {
    if (!confirm("이 파일을 활동에서 연결 해제하시겠습니까?\n파일은 삭제되지 않고 전역 파일함으로 이동합니다.")) return;
    setDeletingId(fileId);
    setActionError(null);
    try {
      await patchFileActivity(fileId, null);
      setFiles((prev) => prev.filter((f) => f.id !== fileId));
      if (previewFile?.id === fileId) setPreviewFile(null);
      onUpdated();
    } catch (err: unknown) {
      setActionError(err instanceof Error ? err.message : "연결 해제 실패");
    } finally {
      setDeletingId(null);
    }
  }

  async function handleToggleSubmission(file: ActivityFile) {
    try {
      const updated = await patchFileSubmission(file.id, {
        is_submission_file: !file.is_submission_file,
      });
      setFiles((prev) => prev.map((f) => (f.id === file.id ? updated : f)));
    } catch (err: unknown) {
      setActionError(err instanceof Error ? err.message : "수정 실패");
    }
  }

  async function handlePkgPreview() {
    if (!pkgMonth) return;
    setPkgLoading(true);
    setPkgError(null);
    setPkgPreview(null);
    setPkgResult(null);
    try {
      const result = await getSubmissionPackagePreview(pkgMonth);
      setPkgPreview(result);
    } catch (err: unknown) {
      setPkgError(err instanceof Error ? err.message : "미리보기 실패");
    } finally {
      setPkgLoading(false);
    }
  }

  async function handlePkgGenerate() {
    if (!pkgMonth) return;
    setPkgGenerating(true);
    setPkgError(null);
    try {
      const result = await generateSubmissionPackage({ month: pkgMonth });
      setPkgResult({ download_url: result.download_url, file_count: result.file_count });
    } catch (err: unknown) {
      setPkgError(err instanceof Error ? err.message : "ZIP 생성 실패");
    } finally {
      setPkgGenerating(false);
    }
  }

  const sel: React.CSSProperties = {
    background: "var(--surface)",
    color: "var(--text-main)",
    border: "1px solid var(--border-soft)",
    borderRadius: 10,
    padding: "7px 10px",
    fontSize: 13,
  };

  return (
    <div className="space-y-3">

      {/* ── 업로드 카드 ── */}
      <Card padding="lg">
        {/* 드래그 영역 */}
        <div
          className="flex flex-col items-center justify-center gap-1.5 rounded-xl p-5 text-center cursor-pointer transition-all hover:opacity-80 mb-3"
          style={{
            border: uploadFile ? "2px dashed var(--primary)" : "2px dashed var(--border-soft)",
            background: uploadFile ? "var(--primary-soft, rgba(99,102,241,0.06))" : "var(--surface-soft)",
          }}
          onClick={() => fileInputRef.current?.click()}
        >
          {uploadFile ? (
            <>
              <p className="text-sm font-medium" style={{ color: "var(--primary)" }}>{uploadFile.name}</p>
              <p className="text-xs" style={{ color: "var(--text-muted)" }}>클릭해서 변경</p>
            </>
          ) : (
            <>
              <p className="text-sm font-medium" style={{ color: "var(--text-muted)" }}>파일 선택 또는 드래그</p>
              <p className="text-xs" style={{ color: "var(--text-muted)" }}>PDF · 이미지 · 엑셀 · HWP · ZIP</p>
            </>
          )}
        </div>
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf,.png,.jpg,.jpeg,.webp,.xlsx,.xls,.csv,.hwp,.hwpx,.zip"
          className="hidden"
          onChange={(e) => {
            const f = e.target.files?.[0] ?? null;
            setUploadFile(f);
            if (f && !uploadCategory) {
              const name = f.name.toLowerCase();
              if (name.includes("내역서") || name.includes("보고")) setUploadCategory("activity_report");
              else if (name.includes("기획서") || name.includes("계획")) setUploadCategory("activity_plan");
              else if (name.includes("영수증")) setUploadCategory("receipt");
            }
          }}
        />

        {/* 옵션 행 */}
        <div className="flex flex-wrap items-center gap-2">
          <select value={uploadCategory} onChange={(e) => setUploadCategory(e.target.value)} style={sel}>
            <option value="">유형 자동</option>
            {Object.entries(FILE_CATEGORY_LABEL).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
          </select>
          <select value={uploadRole} onChange={(e) => setUploadRole(e.target.value)} style={sel}>
            <option value="">역할 자동</option>
            {Object.entries(FILE_ROLE_LABEL).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
          </select>
          <label className="flex items-center gap-1.5 text-xs cursor-pointer select-none" style={{ color: "var(--text-muted)" }}>
            <input type="checkbox" checked={uploadIsSubmission} onChange={(e) => setUploadIsSubmission(e.target.checked)} />
            제출용
          </label>
          {uploadIsSubmission && (
            <input type="month" value={uploadMonth} onChange={(e) => setUploadMonth(e.target.value)}
              style={{ ...sel, width: "auto" }} />
          )}
          <Button onClick={handleUpload} loading={uploading} disabled={!uploadFile || uploading}>
            업로드
          </Button>
        </div>
        {uploadError && <p className="text-xs mt-2" style={{ color: "var(--danger)" }}>{uploadError}</p>}
      </Card>

      {/* ── 필터 + 파일 목록 ── */}
      <Card padding="none">
        {/* 필터 바 */}
        <div className="flex flex-wrap items-center gap-2 px-4 py-3"
          style={{ borderBottom: "1px solid var(--border-soft)" }}>
          <select value={filterCategory} onChange={(e) => setFilterCategory(e.target.value)} style={{ ...sel, flex: "none" }}>
            <option value="">전체 유형</option>
            {Object.entries(FILE_CATEGORY_LABEL).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
          </select>
          <button
            onClick={() => setFilterSubmission(!filterSubmission)}
            className="rounded-full px-3 py-1 text-xs font-medium transition-all"
            style={filterSubmission
              ? { background: "var(--primary)", color: "#fff" }
              : { background: "var(--surface-soft)", color: "var(--text-muted)", border: "1px solid var(--border-soft)" }}
          >
            제출용
          </button>
          {files.length > 0 && (
            <span className="ml-auto text-xs" style={{ color: "var(--text-muted)" }}>
              {files.length}개
            </span>
          )}
        </div>

        {actionError && (
          <p className="px-4 py-2 text-xs" style={{ color: "var(--danger)" }}>{actionError}</p>
        )}

        {/* 미리보기 패널 */}
        {previewFile && (
          <div className="p-3" style={{ borderBottom: "1px solid var(--border-soft)" }}>
            <FilePreviewPanel file={previewFile} onClose={() => setPreviewFile(null)} />
          </div>
        )}

        {/* 목록 */}
        {loadingFiles ? (
          <div className="p-6 text-center">
            <p className="text-sm" style={{ color: "var(--text-muted)" }}>불러오는 중...</p>
          </div>
        ) : files.length === 0 ? (
          <div className="p-6">
            <EmptyState message="파일이 없습니다." description="위에서 파일을 업로드하세요." />
          </div>
        ) : (
          <FileGroupedList
            files={files}
            previewFileId={previewFile?.id ?? null}
            deletingId={deletingId}
            onPreview={(f) => setPreviewFile(previewFile?.id === f.id ? null : f)}
            onDownload={() => {}}
            onToggleSubmission={handleToggleSubmission}
            onUnlink={handleUnlink}
            onDelete={handleDelete}
          />
        )}
      </Card>

      {/* ── 제출 패키지 ── */}
      <Card padding="lg">
        <h3 className="text-sm font-semibold mb-3" style={{ color: "var(--text-main)" }}>월별 제출 패키지</h3>
        <div className="flex flex-wrap items-center gap-2">
          <input type="month" value={pkgMonth} onChange={(e) => setPkgMonth(e.target.value)}
            style={{ ...sel, minHeight: 38 }} />
          <Button size="sm" variant="secondary" onClick={handlePkgPreview} disabled={!pkgMonth || pkgLoading}>
            {pkgLoading ? "조회 중..." : "미리보기"}
          </Button>
          <Button size="sm" onClick={handlePkgGenerate} disabled={!pkgMonth || pkgGenerating}>
            {pkgGenerating ? "생성 중..." : "ZIP 생성"}
          </Button>
        </div>

        {pkgError && <p className="text-xs mt-2" style={{ color: "var(--danger)" }}>{pkgError}</p>}

        {pkgResult && (
          <div className="flex items-center gap-3 mt-3 rounded-xl p-3"
            style={{ background: "var(--success-soft)", border: "1px solid var(--border-soft)" }}>
            <p className="text-sm flex-1" style={{ color: "var(--success)" }}>
              ZIP 완료 · {pkgResult.file_count}개 파일
            </p>
            <a href={pkgResult.download_url} download>
              <Button size="sm" variant="secondary">
                <Download className="h-3.5 w-3.5" />
                다운로드
              </Button>
            </a>
          </div>
        )}

        {pkgPreview && (
          <div className="mt-3 space-y-1.5">
            <div className="flex gap-3 text-xs mb-1" style={{ color: "var(--text-muted)" }}>
              <span>활동 {pkgPreview.summary.activity_count}개</span>
              <span>제출파일 {pkgPreview.summary.submission_file_count}개</span>
              {pkgPreview.summary.missing_count > 0 && (
                <span style={{ color: "var(--warning)" }}>누락 {pkgPreview.summary.missing_count}개</span>
              )}
            </div>
            {pkgPreview.activities.map((act) => (
              <div key={act.activity_id} className="rounded-xl p-3"
                style={{ background: "var(--surface-soft)", border: "1px solid var(--border-soft)" }}>
                <p className="text-xs font-semibold" style={{ color: "var(--text-main)" }}>
                  {act.title}
                  {act.activity_date && (
                    <span className="ml-1.5 font-normal" style={{ color: "var(--text-muted)" }}>{act.activity_date}</span>
                  )}
                </p>
                {act.submission_files.length > 0 ? (
                  <div className="mt-1 space-y-0.5">
                    {act.submission_files.map((sf) => (
                      <p key={sf.id} className="text-xs" style={{ color: "var(--text-muted)" }}>
                        · {sf.filename}
                      </p>
                    ))}
                  </div>
                ) : (
                  <p className="text-xs mt-0.5" style={{ color: "var(--text-muted)" }}>제출용 파일 없음</p>
                )}
                {act.missing_items.length > 0 && (
                  <p className="text-xs mt-1" style={{ color: "var(--warning)" }}>
                    누락: {act.missing_items.map((m) => FILE_CATEGORY_LABEL[m] ?? m).join(", ")}
                  </p>
                )}
              </div>
            ))}
          </div>
        )}
      </Card>
    </div>
  );
}

// ─── Participant Import Tab (Task 27) ─────────────────────────────────────────

const FORM_TYPE_LABEL: Record<string, string> = {
  activity_application_form: "활동 신청서",
  activity_feedback_form: "활동 후 피드백/활동지",
  bank_statement: "거래내역서",
  member_roster: "부원 명부",
  unknown_excel: "알 수 없음",
};

const PARTICIPANT_STATUS_LABEL: Record<string, string> = {
  applied: "신청",
  confirmed: "확정",
  attended: "참석",
  completed: "완료",
  cancelled: "취소",
  no_show: "불참",
};

const MATCH_STATUS_LABEL: Record<string, string> = {
  matched_member: "기존 부원",
  needs_review: "확인 필요",
  duplicate_candidate: "중복 후보",
  unregistered_candidate: "미등록 후보",
  already_participant: "이미 참가자",
};

const MATCH_STATUS_COLOR: Record<string, { bg: string; color: string }> = {
  matched_member: { bg: "#d1fae5", color: "var(--success)" },
  needs_review: { bg: "#fef9c3", color: "var(--warning, #b45309)" },
  duplicate_candidate: { bg: "#fef3c7", color: "#b45309" },
  unregistered_candidate: { bg: "#fee2e2", color: "var(--danger)" },
  already_participant: { bg: "#e0e7ff", color: "#4338ca" },
};

const UNREGISTERED_ACTION_LABEL: Record<string, string> = {
  link_existing_member: "기존 부원 연결",
  create_new_member: "새 부원으로 등록",
  mark_external: "외부인으로 유지",
  ignore: "무시",
  needs_user_selection: "선택 필요",
};

function ParticipantImportTab({
  activityId,
  onUpdated,
}: {
  activityId: string;
  onUpdated: () => void;
}) {
  const [file, setFile] = useState<File | null>(null);
  const [previewing, setPreviewing] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const [preview, setPreview] = useState<import("@/lib/api").ParticipantImportPreview | null>(null);
  const [rowOverrides, setRowOverrides] = useState<Record<number, string>>({});
  const [confirmResult, setConfirmResult] = useState<import("@/lib/api").ParticipantImportConfirmResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const fileInputRef = React.useRef<HTMLInputElement>(null);

  async function handlePreview() {
    if (!file) return;
    setPreviewing(true);
    setError(null);
    setPreview(null);
    setConfirmResult(null);
    setRowOverrides({});
    try {
      const result = await previewParticipantImport(activityId, file);
      setPreview(result);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "미리보기 실패");
    } finally {
      setPreviewing(false);
    }
  }

  async function handleConfirm() {
    if (!preview) return;
    setConfirming(true);
    setError(null);
    try {
      const overrides = Object.entries(rowOverrides).map(([rowIndex, selectedAction]) => ({
        row_index: Number(rowIndex),
        selected_action: selectedAction,
      }));
      const result = await confirmParticipantImport(activityId, {
        action_id: preview.confirm_payload.action_id,
        row_overrides: overrides,
      });
      setConfirmResult(result);
      setPreview(null);
      setFile(null);
      if (fileInputRef.current) fileInputRef.current.value = "";
      onUpdated();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "반영 실패");
    } finally {
      setConfirming(false);
    }
  }

  async function handleCancel() {
    if (!preview) return;
    try {
      await cancelParticipantImport(activityId, preview.confirm_payload.action_id);
    } catch {
      // ignore cancel errors
    }
    setPreview(null);
    setFile(null);
    if (fileInputRef.current) fileInputRef.current.value = "";
    setRowOverrides({});
  }

  const needsUserSelection = preview?.rows.filter(
    (r) => r.action === "needs_user_selection" || r.match_status === "unregistered_candidate" || r.match_status === "duplicate_candidate"
  ) ?? [];

  return (
    <div className="space-y-4">
      <Card padding="lg">
        <h3 className="text-sm font-semibold mb-1" style={{ color: "var(--text-main)" }}>
          참가자 명단 Import
        </h3>
        <p className="text-xs mb-4" style={{ color: "var(--text-muted)" }}>
          참가자 명단 또는 신청서 엑셀을 업로드합니다. 기존 부원과 대조 후 확인하면 참여자로 등록됩니다.
        </p>

        <div
          className="flex flex-col items-center justify-center gap-2 rounded-xl p-5 text-center cursor-pointer transition-opacity hover:opacity-80 mb-3"
          style={{
            border: file ? "2px dashed var(--primary)" : "2px dashed var(--border-soft)",
            background: file ? "var(--primary-soft, rgba(99,102,241,0.06))" : "var(--surface-soft)",
          }}
          onClick={() => fileInputRef.current?.click()}
        >
          {file ? (
            <>
              <p className="text-sm font-medium" style={{ color: "var(--primary)" }}>{file.name}</p>
              <p className="text-xs" style={{ color: "var(--text-muted)" }}>클릭해서 다른 파일로 변경</p>
            </>
          ) : (
            <>
              <p className="text-sm font-medium" style={{ color: "var(--text-muted)" }}>엑셀 파일 선택</p>
              <p className="text-xs" style={{ color: "var(--text-muted)" }}>.xlsx · .xls · .csv</p>
            </>
          )}
        </div>
        <input
          ref={fileInputRef}
          type="file"
          accept=".xlsx,.xls,.csv"
          className="hidden"
          onChange={(e) => {
            setFile(e.target.files?.[0] ?? null);
            setPreview(null);
            setConfirmResult(null);
            setError(null);
            setRowOverrides({});
          }}
        />

        <Button onClick={handlePreview} disabled={!file || previewing} loading={previewing}>
          {previewing ? "분석 중..." : "분석하기"}
        </Button>
      </Card>

      {error && (
        <Card padding="md">
          <p className="text-sm" style={{ color: "var(--danger)" }}>{error}</p>
        </Card>
      )}

      {confirmResult && (
        <Card padding="md">
          <p className="text-sm font-medium mb-2" style={{ color: "var(--success)" }}>참여자 반영 완료</p>
          <div className="text-xs space-y-1" style={{ color: "var(--text-muted)" }}>
            <p>신규 참여자: {confirmResult.result.created_participants}명</p>
            <p>갱신된 참여자: {confirmResult.result.updated_participants}명</p>
            <p>이미 참여자: {confirmResult.result.already_participants}명</p>
            {confirmResult.result.external_participants > 0 && (
              <p>외부인 참가자: {confirmResult.result.external_participants}명</p>
            )}
            {confirmResult.result.ignored_rows > 0 && (
              <p>무시된 행: {confirmResult.result.ignored_rows}개</p>
            )}
            {confirmResult.result.created_members > 0 && (
              <p>신규 부원 생성: {confirmResult.result.created_members}명</p>
            )}
          </div>
        </Card>
      )}

      {preview && (
        <Card padding="lg">
          <div className="flex items-start justify-between gap-3 mb-4">
            <div>
              <p className="text-sm font-semibold" style={{ color: "var(--text-main)" }}>Preview</p>
              <p className="text-xs mt-0.5" style={{ color: "var(--text-muted)" }}>
                확인 후 반영을 누르면 참여자로 등록됩니다
              </p>
            </div>
            <div className="flex gap-2">
              <Button size="sm" variant="secondary" onClick={handleCancel} disabled={confirming}>
                취소
              </Button>
              <Button size="sm" onClick={handleConfirm} disabled={confirming} loading={confirming}>
                {confirming ? "반영 중..." : "확인 후 반영"}
              </Button>
            </div>
          </div>

          {/* Summary */}
          <div className="grid grid-cols-3 gap-2 mb-4">
            {[
              ["전체 행", preview.summary.total_rows + "명"],
              ["기존 부원 연결", preview.summary.matched_members + "명"],
              ["미등록 후보", preview.summary.unregistered_candidates + "명"],
              ["이미 참가자", preview.summary.already_participants + "명"],
              ["중복 후보", preview.summary.duplicate_candidates + "명"],
              ["반영 예정", preview.summary.will_create_participants + "명"],
            ].map(([label, val]) => (
              <div key={label} className="rounded-lg p-2 text-center" style={{ background: "var(--surface-hover)" }}>
                <p className="text-xs" style={{ color: "var(--text-muted)" }}>{label}</p>
                <p className="text-sm font-semibold" style={{ color: "var(--text-main)" }}>{val}</p>
              </div>
            ))}
          </div>

          {/* Unregistered/duplicate rows requiring user action */}
          {needsUserSelection.length > 0 && (
            <div className="mb-4 p-3 rounded-xl" style={{ background: "var(--surface-soft)", border: "1px solid var(--border-soft)" }}>
              <p className="text-xs font-semibold mb-2" style={{ color: "var(--warning, #b45309)" }}>
                처리 선택 필요 ({needsUserSelection.length}명)
              </p>
              <div className="space-y-2">
                {needsUserSelection.map((row) => (
                  <div key={row.row_index} className="flex items-center gap-2 flex-wrap">
                    <span className="text-xs font-medium" style={{ color: "var(--text-main)", minWidth: 60 }}>
                      {row.name ?? "-"}
                    </span>
                    <span className="text-xs" style={{ color: "var(--text-muted)" }}>
                      {row.student_id ?? "-"}
                    </span>
                    <span className="px-1.5 py-0.5 rounded text-xs" style={{
                      background: MATCH_STATUS_COLOR[row.match_status]?.bg ?? "#f3f4f6",
                      color: MATCH_STATUS_COLOR[row.match_status]?.color ?? "var(--text-muted)",
                    }}>
                      {MATCH_STATUS_LABEL[row.match_status] ?? row.match_status}
                    </span>
                    <select
                      value={rowOverrides[row.row_index] ?? row.available_actions[0] ?? "ignore"}
                      onChange={(e) => setRowOverrides((prev) => ({ ...prev, [row.row_index]: e.target.value }))}
                      className="rounded px-2 py-1 text-xs focus:outline-none"
                      style={{ background: "var(--surface)", color: "var(--text-main)", border: "1px solid var(--border-soft)" }}
                    >
                      {row.available_actions.map((a) => (
                        <option key={a} value={a}>
                          {UNREGISTERED_ACTION_LABEL[a] ?? a}
                          {a === "create_new_member" ? " ⚠" : ""}
                        </option>
                      ))}
                    </select>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Row table */}
          <div className="overflow-x-auto">
            <table className="w-full text-xs" style={{ borderCollapse: "collapse" }}>
              <thead>
                <tr style={{ borderBottom: "1px solid var(--border-soft)" }}>
                  {["#", "이름", "학번", "학과", "매칭 상태", "처리 예정"].map((h) => (
                    <th key={h} className="text-left py-1 px-2 font-medium" style={{ color: "var(--text-muted)" }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {preview.rows.slice(0, 50).map((row) => {
                  const effectiveAction = rowOverrides[row.row_index] ?? row.action;
                  return (
                    <tr key={row.row_index} style={{ borderBottom: "1px solid var(--border-soft)" }}>
                      <td className="py-1 px-2" style={{ color: "var(--text-muted)" }}>{row.row_index}</td>
                      <td className="py-1 px-2 font-medium" style={{ color: "var(--text-main)" }}>{row.name ?? "-"}</td>
                      <td className="py-1 px-2" style={{ color: "var(--text-muted)" }}>{row.student_id ?? "-"}</td>
                      <td className="py-1 px-2" style={{ color: "var(--text-muted)" }}>{row.department ?? "-"}</td>
                      <td className="py-1 px-2">
                        <span className="px-1.5 py-0.5 rounded text-xs" style={{
                          background: MATCH_STATUS_COLOR[row.match_status]?.bg ?? "#f3f4f6",
                          color: MATCH_STATUS_COLOR[row.match_status]?.color ?? "var(--text-muted)",
                        }}>
                          {MATCH_STATUS_LABEL[row.match_status] ?? row.match_status}
                        </span>
                      </td>
                      <td className="py-1 px-2">
                        <span className="px-1.5 py-0.5 rounded text-xs" style={{ background: "var(--surface-hover)", color: "var(--text-muted)" }}>
                          {UNREGISTERED_ACTION_LABEL[effectiveAction] ?? effectiveAction}
                        </span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
            {preview.rows.length > 50 && (
              <p className="text-xs mt-2" style={{ color: "var(--text-muted)" }}>
                +{preview.rows.length - 50}행 더 있습니다.
              </p>
            )}
          </div>
        </Card>
      )}
    </div>
  );
}

// ─── AI Work Tab ──────────────────────────────────────────────────────────────

type AIRun = {
  id: string;
  requestMessage: string;
  response: AssistantExecuteResponse;
  status?: "preview" | "applied" | "failed" | "cancelled";
  applying?: boolean;
};

function AIWorkTab({
  activityId,
  onUpdated,
}: {
  activityId: string;
  onUpdated: () => void;
}) {
  const fileRef = React.useRef<HTMLInputElement>(null);
  const [files, setFiles] = useState<File[]>([]);
  const [message, setMessage] = useState("");
  const [running, setRunning] = useState(false);
  const [runError, setRunError] = useState<string | null>(null);
  const [runs, setRuns] = useState<AIRun[]>([]);

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    setFiles((prev) => [...prev, ...Array.from(e.target.files ?? [])]);
    e.target.value = "";
  }

  async function handleRun() {
    if (!message.trim() && files.length === 0) {
      setRunError("파일을 첨부하거나 요청을 입력해 주세요.");
      return;
    }
    setRunning(true);
    setRunError(null);
    try {
      const fd = new FormData();
      if (message) fd.append("message", message);
      fd.append("activity_id", activityId);
      fd.append("activity_mode", "link_existing");
      fd.append("requested_intent", "auto");
      fd.append("auto_apply", "false");
      for (const f of files) fd.append("files", f);

      const res = await executeAssistant(fd);
      setRuns((prev) => [{ id: nanoid(), requestMessage: message || files.map((f) => f.name).join(", "), response: res }, ...prev]);
      setMessage("");
      setFiles([]);
      // Refresh activity detail after any successful AI work so fees/files/checklist update
      const ALWAYS_REFETCH_TYPES = [
        "activity_fee_generation_result", "payment_manual_update_result",
        "receipt_analysis", "activity_report_draft", "activity_import_result",
      ];
      if (res.result_type !== "error" && ALWAYS_REFETCH_TYPES.includes(res.result_type)) {
        setTimeout(() => onUpdated(), 600);
      }
    } catch (err: unknown) {
      setRunError(err instanceof Error ? err.message : "요청 처리 중 오류가 발생했습니다.");
    } finally {
      setRunning(false);
    }
  }

  const EXAMPLE_REQUESTS = [
    "이 사진과 메모로 보고서 작성해줘",
    "이 영수증을 이 활동 증빙으로 연결해줘",
    "참여자 기준으로 활동비 10000원 납부 대상 만들어줘",
  ];

  async function handleApply(runId: string) {
    const run = runs.find((item) => item.id === runId);
    const actionId = run?.response.apply_payload?.action_id;
    if (typeof actionId !== "string") {
      setRunError("반영할 action_id를 찾지 못했습니다.");
      return;
    }
    setRuns((prev) => prev.map((item) => item.id === runId ? { ...item, applying: true } : item));
    setRunError(null);
    try {
      const applied = await confirmAssistantAction(actionId);
      setRuns((prev) => prev.map((item) => {
        if (item.id !== runId) return item;
        return {
          ...item,
          applying: false,
          status: "applied",
          response: {
            ...item.response,
            requires_confirmation: false,
            message: "확인 후 반영이 완료되었습니다.",
            result: { ...item.response.result, applied_result: applied.result ?? {}, proposal_status: applied.status },
          },
        };
      }));
      setTimeout(() => onUpdated(), 300);
    } catch (err: unknown) {
      setRunError(err instanceof Error ? err.message : "반영에 실패했습니다.");
      setRuns((prev) => prev.map((item) => item.id === runId ? { ...item, applying: false, status: "failed" } : item));
    }
  }

  async function handleCancel(runId: string) {
    const run = runs.find((item) => item.id === runId);
    const actionId = run?.response.apply_payload?.action_id;
    if (typeof actionId !== "string") {
      setRunError("취소할 action_id를 찾지 못했습니다.");
      return;
    }
    setRuns((prev) => prev.map((item) => item.id === runId ? { ...item, applying: true } : item));
    setRunError(null);
    try {
      await cancelAssistantAction(actionId);
      setRuns((prev) => prev.map((item) => item.id === runId ? { ...item, applying: false, status: "cancelled" } : item));
    } catch (err: unknown) {
      setRunError(err instanceof Error ? err.message : "취소에 실패했습니다.");
      setRuns((prev) => prev.map((item) => item.id === runId ? { ...item, applying: false } : item));
    }
  }

  return (
    <div className="space-y-4">
      <Card padding="lg">
        <h3 className="text-sm font-semibold mb-1" style={{ color: "var(--text-main)" }}>
          이 활동에서 AI 작업 실행
        </h3>
        <p className="text-xs mb-4" style={{ color: "var(--text-muted)" }}>
          activity_id가 자동으로 포함되어 이 활동과 연결됩니다.
        </p>

        {/* File upload */}
        <div
          className="flex flex-col items-center justify-center gap-2 rounded-xl p-4 text-center cursor-pointer transition-opacity hover:opacity-80 mb-3"
          style={{ border: "2px dashed var(--border-soft)", background: "var(--surface-soft)" }}
          onClick={() => fileRef.current?.click()}
        >
          <p className="text-sm font-medium" style={{ color: "var(--text-muted)" }}>
            파일 첨부 (선택)
          </p>
          <p className="text-xs" style={{ color: "var(--text-muted)" }}>
            영수증 이미지 · 활동 사진 · PDF
          </p>
        </div>
        <input
          ref={fileRef}
          type="file"
          multiple
          accept="image/*,.pdf,.xls,.xlsx,.csv"
          className="hidden"
          onChange={handleFileChange}
        />
        {files.length > 0 && (
          <div className="flex flex-wrap gap-2 mb-3">
            {files.map((f, i) => (
              <div key={i} className="flex items-center gap-1.5 rounded-lg px-2.5 py-1 text-xs"
                style={{ background: "var(--primary-soft)", color: "var(--primary)" }}>
                {f.name}
                <button onClick={() => setFiles((p) => p.filter((_, j) => j !== i))}>
                  <X className="h-3 w-3" />
                </button>
              </div>
            ))}
          </div>
        )}

        {/* Message */}
        <textarea
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          placeholder="예: 이 영수증을 이 활동 증빙으로 연결해줘"
          rows={3}
          className="w-full rounded-xl px-3 py-2 text-sm resize-none focus:outline-none mb-2"
          style={{ background: "var(--surface)", color: "var(--text-main)", border: "1px solid var(--border-soft)", minHeight: 80 }}
          onFocus={(e) => { e.currentTarget.style.borderColor = "var(--primary)"; }}
          onBlur={(e) => { e.currentTarget.style.borderColor = "var(--border-soft)"; }}
        />

        {/* Example chips */}
        <div className="flex flex-wrap gap-1.5 mb-3">
          {EXAMPLE_REQUESTS.map((chip) => (
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

        {runError && (
          <p className="text-sm mb-2" style={{ color: "var(--danger)" }}>{runError}</p>
        )}

        <Button onClick={handleRun} loading={running} disabled={running}>
          {running ? "처리 중..." : "AI 실행"}
        </Button>
      </Card>

      {/* Results */}
      {runs.length > 0 && (
        <div className="space-y-3">
          {runs.map((run) => (
            <AssistantResultCard
              key={run.id}
              response={run.response}
              status={run.status ?? (run.response.result_type === "error" ? "failed" : run.response.requires_confirmation ? "preview" : "applied")}
              requestMessage={run.requestMessage}
              applying={run.applying}
              onApplyClick={() => handleApply(run.id)}
              onCancel={() => handleCancel(run.id)}
            />
          ))}
        </div>
      )}
    </div>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function ActivityDetailPage() {
  const params = useParams();
  const router = useRouter();
  const activityId = params?.id as string;

  const [detail, setDetail] = useState<ActivityDetail | null>(null);
  const [categories, setCategories] = useState<ActivityCategory[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<TabKey>("overview");
  const [deleting, setDeleting] = useState(false);

  const load = useCallback(async () => {
    if (!activityId) return;
    // Only show full-screen loader on first load. Background refreshes (onUpdated calls)
    // update data silently so mounted tabs keep their local state (e.g. AI run results).
    setError(null);
    try {
      const [d, cats] = await Promise.all([
        getActivityDetail(activityId),
        getActivityCategoriesTyped(),
      ]);
      setDetail(d);
      setCategories(cats);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "활동을 불러오지 못했습니다.");
    } finally {
      setLoading(false);
    }
  }, [activityId]);

  useEffect(() => { load(); }, [load]);

  useEffect(() => {
    const applyTab = (value: string | null | undefined) => {
      const next = normalizeActivityTab(value);
      if (next) setActiveTab(next);
    };
    applyTab(new URLSearchParams(window.location.search).get("tab"));

    const handleSwitchTab = (event: Event) => {
      applyTab((event as CustomEvent<string>).detail);
    };
    const handlePopState = () => {
      applyTab(new URLSearchParams(window.location.search).get("tab"));
    };

    window.addEventListener("switch-tab", handleSwitchTab);
    window.addEventListener("popstate", handlePopState);
    return () => {
      window.removeEventListener("switch-tab", handleSwitchTab);
      window.removeEventListener("popstate", handlePopState);
    };
  }, []);

  if (loading) {
    return <AppShell><LoadingState /></AppShell>;
  }

  if (error || !detail) {
    return (
      <AppShell>
        <ErrorState message={error ?? "활동을 찾을 수 없습니다."} />
      </AppShell>
    );
  }

  const { activity, checklist } = detail;

  const completedCount = checklist.filter((c) => c.done).length;

  async function handleDeleteActivity() {
    const ok = window.confirm(
      "이 활동을 삭제하시겠습니까?\n참여자, 파일, 납부 기록은 복구를 위해 보관되지만 활동 목록에서는 보이지 않습니다.",
    );
    if (!ok) return;
    setDeleting(true);
    try {
      await deleteActivity(activityId);
      router.push("/activities");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "활동 삭제에 실패했습니다.");
      setDeleting(false);
    }
  }

  return (
    <AppShell>
      <div className="space-y-5">
        {/* Back + title */}
        <div>
          <button
            onClick={() => router.push("/activities")}
            className="flex items-center gap-1 text-sm mb-3 hover:opacity-75 transition-opacity"
            style={{ color: "var(--text-muted)" }}
          >
            <ArrowLeft className="h-3.5 w-3.5" />
            활동 목록
          </button>
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <div className="flex items-center gap-2 mb-1">
                <StatusBadge status={activity.status} />
                {activity.category_name && (
                  <span className="text-xs" style={{ color: "var(--text-muted)" }}>
                    {activity.category_name}
                  </span>
                )}
              </div>
              <h1 className="text-xl font-semibold" style={{ color: "var(--text-main)" }}>
                {activity.title}
              </h1>
              <div className="flex flex-wrap items-center gap-3 mt-1">
                {activity.activity_date && (
                  <span className="flex items-center gap-1 text-sm" style={{ color: "var(--text-muted)" }}>
                    <Calendar className="h-3.5 w-3.5" />
                    {activity.activity_date}
                  </span>
                )}
                {activity.location && (
                  <span className="flex items-center gap-1 text-sm" style={{ color: "var(--text-muted)" }}>
                    <MapPin className="h-3.5 w-3.5" />
                    {activity.location}
                  </span>
                )}
                <span className="flex items-center gap-1 text-sm" style={{ color: "var(--text-muted)" }}>
                  <Users className="h-3.5 w-3.5" />
                  {detail.participants.length}명 참여
                </span>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <Button variant="ghost" onClick={handleDeleteActivity} disabled={deleting} loading={deleting}>
                <Trash2 className="h-4 w-4" />
                삭제
              </Button>
              {/* Checklist progress */}
              <div
                className="rounded-xl px-4 py-2.5 text-center"
                style={{ background: "var(--surface)", border: "1px solid var(--border-soft)" }}
              >
                <p className="text-xs mb-0.5" style={{ color: "var(--text-muted)" }}>처리 완료</p>
                <p className="text-lg font-semibold" style={{ color: "var(--text-main)" }}>
                  {completedCount}/{checklist.length}
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Checklist */}
        <Checklist items={checklist} />

        {/* Tabs */}
        <div>
          {/* Tab bar */}
          <div
            className="flex overflow-x-auto gap-1 mb-4 pb-0.5"
            style={{ borderBottom: "1px solid var(--border-soft)" }}
          >
            {TABS.map((tab) => (
              <button
                key={tab.key}
                onClick={() => setActiveTab(tab.key)}
                className="px-3 py-2 text-sm font-medium whitespace-nowrap transition-all"
                style={
                  activeTab === tab.key
                    ? {
                        color: "var(--primary)",
                        borderBottom: "2px solid var(--primary)",
                        marginBottom: -1,
                      }
                    : { color: "var(--text-muted)" }
                }
              >
                {tab.label}
              </button>
            ))}
          </div>

          {/* Tab content */}
          {activeTab === "overview" && (
            <OverviewTab detail={detail} categories={categories} onUpdated={load} />
          )}
          {activeTab === "participants" && (
            <ParticipantsTab
              activityId={activityId}
              participants={detail.participants}
              onUpdated={load}
            />
          )}
          {activeTab === "report" && (
            <ReportTab activityId={activityId} detail={detail} onUpdated={load} />
          )}
          {activeTab === "fees" && (
            <ActivityFeeTab
              activityId={activityId}
              feeInfo={detail.activity_fee}
              onUpdated={load}
            />
          )}
          {activeTab === "receipts" && (
            <ReceiptsTab
              activityId={activityId}
              receipts={detail.receipts}
              onUpdated={load}
            />
          )}
          {activeTab === "files" && (
            <FileVaultTab activityId={activityId} onUpdated={load} />
          )}
          {activeTab === "ai" && (
            <AIWorkTab activityId={activityId} onUpdated={load} />
          )}
          {activeTab === "import" && (
            <ParticipantImportTab activityId={activityId} onUpdated={load} />
          )}
        </div>
      </div>
    </AppShell>
  );
}
