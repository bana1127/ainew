"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { Plus } from "lucide-react";

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
  createMember,
  deleteMember,
  getMembersFiltered,
  updateMember,
} from "@/lib/api";

const STATUS_OPTIONS = [
  { value: "active", label: "활동중" },
  { value: "inactive", label: "비활성" },
  { value: "graduated", label: "졸업" },
  { value: "paused", label: "휴면" },
];

const STATUS_FILTER_OPTIONS = [{ value: "", label: "전체 상태" }, ...STATUS_OPTIONS];

type FormData = {
  name: string;
  student_id: string;
  department: string;
  phone: string;
  email: string;
  status: string;
  memo: string;
};

const emptyForm: FormData = {
  name: "", student_id: "", department: "", phone: "", email: "", status: "active", memo: "",
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
  };
}

export default function MembersPage() {
  const [members, setMembers] = useState<Member[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingMember, setEditingMember] = useState<Member | null>(null);
  const [form, setForm] = useState<FormData>(emptyForm);
  const [formError, setFormError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [confirmTarget, setConfirmTarget] = useState<Member | null>(null);
  const [confirmLoading, setConfirmLoading] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getMembersFiltered({
        status: statusFilter || undefined,
        q: search || undefined,
      });
      setMembers(data);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "데이터를 불러오지 ���했습니다.");
    } finally {
      setLoading(false);
    }
  }, [search, statusFilter]);

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
      await deleteMember(confirmTarget.id);
      setConfirmTarget(null);
      load();
    } catch {
      // silently ignore
    } finally {
      setConfirmLoading(false);
    }
  }

  return (
    <AppShell>
      <div className="space-y-6">
        <PageHeader
          title="부원 관리"
          description="부원 명부를 등록·수정·관리합니다."
          action={
            <Button onClick={openCreate}>
              <Plus className="h-4 w-4" />
              부원 추가
            </Button>
          }
        />

        {/* Filters */}
        <div className="flex flex-wrap gap-3">
          <Input
            placeholder="이름 / 학번 / 학과 검색"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-64"
          />
          <Select
            options={STATUS_FILTER_OPTIONS}
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="w-36"
          />
        </div>

        {/* Table */}
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
            <div className="overflow-x-auto">
              <table className="min-w-full text-sm">
                <thead>
                  <tr style={{ background: "var(--surface-soft)", borderBottom: "1px solid var(--border-soft)" }}>
                    {["이름", "학번", "학과", "전화번호", "이메일", "상태", "메모", "생성일", "관리"].map((h) => (
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
                      style={{ borderBottom: "1px solid var(--border-soft)" }}
                      onMouseEnter={(e) => (e.currentTarget.style.background = "var(--surface-soft)")}
                      onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}>
                      <td className="px-4 py-3 font-medium" style={{ color: "var(--text-main)" }}>
                        <Link href={`/members/${m.id}`} className="hover:underline">
                          {m.name}
                        </Link>
                      </td>
                      <td className="px-4 py-3 text-xs" style={{ color: "var(--text-muted)" }}>
                        {m.student_id ?? "-"}
                      </td>
                      <td className="px-4 py-3 text-xs" style={{ color: "var(--text-muted)" }}>
                        {m.department ?? "-"}
                      </td>
                      <td className="px-4 py-3 text-xs" style={{ color: "var(--text-muted)" }}>
                        {m.phone ?? "-"}
                      </td>
                      <td className="px-4 py-3 text-xs" style={{ color: "var(--text-muted)" }}>
                        {m.email ?? "-"}
                      </td>
                      <td className="px-4 py-3">
                        <StatusBadge status={m.status} />
                      </td>
                      <td className="px-4 py-3 max-w-xs text-xs" style={{ color: "var(--text-muted)" }}>
                        <span className="line-clamp-1">{m.memo ?? "-"}</span>
                      </td>
                      <td className="px-4 py-3 text-xs whitespace-nowrap"
                        style={{ color: "var(--text-muted)" }}>
                        {m.created_at?.slice(0, 10) ?? "-"}
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex gap-2">
                          <Link href={`/members/${m.id}`}>
                            <Button size="sm" variant="ghost">상세</Button>
                          </Link>
                          <Button size="sm" variant="ghost" onClick={() => openEdit(m)}>
                            수정
                          </Button>
                          <Button
                            size="sm"
                            variant="ghost"
                            onClick={() => setConfirmTarget(m)}
                            disabled={m.status === "inactive"}
                          >
                            비활성화
                          </Button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
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
        message={`${confirmTarget?.name ?? ""}을(를) 비활성화 처리하겠습니까?`}
        confirmLabel="비활성화"
        loading={confirmLoading}
      />
    </AppShell>
  );
}
