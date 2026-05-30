"use client";

import { useEffect, useState } from "react";
import { Activity, Bell, CreditCard, ReceiptText } from "lucide-react";

import { AppShell } from "@/components/layout/AppShell";
import { StatCard } from "@/components/ui/StatCard";
import { fetchHealth, type HealthResponse } from "@/lib/api";

const placeholders = [
  {
    title: "Members",
    description: "회원 DB와 CRUD API는 Task 2 이후에 연결합니다.",
  },
  {
    title: "Receipts",
    description: "영수증 OCR과 파일 파싱은 이후 Task에서 구현합니다.",
  },
  {
    title: "Transactions",
    description: "거래내역 업로드와 매칭 로직은 placeholder 상태입니다.",
  },
  {
    title: "Notifications",
    description: "Slack, Telegram, Notion, n8n 연동은 아직 구현하지 않습니다.",
  },
];

export default function DashboardPage() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchHealth()
      .then((data) => {
        setHealth(data);
        setError(null);
      })
      .catch(() => {
        setError("Backend health API에 연결할 수 없습니다.");
      });
  }, []);

  const databaseStatus = health?.database ?? "checking";
  const apiStatus = error ? "unavailable" : health?.status ?? "checking";

  return (
    <AppShell>
      <section className="space-y-6">
        <div className="flex flex-col gap-2">
          <p className="text-sm font-medium text-pine">ClubAgent Admin</p>
          <h1 className="text-3xl font-semibold text-ink">Dashboard</h1>
          <p className="max-w-2xl text-sm leading-6 text-gray-600">
            동아리 운영 자동화를 위한 1차 기반 구조입니다. 이번 Task에서는 health
            API와 기본 관리자 화면만 연결합니다.
          </p>
        </div>

        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <StatCard
            icon={Activity}
            label="Backend API"
            value={apiStatus}
            tone={error ? "danger" : "success"}
          />
          <StatCard
            icon={CreditCard}
            label="Database"
            value={databaseStatus}
            tone={databaseStatus === "configured" ? "success" : "warning"}
          />
          <StatCard icon={ReceiptText} label="Task Scope" value="Task 1" tone="neutral" />
          <StatCard icon={Bell} label="Integrations" value="TODO" tone="neutral" />
        </div>

        <div className="grid gap-4 lg:grid-cols-2">
          <div className="rounded-lg border border-line bg-white p-5 shadow-sm">
            <div className="flex items-center justify-between gap-4">
              <div>
                <h2 className="text-base font-semibold text-ink">Health API</h2>
                <p className="mt-1 text-sm text-gray-600">
                  Frontend에서 Backend `/api/health` 응답을 확인합니다.
                </p>
              </div>
              <span className="rounded-full bg-mist px-3 py-1 text-xs font-medium text-ink">
                {process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000"}
              </span>
            </div>
            <pre className="mt-4 overflow-auto rounded-md bg-ink p-4 text-sm text-white">
              {error
                ? JSON.stringify({ status: "error", message: error }, null, 2)
                : JSON.stringify(health ?? { status: "checking" }, null, 2)}
            </pre>
          </div>

          <div className="rounded-lg border border-line bg-white p-5 shadow-sm">
            <h2 className="text-base font-semibold text-ink">Task 1 Boundaries</h2>
            <div className="mt-4 grid gap-3 sm:grid-cols-2">
              {placeholders.map((item) => (
                <div key={item.title} className="rounded-md border border-line p-4">
                  <h3 className="text-sm font-semibold text-ink">{item.title}</h3>
                  <p className="mt-2 text-sm leading-5 text-gray-600">{item.description}</p>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>
    </AppShell>
  );
}

