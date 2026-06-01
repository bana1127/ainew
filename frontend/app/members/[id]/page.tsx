"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { ArrowLeft, Calendar, MapPin } from "lucide-react";

import { AppShell } from "@/components/layout/AppShell";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { ErrorState } from "@/components/ui/ErrorState";
import { LoadingState } from "@/components/ui/LoadingState";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { type MemberSummaryDetail, getMemberSummary } from "@/lib/api";

function fmt(n: number): string {
  return n.toLocaleString("ko-KR");
}

function statusLabel(status: string): string {
  const map: Record<string, string> = {
    active: "활동중",
    inactive: "비활성",
    graduated: "졸업",
    paused: "휴면",
    paid: "납부 완료",
    unpaid: "미납",
    partial: "부분 납부",
    exempt: "면제",
    need_check: "확인 필요",
    planned: "예정",
    in_progress: "진행 중",
    done: "완료",
    draft: "초안",
    confirmed: "확정",
    archived: "보관",
  };
  return map[status] ?? status;
}

export default function MemberDetailPage() {
  const params = useParams();
  const router = useRouter();
  const memberId = params?.id as string;

  const [data, setData] = useState<MemberSummaryDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!memberId) return;
    setLoading(true);
    getMemberSummary(memberId)
      .then(setData)
      .catch((err: unknown) => {
        setError(err instanceof Error ? err.message : "부원 정보를 불러오지 못했습니다.");
      })
      .finally(() => setLoading(false));
  }, [memberId]);

  if (loading) return <AppShell><LoadingState /></AppShell>;
  if (error || !data) {
    return (
      <AppShell>
        <ErrorState message={error ?? "부원을 찾을 수 없습니다."} />
      </AppShell>
    );
  }

  const { member, activities, membership_payments, activity_fee_payments, summary } = data;
  const unpaidMembership = membership_payments.filter((p) => p.status === "unpaid").length;
  const unpaidActivityFee = activity_fee_payments.filter((p) => p.status === "unpaid").length;

  return (
    <AppShell>
      <div className="space-y-5">
        {/* Back */}
        <button
          onClick={() => router.push("/members")}
          className="flex items-center gap-1 text-sm hover:opacity-75 transition-opacity"
          style={{ color: "var(--text-muted)" }}
        >
          <ArrowLeft className="h-3.5 w-3.5" />
          부원 목록
        </button>

        {/* Profile card */}
        <Card padding="lg">
          <div className="flex items-start justify-between gap-4">
            <div>
              <div className="flex items-center gap-3 mb-2">
                <h1 className="text-xl font-semibold" style={{ color: "var(--text-main)" }}>
                  {member.name}
                </h1>
                <StatusBadge status={member.status} />
              </div>
              <div className="space-y-1">
                {member.student_id && (
                  <p className="text-sm" style={{ color: "var(--text-muted)" }}>
                    학번: {member.student_id}
                  </p>
                )}
                {member.department && (
                  <p className="text-sm" style={{ color: "var(--text-muted)" }}>
                    학과: {member.department}
                  </p>
                )}
                {member.phone && (
                  <p className="text-sm" style={{ color: "var(--text-muted)" }}>
                    전화: {member.phone}
                  </p>
                )}
                {member.email && (
                  <p className="text-sm" style={{ color: "var(--text-muted)" }}>
                    이메일: {member.email}
                  </p>
                )}
                {member.memo && (
                  <p className="text-sm mt-2" style={{ color: "var(--text-muted)" }}>
                    메모: {member.memo}
                  </p>
                )}
              </div>
            </div>
          </div>
        </Card>

        {/* Summary cards */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {[
            {
              label: "참여 활동",
              value: summary.activity_count,
              style: {},
            },
            {
              label: "회비 납부",
              value: `${summary.membership_paid_count}건`,
              style: summary.unpaid_membership_count > 0
                ? { background: "var(--warning-soft)", border: "1px solid rgba(185,130,43,0.15)" }
                : {},
            },
            {
              label: "회비 미납",
              value: summary.unpaid_membership_count,
              style: summary.unpaid_membership_count > 0
                ? { background: "var(--danger-soft)", border: "1px solid rgba(185,74,72,0.15)" }
                : {},
            },
            {
              label: "활동비 미납",
              value: summary.unpaid_activity_fee_count,
              style: summary.unpaid_activity_fee_count > 0
                ? { background: "var(--danger-soft)", border: "1px solid rgba(185,74,72,0.15)" }
                : {},
            },
          ].map((card) => (
            <div
              key={card.label}
              className="rounded-2xl p-4"
              style={{
                background: "var(--surface)",
                border: "1px solid var(--border-soft)",
                boxShadow: "0 1px 4px 0 rgba(31,31,36,0.04)",
                ...card.style,
              }}
            >
              <p className="text-xs mb-1.5" style={{ color: "var(--text-muted)" }}>{card.label}</p>
              <p className="text-xl font-semibold" style={{ color: "var(--text-main)" }}>{card.value}</p>
            </div>
          ))}
        </div>

        {/* Activities */}
        <Card padding="none">
          <div
            className="p-4"
            style={{ borderBottom: "1px solid var(--border-soft)" }}
          >
            <h2 className="text-sm font-semibold" style={{ color: "var(--text-main)" }}>
              참여 활동 ({activities.length}건)
            </h2>
          </div>
          {activities.length === 0 ? (
            <div className="p-6 text-center">
              <p className="text-sm" style={{ color: "var(--text-muted)" }}>참여한 활동이 없습니다.</p>
            </div>
          ) : (
            <>
              {/* Desktop */}
              <div className="hidden md:block overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr style={{ background: "var(--surface-soft)", borderBottom: "1px solid var(--border-soft)" }}>
                      {["활동명", "활동일", "장소", "역할", "상태", "상세"].map((h) => (
                        <th
                          key={h}
                          className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide"
                          style={{ color: "var(--text-muted)" }}
                        >
                          {h}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {activities.map((a) => (
                      <tr
                        key={a.id}
                        style={{ borderBottom: "1px solid var(--border-soft)" }}
                        onMouseEnter={(e) => (e.currentTarget.style.background = "var(--surface-soft)")}
                        onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}
                      >
                        <td className="px-4 py-3 font-medium" style={{ color: "var(--text-main)" }}>
                          {a.title}
                        </td>
                        <td className="px-4 py-3 text-xs" style={{ color: "var(--text-muted)" }}>
                          {a.activity_date ?? "-"}
                        </td>
                        <td className="px-4 py-3 text-xs" style={{ color: "var(--text-muted)" }}>
                          {a.location ?? "-"}
                        </td>
                        <td className="px-4 py-3 text-xs" style={{ color: "var(--text-muted)" }}>
                          {a.role ?? "participant"}
                        </td>
                        <td className="px-4 py-3">
                          <StatusBadge status={a.status} />
                        </td>
                        <td className="px-4 py-3">
                          <Link href={`/activities/${a.id}`}>
                            <Button size="sm" variant="ghost">보기</Button>
                          </Link>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              {/* Mobile */}
              <div className="md:hidden divide-y" style={{ borderTop: "1px solid var(--border-soft)" }}>
                {activities.map((a) => (
                  <div key={a.id} className="p-4">
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex-1 min-w-0">
                        <p className="font-medium text-sm" style={{ color: "var(--text-main)" }}>
                          {a.title}
                        </p>
                        <div className="flex flex-wrap gap-2 mt-1">
                          {a.activity_date && (
                            <span className="flex items-center gap-1 text-xs" style={{ color: "var(--text-muted)" }}>
                              <Calendar className="h-3 w-3" />
                              {a.activity_date}
                            </span>
                          )}
                          {a.location && (
                            <span className="flex items-center gap-1 text-xs" style={{ color: "var(--text-muted)" }}>
                              <MapPin className="h-3 w-3" />
                              {a.location}
                            </span>
                          )}
                        </div>
                      </div>
                      <div className="flex items-center gap-2 shrink-0">
                        <StatusBadge status={a.status} />
                        <Link href={`/activities/${a.id}`}>
                          <Button size="sm" variant="ghost">보기</Button>
                        </Link>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </>
          )}
        </Card>

        {/* Membership payments */}
        <Card padding="none">
          <div
            className="p-4"
            style={{ borderBottom: "1px solid var(--border-soft)" }}
          >
            <div className="flex items-center justify-between">
              <h2 className="text-sm font-semibold" style={{ color: "var(--text-main)" }}>
                회비 납부 이력 ({membership_payments.length}건)
              </h2>
              {unpaidMembership > 0 && (
                <span className="text-xs rounded-full px-2.5 py-1"
                  style={{ background: "var(--danger-soft)", color: "var(--danger)" }}>
                  미납 {unpaidMembership}건
                </span>
              )}
            </div>
          </div>
          {membership_payments.length === 0 ? (
            <div className="p-6 text-center">
              <p className="text-sm" style={{ color: "var(--text-muted)" }}>회비 납부 이력이 없습니다.</p>
            </div>
          ) : (
            <>
              {/* Desktop */}
              <div className="hidden md:block overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr style={{ background: "var(--surface-soft)", borderBottom: "1px solid var(--border-soft)" }}>
                      {["기간", "필요 금액", "납부 금액", "상태"].map((h) => (
                        <th key={h} className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide"
                          style={{ color: "var(--text-muted)" }}>{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {membership_payments.map((p) => (
                      <tr key={p.id} style={{ borderBottom: "1px solid var(--border-soft)" }}
                        onMouseEnter={(e) => (e.currentTarget.style.background = "var(--surface-soft)")}
                        onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}>
                        <td className="px-4 py-3" style={{ color: "var(--text-main)" }}>{p.period}</td>
                        <td className="px-4 py-3 text-right" style={{ color: "var(--text-main)" }}>
                          {fmt(p.required_amount)}원
                        </td>
                        <td className="px-4 py-3 text-right" style={{ color: "var(--text-main)" }}>
                          {fmt(p.paid_amount)}원
                        </td>
                        <td className="px-4 py-3"><StatusBadge status={p.status} /></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              {/* Mobile */}
              <div className="md:hidden divide-y" style={{ borderTop: "1px solid var(--border-soft)" }}>
                {membership_payments.map((p) => (
                  <div key={p.id} className="p-4 flex items-center justify-between">
                    <div>
                      <p className="font-medium text-sm" style={{ color: "var(--text-main)" }}>{p.period}</p>
                      <p className="text-xs mt-0.5" style={{ color: "var(--text-muted)" }}>
                        필요: {fmt(p.required_amount)}원 / 납부: {fmt(p.paid_amount)}원
                      </p>
                    </div>
                    <StatusBadge status={p.status} />
                  </div>
                ))}
              </div>
            </>
          )}
        </Card>

        {/* Activity fee payments */}
        <Card padding="none">
          <div
            className="p-4"
            style={{ borderBottom: "1px solid var(--border-soft)" }}
          >
            <div className="flex items-center justify-between">
              <h2 className="text-sm font-semibold" style={{ color: "var(--text-main)" }}>
                활동비 납부 이력 ({activity_fee_payments.length}건)
              </h2>
              {unpaidActivityFee > 0 && (
                <span className="text-xs rounded-full px-2.5 py-1"
                  style={{ background: "var(--danger-soft)", color: "var(--danger)" }}>
                  미납 {unpaidActivityFee}건
                </span>
              )}
            </div>
          </div>
          {activity_fee_payments.length === 0 ? (
            <div className="p-6 text-center">
              <p className="text-sm" style={{ color: "var(--text-muted)" }}>활동비 납부 이력이 없습니다.</p>
            </div>
          ) : (
            <>
              {/* Desktop */}
              <div className="hidden md:block overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr style={{ background: "var(--surface-soft)", borderBottom: "1px solid var(--border-soft)" }}>
                      {["활동 기간", "필요 금액", "납부 금액", "상태"].map((h) => (
                        <th key={h} className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide"
                          style={{ color: "var(--text-muted)" }}>{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {activity_fee_payments.map((p) => (
                      <tr key={p.id} style={{ borderBottom: "1px solid var(--border-soft)" }}
                        onMouseEnter={(e) => (e.currentTarget.style.background = "var(--surface-soft)")}
                        onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}>
                        <td className="px-4 py-3" style={{ color: "var(--text-main)" }}>{p.period}</td>
                        <td className="px-4 py-3 text-right" style={{ color: "var(--text-main)" }}>
                          {fmt(p.required_amount)}원
                        </td>
                        <td className="px-4 py-3 text-right" style={{ color: "var(--text-main)" }}>
                          {fmt(p.paid_amount)}원
                        </td>
                        <td className="px-4 py-3"><StatusBadge status={p.status} /></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              {/* Mobile */}
              <div className="md:hidden divide-y" style={{ borderTop: "1px solid var(--border-soft)" }}>
                {activity_fee_payments.map((p) => (
                  <div key={p.id} className="p-4 flex items-center justify-between">
                    <div>
                      <p className="font-medium text-sm" style={{ color: "var(--text-main)" }}>{p.period}</p>
                      <p className="text-xs mt-0.5" style={{ color: "var(--text-muted)" }}>
                        필요: {fmt(p.required_amount)}원 / 납부: {fmt(p.paid_amount)}원
                      </p>
                    </div>
                    <StatusBadge status={p.status} />
                  </div>
                ))}
              </div>
            </>
          )}
        </Card>

        {/* Quick links */}
        <div className="flex flex-wrap gap-2">
          <Link href={`/payments?tab=membership_fee`}>
            <Button size="sm" variant="secondary">회비 관리</Button>
          </Link>
          <Link href={`/payments?tab=activity_fee`}>
            <Button size="sm" variant="secondary">활동비 관리</Button>
          </Link>
        </div>
      </div>
    </AppShell>
  );
}
