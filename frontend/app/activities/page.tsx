"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import {
  Activity,
  Calendar,
  ChevronRight,
  MapPin,
  Plus,
  Trash2,
  Users,
} from "lucide-react";

import { AppShell } from "@/components/layout/AppShell";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorState } from "@/components/ui/ErrorState";
import { Input } from "@/components/ui/Input";
import { LoadingState } from "@/components/ui/LoadingState";
import { Modal } from "@/components/ui/Modal";
import { PageHeader } from "@/components/ui/PageHeader";
import { Select } from "@/components/ui/Select";
import { StatusBadge } from "@/components/ui/StatusBadge";
import {
  type ActivityCategory,
  type ActivityCreate,
  type ActivitySummary,
  type Member,
  createActivity,
  deleteActivity,
  getActivities,
  getActivityCategoriesTyped,
  getMembersFiltered,
} from "@/lib/api";

const STATUS_FILTER_OPTIONS = [
  { value: "", label: "전체 상태" },
  { value: "planned", label: "예정" },
  { value: "in_progress", label: "진행 중" },
  { value: "done", label: "완료" },
  { value: "draft", label: "초안" },
  { value: "confirmed", label: "확정" },
  { value: "archived", label: "보관 포함" },
];

const STATUS_OPTIONS = [
  { value: "planned", label: "예정" },
  { value: "in_progress", label: "진행 중" },
  { value: "done", label: "완료" },
  { value: "draft", label: "초안" },
];

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

function feeStatusColor(s: string): string {
  if (s.includes("0/") || s === "미설정") return "var(--text-muted)";
  if (s.endsWith("납부") && s.startsWith("0")) return "var(--danger)";
  return "var(--success)";
}

// ─── Activity Card ────────────────────────────────────────────────────────────

interface ActivityCardProps {
  activity: ActivitySummary;
  categoryName: string;
  onDelete: (activity: ActivitySummary) => void;
  deleting: boolean;
}

function ActivityCard({ activity, onDelete, deleting }: ActivityCardProps) {
  return (
    <Link href={`/activities/${activity.id}`}>
      <div
        className="rounded-2xl p-5 cursor-pointer transition-all hover:shadow-card-hover h-full"
        style={{
          background: "var(--surface)",
          border: "1px solid var(--border-soft)",
          boxShadow: "0 1px 4px 0 rgba(31,31,36,0.05)",
        }}
      >
        {/* Top row */}
        <div className="flex items-start justify-between gap-2 mb-3">
          <StatusBadge status={activity.status} />
          <div className="flex items-center gap-2">
            {activity.category_name && (
              <span
                className="text-xs truncate max-w-[120px] shrink-0"
                style={{ color: "var(--text-muted)" }}
              >
                {activity.category_name}
              </span>
            )}
            <button
              type="button"
              aria-label="활동 삭제"
              disabled={deleting}
              onClick={(e) => {
                e.preventDefault();
                e.stopPropagation();
                onDelete(activity);
              }}
              className="rounded-lg p-1.5 transition-opacity hover:opacity-75 disabled:opacity-40"
              style={{ color: "var(--danger)", background: "var(--danger-soft)" }}
            >
              <Trash2 className="h-3.5 w-3.5" />
            </button>
          </div>
        </div>

        {/* Title */}
        <h3
          className="text-sm font-semibold leading-snug mb-2 line-clamp-2"
          style={{ color: "var(--text-main)" }}
        >
          {activity.title}
        </h3>

        {/* Meta */}
        <div className="flex flex-wrap items-center gap-3 mb-3">
          {activity.activity_date && (
            <span
              className="flex items-center gap-1 text-xs"
              style={{ color: "var(--text-muted)" }}
            >
              <Calendar className="h-3 w-3" />
              {activity.activity_date}
            </span>
          )}
          {activity.location && (
            <span
              className="flex items-center gap-1 text-xs"
              style={{ color: "var(--text-muted)" }}
            >
              <MapPin className="h-3 w-3" />
              {activity.location}
            </span>
          )}
        </div>

        {/* Stats row */}
        <div
          className="grid grid-cols-3 gap-2 rounded-xl p-3 mb-3"
          style={{ background: "var(--surface-soft)", border: "1px solid var(--border-soft)" }}
        >
          <div className="text-center">
            <p className="text-xs mb-0.5" style={{ color: "var(--text-muted)" }}>참여자</p>
            <p className="text-sm font-semibold" style={{ color: "var(--text-main)" }}>
              <Users className="h-3 w-3 inline mr-0.5" />
              {activity.participant_count}명
            </p>
          </div>
          <div className="text-center">
            <p className="text-xs mb-0.5" style={{ color: "var(--text-muted)" }}>보고서</p>
            <p className="text-sm font-semibold" style={{ color: "var(--text-main)" }}>
              {statusLabel(activity.report_status)}
            </p>
          </div>
          <div className="text-center">
            <p className="text-xs mb-0.5" style={{ color: "var(--text-muted)" }}>활동비</p>
            <p
              className="text-xs font-semibold"
              style={{ color: feeStatusColor(activity.activity_fee_status) }}
            >
              {activity.activity_fee_status}
            </p>
          </div>
        </div>

        {/* Footer */}
        <div
          className="pt-3 flex items-center justify-between"
          style={{ borderTop: "1px solid var(--border-soft)" }}
        >
          <div className="flex items-center gap-2">
            {activity.receipt_count > 0 && (
              <span className="text-xs rounded-full px-2 py-0.5"
                style={{ background: "var(--primary-soft)", color: "var(--primary)" }}>
                영수증 {activity.receipt_count}건
              </span>
            )}
            {activity.need_check_count > 0 && (
              <span className="text-xs rounded-full px-2 py-0.5"
                style={{ background: "var(--warning-soft)", color: "var(--warning)" }}>
                확인 필요 {activity.need_check_count}건
              </span>
            )}
          </div>
          <ChevronRight className="h-4 w-4" style={{ color: "var(--text-muted)" }} />
        </div>
      </div>
    </Link>
  );
}

// ─── Create Activity Modal ────────────────────────────────────────────────────

interface CreateModalProps {
  categories: ActivityCategory[];
  members: Member[];
  onClose: () => void;
  onCreated: (id: string) => void;
}

function CreateActivityModal({ categories, members, onClose, onCreated }: CreateModalProps) {
  const [title, setTitle] = useState("");
  const [categoryId, setCategoryId] = useState("");
  const [activityDate, setActivityDate] = useState("");
  const [location, setLocation] = useState("");
  const [description, setDescription] = useState("");
  const [participantIds, setParticipantIds] = useState<string[]>([]);
  const [status, setStatus] = useState("planned");
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  const categoryOptions = [
    { value: "", label: "카테고리 선택" },
    ...categories.map((c) => ({ value: c.id, label: c.name })),
  ];

  function toggleParticipant(id: string) {
    setParticipantIds((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id],
    );
  }

  async function handleSave() {
    if (!title.trim()) {
      setFormError("활동명은 필수입니다.");
      return;
    }
    setSaving(true);
    setFormError(null);
    try {
      const payload: ActivityCreate = {
        title: title.trim(),
        category_id: categoryId || null,
        activity_date: activityDate || null,
        location: location.trim() || null,
        description: description.trim() || null,
        participant_member_ids: participantIds,
        status,
      };
      const created = await createActivity(payload);
      onCreated(created.id);
    } catch (err: unknown) {
      setFormError(err instanceof Error ? err.message : "저장에 실패했습니다.");
      setSaving(false);
    }
  }

  return (
    <Modal isOpen onClose={onClose} title="새 활동 만들기" size="lg">
      <div className="space-y-4">
        <Input
          label="활동명 *"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="예: 5월 AI 스터디"
        />
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <Select
            label="카테고리"
            options={categoryOptions}
            value={categoryId}
            onChange={(e) => setCategoryId(e.target.value)}
          />
          <Select
            label="활동 상태"
            options={STATUS_OPTIONS}
            value={status}
            onChange={(e) => setStatus(e.target.value)}
          />
          <Input
            label="활동일"
            type="date"
            value={activityDate}
            onChange={(e) => setActivityDate(e.target.value)}
          />
          <Input
            label="장소"
            value={location}
            onChange={(e) => setLocation(e.target.value)}
            placeholder="동아리방"
          />
        </div>
        <div>
          <label className="block text-sm font-medium mb-1.5" style={{ color: "var(--text-main)" }}>
            설명
          </label>
          <textarea
            className="w-full rounded-xl px-3 py-2 text-sm focus:outline-none"
            style={{
              background: "var(--surface)",
              color: "var(--text-main)",
              border: "1px solid var(--border-soft)",
              minHeight: 72,
              resize: "vertical",
            }}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="활동 설명 (선택)"
          />
        </div>

        {/* Participant selection */}
        {members.length > 0 && (
          <div>
            <p className="text-sm font-medium mb-2" style={{ color: "var(--text-main)" }}>
              참여자 선택 ({participantIds.length}명 선택됨)
            </p>
            <div
              className="rounded-xl p-3 max-h-48 overflow-y-auto"
              style={{ background: "var(--surface-soft)", border: "1px solid var(--border-soft)" }}
            >
              <div className="grid gap-1.5 sm:grid-cols-2">
                {members.map((m) => (
                  <label
                    key={m.id}
                    className="flex items-center gap-2 rounded-lg px-2 py-1.5 cursor-pointer transition-colors hover:bg-white"
                  >
                    <input
                      type="checkbox"
                      checked={participantIds.includes(m.id)}
                      onChange={() => toggleParticipant(m.id)}
                      className="h-4 w-4 rounded"
                    />
                    <span className="text-sm" style={{ color: "var(--text-main)" }}>
                      {m.name}
                      {m.student_id && (
                        <span className="ml-1 text-xs" style={{ color: "var(--text-muted)" }}>
                          ({m.student_id})
                        </span>
                      )}
                    </span>
                  </label>
                ))}
              </div>
            </div>
          </div>
        )}

        {formError && (
          <p className="text-sm" style={{ color: "var(--danger)" }}>{formError}</p>
        )}
        <div className="flex justify-end gap-2 pt-2">
          <Button variant="secondary" onClick={onClose} disabled={saving}>
            취소
          </Button>
          <Button onClick={handleSave} loading={saving}>
            활동 만들기
          </Button>
        </div>
      </div>
    </Modal>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function ActivitiesPage() {
  const [activities, setActivities] = useState<ActivitySummary[]>([]);
  const [categories, setCategories] = useState<ActivityCategory[]>([]);
  const [members, setMembers] = useState<Member[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [categoryFilter, setCategoryFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [showCreate, setShowCreate] = useState(false);
  const [redirectTo, setRedirectTo] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [data, cats, mems] = await Promise.all([
        getActivities({
          category_id: categoryFilter || undefined,
          status: statusFilter || undefined,
          q: search || undefined,
        }),
        getActivityCategoriesTyped(),
        getMembersFiltered({ status: "active" }),
      ]);
      // default: exclude archived unless specifically selected
      const filtered = statusFilter === ""
        ? data.filter((a) => a.status !== "archived")
        : data;
      setActivities(filtered);
      setCategories(cats);
      setMembers(mems);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "데이터를 불러오지 못했습니다.");
    } finally {
      setLoading(false);
    }
  }, [search, categoryFilter, statusFilter]);

  useEffect(() => { load(); }, [load]);

  // Redirect after creation
  useEffect(() => {
    if (redirectTo) {
      window.location.href = `/activities/${redirectTo}`;
    }
  }, [redirectTo]);

  const categoryMap = Object.fromEntries(categories.map((c) => [c.id, c.name]));
  const categoryFilterOptions = [
    { value: "", label: "전체 카테고리" },
    ...categories.map((c) => ({ value: c.id, label: c.name })),
  ];

  async function handleDelete(activity: ActivitySummary) {
    const ok = window.confirm(
      "이 활동을 삭제하시겠습니까?\n참여자, 파일, 납부 기록은 복구를 위해 보관되지만 활동 목록에서는 보이지 않습니다.",
    );
    if (!ok) return;
    setDeletingId(activity.id);
    setError(null);
    try {
      await deleteActivity(activity.id);
      setActivities((prev) => prev.filter((a) => a.id !== activity.id));
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "활동 삭제에 실패했습니다.");
    } finally {
      setDeletingId(null);
    }
  }

  return (
    <AppShell>
      <div className="space-y-6">
        <PageHeader
          title="활동 관리"
          description="활동을 만들고 참여자, 보고서, 활동비, 증빙을 한 곳에서 관리하세요."
          action={
            <Button onClick={() => setShowCreate(true)}>
              <Plus className="h-4 w-4" />
              새 활동 만들기
            </Button>
          }
        />

        {/* Filters */}
        <div className="flex flex-wrap gap-3">
          <Input
            placeholder="활동명 / 장소 검색"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-56"
          />
          <Select
            options={categoryFilterOptions}
            value={categoryFilter}
            onChange={(e) => setCategoryFilter(e.target.value)}
            className="w-44"
          />
          <Select
            options={STATUS_FILTER_OPTIONS}
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="w-36"
          />
        </div>

        {/* Content */}
        {loading ? (
          <LoadingState />
        ) : error ? (
          <ErrorState message={error} onRetry={load} />
        ) : activities.length === 0 ? (
          <EmptyState
            message="아직 활동이 없습니다."
            description="새 활동 만들기 버튼으로 첫 활동을 시작하세요."
            action={
              <Button size="sm" onClick={() => setShowCreate(true)}>
                <Plus className="h-3.5 w-3.5" />
                새 활동 만들기
              </Button>
            }
          />
        ) : (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {activities.map((a) => (
              <ActivityCard
                key={a.id}
                activity={a}
                categoryName={a.category_id ? (categoryMap[a.category_id] ?? "") : ""}
                onDelete={handleDelete}
                deleting={deletingId === a.id}
              />
            ))}
          </div>
        )}
      </div>

      {/* Create Modal */}
      {showCreate && (
        <CreateActivityModal
          categories={categories}
          members={members}
          onClose={() => setShowCreate(false)}
          onCreated={(id) => {
            setShowCreate(false);
            setRedirectTo(id);
          }}
        />
      )}
    </AppShell>
  );
}
