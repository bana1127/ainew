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
  type ActivityFeeRecord,
  type ActivityParticipantInfo,
  type Member,
  type Receipt,
  type AssistantExecuteResponse,
  type ActivityDraftInfo,
  addActivityParticipant,
  generateActivityFees,
  getActivityDetail,
  getActivityCategoriesTyped,
  getMembersFiltered,
  getReceiptsTyped,
  linkReceiptToActivity,
  removeActivityParticipant,
  updateActivity,
  updateActivityFeeRecord,
  updateActivityReport,
  generateActivityReportDraft,
  executeAssistant,
  type ActivityReportGenerateRequest,
  type ActivityCategory,
} from "@/lib/api";
import { AssistantResultCard } from "@/components/assistant/AssistantResultCard";
import { nanoid } from "nanoid";

type TabKey = "overview" | "participants" | "report" | "fees" | "receipts" | "attachments" | "ai";

const TABS: { key: TabKey; label: string }[] = [
  { key: "overview", label: "개요" },
  { key: "participants", label: "참여자" },
  { key: "report", label: "보고서" },
  { key: "fees", label: "활동비" },
  { key: "receipts", label: "증빙" },
  { key: "attachments", label: "첨부" },
  { key: "ai", label: "AI 작업" },
];

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

  useEffect(() => {
    if (showAdd) {
      getMembersFiltered({ status: "active" }).then(setAllMembers).catch(() => {});
    }
  }, [showAdd]);

  const participantMemberIds = new Set(participants.map((p) => p.member_id));
  const availableMembers = allMembers.filter((m) => !participantMemberIds.has(m.id));

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
                      <Link href={`/members/${p.member_id}`} className="hover:underline">
                        {p.name ?? "-"}
                      </Link>
                    </td>
                    <td className="px-4 py-3 text-xs" style={{ color: "var(--text-muted)" }}>{p.student_id ?? "-"}</td>
                    <td className="px-4 py-3 text-xs" style={{ color: "var(--text-muted)" }}>{p.department ?? "-"}</td>
                    <td className="px-4 py-3 text-xs" style={{ color: "var(--text-muted)" }}>{p.role ?? "participant"}</td>
                    <td className="px-4 py-3">
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => handleRemove(p.member_id)}
                        disabled={removing === p.member_id}
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </Button>
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
                  <Link href={`/members/${p.member_id}`}>
                    <p className="font-medium text-sm hover:underline" style={{ color: "var(--text-main)" }}>
                      {p.name ?? "-"}
                    </p>
                  </Link>
                  <p className="text-xs mt-0.5" style={{ color: "var(--text-muted)" }}>
                    {p.student_id ?? ""} {p.department ? `· ${p.department}` : ""}
                  </p>
                </div>
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => handleRemove(p.member_id)}
                  disabled={removing === p.member_id}
                >
                  <X className="h-3.5 w-3.5" />
                </Button>
              </div>
            ))}
          </div>
        </>
      )}

      {/* Add Participant Modal */}
      {showAdd && (
        <Modal isOpen onClose={() => setShowAdd(false)} title="참여자 추가">
          <div className="space-y-4">
            {availableMembers.length === 0 ? (
              <p className="text-sm" style={{ color: "var(--text-muted)" }}>
                추가할 수 있는 활동 중인 부원이 없습니다.
              </p>
            ) : (
              <div>
                <label className="block text-xs font-medium mb-1.5" style={{ color: "var(--text-muted)" }}>
                  부원 선택
                </label>
                <select
                  className="w-full rounded-xl px-3 py-2 text-sm focus:outline-none min-h-[44px]"
                  style={{ background: "var(--surface)", color: "var(--text-main)", border: "1px solid var(--border-soft)" }}
                  value={selectedId}
                  onChange={(e) => setSelectedId(e.target.value)}
                >
                  <option value="">-- 부원 선택 --</option>
                  {availableMembers.map((m) => (
                    <option key={m.id} value={m.id}>
                      {m.name} {m.student_id ? `(${m.student_id})` : ""}
                    </option>
                  ))}
                </select>
              </div>
            )}
            {actionError && <p className="text-sm" style={{ color: "var(--danger)" }}>{actionError}</p>}
            <div className="flex gap-2">
              <Button onClick={handleAdd} loading={adding} disabled={!selectedId}>추가</Button>
              <Button variant="secondary" onClick={() => setShowAdd(false)}>취소</Button>
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
        participant_ids: detail.participants.map((p) => p.member_id),
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
    try {
      await updateActivityReport(activityId, { final_content: editContent });
      setEditing(false);
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
          <h3 className="text-sm font-semibold" style={{ color: "var(--text-main)" }}>활동 보고서</h3>
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
    </Card>
  );
}

// ─── Activity Fees Tab ────────────────────────────────────────────────────────

function FeesTab({
  activityId,
  feeInfo,
  onUpdated,
}: {
  activityId: string;
  feeInfo: ActivityDetail["activity_fee"];
  onUpdated: () => void;
}) {
  const [feeAmount, setFeeAmount] = useState(feeInfo.amount || 10000);
  const [generating, setGenerating] = useState(false);
  const [genResult, setGenResult] = useState<string | null>(null);
  const [genError, setGenError] = useState<string | null>(null);
  const [editingRecord, setEditingRecord] = useState<ActivityFeeRecord | null>(null);
  const [editPaid, setEditPaid] = useState(0);
  const [editStatus, setEditStatus] = useState("unpaid");
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  async function handleGenerate() {
    setGenerating(true);
    setGenError(null);
    setGenResult(null);
    try {
      const result = await generateActivityFees(activityId, feeAmount);
      setGenResult(`완료: ${result.created}건 생성, ${result.skipped}건 건너뜀`);
      onUpdated();
    } catch (err: unknown) {
      setGenError(err instanceof Error ? err.message : "생성에 실패했습니다.");
    } finally {
      setGenerating(false);
    }
  }

  function openEdit(record: ActivityFeeRecord) {
    setEditingRecord(record);
    setEditPaid(record.paid_amount);
    setEditStatus(record.status);
    setSaveError(null);
  }

  async function handleSaveEdit() {
    if (!editingRecord) return;
    setSaving(true);
    setSaveError(null);
    try {
      await updateActivityFeeRecord(activityId, editingRecord.id, {
        paid_amount: editPaid,
        status: editStatus,
      });
      setEditingRecord(null);
      onUpdated();
    } catch (err: unknown) {
      setSaveError(err instanceof Error ? err.message : "저장에 실패했습니다.");
    } finally {
      setSaving(false);
    }
  }

  const paidCount = feeInfo.records.filter((r) => r.status === "paid").length;
  const unpaidCount = feeInfo.records.filter((r) => r.status === "unpaid").length;

  return (
    <div className="space-y-4">
      {/* Fee setup */}
      <Card padding="lg">
        <h3 className="text-sm font-semibold mb-4" style={{ color: "var(--text-main)" }}>활동비 설정</h3>
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
            활동비 대상 생성 / 갱신
          </Button>
        </div>
        {genResult && (
          <p className="mt-3 text-sm" style={{ color: "var(--success)" }}>{genResult}</p>
        )}
        {genError && (
          <p className="mt-3 text-sm" style={{ color: "var(--danger)" }}>{genError}</p>
        )}
        <p className="mt-2 text-xs" style={{ color: "var(--text-muted)" }}>
          참여자 탭에 등록된 부원을 대상으로 납부 대상을 생성합니다. 이미 납부/부분납부/면제 상태인 기록은 덮어쓰지 않습니다.
        </p>
      </Card>

      {/* Fee summary */}
      {feeInfo.records.length > 0 && (
        <Card padding="lg">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-semibold" style={{ color: "var(--text-main)" }}>
              납부 현황 ({feeInfo.total_count}명)
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
                  {["이름", "학번", "필요 금액", "납부 금액", "상태", "수정"].map((h) => (
                    <th key={h} className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide"
                      style={{ color: "var(--text-muted)" }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {feeInfo.records.map((r) => (
                  <tr key={r.id} style={{ borderBottom: "1px solid var(--border-soft)" }}
                    onMouseEnter={(e) => (e.currentTarget.style.background = "var(--surface-soft)")}
                    onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}>
                    <td className="px-4 py-3 font-medium" style={{ color: "var(--text-main)" }}>{r.member_name ?? "-"}</td>
                    <td className="px-4 py-3 text-xs" style={{ color: "var(--text-muted)" }}>{r.student_id ?? "-"}</td>
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
          <div className="md:hidden space-y-2">
            {feeInfo.records.map((r) => (
              <div key={r.id} className="rounded-xl p-3"
                style={{ border: "1px solid var(--border-soft)", background: "var(--surface-soft)" }}>
                <div className="flex items-center justify-between">
                  <div>
                    <p className="font-medium text-sm" style={{ color: "var(--text-main)" }}>{r.member_name ?? "-"}</p>
                    {r.student_id && <p className="text-xs" style={{ color: "var(--text-muted)" }}>{r.student_id}</p>}
                  </div>
                  <StatusBadge status={r.status} />
                </div>
                <div className="flex items-center justify-between mt-2">
                  <p className="text-xs" style={{ color: "var(--text-muted)" }}>
                    필요: {fmt(r.required_amount)}원 / 납부: {fmt(r.paid_amount)}원
                  </p>
                  <Button size="sm" variant="ghost" onClick={() => openEdit(r)}>수정</Button>
                </div>
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* Edit modal */}
      {editingRecord && (
        <Modal isOpen onClose={() => setEditingRecord(null)} title="납부 상태 직접 수정">
          <div className="space-y-4">
            <div
              className="rounded-xl p-3 text-sm"
              style={{ background: "var(--surface-soft)", border: "1px solid var(--border-soft)" }}
            >
              <p className="font-medium" style={{ color: "var(--text-main)" }}>
                {editingRecord.member_name}
                {editingRecord.student_id && (
                  <span className="ml-1.5 text-xs font-normal" style={{ color: "var(--text-muted)" }}>
                    ({editingRecord.student_id})
                  </span>
                )}
              </p>
            </div>
            <div>
              <label className="block text-xs font-medium mb-1" style={{ color: "var(--text-muted)" }}>납부 상태</label>
              <select
                className="w-full rounded-xl px-3 py-2 text-sm focus:outline-none min-h-[44px]"
                style={{ background: "var(--surface)", color: "var(--text-main)", border: "1px solid var(--border-soft)" }}
                value={editStatus}
                onChange={(e) => setEditStatus(e.target.value)}
              >
                <option value="unpaid">미납</option>
                <option value="paid">납부 완료</option>
                <option value="partial">부분 납부</option>
                <option value="need_check">확인 필요</option>
                <option value="exempt">면제</option>
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium mb-1" style={{ color: "var(--text-muted)" }}>납부 금액 (원)</label>
              <input
                type="number"
                className="w-full rounded-xl px-3 py-2 text-sm focus:outline-none min-h-[44px]"
                style={{ background: "var(--surface)", color: "var(--text-main)", border: "1px solid var(--border-soft)" }}
                value={editPaid}
                onChange={(e) => setEditPaid(Number(e.target.value))}
              />
            </div>
            {saveError && <p className="text-sm" style={{ color: "var(--danger)" }}>{saveError}</p>}
            <div className="flex gap-2">
              <Button className="flex-1 min-h-[44px]" onClick={handleSaveEdit} loading={saving}>저장</Button>
              <Button className="flex-1 min-h-[44px]" variant="secondary" onClick={() => setEditingRecord(null)} disabled={saving}>취소</Button>
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
}

// ─── Receipts Tab ─────────────────────────────────────────────────────────────

function ReceiptsTab({
  activityId,
  receipts,
  onUpdated,
}: {
  activityId: string;
  receipts: ActivityDetail["receipts"];
  onUpdated: () => void;
}) {
  const [allReceipts, setAllReceipts] = useState<Receipt[]>([]);
  const [showLink, setShowLink] = useState(false);
  const [linking, setLinking] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  async function loadAll() {
    try {
      const data = await getReceiptsTyped({ limit: 100 });
      setAllReceipts(data);
    } catch { /* ignore */ }
  }

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
    } catch (err: unknown) {
      setActionError(err instanceof Error ? err.message : "연결 해제에 실패했습니다.");
    } finally {
      setLinking(null);
    }
  }

  return (
    <Card padding="none">
      <div
        className="p-4 flex items-center justify-between"
        style={{ borderBottom: "1px solid var(--border-soft)" }}
      >
        <h3 className="text-sm font-semibold" style={{ color: "var(--text-main)" }}>
          영수증/증빙 ({receipts.length}건)
        </h3>
        <div className="flex gap-2">
          <Button size="sm" variant="secondary" onClick={() => setShowLink(true)}>
            <Plus className="h-3.5 w-3.5" />
            기존 영수증 연결
          </Button>
          <Link href="/receipts">
            <Button size="sm" variant="ghost">
              영수증 업로드
            </Button>
          </Link>
        </div>
      </div>

      {actionError && (
        <div className="p-4"><ErrorState message={actionError} /></div>
      )}

      {receipts.length === 0 ? (
        <EmptyState
          message="연결된 영수증이 없습니다."
          description="영수증 업로드 후 이 활동에 연결하세요."
        />
      ) : (
        <div className="divide-y" style={{ borderTop: "1px solid var(--border-soft)" }}>
          {receipts.map((r) => (
            <div key={r.id} className="p-4 flex items-center justify-between gap-3">
              <div className="flex-1 min-w-0">
                <p className="font-medium text-sm" style={{ color: "var(--text-main)" }}>
                  {r.store_name ?? "(상호명 없음)"}
                  {r.amount > 0 && (
                    <span className="ml-2 text-xs" style={{ color: "var(--text-muted)" }}>
                      {fmt(r.amount)}원
                    </span>
                  )}
                </p>
                <div className="flex flex-wrap items-center gap-2 mt-0.5">
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
                </div>
              </div>
              <Button
                size="sm"
                variant="ghost"
                onClick={() => handleUnlink(r.id)}
                disabled={linking === r.id}
              >
                연결 해제
              </Button>
            </div>
          ))}
        </div>
      )}

      {/* Link receipt modal */}
      {showLink && (
        <Modal isOpen onClose={() => setShowLink(false)} title="기존 영수증 연결">
          <div className="space-y-3">
            {unlinkable.length === 0 ? (
              <p className="text-sm" style={{ color: "var(--text-muted)" }}>
                연결할 수 있는 영수증이 없습니다. 먼저 영수증을 업로드하세요.
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
    </Card>
  );
}

// ─── Attachments Tab ──────────────────────────────────────────────────────────

function AttachmentsTab() {
  return (
    <Card padding="lg">
      <h3 className="text-sm font-semibold mb-3" style={{ color: "var(--text-main)" }}>
        첨부 자료
      </h3>
      <p className="text-sm" style={{ color: "var(--text-muted)" }}>
        사진, PDF, 활동 자료를 업로드할 수 있습니다. 업로드된 파일은 보고서 생성에 활용됩니다.
      </p>
      <div className="mt-4">
        <Link href="/assistant">
          <Button variant="secondary" size="sm">
            AI 작업실에서 파일 업로드
          </Button>
        </Link>
      </div>
    </Card>
  );
}

// ─── AI Work Tab ──────────────────────────────────────────────────────────────

type AIRun = {
  id: string;
  requestMessage: string;
  response: AssistantExecuteResponse;
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
      // Refresh activity detail after AI work
      if (res.result_type !== "error") {
        setTimeout(() => onUpdated(), 800);
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
              status={run.response.result_type === "error" ? "failed" : run.response.requires_confirmation ? "preview" : "applied"}
              requestMessage={run.requestMessage}
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

  const load = useCallback(async () => {
    if (!activityId) return;
    setLoading(true);
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
            <FeesTab
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
          {activeTab === "attachments" && <AttachmentsTab />}
          {activeTab === "ai" && (
            <AIWorkTab activityId={activityId} onUpdated={load} />
          )}
        </div>
      </div>
    </AppShell>
  );
}
