"use client";

import { useEffect, useState } from "react";
import Image from "next/image";
import Link from "next/link";
import {
  AlertTriangle,
  Bell,
  Bot,
  CreditCard,
  FileText,
  PenLine,
  ReceiptText,
  Users,
} from "lucide-react";

import { AppShell } from "@/components/layout/AppShell";
import { Card } from "@/components/ui/Card";
import { StatCard } from "@/components/ui/StatCard";
import { DashboardCalendar } from "@/components/dashboard/DashboardCalendar";
import {
  getDashboardSummary,
  getDashboardTodo,
  type DashboardSummary,
  type DashboardTodo,
} from "@/lib/api";

function num(v: number | undefined): string {
  return v === undefined ? "—" : v.toLocaleString();
}

// ── Summary Cards ─────────────────────────────────────────────────────────────

function DashboardSummaryCards({
  summary,
  loading,
}: {
  summary: DashboardSummary | null;
  loading: boolean;
}) {
  const cards = [
    { icon: Users, label: "전체 부원", value: loading ? "…" : num(summary?.total_members), tone: "neutral" as const, href: "/members" },
    { icon: FileText, label: "전체 활동", value: loading ? "…" : num(summary?.total_activity_reports), tone: "neutral" as const, href: "/activities" },
    { icon: CreditCard, label: "회비 미납", value: loading ? "…" : num(summary?.unpaid_membership_fee_count), tone: (summary?.unpaid_membership_fee_count ?? 0) > 0 ? "danger" as const : "neutral" as const, href: "/payments?tab=membership_fee" },
    { icon: ReceiptText, label: "증빙 확인 필요", value: loading ? "…" : num(summary?.pending_receipts), tone: (summary?.pending_receipts ?? 0) > 0 ? "warning" as const : "neutral" as const, href: "/receipts" },
  ];

  return (
    <section>
      <h2 className="text-sm font-semibold mb-3" style={{ color: "var(--text-main)" }}>운영 요약</h2>
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {cards.map((card) => (
          <Link key={card.label} href={card.href}>
            <StatCard icon={card.icon} label={card.label} value={card.value} tone={card.tone} />
          </Link>
        ))}
      </div>
    </section>
  );
}

// ── Todo List ─────────────────────────────────────────────────────────────────

function DashboardTodoList({
  summary,
  todo,
  loading,
}: {
  summary: DashboardSummary | null;
  todo: DashboardTodo | null;
  loading: boolean;
}) {
  const items = [
    {
      label: "회비 미납",
      value: summary?.unpaid_membership_fee_count ?? 0,
      href: "/payments?tab=membership_fee",
      icon: CreditCard,
      urgent: true,
    },
    {
      label: "활동비 미납",
      value: summary?.unpaid_activity_fee_count ?? 0,
      href: "/payments?tab=activity_fee",
      icon: CreditCard,
      urgent: true,
    },
    {
      label: "보고서 미작성 활동",
      value: todo?.no_report_activities ?? 0,
      href: "/activities",
      icon: PenLine,
      urgent: false,
    },
    {
      label: "증빙 부족 활동",
      value: todo?.no_evidence_activities ?? 0,
      href: "/receipts",
      icon: ReceiptText,
      urgent: false,
    },
    {
      label: "활동 사진 누락",
      value: todo?.no_activity_photo_activities ?? 0,
      href: "/activities",
      icon: ReceiptText,
      urgent: false,
    },
    {
      label: "HWPX 미생성 활동",
      value: todo?.no_hwpx_activities ?? 0,
      href: "/activities",
      icon: FileText,
      urgent: false,
    },
    {
      label: "읽지 않은 알림",
      value: summary?.unread_notifications ?? 0,
      href: "/notifications",
      icon: Bell,
      urgent: true,
    },
  ];

  const anyItem = !loading && items.some((i) => i.value > 0);

  return (
    <section>
      <h2 className="text-sm font-semibold mb-3" style={{ color: "var(--text-main)" }}>처리해야 할 일</h2>
      <Card padding="none">
        {loading ? (
          <div className="px-4 py-3 text-xs" style={{ color: "var(--text-muted)" }}>로딩 중…</div>
        ) : !anyItem ? (
          <div className="px-4 py-3 text-xs" style={{ color: "var(--text-muted)" }}>처리할 항목이 없습니다.</div>
        ) : (
          <div className="divide-y" style={{ borderColor: "var(--border-soft)" }}>
            {items.filter((i) => i.value > 0).map((item) => {
              const Icon = item.icon;
              const isUrgent = item.urgent && item.value > 0;
              return (
                <Link key={item.label} href={item.href}>
                  <div
                    className="flex items-center justify-between gap-3 px-4 py-3 transition-all hover:opacity-80"
                    style={{ background: isUrgent ? "var(--warning-soft)" : "transparent" }}
                  >
                    <div className="flex items-center gap-2.5">
                      <div className="p-1.5 rounded-lg" style={{ background: isUrgent ? "rgba(185,130,43,0.1)" : "var(--surface-soft)" }}>
                        <Icon className="h-3.5 w-3.5" style={{ color: isUrgent ? "var(--warning)" : "var(--text-muted)" }} />
                      </div>
                      <span className="text-sm" style={{ color: isUrgent ? "var(--warning)" : "var(--text-main)" }}>
                        {item.label}
                      </span>
                    </div>
                    <span className="text-sm font-semibold" style={{ color: isUrgent ? "var(--warning)" : "var(--text-muted)" }}>
                      {item.value}건
                    </span>
                  </div>
                </Link>
              );
            })}
          </div>
        )}
      </Card>
    </section>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function DashboardPage() {
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [todo, setTodo] = useState<DashboardTodo | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      getDashboardSummary(),
      getDashboardTodo(),
    ])
      .then(([s, t]) => {
        setSummary(s);
        setTodo(t);
      })
      .catch((err: Error) => setError(err.message || "Backend API 연결 실패"))
      .finally(() => setLoading(false));
  }, []);

  return (
    <AppShell>
      <div className="space-y-6">
        {/* Error banner */}
        {error && (
          <div className="flex items-center gap-3 rounded-xl px-4 py-3"
            style={{ background: "var(--danger-soft)", border: "1px solid rgba(185,74,72,0.15)" }}>
            <AlertTriangle className="h-4 w-4 shrink-0" style={{ color: "var(--danger)" }} />
            <p className="text-sm" style={{ color: "var(--danger)" }}>
              {error} — 백엔드가 실행 중인지 확인하세요.
            </p>
          </div>
        )}

        {/* Brand header (compact) */}
        <Card padding="md">
          <div className="flex items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <div className="shrink-0 rounded-full overflow-hidden"
                style={{ width: 40, height: 40, border: "1px solid var(--border-soft)" }}>
                <Image src="/brand/oui-parfum.png" alt="ClubAgent" width={40} height={40} className="object-cover w-full h-full" priority />
              </div>
              <div>
                <p className="text-xs font-medium uppercase tracking-wider" style={{ color: "var(--text-muted)" }}>
                  ClubAgent 운영 센터
                </p>
                <p className="text-sm font-semibold" style={{ color: "var(--text-main)" }}>
                  부원 {loading ? "…" : num(summary?.total_members)}명 · 활동 {loading ? "…" : num(summary?.total_activity_reports)}건
                </p>
              </div>
            </div>
            <Link
              href="/assistant"
              className="flex items-center gap-1.5 rounded-xl px-3 py-2 text-xs font-medium transition-opacity hover:opacity-85 shrink-0"
              style={{ background: "var(--primary)", color: "#fff" }}
            >
              <Bot className="h-3.5 w-3.5" />
              AI 작업실
            </Link>
          </div>
        </Card>

        {/* 1. Monthly calendar */}
        <section>
          <h2 className="text-sm font-semibold mb-3" style={{ color: "var(--text-main)" }}>월간 활동 캘린더</h2>
          <DashboardCalendar />
        </section>

        {/* 2. Summary cards */}
        <DashboardSummaryCards summary={summary} loading={loading} />

        {/* 3. Todo list */}
        <DashboardTodoList summary={summary} todo={todo} loading={loading} />

        {/* 4. Quick links */}
        <Card padding="md">
          <div className="flex items-start gap-3">
            <div className="rounded-xl p-2 shrink-0" style={{ background: "var(--primary-soft)" }}>
              <Bot className="h-4 w-4" style={{ color: "var(--primary)" }} />
            </div>
            <div className="flex-1">
              <h3 className="text-sm font-semibold mb-2" style={{ color: "var(--text-main)" }}>바로가기</h3>
              <div className="flex flex-wrap gap-2">
                {[
                  { label: "AI 작업실", href: "/assistant" },
                  { label: "활동 관리", href: "/activities" },
                  { label: "부원 관리", href: "/members" },
                  { label: "납부 현황", href: "/payments" },
                  { label: "거래내역", href: "/transactions" },
                  { label: "영수증", href: "/receipts" },
                ].map((link) => (
                  <Link key={link.label} href={link.href}
                    className="rounded-lg px-2.5 py-1 text-xs font-medium transition-opacity hover:opacity-75"
                    style={{ background: "var(--primary-soft)", color: "var(--primary)" }}>
                    {link.label}
                  </Link>
                ))}
              </div>
            </div>
          </div>
        </Card>
      </div>
    </AppShell>
  );
}
