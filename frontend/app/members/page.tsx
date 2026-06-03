"use client";

import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";
import { ChevronDown, ChevronUp, Plus, Upload, X } from "lucide-react";

import { AppShell } from "@/components/layout/AppShell";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorState } from "@/components/ui/ErrorState";
import { Input } from "@/components/ui/Input";
import { LoadingState } from "@/components/ui/LoadingState";
import { Modal } from "@/components/ui/Modal";
import { PageHeader } from "@/components/ui/PageHeader";
import { Select } from "@/components/ui/Select";
import { StatusBadge } from "@/components/ui/StatusBadge";
import {
  type Member,
  type MemberCreate,
  type MemberImportPreviewOut,
  confirmAssistantAction,
  createMember,
  deactivateMember,
  restoreMember,
  getMembersFiltered,
  previewMemberImport,
  updateMember,
} from "@/lib/api";

const STATUS_OPTIONS = [
  { value: "active", label: "활동중" },
  { value: "inactive", label: "비활성" },
  { value: "graduated", label: "졸업" },
  { value: "paused", label: "휴면" },
];


const ROLE_OPTIONS = [
  { value: "", label: "전체" },
  { value: "__officer__", label: "임원 전체" },
  { value: "president", label: "회장" },
  { value: "vice_president", label: "부회장" },
  { value: "officer", label: "임원" },
  { value: "__regular__", label: "일반 부원" },
];

const ROLE_EDIT_OPTIONS = [
  { value: "president", label: "회장" },
  { value: "vice_president", label: "부회장" },
  { value: "officer", label: "임원" },
];

const ROLE_BADGE_STYLE: Record<string, { label: string; bg: string; color: string }> = {
  president: { label: "회장", bg: "#7C6CF233", color: "var(--primary)" },
  vice_president: { label: "부회장", bg: "#3F7D5833", color: "var(--success)" },
  officer: { label: "임원", bg: "#5A7FAA33", color: "#5A7FAA" },
};

type OfficerRole = "president" | "vice_president" | "officer";

function normalizeOfficerRole(member: Pick<Member, "is_officer" | "is_executive" | "officer_role" | "role">): OfficerRole | null {
  if (member.officer_role) return member.officer_role;
  if (member.role === "회장" || member.role === "president") return "president";
  if (member.role === "부회장" || member.role === "vice_president") return "vice_president";
  if (member.is_officer || member.is_executive || member.role) return "officer";
  return null;
}

type FormData = {
  name: string;
  student_id: string;
  department: string;
  phone: string;
  email: string;
  status: string;
  memo: string;
  is_officer: boolean;
  officer_role: OfficerRole;
};

const emptyForm: FormData = {
  name: "", student_id: "", department: "", phone: "", email: "",
  status: "active", memo: "", is_officer: false, officer_role: "officer",
};

function memberToForm(m: Member): FormData {
  return {
    name: m.name,
    student_id: m.student_id ?? "",
    department: m.department ?? "",
    phone: m.phone ?? "",
    email: m.email ?? "",
    status: m.status,
    memo: m.memo ?? "",
    is_officer: m.is_officer ?? m.is_executive,
    officer_role: normalizeOfficerRole(m) ?? "officer",
  };
}

function RoleBadge({ role }: { role: OfficerRole | null | undefined }) {
  if (!role) return <span className="text-xs" style={{ color: "var(--text-muted)" }}>일반</span>;
  const s = ROLE_BADGE_STYLE[role];
  if (!s) return null;
  return (
    <span className="px-1.5 py-0.5 rounded text-xs font-semibold"
      style={{ background: s.bg, color: s.color }}>
      {s.label}
    </span>
  );
}

const ACTION_BADGE: Record<string, { label: string; color: string }> = {
  new_member: { label: "신규", color: "var(--primary)" },
  update_existing: { label: "업데이트", color: "var(--success)" },
  duplicate_candidate: { label: "중복 후보", color: "var(--warning)" },
  needs_review: { label: "검토 필요", color: "var(--warning)" },
  invalid: { label: "건너뜀", color: "var(--text-muted)" },
};

export default function MembersPage() {
  const fileRef = useRef<HTMLInputElement>(null);

  const [members, setMembers] = useState<Member[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [showInactive, setShowInactive] = useState(false);
  const [roleFilter, setRoleFilter] = useState("");
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingMember, setEditingMember] = useState<Member | null>(null);
  const [form, setForm] = useState<FormData>(emptyForm);
  const [formError, setFormError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [confirmTarget, setConfirmTarget] = useState<Member | null>(null);
  const [confirmLoading, setConfirmLoading] = useState(false);

  // Upload / import state
  const [importFile, setImportFile] = useState<File | null>(null);
  const [importing, setImporting] = useState(false);
  const [importPreview, setImportPreview] = useState<MemberImportPreviewOut | null>(null);
  const [importError, setImportError] = useState<string | null>(null);
  const [applying, setApplying] = useState(false);
  const [applyResult, setApplyResult] = useState<{ created: number; updated: number } | null>(null);
  const [showUpload, setShowUpload] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params: Parameters<typeof getMembersFiltered>[0] = {
        status: showInactive ? undefined : "active",
        q: search || undefined,
        limit: 200,
      };
      if (roleFilter === "__officer__") {
        params.is_officer = true;
      } else if (roleFilter === "__regular__") {
        params.is_officer = false;
      } else if (roleFilter) {
        params.officer_role = roleFilter;
      }
      const data = await getMembersFiltered(params);
      setMembers(data);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "데이터를 불러오지 못했습니다.");
    } finally {
      setLoading(false);
    }
  }, [search, showInactive, roleFilter]);

  useEffect(() => { load(); }, [load]);

  function openCreate() {
    setEditingMember(null);
    setForm(emptyForm);
    setFormError(null);
    setIsModalOpen(true);
  }

  function openEdit(member: Member) {
    setEditingMember(member);
    setForm(memberToForm(member));
    setFormError(null);
    setIsModalOpen(true);
  }

  async function handleSave() {
    if (!form.name.trim()) {
      setFormError("이름은 필수입니다.");
      return;
    }
    setSaving(true);
    setFormError(null);
    try {
      const payload: MemberCreate = {
        name: form.name.trim(),
        student_id: form.student_id.trim() || null,
        department: form.department.trim() || null,
        phone: form.phone.trim() || null,
        email: form.email.trim() || null,
        status: form.status,
        memo: form.memo.trim() || null,
        is_officer: form.is_officer,
        officer_role: form.is_officer ? form.officer_role : null,
        is_executive: form.is_officer,
        role: form.is_officer ? ROLE_BADGE_STYLE[form.officer_role].label : null,
      };
      if (editingMember) {
        await updateMember(editingMember.id, payload);
      } else {
        await createMember(payload);
      }
      setIsModalOpen(false);
      load();
    } catch (err: unknown) {
      setFormError(err instanceof Error ? err.message : "저장에 실패했습니다.");
    } finally {
      setSaving(false);
    }
  }

  async function handleDeactivate() {
    if (!confirmTarget) return;
    setConfirmLoading(true);
    try {
      await deactivateMember(confirmTarget.id);
      setConfirmTarget(null);
      load();
    } catch {
      // silently ignore
    } finally {
      setConfirmLoading(false);
    }
  }

  async function handleRestore(id: string) {
    try {
      await restoreMember(id);
      load();
    } catch {
      // silently ignore
    }
  }

  // ── Import ──────────────────────────────────────────────────────────────

  async function handleImportPreview() {
    if (!importFile) return;
    setImporting(true);
    setImportError(null);
    setImportPreview(null);
    setApplyResult(null);
    try {
      const preview = await previewMemberImport(importFile);
      setImportPreview(preview);
    } catch (err: unknown) {
      setImportError(err instanceof Error ? err.message : "파일 분석 중 오류가 발생했습니다.");
    } finally {
      setImporting(false);
    }
  }

  async function handleImportConfirm() {
    if (!importPreview?.action_id) return;
    setApplying(true);
    try {
      const result = await confirmAssistantAction(importPreview.action_id);
      const r = result.result as { created_members?: number; updated_members?: number } | undefined;
      setApplyResult({ created: r?.created_members ?? 0, updated: r?.updated_members ?? 0 });
      setImportPreview(null);
      setImportFile(null);
      load();
    } catch (err: unknown) {
      setImportError(err instanceof Error ? err.message : "반영 중 오류가 발생했습니다.");
    } finally {
      setApplying(false);
    }
  }

  function handleImportCancel() {
    setImportPreview(null);
    setImportFile(null);
    setImportError(null);
    setApplyResult(null);
  }

  return (
    <AppShell>
      <div className="space-y-6">
        <PageHeader
          title="부원 관리"
          description="부원 명부를 등록·수정·관리합니다."
          action={
            <div className="flex gap-2">
              <Button variant="secondary" onClick={() => setShowUpload((v) => !v)}>
                <Upload className="h-4 w-4" />
                명단 업로드
              </Button>
              <Button onClick={openCreate}>
                <Plus className="h-4 w-4" />
                부원 추가
              </Button>
            </div>
          }
        />

        {/* ── 부원 명단 업로드 섹션 ─────────────────────────────────── */}
        {showUpload && (
          <Card padding="lg">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-sm font-semibold" style={{ color: "var(--text-main)" }}>
                부원 명단 업로드
              </h3>
              <button onClick={() => { setShowUpload(false); handleImportCancel(); }}
                className="text-xs hover:opacity-70" style={{ color: "var(--text-muted)" }}>
                <X className="h-4 w-4" />
              </button>
            </div>

            <div className="text-xs mb-4 rounded-xl px-3 py-2"
              style={{ background: "var(--warning-soft)", color: "var(--warning)", border: "1px solid rgba(185,130,43,0.15)" }}>
              부원 명단 업로드는 확인 후 반영됩니다. 미리보기를 확인한 뒤 반영 버튼을 누르세요.
              활동 참가자 파일은 여기에 올리지 마세요.
            </div>

            {!importPreview && !applyResult && (
              <div className="flex flex-col sm:flex-row gap-3 items-start">
                <input
                  ref={fileRef}
                  type="file"
                  accept=".xls,.xlsx,.csv"
                  className="hidden"
                  onChange={(e) => setImportFile(e.target.files?.[0] ?? null)}
                />
                <div
                  className="flex-1 flex items-center gap-3 rounded-xl px-4 py-3 cursor-pointer hover:opacity-80 transition-opacity"
                  style={{ border: "2px dashed var(--border-soft)", background: "var(--surface-soft)" }}
                  onClick={() => fileRef.current?.click()}
                >
                  <Upload className="h-4 w-4" style={{ color: "var(--primary)" }} />
                  <span className="text-sm" style={{ color: "var(--text-muted)" }}>
                    {importFile ? importFile.name : "엑셀/CSV 파일 선택"}
                  </span>
                </div>
                <Button onClick={handleImportPreview} loading={importing} disabled={!importFile || importing}>
                  미리보기
                </Button>
              </div>
            )}

            {importError && (
              <div className="mt-3">
                <ErrorState message={importError} onRetry={() => setImportError(null)} />
              </div>
            )}

            {applyResult && (
              <div className="rounded-xl p-4 mt-3"
                style={{ background: "var(--success-soft)", border: "1px solid rgba(63,125,88,0.15)" }}>
                <p className="text-sm font-semibold" style={{ color: "var(--success)" }}>
                  반영 완료 — 신규 {applyResult.created}명 추가, {applyResult.updated}명 업데이트
                </p>
                <button className="mt-2 text-xs hover:opacity-75" style={{ color: "var(--success)" }}
                  onClick={() => { setApplyResult(null); setShowUpload(false); }}>
                  닫기
                </button>
              </div>
            )}

            {importPreview && (
              <div className="mt-4 space-y-4">
                {/* Summary */}
                <div className="grid grid-cols-3 sm:grid-cols-6 gap-2">
                  {[
                    ["전체", importPreview.summary.total_rows],
                    ["신규", importPreview.summary.new_members],
                    ["업데이트", importPreview.summary.updates],
                    ["중복 후보", importPreview.summary.duplicate_candidates],
                    ["검토 필요", importPreview.summary.needs_review],
                    ["건너뜀", importPreview.summary.invalid_rows],
                  ].map(([label, value]) => (
                    <div key={label} className="rounded-xl p-3 text-center"
                      style={{ background: "var(--surface-soft)", border: "1px solid var(--border-soft)" }}>
                      <p className="text-xs" style={{ color: "var(--text-muted)" }}>{label}</p>
                      <p className="text-sm font-semibold" style={{ color: "var(--text-main)" }}>{value}</p>
                    </div>
                  ))}
                </div>

                {/* Preview table — shows Oui Parfum extended columns when present */}
                <div className="overflow-x-auto rounded-xl" style={{ border: "1px solid var(--border-soft)" }}>
                  <table className="min-w-full text-xs whitespace-nowrap">
                    <thead>
                      <tr style={{ background: "var(--surface-soft)", borderBottom: "1px solid var(--border-soft)" }}>
                        {["행", "이름", "성별", "학과", "학년", "학번", "출생년도", "전화번호", "가입 시기", "직위", "처리 예정", "사유"].map((h) => (
                          <th key={h} className="px-3 py-2 text-left font-medium"
                            style={{ color: "var(--text-muted)" }}>{h}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {importPreview.rows.slice(0, 50).map((r) => {
                        const badge = ACTION_BADGE[r.action] ?? { label: r.action, color: "var(--text-muted)" };
                        return (
                          <tr key={r.row_index} style={{ borderBottom: "1px solid var(--border-soft)" }}>
                            <td className="px-3 py-2" style={{ color: "var(--text-muted)" }}>{r.row_index}</td>
                            <td className="px-3 py-2 font-medium" style={{ color: "var(--text-main)" }}>{r.name ?? "-"}</td>
                            <td className="px-3 py-2" style={{ color: "var(--text-muted)" }}>{r.gender ?? "-"}</td>
                            <td className="px-3 py-2" style={{ color: "var(--text-muted)" }}>{r.department ?? "-"}</td>
                            <td className="px-3 py-2" style={{ color: "var(--text-muted)" }}>{r.grade ?? "-"}</td>
                            <td className="px-3 py-2" style={{ color: "var(--text-muted)" }}>{r.student_id ?? "-"}</td>
                            <td className="px-3 py-2" style={{ color: "var(--text-muted)" }}>{r.birth_year ?? "-"}</td>
                            <td className="px-3 py-2" style={{ color: "var(--text-muted)" }}>{r.phone ?? "-"}</td>
                            <td className="px-3 py-2" style={{ color: "var(--text-muted)" }}>{r.joined_term ?? "-"}</td>
                            <td className="px-3 py-2">
                              <RoleBadge role={(r.officer_role ?? (r.is_executive ? "officer" : null)) as OfficerRole | null} />
                            </td>
                            <td className="px-3 py-2">
                              <span className="px-2 py-0.5 rounded-full text-xs font-medium"
                                style={{ background: `${badge.color}22`, color: badge.color }}>
                                {badge.label}
                              </span>
                            </td>
                            <td className="px-3 py-2 max-w-xs" style={{ color: "var(--text-muted)" }}>
                              <span className="line-clamp-1">{r.reason}</span>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                  {importPreview.rows.length > 50 && (
                    <p className="text-xs px-4 py-2" style={{ color: "var(--text-muted)" }}>
                      … 외 {importPreview.rows.length - 50}건
                    </p>
                  )}
                </div>

                <div className="flex gap-3">
                  <Button onClick={handleImportConfirm} loading={applying}>
                    확인 후 반영
                  </Button>
                  <Button variant="ghost" onClick={handleImportCancel} disabled={applying}>
                    취소
                  </Button>
                </div>
              </div>
            )}
          </Card>
        )}

        {/* ── Filters ───────────────────────────────────────────────── */}
        <div className="flex flex-wrap items-center gap-3">
          <Input
            placeholder="이름 / 학번 / 학과 검색"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-64"
          />
          <Select
            options={ROLE_OPTIONS}
            value={roleFilter}
            onChange={(e) => setRoleFilter(e.target.value)}
            className="w-36"
          />
          <button
            type="button"
            onClick={() => setShowInactive((v) => !v)}
            className="flex items-center gap-1.5 text-xs rounded-lg px-3 py-2 transition-all"
            style={showInactive
              ? { background: "var(--primary)", color: "#fff" }
              : { background: "var(--surface-soft)", color: "var(--text-muted)", border: "1px solid var(--border-soft)" }}
          >
            {showInactive ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
            비활성 포함
          </button>
        </div>

        {/* ── 요약 ─────────────────────────────────────────────────── */}
        {members.length > 0 && (
          <div className="flex gap-3 text-xs" style={{ color: "var(--text-muted)" }}>
            <span>전체 {members.length}명</span>
            <span>·</span>
            <span>임원 {members.filter((m) => m.is_officer ?? m.is_executive).length}명</span>
            <span>·</span>
            <span>일반 부원 {members.filter((m) => !(m.is_officer ?? m.is_executive)).length}명</span>
          </div>
        )}

        {/* ── Table ─────────────────────────────────────────────────── */}
        <Card padding="none">
          {loading ? (
            <LoadingState />
          ) : error ? (
            <div className="p-5">
              <ErrorState message={error} onRetry={load} />
            </div>
          ) : members.length === 0 ? (
            <EmptyState
              message="등록된 부원이 없습니다."
              description="부원 추가 버튼으로 새 부원을 등록하세요."
              action={
                <Button size="sm" onClick={openCreate}>
                  <Plus className="h-3.5 w-3.5" />
                  부원 추가
                </Button>
              }
            />
          ) : (
            <div className="hidden md:block overflow-x-auto">
              <table className="min-w-full text-sm">
                <thead>
                  <tr style={{ background: "var(--surface-soft)", borderBottom: "1px solid var(--border-soft)" }}>
                    {["이름", "직위", "학번", "학과", "전화번호", "이메일", "상태", "생성일", "관리"].map((h) => (
                      <th key={h}
                        className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide"
                        style={{ color: "var(--text-muted)" }}>
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {members.map((m) => (
                    <tr key={m.id}
                      style={{
                        borderBottom: "1px solid var(--border-soft)",
                        opacity: m.status === "inactive" ? 0.55 : 1,
                      }}
                      onMouseEnter={(e) => (e.currentTarget.style.background = "var(--surface-soft)")}
                      onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}>
                      <td className="px-4 py-3" style={{ color: "var(--text-main)" }}>
                        <div className="flex items-center gap-2">
                          <Link href={`/members/${m.id}`} className="font-medium hover:underline">
                            {m.name}
                          </Link>
                        </div>
                      </td>
                      <td className="px-4 py-3">
                        <RoleBadge role={normalizeOfficerRole(m)} />
                      </td>
                      <td className="px-4 py-3 text-xs" style={{ color: "var(--text-muted)" }}>
                        {m.student_id ?? "-"}
                      </td>
                      <td className="px-4 py-3 text-xs max-w-[120px] truncate" title={m.department ?? "-"} style={{ color: "var(--text-muted)" }}>
                        {m.department ?? "-"}
                      </td>
                      <td className="px-4 py-3 text-xs whitespace-nowrap" style={{ color: "var(--text-muted)" }}>
                        {m.phone ?? "-"}
                      </td>
                      <td className="px-4 py-3 text-xs max-w-[160px] truncate" title={m.email ?? "-"} style={{ color: "var(--text-muted)" }}>
                        {m.email ?? "-"}
                      </td>
                      <td className="px-4 py-3">
                        <StatusBadge status={m.status} />
                      </td>
                      <td className="px-4 py-3 text-xs whitespace-nowrap"
                        style={{ color: "var(--text-muted)" }}>
                        {m.created_at?.slice(0, 10) ?? "-"}
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-1.5 whitespace-nowrap">
                          <Link href={`/members/${m.id}`}>
                            <Button size="sm" variant="ghost">상세</Button>
                          </Link>
                          {m.status !== "inactive" ? (
                            <Button size="sm" variant="ghost" onClick={() => openEdit(m)}>수정</Button>
                          ) : (
                            <Button size="sm" variant="ghost" onClick={() => handleRestore(m.id)}>복구</Button>
                          )}
                          {m.status !== "inactive" && (
                            <button
                              className="text-xs px-2 py-1 rounded-lg transition-all hover:opacity-75"
                              style={{ color: "var(--text-muted)", border: "1px solid var(--border-soft)", background: "transparent" }}
                              onClick={() => setConfirmTarget(m)}
                              title="비활성화"
                            >
                              ⋯
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          {/* Mobile card list */}
          {!loading && !error && members.length > 0 && (
            <div className="md:hidden divide-y" style={{ borderTop: "1px solid var(--border-soft)" }}>
              {members.map((m) => (
                <div key={m.id} className="flex items-center gap-3 px-4 py-3"
                  style={{ opacity: m.status === "inactive" ? 0.55 : 1 }}>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <Link href={`/members/${m.id}`} className="font-medium text-sm hover:underline" style={{ color: "var(--text-main)" }}>
                        {m.name}
                      </Link>
                      <RoleBadge role={normalizeOfficerRole(m)} />
                      <StatusBadge status={m.status} />
                    </div>
                    <p className="text-xs mt-0.5 truncate" style={{ color: "var(--text-muted)" }}>
                      {[m.student_id, m.department].filter(Boolean).join(" · ") || "-"}
                    </p>
                  </div>
                  <div className="flex items-center gap-1 shrink-0">
                    <Link href={`/members/${m.id}`}>
                      <Button size="sm" variant="ghost">상세</Button>
                    </Link>
                  </div>
                </div>
              ))}
            </div>
          )}
        </Card>
      </div>

      <Modal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        title={editingMember ? "부원 수정" : "부원 추가"}
      >
        <div className="space-y-4">
          <Input label="이름 *" value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="홍길동" />
          <Input label="학번" value={form.student_id}
            onChange={(e) => setForm({ ...form, student_id: e.target.value })} placeholder="20240001" />
          <Input label="학과" value={form.department}
            onChange={(e) => setForm({ ...form, department: e.target.value })} placeholder="컴퓨터공학과" />
          <Input label="전화번호" value={form.phone}
            onChange={(e) => setForm({ ...form, phone: e.target.value })} placeholder="010-0000-0000" />
          <Input label="이메일" type="email" value={form.email}
            onChange={(e) => setForm({ ...form, email: e.target.value })} placeholder="user@example.com" />
          <Select label="상태" options={STATUS_OPTIONS} value={form.status}
            onChange={(e) => setForm({ ...form, status: e.target.value })} />
          <label className="flex items-center gap-2 text-sm" style={{ color: "var(--text-main)" }}>
            <input
              type="checkbox"
              checked={form.is_officer}
              onChange={(e) => setForm({ ...form, is_officer: e.target.checked })}
            />
            임원 여부
          </label>
          {form.is_officer && (
            <Select
              label="직위"
              options={ROLE_EDIT_OPTIONS}
              value={form.officer_role}
              onChange={(e) => setForm({ ...form, officer_role: e.target.value as OfficerRole })}
            />
          )}
          <Input label="메모" value={form.memo}
            onChange={(e) => setForm({ ...form, memo: e.target.value })} placeholder="기타 메모" />
          {formError && <ErrorState message={formError} />}
          <div className="flex justify-end gap-2 pt-2">
            <Button variant="secondary" onClick={() => setIsModalOpen(false)} disabled={saving}>취소</Button>
            <Button onClick={handleSave} loading={saving}>저장</Button>
          </div>
        </div>
      </Modal>

      <ConfirmDialog
        isOpen={confirmTarget !== null}
        onClose={() => setConfirmTarget(null)}
        onConfirm={handleDeactivate}
        title="부원 비활성화"
        message={`${confirmTarget?.name ?? ""}을(를) 비활성화 하시겠습니까? 기존 활동 참여 기록과 납부 기록은 보존됩니다.`}
        confirmLabel="비활성화"
        loading={confirmLoading}
      />
    </AppShell>
  );
}
