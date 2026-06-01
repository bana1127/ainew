"use client";

import { useEffect, useState } from "react";
import { Bell, Cpu } from "lucide-react";

import { AppShell } from "@/components/layout/AppShell";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorState } from "@/components/ui/ErrorState";
import { LoadingState } from "@/components/ui/LoadingState";
import { PageHeader } from "@/components/ui/PageHeader";
import { getNotifications } from "@/lib/api";
import type { ApiRecord } from "@/lib/api";

const SEVERITY_STYLE: Record<string, React.CSSProperties> = {
  info: { background: "var(--primary-soft)", color: "var(--primary)" },
  warning: { background: "var(--warning-soft)", color: "var(--warning)" },
  error: { background: "var(--danger-soft)", color: "var(--danger)" },
  success: { background: "var(--success-soft)", color: "var(--success)" },
};

function NotificationRow({ item }: { item: ApiRecord }) {
  const isAutomation = item.type === "automation";
  const isRead = item.is_read === true || item.is_read === "true";
  const severity = String(item.severity ?? "info");
  const sevStyle = SEVERITY_STYLE[severity] ?? SEVERITY_STYLE.info;

  return (
    <div
      className="flex items-start gap-4 px-5 py-4 transition-colors"
      style={{
        borderBottom: "1px solid var(--border-soft)",
        background: isRead ? "transparent" : "var(--surface-soft)",
      }}
    >
      {/* Icon */}
      <div className="rounded-xl p-2 shrink-0" style={sevStyle}>
        {isAutomation
          ? <Cpu className="h-3.5 w-3.5" />
          : <Bell className="h-3.5 w-3.5" />}
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 flex-wrap mb-0.5">
          <p className="text-sm font-medium" style={{ color: "var(--text-main)" }}>
            {String(item.title ?? "-")}
          </p>
          {isAutomation && (
            <span
              className="inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium"
              style={{ background: "var(--primary-soft)", color: "var(--primary)" }}
            >
              자동 점검
            </span>
          )}
          <span
            className="inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium"
            style={sevStyle}
          >
            {severity}
          </span>
        </div>
        <p className="text-sm leading-relaxed" style={{ color: "var(--text-muted)" }}>
          {String(item.message ?? "-")}
        </p>
        <p className="text-xs mt-1" style={{ color: "var(--text-muted)", opacity: 0.7 }}>
          {item.created_at ? String(item.created_at).slice(0, 16).replace("T", " ") : "-"}
          {" · "}
          {isRead ? "읽음" : <span style={{ color: "var(--primary)" }}>안 읽음</span>}
        </p>
      </div>
    </div>
  );
}

export default function NotificationsPage() {
  const [items, setItems] = useState<ApiRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<"all" | "automation" | "unread">("all");

  function load() {
    setLoading(true);
    getNotifications()
      .then((data) => { setItems(data); setError(null); })
      .catch((err: Error) => setError(err.message || "데이터를 불러오지 못했습니다."))
      .finally(() => setLoading(false));
  }

  useEffect(() => { load(); }, []);

  const filtered = items.filter((item) => {
    if (filter === "automation") return item.type === "automation";
    if (filter === "unread") return item.is_read !== true && item.is_read !== "true";
    return true;
  });

  const unreadCount = items.filter((i) => i.is_read !== true && i.is_read !== "true").length;
  const autoCount = items.filter((i) => i.type === "automation").length;

  return (
    <AppShell>
      <div className="space-y-6">
        <PageHeader
          title="알림"
          description="시스템 알림 및 자동 점검 결과를 조회합니다."
          action={
            <Button variant="ghost" size="sm" onClick={load}>
              새로고침
            </Button>
          }
        />

        {/* Filter tabs */}
        <div className="flex gap-2 flex-wrap">
          {[
            { key: "all" as const, label: `전체 (${items.length})` },
            { key: "automation" as const, label: `자동 점검 (${autoCount})` },
            { key: "unread" as const, label: `안 읽음 (${unreadCount})` },
          ].map(({ key, label }) => (
            <button
              key={key}
              onClick={() => setFilter(key)}
              className="rounded-xl px-3 py-1.5 text-xs font-medium transition-all"
              style={
                filter === key
                  ? { background: "var(--primary)", color: "#fff" }
                  : { background: "var(--surface-soft)", color: "var(--text-muted)", border: "1px solid var(--border-soft)" }
              }
            >
              {label}
            </button>
          ))}
        </div>

        <Card padding="none">
          {loading ? (
            <LoadingState />
          ) : error ? (
            <div className="p-5">
              <ErrorState message={error} onRetry={load} />
            </div>
          ) : filtered.length === 0 ? (
            <EmptyState
              message="알림이 없습니다."
              description="시스템 이벤트 발생 시 또는 자동 점검 실행 후 여기에 표시됩니다."
            />
          ) : (
            <div>
              {filtered.map((item, idx) => (
                <NotificationRow key={String(item.id ?? idx)} item={item} />
              ))}
            </div>
          )}
        </Card>

        {/* Automation notice */}
        <div
          className="rounded-xl px-4 py-3 text-sm"
          style={{ background: "var(--primary-soft)", border: "1px solid rgba(124,108,242,0.15)", color: "var(--primary)" }}
        >
          자동 점검은 <code className="text-xs px-1 rounded" style={{ background: "rgba(124,108,242,0.15)" }}>POST /api/automations/weekly-check</code> 등을 n8n이나 curl로 호출하면 실행됩니다. 자세한 내용은 <code className="text-xs">AUTOMATION.md</code>를 참고하세요.
        </div>
      </div>
    </AppShell>
  );
}
