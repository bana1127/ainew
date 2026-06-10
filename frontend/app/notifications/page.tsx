"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import { BellRing, Eye, Mail, Play, Plus, RefreshCw, Send, Settings2 } from "lucide-react";

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
import { Textarea } from "@/components/ui/Textarea";
import {
  createNotificationRule,
  deleteNotificationRule,
  getN8nStatus,
  getNotificationDeliveryLogs,
  getNotificationRules,
  previewNotificationRule,
  sendN8nTest,
  sendNotificationRuleNow,
  updateNotificationRule,
  type N8nStatus,
  type NotificationDeliveryLog,
  type NotificationPreviewResponse,
  type NotificationRule,
  type NotificationRulePayload,
  type NotificationSendResult,
} from "@/lib/api";

const REMINDER_OPTIONS = [
  { value: "membership_fee_due", label: "회비 미납" },
  { value: "activity_fee_due", label: "활동비 미납" },
  { value: "activity_upcoming", label: "활동 전날" },
  { value: "activity_report_missing", label: "활동 보고서 미작성" },
  { value: "activity_evidence_missing", label: "활동 증빙 누락" },
  { value: "evidence_missing", label: "증빙 누락" },
  { value: "activity_photo_missing", label: "활동 사진 누락" },
  { value: "report_missing", label: "보고서 누락" },
  { value: "calendar_deadline", label: "일정/마감" },
  { value: "quarter_settlement", label: "분기 정산" },
  { value: "custom", label: "사용자 지정" },
];

const SCOPE_OPTIONS = [
  { value: "term", label: "학기" },
  { value: "quarter", label: "분기" },
  { value: "activity", label: "활동" },
  { value: "calendar_event", label: "캘린더" },
  { value: "global", label: "전체" },
];

const emptyForm = {
  name: "",
  enabled: true,
  reminder_type: "activity_photo_missing",
  target_scope: "activity",
  channel: "gmail",
  send_time: "09:00",
  days_before: "",
  days_after: "2",
  repeat_interval_days: "2",
  max_send_count: "3",
  require_confirm_before_send: true,
  term: "",
  quarter: "",
  activity_id: "",
  recipient_email: "",
  recipient_name: "운영진",
  template_subject: "[ClubAgent] {activity_title} 활동 사진 업로드 필요",
  template_body: "{activity_title}의 활동 사진이 아직 업로드되지 않았습니다.\n\n확인 링크: {target_url}",
};

type RuleForm = typeof emptyForm;

function ruleToForm(rule: NotificationRule): RuleForm {
  const conditions = rule.conditions ?? {};
  return {
    name: rule.name,
    enabled: rule.enabled,
    reminder_type: rule.reminder_type,
    target_scope: rule.target_scope,
    channel: rule.channel,
    send_time: (rule.send_time ?? "09:00").slice(0, 5),
    days_before: rule.days_before?.toString() ?? "",
    days_after: rule.days_after?.toString() ?? "",
    repeat_interval_days: rule.repeat_interval_days?.toString() ?? "",
    max_send_count: rule.max_send_count?.toString() ?? "",
    require_confirm_before_send: rule.require_confirm_before_send,
    term: rule.term ?? "",
    quarter: rule.quarter ?? "",
    activity_id: rule.activity_id ?? "",
    recipient_email: String(conditions.recipient_email ?? ""),
    recipient_name: String(conditions.recipient_name ?? "운영진"),
    template_subject: rule.template_subject,
    template_body: rule.template_body,
  };
}

function formToPayload(form: RuleForm): NotificationRulePayload {
  return {
    name: form.name.trim(),
    enabled: form.enabled,
    reminder_type: form.reminder_type,
    target_scope: form.target_scope,
    channel: form.channel,
    send_time: form.send_time || null,
    days_before: numberOrNull(form.days_before),
    days_after: numberOrNull(form.days_after),
    repeat_interval_days: numberOrNull(form.repeat_interval_days),
    max_send_count: numberOrNull(form.max_send_count),
    require_confirm_before_send: form.require_confirm_before_send,
    term: form.term.trim() || null,
    quarter: form.quarter.trim() || null,
    activity_id: form.activity_id.trim() || null,
    conditions: {
      include_statuses: ["unpaid", "partial", "need_check"],
      exclude_cancelled: true,
      recipient_email: form.recipient_email.trim() || undefined,
      recipient_name: form.recipient_name.trim() || undefined,
    },
    template_subject: form.template_subject,
    template_body: form.template_body,
  };
}

function numberOrNull(value: string): number | null {
  const trimmed = value.trim();
  if (!trimmed) return null;
  const n = Number(trimmed);
  return Number.isFinite(n) ? n : null;
}

function reminderLabel(value: string) {
  return REMINDER_OPTIONS.find((o) => o.value === value)?.label ?? value;
}

function statusTone(status: string) {
  if (status === "sent" || status === "success") return { bg: "var(--success-soft)", color: "var(--success)" };
  if (status === "failed") return { bg: "var(--danger-soft)", color: "var(--danger)" };
  if (status === "pending") return { bg: "var(--warning-soft)", color: "var(--warning)" };
  return { bg: "var(--surface-soft)", color: "var(--text-muted)" };
}

function StatusPill({ children, tone }: { children: ReactNode; tone: { bg: string; color: string } }) {
  return (
    <span className="inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium" style={{ background: tone.bg, color: tone.color }}>
      {children}
    </span>
  );
}

export default function NotificationsPage() {
  const [rules, setRules] = useState<NotificationRule[]>([]);
  const [logs, setLogs] = useState<NotificationDeliveryLog[]>([]);
  const [n8n, setN8n] = useState<N8nStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [ruleModalOpen, setRuleModalOpen] = useState(false);
  const [editingRule, setEditingRule] = useState<NotificationRule | null>(null);
  const [form, setForm] = useState<RuleForm>(emptyForm);
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [preview, setPreview] = useState<NotificationPreviewResponse | null>(null);
  const [previewOpen, setPreviewOpen] = useState(false);
  const [testOpen, setTestOpen] = useState(false);
  const [testEmail, setTestEmail] = useState("");
  const [testLoading, setTestLoading] = useState(false);
  const [sendTarget, setSendTarget] = useState<NotificationRule | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<NotificationRule | null>(null);
  const [sendResult, setSendResult] = useState<NotificationSendResult | null>(null);
  const [actionLoading, setActionLoading] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [status, loadedRules, loadedLogs] = await Promise.all([
        getN8nStatus(),
        getNotificationRules(),
        getNotificationDeliveryLogs(),
      ]);
      setN8n(status);
      setRules(loadedRules);
      setLogs(loadedLogs);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "알림 설정을 불러오지 못했습니다.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const enabledCount = useMemo(() => rules.filter((r) => r.enabled).length, [rules]);

  function openCreate() {
    setEditingRule(null);
    setForm(emptyForm);
    setFormError(null);
    setRuleModalOpen(true);
  }

  function openEdit(rule: NotificationRule) {
    setEditingRule(rule);
    setForm(ruleToForm(rule));
    setFormError(null);
    setRuleModalOpen(true);
  }

  async function handleSaveRule() {
    if (!form.name.trim()) { setFormError("알림 이름은 필수입니다."); return; }
    if (!form.template_subject.trim()) { setFormError("메일 제목 템플릿은 필수입니다."); return; }
    if (!form.template_body.trim()) { setFormError("메일 본문 템플릿은 필수입니다."); return; }
    setSaving(true);
    setFormError(null);
    try {
      const payload = formToPayload(form);
      if (editingRule) await updateNotificationRule(editingRule.id, payload);
      else await createNotificationRule(payload);
      setRuleModalOpen(false);
      await load();
    } catch (err: unknown) {
      setFormError(err instanceof Error ? err.message : "규칙 저장에 실패했습니다.");
    } finally {
      setSaving(false);
    }
  }

  async function handlePreview(rule: NotificationRule) {
    setActionLoading(true);
    try {
      setPreview(await previewNotificationRule(rule.id));
      setPreviewOpen(true);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "대상자 미리보기에 실패했습니다.");
    } finally {
      setActionLoading(false);
    }
  }

  async function handleSendNow() {
    if (!sendTarget) return;
    setActionLoading(true);
    try {
      setSendResult(await sendNotificationRuleNow(sendTarget.id));
      setSendTarget(null);
      await load();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "즉시 발송에 실패했습니다.");
    } finally {
      setActionLoading(false);
    }
  }

  async function handleToggleEnabled(rule: NotificationRule) {
    setActionLoading(true);
    try {
      await updateNotificationRule(rule.id, { enabled: !rule.enabled });
      await load();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "사용 여부 변경에 실패했습니다.");
    } finally {
      setActionLoading(false);
    }
  }

  async function handleDeleteRule() {
    if (!deleteTarget) return;
    setActionLoading(true);
    try {
      await deleteNotificationRule(deleteTarget.id);
      setDeleteTarget(null);
      await load();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "규칙 삭제에 실패했습니다.");
    } finally {
      setActionLoading(false);
    }
  }

  async function handleTestEmail() {
    if (!testEmail.trim()) return;
    setTestLoading(true);
    try {
      await sendN8nTest({
        recipient_email: testEmail.trim(),
        recipient_name: "테스트 수신자",
        subject: "[ClubAgent] n8n 테스트 메일",
        body: "n8n Gmail 발송 테스트입니다.",
        target_url: "/notifications",
      });
      setTestOpen(false);
      await load();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "테스트 메일 발송에 실패했습니다.");
    } finally {
      setTestLoading(false);
    }
  }

  return (
    <AppShell>
      <div className="space-y-6">
        <PageHeader
          title="알림 설정"
          description="n8n Gmail 발송과 사용자 설정형 리마인드 규칙을 관리합니다."
          action={
            <div className="flex gap-2">
              <Button variant="secondary" size="sm" onClick={load}>
                <RefreshCw className="h-3.5 w-3.5" />
                새로고침
              </Button>
              <Button size="sm" onClick={openCreate}>
                <Plus className="h-3.5 w-3.5" />
                규칙 추가
              </Button>
            </div>
          }
        />

        {loading ? (
          <LoadingState />
        ) : error ? (
          <ErrorState message={error} onRetry={load} />
        ) : (
          <>
            <div className="grid gap-4 md:grid-cols-3">
              <Card>
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="text-xs font-medium" style={{ color: "var(--text-muted)" }}>n8n 연결</p>
                    <p className="mt-1 text-lg font-semibold" style={{ color: "var(--text-main)" }}>
                      {n8n?.enabled && n8n.webhook_configured ? "사용 가능" : "설정 필요"}
                    </p>
                  </div>
                  <Settings2 className="h-5 w-5" style={{ color: "var(--primary)" }} />
                </div>
                <div className="mt-4 flex flex-wrap gap-2">
                  <StatusPill tone={statusTone(n8n?.enabled ? "sent" : "failed")}>enabled {String(n8n?.enabled)}</StatusPill>
                  <StatusPill tone={statusTone(n8n?.webhook_configured ? "sent" : "failed")}>webhook {String(n8n?.webhook_configured)}</StatusPill>
                  <StatusPill tone={statusTone(n8n?.secret_configured ? "sent" : "failed")}>secret {String(n8n?.secret_configured)}</StatusPill>
                </div>
              </Card>

              <Card>
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="text-xs font-medium" style={{ color: "var(--text-muted)" }}>Gmail 테스트</p>
                    <p className="mt-1 text-lg font-semibold" style={{ color: "var(--text-main)" }}>
                      {n8n?.last_test_status ?? "미실행"}
                    </p>
                  </div>
                  <Mail className="h-5 w-5" style={{ color: "var(--primary)" }} />
                </div>
                <Button className="mt-4" size="sm" variant="secondary" onClick={() => setTestOpen(true)}>
                  <Send className="h-3.5 w-3.5" />
                  테스트 발송
                </Button>
              </Card>

              <Card>
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="text-xs font-medium" style={{ color: "var(--text-muted)" }}>알림 규칙</p>
                    <p className="mt-1 text-lg font-semibold" style={{ color: "var(--text-main)" }}>
                      {enabledCount} / {rules.length}
                    </p>
                  </div>
                  <BellRing className="h-5 w-5" style={{ color: "var(--primary)" }} />
                </div>
                <p className="mt-4 text-xs" style={{ color: "var(--text-muted)" }}>
                  발송 이력 {logs.length}건
                </p>
              </Card>
            </div>

            <Card padding="none">
              {rules.length === 0 ? (
                <EmptyState
                  message="등록된 알림 규칙이 없습니다."
                  description="규칙 추가 버튼으로 Gmail 리마인드 기준을 설정하세요."
                  action={<Button size="sm" onClick={openCreate}><Plus className="h-3.5 w-3.5" />규칙 추가</Button>}
                />
              ) : (
                <div className="overflow-x-auto">
                  <table className="min-w-full text-sm">
                    <thead>
                      <tr style={{ background: "var(--surface-soft)", borderBottom: "1px solid var(--border-soft)" }}>
                        {["이름", "유형", "기준", "반복", "상태", "작업"].map((h) => (
                          <th key={h} className="px-4 py-3 text-left text-xs font-semibold" style={{ color: "var(--text-muted)" }}>{h}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {rules.map((rule) => (
                        <tr key={rule.id} style={{ borderBottom: "1px solid var(--border-soft)" }}>
                          <td className="px-4 py-3 font-medium" style={{ color: "var(--text-main)" }}>{rule.name}</td>
                          <td className="px-4 py-3" style={{ color: "var(--text-muted)" }}>{reminderLabel(rule.reminder_type)}</td>
                          <td className="px-4 py-3 text-xs" style={{ color: "var(--text-muted)" }}>
                            {rule.term || rule.quarter || rule.activity_id?.slice(0, 8) || rule.target_scope}
                          </td>
                          <td className="px-4 py-3 text-xs" style={{ color: "var(--text-muted)" }}>
                            {rule.repeat_interval_days ?? "-"}일 / 최대 {rule.max_send_count ?? "-"}회
                          </td>
                          <td className="px-4 py-3">
                            <StatusPill tone={statusTone(rule.enabled ? "sent" : "failed")}>{rule.enabled ? "사용" : "중지"}</StatusPill>
                          </td>
                          <td className="px-4 py-3">
                            <div className="flex flex-wrap gap-2">
                              <Button size="sm" variant="ghost" onClick={() => openEdit(rule)}>수정</Button>
                              <Button size="sm" variant="ghost" onClick={() => handlePreview(rule)} disabled={actionLoading}>
                                <Eye className="h-3.5 w-3.5" />
                                미리보기
                              </Button>
                              <Button size="sm" variant="ghost" onClick={() => setSendTarget(rule)}>
                                <Play className="h-3.5 w-3.5" />
                                즉시 발송
                              </Button>
                              <Button size="sm" variant="ghost" onClick={() => handleToggleEnabled(rule)} disabled={actionLoading}>
                                {rule.enabled ? "비활성화" : "활성화"}
                              </Button>
                              <Button size="sm" variant="ghost" onClick={() => setDeleteTarget(rule)}>삭제</Button>
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </Card>

            <Card padding="none">
              <div className="px-5 py-4" style={{ borderBottom: "1px solid var(--border-soft)" }}>
                <h2 className="text-base font-semibold" style={{ color: "var(--text-main)" }}>발송 이력</h2>
              </div>
              {logs.length === 0 ? (
                <EmptyState message="발송 이력이 없습니다." description="테스트 발송 또는 즉시 발송 후 이력이 표시됩니다." />
              ) : (
                <div className="overflow-x-auto">
                  <table className="min-w-full text-sm">
                    <thead>
                      <tr style={{ background: "var(--surface-soft)", borderBottom: "1px solid var(--border-soft)" }}>
                        {["상태", "유형", "수신자", "제목", "생성일"].map((h) => (
                          <th key={h} className="px-4 py-3 text-left text-xs font-semibold" style={{ color: "var(--text-muted)" }}>{h}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {logs.slice(0, 30).map((log) => (
                        <tr key={log.id} style={{ borderBottom: "1px solid var(--border-soft)" }}>
                          <td className="px-4 py-3"><StatusPill tone={statusTone(log.status)}>{log.status}</StatusPill></td>
                          <td className="px-4 py-3" style={{ color: "var(--text-muted)" }}>{reminderLabel(log.reminder_type)}</td>
                          <td className="px-4 py-3" style={{ color: "var(--text-muted)" }}>{log.recipient_email}</td>
                          <td className="px-4 py-3 max-w-sm truncate" style={{ color: "var(--text-main)" }}>{log.subject}</td>
                          <td className="px-4 py-3 text-xs" style={{ color: "var(--text-muted)" }}>{log.created_at.slice(0, 16).replace("T", " ")}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </Card>
          </>
        )}
      </div>

      <Modal isOpen={ruleModalOpen} onClose={() => setRuleModalOpen(false)} title={editingRule ? "알림 규칙 수정" : "알림 규칙 추가"} size="lg">
        <div className="space-y-4">
          <div className="grid gap-3 md:grid-cols-2">
            <Input label="알림 이름" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
            <Select label="알림 유형" options={REMINDER_OPTIONS} value={form.reminder_type} onChange={(e) => setForm({ ...form, reminder_type: e.target.value })} />
            <Select label="대상 기준" options={SCOPE_OPTIONS} value={form.target_scope} onChange={(e) => setForm({ ...form, target_scope: e.target.value })} />
            <Input label="발송 시간" type="time" value={form.send_time} onChange={(e) => setForm({ ...form, send_time: e.target.value })} />
            <Input label="학기" placeholder="2026-1" value={form.term} onChange={(e) => setForm({ ...form, term: e.target.value })} />
            <Input label="분기" placeholder="2026-Q2" value={form.quarter} onChange={(e) => setForm({ ...form, quarter: e.target.value })} />
            <Input label="활동 ID" value={form.activity_id} onChange={(e) => setForm({ ...form, activity_id: e.target.value })} />
            <Input label="수신자 이메일" value={form.recipient_email} onChange={(e) => setForm({ ...form, recipient_email: e.target.value })} />
            <Input label="마감 전 N일" type="number" value={form.days_before} onChange={(e) => setForm({ ...form, days_before: e.target.value })} />
            <Input label="기준 후 N일" type="number" value={form.days_after} onChange={(e) => setForm({ ...form, days_after: e.target.value })} />
            <Input label="반복 간격(일)" type="number" value={form.repeat_interval_days} onChange={(e) => setForm({ ...form, repeat_interval_days: e.target.value })} />
            <Input label="최대 발송 횟수" type="number" value={form.max_send_count} onChange={(e) => setForm({ ...form, max_send_count: e.target.value })} />
          </div>
          <div className="flex flex-wrap gap-4 text-sm" style={{ color: "var(--text-main)" }}>
            <label className="inline-flex items-center gap-2"><input type="checkbox" checked={form.enabled} onChange={(e) => setForm({ ...form, enabled: e.target.checked })} />사용</label>
            <label className="inline-flex items-center gap-2"><input type="checkbox" checked={form.require_confirm_before_send} onChange={(e) => setForm({ ...form, require_confirm_before_send: e.target.checked })} />발송 전 확인</label>
          </div>
          <Input label="메일 제목 템플릿" value={form.template_subject} onChange={(e) => setForm({ ...form, template_subject: e.target.value })} />
          <Textarea label="메일 본문 템플릿" rows={5} value={form.template_body} onChange={(e) => setForm({ ...form, template_body: e.target.value })} />
          {formError && <ErrorState message={formError} />}
          <div className="flex justify-end gap-2">
            <Button variant="secondary" onClick={() => setRuleModalOpen(false)} disabled={saving}>취소</Button>
            <Button onClick={handleSaveRule} loading={saving}>저장</Button>
          </div>
        </div>
      </Modal>

      <Modal isOpen={previewOpen} onClose={() => setPreviewOpen(false)} title="대상자 미리보기" size="lg">
        {preview && (
          <div className="space-y-3">
            <p className="text-sm" style={{ color: "var(--text-muted)" }}>대상 {preview.count}명</p>
            <div className="max-h-96 overflow-y-auto space-y-2">
              {preview.items.map((item, idx) => (
                <div key={`${item.target_id}-${idx}`} className="rounded-lg p-3" style={{ border: "1px solid var(--border-soft)" }}>
                  <p className="text-sm font-medium" style={{ color: "var(--text-main)" }}>{item.recipient_name ?? item.recipient_email}</p>
                  <p className="text-xs" style={{ color: "var(--text-muted)" }}>{item.reason} · {item.target_url ?? "-"}</p>
                  <p className="mt-2 text-sm" style={{ color: "var(--text-main)" }}>{item.subject}</p>
                  <p className="mt-1 whitespace-pre-wrap text-xs" style={{ color: "var(--text-muted)" }}>{item.body}</p>
                </div>
              ))}
            </div>
          </div>
        )}
      </Modal>

      <Modal isOpen={testOpen} onClose={() => setTestOpen(false)} title="Gmail 테스트 발송" size="sm">
        <div className="space-y-4">
          <Input label="수신자 이메일" type="email" value={testEmail} onChange={(e) => setTestEmail(e.target.value)} />
          <div className="flex justify-end gap-2">
            <Button variant="secondary" onClick={() => setTestOpen(false)} disabled={testLoading}>취소</Button>
            <Button onClick={handleTestEmail} loading={testLoading}>발송</Button>
          </div>
        </div>
      </Modal>

      <ConfirmDialog
        isOpen={sendTarget !== null}
        onClose={() => setSendTarget(null)}
        onConfirm={handleSendNow}
        title="즉시 발송"
        message={`"${sendTarget?.name ?? ""}" 규칙의 현재 대상자에게 Gmail 발송을 요청합니다.`}
        confirmLabel="발송"
        confirmVariant="primary"
        loading={actionLoading}
      />

      <ConfirmDialog
        isOpen={deleteTarget !== null}
        onClose={() => setDeleteTarget(null)}
        onConfirm={handleDeleteRule}
        title="알림 규칙 삭제"
        message="이 알림 규칙을 삭제하시겠습니까? 삭제 후에는 자동 알림 대상 계산에서 제외되고, 기존 발송 이력은 유지됩니다."
        confirmLabel="삭제"
        loading={actionLoading}
      />

      {sendResult && (
        <Modal isOpen onClose={() => setSendResult(null)} title="발송 결과" size="sm">
          <div className="space-y-3 text-sm" style={{ color: "var(--text-main)" }}>
            <p>요청 {sendResult.requested}건 · 성공 {sendResult.sent}건 · 실패 {sendResult.failed}건</p>
            <Button size="sm" onClick={() => setSendResult(null)}>확인</Button>
          </div>
        </Modal>
      )}
    </AppShell>
  );
}
