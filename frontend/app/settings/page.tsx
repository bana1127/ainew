"use client";

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
import { Textarea } from "@/components/ui/Textarea";
import {
  type ActivityCategory,
  type ActivityCategoryCreate,
  createActivityCategory,
  deleteActivityCategory,
  getActivityCategoriesTyped,
  updateActivityCategory,
} from "@/lib/api";

type FormData = {
  name: string;
  description: string;
  required_fields: string;
  report_template: string;
};

const emptyForm: FormData = { name: "", description: "", required_fields: "", report_template: "" };

function categoryToForm(c: ActivityCategory): FormData {
  let fields = "";
  if (c.required_fields_json && Array.isArray((c.required_fields_json as Record<string, unknown>).fields)) {
    fields = ((c.required_fields_json as { fields: string[] }).fields).join(", ");
  }
  return { name: c.name, description: c.description ?? "", required_fields: fields, report_template: c.report_template ?? "" };
}

function formToPayload(form: FormData): ActivityCategoryCreate {
  const fields = form.required_fields.split(",").map((s) => s.trim()).filter(Boolean);
  return {
    name: form.name.trim(),
    description: form.description.trim() || null,
    required_fields_json: fields.length > 0 ? { fields } : null,
    report_template: form.report_template.trim() || null,
  };
}

export default function SettingsPage() {
  const [categories, setCategories] = useState<ActivityCategory[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingCategory, setEditingCategory] = useState<ActivityCategory | null>(null);
  const [form, setForm] = useState<FormData>(emptyForm);
  const [formError, setFormError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [confirmTarget, setConfirmTarget] = useState<ActivityCategory | null>(null);
  const [confirmLoading, setConfirmLoading] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setCategories(await getActivityCategoriesTyped());
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "데이터를 불러오지 못했습니다.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  function openCreate() {
    setEditingCategory(null);
    setForm(emptyForm);
    setFormError(null);
    setIsModalOpen(true);
  }

  function openEdit(cat: ActivityCategory) {
    setEditingCategory(cat);
    setForm(categoryToForm(cat));
    setFormError(null);
    setIsModalOpen(true);
  }

  async function handleSave() {
    if (!form.name.trim()) { setFormError("카테고리명은 필수입니다."); return; }
    setSaving(true);
    setFormError(null);
    try {
      const payload = formToPayload(form);
      if (editingCategory) {
        await updateActivityCategory(editingCategory.id, payload);
      } else {
        await createActivityCategory(payload);
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
      await deleteActivityCategory(confirmTarget.id);
      setConfirmTarget(null);
      load();
    } catch {
      // silently ignore
    } finally {
      setConfirmLoading(false);
    }
  }

  function previewFields(cat: ActivityCategory): string {
    if (!cat.required_fields_json) return "-";
    const json = cat.required_fields_json as Record<string, unknown>;
    if (Array.isArray(json.fields)) {
      return (json.fields as string[]).slice(0, 3).join(", ") +
        ((json.fields as string[]).length > 3 ? " ..." : "");
    }
    return JSON.stringify(cat.required_fields_json).slice(0, 60);
  }

  return (
    <AppShell>
      <div className="space-y-6">
        <PageHeader
          title="설정"
          description="활동 카테고리 및 OpenAI 설정을 관리합니다."
        />

        {/* Developer config (collapsed by default) */}
        <details className="rounded-2xl overflow-hidden"
          style={{ border: "1px solid var(--border-soft)", background: "var(--surface)" }}>
          <summary className="px-5 py-3 text-sm font-medium cursor-pointer select-none"
            style={{ color: "var(--text-muted)" }}>
            개발자 설정 안내 (클릭하여 펼치기)
          </summary>
          <div className="px-5 pb-5 pt-2 space-y-3">
            <div className="rounded-xl px-4 py-3 text-sm space-y-1.5"
              style={{ background: "var(--surface-soft)", border: "1px solid var(--border-soft)", color: "var(--text-muted)" }}>
              <p>• OpenAI API Key는 <code className="px-1.5 py-0.5 rounded text-xs"
                style={{ background: "var(--border-soft)" }}>backend/.env</code>의 <code className="px-1.5 py-0.5 rounded text-xs"
                style={{ background: "var(--border-soft)" }}>OPENAI_API_KEY</code>에 설정합니다.</p>
              <p>• 실제 AI 분석 사용 시 <code className="px-1.5 py-0.5 rounded text-xs"
                style={{ background: "var(--border-soft)" }}>OPENAI_MOCK_MODE=false</code>로 설정 후 백엔드를 재시작하세요.</p>
            </div>
            <pre className="rounded-xl px-4 py-3 text-xs"
              style={{ background: "var(--surface-soft)", border: "1px solid var(--border-soft)", color: "var(--text-main)" }}>
              {"OPENAI_API_KEY=sk-...\nOPENAI_MODEL=gpt-4.1-mini\nOPENAI_MOCK_MODE=false"}
            </pre>
          </div>
        </details>

        {/* Activity Category Management */}
        <div>
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="text-base font-semibold" style={{ color: "var(--text-main)" }}>
                활동 카테고리 관리
              </h2>
              <p className="text-sm mt-0.5" style={{ color: "var(--text-muted)" }}>
                활동 보고서 작성 시 사용할 카테고리를 등록·수정·삭제합니다.
              </p>
            </div>
            <Button onClick={openCreate}>
              <Plus className="h-4 w-4" />
              카테고리 추가
            </Button>
          </div>

          <Card padding="none">
            {loading ? (
              <LoadingState />
            ) : error ? (
              <div className="p-5">
                <ErrorState message={error} onRetry={load} />
              </div>
            ) : categories.length === 0 ? (
              <EmptyState
                message="등록된 카테고리가 없습니다."
                description="카테고리 추가 버튼으로 새 카테고리를 등록하세요."
                action={
                  <Button size="sm" onClick={openCreate}>
                    <Plus className="h-3.5 w-3.5" />
                    카테고리 추가
                  </Button>
                }
              />
            ) : (
              <div className="overflow-x-auto">
                <table className="min-w-full text-sm">
                  <thead>
                    <tr style={{ background: "var(--surface-soft)", borderBottom: "1px solid var(--border-soft)" }}>
                      {["카테고리명", "설명", "필수 입력값", "템플릿 미리보기", "생성일", "관리"].map((h) => (
                        <th key={h}
                          className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide"
                          style={{ color: "var(--text-muted)" }}>
                          {h}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {categories.map((cat) => (
                      <tr key={cat.id}
                        style={{ borderBottom: "1px solid var(--border-soft)" }}
                        onMouseEnter={(e) => (e.currentTarget.style.background = "var(--surface-soft)")}
                        onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}>
                        <td className="px-4 py-3 font-medium" style={{ color: "var(--text-main)" }}>{cat.name}</td>
                        <td className="px-4 py-3 max-w-xs text-xs" style={{ color: "var(--text-muted)" }}>
                          <span className="line-clamp-2">{cat.description ?? "-"}</span>
                        </td>
                        <td className="px-4 py-3 max-w-xs text-xs" style={{ color: "var(--text-muted)" }}>
                          <span className="line-clamp-1">{previewFields(cat)}</span>
                        </td>
                        <td className="px-4 py-3 max-w-xs text-xs" style={{ color: "var(--text-muted)" }}>
                          <span className="line-clamp-2">{cat.report_template?.slice(0, 80) ?? "-"}</span>
                        </td>
                        <td className="px-4 py-3 text-xs whitespace-nowrap" style={{ color: "var(--text-muted)" }}>
                          {cat.created_at?.slice(0, 10) ?? "-"}
                        </td>
                        <td className="px-4 py-3">
                          <div className="flex gap-2">
                            <Button size="sm" variant="ghost" onClick={() => openEdit(cat)}>수정</Button>
                            <Button size="sm" variant="ghost" onClick={() => setConfirmTarget(cat)}>삭제</Button>
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
      </div>

      <Modal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        title={editingCategory ? "카테고리 수정" : "카테고리 추가"}
        size="lg"
      >
        <div className="space-y-4">
          <Input label="카테고리명 *" value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="예: 정기 세미나" />
          <Textarea label="설명" value={form.description}
            onChange={(e) => setForm({ ...form, description: e.target.value })} rows={2} />
          <div>
            <Input label="필수 입력값 (쉼표 구분)" value={form.required_fields}
              onChange={(e) => setForm({ ...form, required_fields: e.target.value })}
              placeholder="활동명, 활동 일시, 활동 장소, 참석자" />
            <p className="mt-1 text-xs" style={{ color: "var(--text-muted)" }}>
              쉼표로 구분하면 JSON 배열로 저장됩니다.
            </p>
          </div>
          <Textarea label="보고서 템플릿" value={form.report_template}
            onChange={(e) => setForm({ ...form, report_template: e.target.value })} rows={5} />
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
        onConfirm={handleDelete}
        title="카테고리 삭제"
        message={`"${confirmTarget?.name ?? ""}" 카테고리를 삭제하겠습니까?`}
        confirmLabel="삭제"
        loading={confirmLoading}
      />
    </AppShell>
  );
}
