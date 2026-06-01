"use client";

import { useCallback, useEffect, useState } from "react";
import { Eye, Plus } from "lucide-react";

import { AppShell } from "@/components/layout/AppShell";
import { Button } from "@/components/ui/Button";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorState } from "@/components/ui/ErrorState";
import { Input } from "@/components/ui/Input";
import { LoadingState } from "@/components/ui/LoadingState";
import { Modal } from "@/components/ui/Modal";
import { Select } from "@/components/ui/Select";
import { Textarea } from "@/components/ui/Textarea";
import {
  type ActivityCategory,
  type ReferenceReport,
  type ReferenceReportCreate,
  createReferenceReport,
  deleteReferenceReport,
  getActivityCategoriesTyped,
  getReferenceReportsFiltered,
  updateReferenceReport,
} from "@/lib/api";

type FormData = {
  category_id: string;
  title: string;
  content: string;
  tags: string; // comma-separated
};

const emptyForm: FormData = { category_id: "", title: "", content: "", tags: "" };

function reportToForm(r: ReferenceReport): FormData {
  return {
    category_id: r.category_id ?? "",
    title: r.title,
    content: r.content,
    tags: (r.tags ?? []).join(", "),
  };
}

function formToPayload(form: FormData): ReferenceReportCreate {
  const tags = form.tags
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean);
  return {
    category_id: form.category_id || null,
    title: form.title.trim(),
    content: form.content.trim(),
    tags: tags.length > 0 ? tags : null,
  };
}

export default function ReferencesPage() {
  const [reports, setReports] = useState<ReferenceReport[]>([]);
  const [categories, setCategories] = useState<ActivityCategory[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [categoryFilter, setCategoryFilter] = useState("");
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingReport, setEditingReport] = useState<ReferenceReport | null>(null);
  const [form, setForm] = useState<FormData>(emptyForm);
  const [formError, setFormError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [confirmTarget, setConfirmTarget] = useState<ReferenceReport | null>(null);
  const [confirmLoading, setConfirmLoading] = useState(false);
  const [previewReport, setPreviewReport] = useState<ReferenceReport | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [data, cats] = await Promise.all([
        getReferenceReportsFiltered({
          category_id: categoryFilter || undefined,
          q: search || undefined,
        }),
        getActivityCategoriesTyped(),
      ]);
      setReports(data);
      setCategories(cats);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "데이터를 불러오지 못했습니다.");
    } finally {
      setLoading(false);
    }
  }, [search, categoryFilter]);

  useEffect(() => {
    load();
  }, [load]);

  const categoryMap = Object.fromEntries(categories.map((c) => [c.id, c.name]));

  const categoryFilterOptions = [
    { value: "", label: "전체 카테고리" },
    ...categories.map((c) => ({ value: c.id, label: c.name })),
  ];

  const categoryFormOptions = [
    { value: "", label: "카테고리 없음" },
    ...categories.map((c) => ({ value: c.id, label: c.name })),
  ];

  function openCreate() {
    setEditingReport(null);
    setForm(emptyForm);
    setFormError(null);
    setIsModalOpen(true);
  }

  function openEdit(report: ReferenceReport) {
    setEditingReport(report);
    setForm(reportToForm(report));
    setFormError(null);
    setIsModalOpen(true);
  }

  async function handleSave() {
    if (!form.title.trim()) {
      setFormError("제목은 필수입니다.");
      return;
    }
    if (!form.content.trim()) {
      setFormError("내용은 필수입니다.");
      return;
    }
    setSaving(true);
    setFormError(null);
    try {
      const payload = formToPayload(form);
      if (editingReport) {
        await updateReferenceReport(editingReport.id, payload);
      } else {
        await createReferenceReport(payload);
      }
      setIsModalOpen(false);
      load();
    } catch (err: unknown) {
      setFormError(err instanceof Error ? err.message : "저장에 실패했습니다.");
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete() {
    if (!confirmTarget) return;
    setConfirmLoading(true);
    try {
      await deleteReferenceReport(confirmTarget.id);
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
      <section className="space-y-5">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-semibold" style={{ color: "var(--text-main)" }}>레퍼런스 보고서</h1>
            <p className="mt-1 text-sm" style={{ color: "var(--text-muted)" }}>
              활동 보고서 작성 시 참고할 레퍼런스 등록 / 수정 / 삭제
            </p>
          </div>
          <Button onClick={openCreate}>
            <Plus className="h-4 w-4" />
            레퍼런스 추가
          </Button>
        </div>

        <div className="flex flex-wrap gap-3">
          <Input
            placeholder="제목 / 내용 검색"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-64"
          />
          <Select
            options={categoryFilterOptions}
            value={categoryFilter}
            onChange={(e) => setCategoryFilter(e.target.value)}
            className="w-44"
          />
        </div>

        <div className="rounded-2xl overflow-hidden"
          style={{ background: "var(--surface)", border: "1px solid var(--border-soft)", boxShadow: "0 1px 4px 0 rgba(31,31,36,0.05)" }}>
          {loading ? (
            <LoadingState />
          ) : error ? (
            <div className="p-4">
              <ErrorState message={error} />
            </div>
          ) : reports.length === 0 ? (
            <EmptyState message="등록된 레퍼런스 보고서가 없습니다." />
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-line text-sm">
                <thead>
                  <tr style={{ background: "var(--surface-soft)", borderBottom: "1px solid var(--border-soft)" }}>
                    {["제목", "카테고리", "태그", "내용 미리보기", "생성일", "관리"].map((h) => (
                      <th key={h}
                        className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide"
                        style={{ color: "var(--text-muted)" }}>
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-line">
                  {reports.map((r) => (
                    <tr key={r.id}
                      style={{ borderBottom: "1px solid var(--border-soft)" }}
                      onMouseEnter={(e) => (e.currentTarget.style.background = "var(--surface-soft)")}
                      onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}>
                      <td className="px-4 py-3 font-medium" style={{ color: "var(--text-main)" }}>{r.title}</td>
                      <td className="px-4 py-3 text-xs" style={{ color: "var(--text-muted)" }}>
                        {r.category_id ? (categoryMap[r.category_id] ?? r.category_id.slice(0, 8)) : "-"}
                      </td>
                      <td className="px-4 py-3 text-xs" style={{ color: "var(--text-muted)" }}>
                        {(r.tags ?? []).join(", ") || "-"}
                      </td>
                      <td className="px-4 py-3 max-w-xs text-xs" style={{ color: "var(--text-muted)" }}>
                        <span className="line-clamp-2">{r.content.slice(0, 120)}</span>
                      </td>
                      <td className="px-4 py-3 text-xs whitespace-nowrap" style={{ color: "var(--text-muted)" }}>
                        {r.created_at?.slice(0, 10) ?? "-"}
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex gap-2">
                          <Button
                            size="sm"
                            variant="ghost"
                            onClick={() => setPreviewReport(r)}
                          >
                            <Eye className="h-3.5 w-3.5" />
                          </Button>
                          <Button
                            size="sm"
                            variant="secondary"
                            onClick={() => openEdit(r)}
                          >
                            수정
                          </Button>
                          <Button
                            size="sm"
                            variant="ghost"
                            onClick={() => setConfirmTarget(r)}
                          >
                            삭제
                          </Button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </section>

      {/* Create / Edit Modal */}
      <Modal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        title={editingReport ? "레퍼런스 수정" : "레퍼런스 추가"}
        size="lg"
      >
        <div className="space-y-4">
          <Select
            label="카테고리"
            options={categoryFormOptions}
            value={form.category_id}
            onChange={(e) => setForm({ ...form, category_id: e.target.value })}
          />
          <Input
            label="제목 *"
            value={form.title}
            onChange={(e) => setForm({ ...form, title: e.target.value })}
            placeholder="레퍼런스 보고서 제목"
          />
          <Textarea
            label="내용 *"
            value={form.content}
            onChange={(e) => setForm({ ...form, content: e.target.value })}
            rows={8}
            placeholder="활동 보고서 내용을 입력하세요"
          />
          <div>
            <Input
              label="태그 (쉼표 구분)"
              value={form.tags}
              onChange={(e) => setForm({ ...form, tags: e.target.value })}
              placeholder="스터디, 정기모임, AI"
            />
            <p className="mt-1 text-xs text-gray-400">쉼표로 구분하여 입력합니다.</p>
          </div>
          {formError && <ErrorState message={formError} />}
          <div className="flex justify-end gap-2 pt-2">
            <Button
              variant="secondary"
              onClick={() => setIsModalOpen(false)}
              disabled={saving}
            >
              취소
            </Button>
            <Button onClick={handleSave} loading={saving}>
              저장
            </Button>
          </div>
        </div>
      </Modal>

      {/* Preview Modal */}
      <Modal
        isOpen={previewReport !== null}
        onClose={() => setPreviewReport(null)}
        title={previewReport?.title ?? ""}
        size="lg"
      >
        {previewReport && (
          <div className="space-y-3">
            <div className="flex gap-2 text-sm text-gray-500">
              <span>
                카테고리:{" "}
                {previewReport.category_id
                  ? (categoryMap[previewReport.category_id] ?? previewReport.category_id.slice(0, 8))
                  : "없음"}
              </span>
              {(previewReport.tags ?? []).length > 0 && (
                <span>| 태그: {(previewReport.tags ?? []).join(", ")}</span>
              )}
            </div>
            <div className="rounded-md bg-mist p-4">
              <pre className="whitespace-pre-wrap text-sm text-ink">{previewReport.content}</pre>
            </div>
          </div>
        )}
      </Modal>

      <ConfirmDialog
        isOpen={confirmTarget !== null}
        onClose={() => setConfirmTarget(null)}
        onConfirm={handleDelete}
        title="레퍼런스 삭제"
        message={`"${confirmTarget?.title ?? ""}"을(를) 삭제하겠습니까?`}
        confirmLabel="삭제"
        loading={confirmLoading}
      />
    </AppShell>
  );
}
