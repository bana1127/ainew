"use client";

import { useEffect, useState } from "react";
import Image from "next/image";
import Link from "next/link";
import {
  Activity,
  AlertTriangle,
  Bell,
  Bot,
  CreditCard,
  FileText,
  PenLine,
  ReceiptText,
  Users,
  WalletCards,
} from "lucide-react";

import { AppShell } from "@/components/layout/AppShell";
import { Card } from "@/components/ui/Card";
import { StatCard } from "@/components/ui/StatCard";
import {
  getDashboardSummary,
  getActivities,
  type DashboardSummary,
  type ActivitySummary,
} from "@/lib/api";

function num(v: number | undefined): string {
  return v === undefined ? "—" : v.toLocaleString();
}

const TODAY_ITEMS = [
  {
    key: "pending_receipts" as keyof DashboardSummary,
    label: "확인 필요 영수증",
    href: "/receipts",
    icon: ReceiptText,
    urgent: (v: number) => v > 0,
  },
  {
    key: "unpaid_membership_fee_count" as keyof DashboardSummary,
    label: "회비 미납",
    href: "/payments?tab=membership_fee",
    icon: CreditCard,
    urgent: (v: number) => v > 0,
  },
  {
    key: "unpaid_activity_fee_count" as keyof DashboardSummary,
    label: "활동비 미납 건",
    href: "/payments?tab=activity_fee",
    icon: WalletCards,
    urgent: (v: number) => v > 0,
  },
  {
    key: "draft_reports" as keyof DashboardSummary,
    label: "작성 중 보고서",
    href: "/activities",
    icon: PenLine,
    urgent: (_v: number) => false,
  },
  {
    key: "unread_notifications" as keyof DashboardSummary,
    label: "읽지 않은 알림",
    href: "/notifications",
    icon: Bell,
    urgent: (v: number) => v > 0,
  },
];

type ActivityMetrics = {
  inProgress: number;
  noReport: number;
  feeUnpaid: number;
  needCheck: number;
};

export default function DashboardPage() {
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [activityMetrics, setActivityMetrics] = useState<ActivityMetrics | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      getDashboardSummary(),
      getActivities({ limit: 100 }),
    ])
      .then(([data, activities]) => {
        setSummary(data);
        const active = activities.filter((a: ActivitySummary) => a.status !== "archived");
        setActivityMetrics({
          inProgress: active.filter((a: ActivitySummary) => a.status === "in_progress").length,
          noReport: active.filter((a: ActivitySummary) =>
            a.report_status === "draft" || a.report_status === "planned"
          ).length,
          feeUnpaid: active.filter((a: ActivitySummary) =>
            a.activity_fee_status !== "미설정" && a.activity_fee_status.startsWith("0/")
          ).length,
          needCheck: active.reduce((acc: number, a: ActivitySummary) => acc + a.need_check_count, 0),
        });
      })
      .catch((err: Error) => { setError(err.message || "Backend API 연결 실패"); })
      .finally(() => setLoading(false));
  }, []);

  return (
    <AppShell>
      <div className="space-y-7">
        {/* Error banner */}
        {error && (
          <div
            className="flex items-center gap-3 rounded-xl px-4 py-3"
            style={{ background: "var(--danger-soft)", border: "1px solid rgba(185,74,72,0.15)" }}
          >
            <AlertTriangle className="h-4 w-4 shrink-0" style={{ color: "var(--danger)" }} />
            <p className="text-sm" style={{ color: "var(--danger)" }}>
              {error} — 백엔드가 실행 중인지 확인하세요.
            </p>
          </div>
        )}

        {/* 1. Brand Hero */}
        <Card padding="lg">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-5">
            {/* Left: brand + title */}
            <div className="flex items-center gap-4">
              <div
                className="shrink-0 rounded-full overflow-hidden"
                style={{
                  width: 64,
                  height: 64,
                  border: "1px solid var(--border-soft)",
                  background: "var(--surface)",
                }}
              >
                <Image
                  src="/brand/oui-parfum.png"
                  alt="ClubAgent"
                  width={64}
                  height={64}
                  className="object-cover w-full h-full"
                  priority
                />
              </div>
              <div>
                <p
                  className="text-xs font-medium uppercase tracking-wider mb-1"
                  style={{ color: "var(--text-muted)" }}
                >
                  ClubAgent 운영 센터
                </p>
                <h2
                  className="text-lg font-semibold leading-tight"
                  style={{ color: "var(--text-main)" }}
                >
                  동아리 운영에 필요한 문서, 예산,
                  <br className="hidden sm:block" />
                  납부 상태를 한 곳에서 확인하세요.
                </h2>
                <p className="text-xs mt-1.5" style={{ color: "var(--text-muted)" }}>
                  부원 {loading ? "…" : num(summary?.total_members)}명 ·{" "}
                  보고서 {loading ? "…" : num(summary?.total_activity_reports)}건
                </p>
              </div>
            </div>

            {/* Right: CTAs */}
            <div className="flex flex-wrap sm:flex-col gap-2 sm:items-stretch">
              <Link
                href="/assistant"
                className="flex items-center justify-center gap-2 rounded-xl px-4 py-2.5 text-sm font-medium transition-opacity hover:opacity-85"
                style={{ background: "var(--primary)", color: "#fff" }}
              >
                <Bot className="h-4 w-4" />
                AI 작업실 열기
              </Link>
              <Link
                href="/payments"
                className="flex items-center justify-center gap-2 rounded-xl px-4 py-2.5 text-sm font-medium transition-opacity hover:opacity-80"
                style={{
                  background: "var(--surface-soft)",
                  color: "var(--text-main)",
                  border: "1px solid var(--border-soft)",
                }}
              >
                <CreditCard className="h-4 w-4" />
                운영 데이터 확인
              </Link>
            </div>
          </div>
        </Card>

        {/* 2. 오늘 처리할 일 */}
        <section>
          <h2 className="text-sm font-semibold mb-3" style={{ color: "var(--text-main)" }}>
            오늘 처리할 일
          </h2>
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
            {TODAY_ITEMS.map((item) => {
              const Icon = item.icon;
              const raw = summary ? (summary[item.key] as number) : undefined;
              const val = loading ? null : (raw ?? 0);
              const isUrgent = !loading && raw !== undefined && item.urgent(raw);
              return (
                <Link key={item.label} href={item.href}>
                  <div
                    className="rounded-2xl p-4 cursor-pointer transition-all hover:shadow-soft"
                    style={{
                      background: isUrgent ? "var(--warning-soft)" : "var(--surface)",
                      border: isUrgent
                        ? "1px solid rgba(185,130,43,0.25)"
                        : "1px solid var(--border-soft)",
                    }}
                  >
                    <div className="flex items-center justify-between mb-3">
                      <div
                        className="rounded-xl p-2"
                        style={{
                          background: isUrgent ? "rgba(185,130,43,0.1)" : "var(--border-soft)",
                        }}
                      >
                        <Icon
                          className="h-3.5 w-3.5"
                          style={{ color: isUrgent ? "var(--warning)" : "var(--text-muted)" }}
                        />
                      </div>
                      {isUrgent && (
                        <span
                          className="h-2 w-2 rounded-full shrink-0"
                          style={{ background: "var(--warning)" }}
                        />
                      )}
                    </div>
                    <p className="text-2xl font-semibold" style={{ color: "var(--text-main)" }}>
                      {val === null ? "—" : val}
                    </p>
                    <p className="text-xs mt-1" style={{ color: "var(--text-muted)" }}>
                      {item.label}
                    </p>
                  </div>
                </Link>
              );
            })}
          </div>
        </section>

        {/* 3. 핵심 운영 요약 */}
        <section>
          <h2 className="text-sm font-semibold mb-3" style={{ color: "var(--text-main)" }}>
            운영 요약
          </h2>
          <div className="grid grid-cols-2 sm:grid-cols-2 lg:grid-cols-3 gap-3">
            <StatCard
              icon={Users}
              label="전체 부원"
              value={loading ? "…" : num(summary?.total_members)}
              tone="neutral"
            />
            <StatCard
              icon={FileText}
              label="활동 카테고리"
              value={loading ? "…" : num(summary?.total_activity_categories)}
              tone="neutral"
            />
            <StatCard
              icon={PenLine}
              label="전체 보고서"
              value={loading ? "…" : num(summary?.total_activity_reports)}
              tone="neutral"
            />
            <StatCard
              icon={WalletCards}
              label="전체 거래내역"
              value={loading ? "…" : num(summary?.total_transactions)}
              tone="neutral"
            />
            <StatCard
              icon={CreditCard}
              label="총 입금액"
              value={loading ? "…" : `${num(summary?.total_deposit_amount)}원`}
              tone="success"
            />
            <StatCard
              icon={CreditCard}
              label="총 출금액"
              value={loading ? "…" : `${num(summary?.total_withdraw_amount)}원`}
              tone="danger"
            />
          </div>
        </section>

        {/* 3-2. 활동 현황 */}
        {activityMetrics && (
          <section>
            <h2 className="text-sm font-semibold mb-3" style={{ color: "var(--text-main)" }}>
              활동 현황
            </h2>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              {[
                {
                  icon: Activity,
                  label: "진행 중 활동",
                  value: loading ? "…" : num(activityMetrics.inProgress),
                  tone: "neutral" as const,
                  href: "/activities?status=in_progress",
                },
                {
                  icon: PenLine,
                  label: "보고서 미작성",
                  value: loading ? "…" : num(activityMetrics.noReport),
                  tone: activityMetrics.noReport > 0 ? ("warning" as const) : ("neutral" as const),
                  href: "/activities",
                },
                {
                  icon: CreditCard,
                  label: "활동비 미납",
                  value: loading ? "…" : num(activityMetrics.feeUnpaid),
                  tone: activityMetrics.feeUnpaid > 0 ? ("danger" as const) : ("neutral" as const),
                  href: "/payments?tab=activity_fee",
                },
                {
                  icon: ReceiptText,
                  label: "증빙 확인 필요",
                  value: loading ? "…" : num(activityMetrics.needCheck),
                  tone: activityMetrics.needCheck > 0 ? ("warning" as const) : ("neutral" as const),
                  href: "/receipts",
                },
              ].map((item) => (
                <Link key={item.label} href={item.href}>
                  <StatCard
                    icon={item.icon}
                    label={item.label}
                    value={item.value}
                    tone={item.tone}
                  />
                </Link>
              ))}
            </div>
          </section>
        )}

        {/* 4. 추천 작업 안내 */}
        <Card padding="md">
          <div className="flex items-start gap-4">
            <div
              className="rounded-xl p-2.5 shrink-0"
              style={{ background: "var(--primary-soft)" }}
            >
              <Bot className="h-4 w-4" style={{ color: "var(--primary)" }} />
            </div>
            <div>
              <h3 className="text-sm font-semibold" style={{ color: "var(--text-main)" }}>
                추천 작업
              </h3>
              <p className="text-sm mt-1" style={{ color: "var(--text-muted)" }}>
                AI 작업실에서 영수증, 거래내역서, 활동 자료를 한 번에 올려보세요.
                자동으로 분류하고 미리보기 결과를 확인한 뒤 반영할 수 있습니다.
              </p>
              <div className="mt-3 flex flex-wrap gap-2">
                {[
                  { label: "AI 작업실로 이동 →", href: "/assistant" },
                  { label: "활동 관리", href: "/activities" },
                  { label: "부원 관리", href: "/members" },
                  { label: "납부 현황", href: "/payments" },
                ].map((link) => (
                  <Link
                    key={link.label}
                    href={link.href}
                    className="rounded-lg px-2.5 py-1 text-xs font-medium transition-opacity hover:opacity-75"
                    style={{
                      background: "var(--primary-soft)",
                      color: "var(--primary)",
                    }}
                  >
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
