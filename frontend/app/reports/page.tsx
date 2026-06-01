"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { Calendar, Copy, Download, MapPin } from "lucide-react";

import { AppShell } from "@/components/layout/AppShell";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorState } from "@/components/ui/ErrorState";
import { Input } from "@/components/ui/Input";
import { LoadingState } from "@/components/ui/LoadingState";
import { PageHeader } from "@/components/ui/PageHeader";
import { Select } from "@/components/ui/Select";
import { StatusBadge } from "@/components/ui/StatusBadge";
import {
  type ActivityCategory,
  type ActivityReport,
  deleteActivityReport,
  getActivityCategoriesTyped,
  getActivityReportsFiltered,
} from "@/lib/api";

const STATUS_FILTER_OPTIONS = [
  { value: "", label: "전체 상태" },
  { value: "draft", label: "초안" },
  { value: "generated", label: "생성됨" },
  { value: "confirmed", label: "확정" },
  { value: "archived", label: "보관 포함" },
];

function getContent(r: ActivityReport): string {
  return r.final_content ?? r.generated_content ?? r.input_text ?? "";
}

function slugify(text: string): string {
  return text.toLowerCase().replace(/[^a-z0-9가-힣]+/g, "-").slice(0, 40);
}

function downloadFile(filename: string, content: string, mime: string) {
  const blob = new Blob([content], { type: mime });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

function buildMarkdown(r: ActivityReport, categoryName: string): string {
  const content = getContent(r);
  return [
    `# ${r.title}`,
    "",
    `- 활동일: ${r.activity_date ?? "-"}`,
    `- 장소: ${r.location ?? "-"}`,
    `- 카테고리: ${categoryName}`,
    `- 상태: ${r.status}`,
    "",
    "## 본문",
    "",
    content,
  ].join("\n");
}

// ─── Report Row / Card ────────────────────────────────────────────────────────

interface ReportItemProps {
  report: ActivityReport;
  categoryName: string;
  onArchive: (r: ActivityReport) => void;
}

function ReportItem({ report, categoryName, onArchive }: ReportItemProps) {
  const content = getContent(report);
  const [copied, setCopied] = useState(false);

  async function handleCopy() {
    if (!content) return;
    try {
      await navigator.clipboard.writeText(content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch { /* ignore */ }
  }

  function handleMdDownload() {
    const date = report.activity_date ?? "unknown";
    downloadFile(
      `activity-report-${date}-${slugify(report.title)}.md`,
      buildMarkdown(report, categoryName),
      "text/markdown;charset=utf-8",
    );
  }

  function handleTxtDownload() {
    const date = report.activity_date ?? "unknown";
    downloadFile(
      `activity-report-${date}-${slugify(report.title)}.txt`,
      content,
      "text/plain;charset=utf-8",
    );
  }

  return (
    <div
      className="rounded-2xl p-5"
      style={{
        background: "var(--surface)",
        border: "1px solid var(--border-soft)",
        boxShadow: "0 1px 4px 0 rgba(31,31,36,0.05)",
      }}
    >
      {/* Header */}
      <div className="flex items-start justify-between gap-3 mb-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <StatusBadge status={report.status} />
            {categoryName && (
              <span className="text-xs" style={{ color: "var(--text-muted)" }}>{categoryName}</span>
            )}
          </div>
          <h3 className="text-sm font-semibold" style={{ color: "var(--text-main)" }}>
            {report.title}
          </h3>
          <div className="flex flex-wrap items-center gap-3 mt-1">
            {report.activity_date && (
              <span className="flex items-center gap-1 text-xs" style={{ color: "var(--text-muted)" }}>
                <Calendar className="h-3 w-3" />
                {report.activity_date}
              </span>
            )}
            {report.location && (
              <span className="flex items-center gap-1 text-xs" style={{ color: "var(--text-muted)" }}>
                <MapPin className="h-3 w-3" />
                {report.location}
              </span>
            )}
          </div>
        </div>
        <Link href={`/activities/${report.id}`}>
          <Button size="sm" variant="ghost">활동 상세</Button>
        </Link>
      </div>

      {/* Content preview */}
      {content && (
        <pre
          className="whitespace-pre-wrap text-xs leading-relaxed rounded-xl p-3 max-h-32 overflow-hidden mb-3"
          style={{
            background: "var(--surface-soft)",
            border: "1px solid var(--border-soft)",
            color: "var(--text-muted)",
            fontFamily: "inherit",
          }}
        >
          {content.slice(0, 300)}{content.length > 300 ? "…" : ""}
        </pre>
      )}

      {/* Actions */}
      <div className="flex flex-wrap gap-2">
        <Button size="sm" variant="secondary" onClick={handleCopy} disabled={!content}>
          <Copy className="h-3.5 w-3.5" />
          {copied ? "복사됨!" : "본문 복사"}
        </Button>
        <Button size="sm" variant="secondary" onClick={handleMdDownload} disabled={!content}>
          <Download className="h-3.5 w-3.5" />
          .md
        </Button>
        <Button size="sm" variant="secondary" onClick={handleTxtDownload} disabled={!content}>
          <Download className="h-3.5 w-3.5" />
          .txt
        </Button>
        {report.status !== "archived" && (
          <Button size="sm" variant="ghost" onClick={() => onArchive(report)}>
            보관
          </Button>
        )}
      </div>
    </div>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function ReportsPage() {
  const [reports, setReports] = useState<ActivityReport[]>([]);
  const [categories, setCategories] = useState<ActivityCategory[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [categoryFilter, setCategoryFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [archiving, setArchiving] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [data, cats] = await Promise.all([
        getActivityReportsFiltered({
          category_id: categoryFilter || undefined,
          status: statusFilter || undefined,
          q: search || undefined,
        }),
        getActivityCategoriesTyped(),
      ]);
      const filtered = statusFilter === ""
        ? data.filter((r) => r.status !== "archived")
        : data;
      setReports(filtered);
      setCategories(cats);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "데이터를 불러오지 못했습니다.");
    } finally {
      setLoading(false);
    }
  }, [search, categoryFilter, statusFilter]);

  useEffect(() => { load(); }, [load]);

  async function handleArchive(report: ActivityReport) {
    setArchiving(report.id);
    try {
      await deleteActivityReport(report.id);
      load();
    } catch { /* silently ignore */ }
    finally { setArchiving(null); }
  }

  const categoryMap = Object.fromEntries(categories.map((c) => [c.id, c.name]));
  const categoryFilterOptions = [
    { value: "", label: "전체 카테고리" },
    ...categories.map((c) => ({ value: c.id, label: c.name })),
  ];

  return (
    <AppShell>
      <div className="space-y-5">
        <PageHeader
          title="보고서 모아보기"
          description="전체 활동 보고서를 모아보고 복사하거나 내보낼 수 있습니다."
        />

        {/* Guide banner */}
        <div
          className="rounded-xl px-4 py-3 text-sm"
          style={{ background: "var(--primary-soft)", border: "1px solid rgba(124,108,242,0.15)" }}
        >
          <p style={{ color: "var(--primary)" }}>
            새 보고서는 <Link href="/activities" className="font-semibold underline">Activities</Link>에서
            활동을 만든 뒤 작성하세요.
            이 페이지는 전체 보고서 열람, 복사, 다운로드, 보관 용도입니다.
          </p>
        </div>

        {/* Filters */}
        <div className="flex flex-wrap gap-3">
          <Input
            placeholder="제목 / 내용 검색"
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
        ) : reports.length === 0 ? (
          <EmptyState
            message="보고서가 없습니다."
            description="Activities에서 활동을 만든 뒤 보고서를 작성하세요."
            action={
              <Link href="/activities">
                <Button size="sm">활동 관리로 이동</Button>
              </Link>
            }
          />
        ) : (
          <div className="space-y-4">
            {reports.map((r) => (
              <ReportItem
                key={r.id}
                report={r}
                categoryName={r.category_id ? (categoryMap[r.category_id] ?? "") : ""}
                onArchive={handleArchive}
              />
            ))}
          </div>
        )}
      </div>
    </AppShell>
  );
}
