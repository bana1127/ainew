"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { ChevronLeft, ChevronRight, Plus } from "lucide-react";
import { useEffect, useState } from "react";
import {
  createActivity,
  getDashboardCalendar,
  getActivityCategoriesTyped,
  type ActivityCategory,
  type CalendarEvent,
} from "@/lib/api";

const WEEKDAYS = ["일", "월", "화", "수", "목", "금", "토"];

function toYM(d: Date): string {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
}

function isSameDay(a: string, b: Date): boolean {
  const [y, m, day] = a.split("-").map(Number);
  return y === b.getFullYear() && m === b.getMonth() + 1 && day === b.getDate();
}

function statusDot(event: CalendarEvent): string {
  if (event.status === "completed") return "var(--success)";
  if (event.status === "in_progress") return "var(--primary)";
  if (event.needs_report || event.needs_evidence || event.fee_status === "unpaid") return "var(--warning)";
  return "var(--text-muted)";
}

function eventTooltip(ev: CalendarEvent): string {
  const parts = [ev.title];
  if (ev.location) parts.push(ev.location);
  if (ev.participant_count !== undefined && ev.participant_count > 0) parts.push(`${ev.participant_count}명`);
  if (ev.fee_status === "unpaid") parts.push("활동비 미납");
  return parts.join(" · ");
}

export function DashboardCalendar() {
  const today = new Date();
  const router = useRouter();
  const [currentDate, setCurrentDate] = useState(new Date(today.getFullYear(), today.getMonth(), 1));
  const [events, setEvents] = useState<CalendarEvent[]>([]);
  const [loading, setLoading] = useState(true);

  // Add-activity modal state
  const [addDate, setAddDate] = useState<string | null>(null);
  const [categories, setCategories] = useState<ActivityCategory[]>([]);
  const [newTitle, setNewTitle] = useState("");
  const [newLocation, setNewLocation] = useState("");
  const [newCategoryId, setNewCategoryId] = useState("");
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    getDashboardCalendar(toYM(currentDate))
      .then((data) => setEvents(data.events))
      .catch(() => setEvents([]))
      .finally(() => setLoading(false));
  }, [currentDate]);

  useEffect(() => {
    if (addDate) {
      getActivityCategoriesTyped().then(setCategories).catch(() => {});
    }
  }, [addDate]);

  function openAddModal(ds: string) {
    setAddDate(ds);
    setNewTitle("");
    setNewLocation("");
    setNewCategoryId("");
    setSaveError(null);
  }

  async function handleSave(navigate: boolean) {
    if (!addDate || !newTitle.trim()) return;
    setSaving(true);
    setSaveError(null);
    try {
      const created = await createActivity({
        title: newTitle.trim(),
        activity_date: addDate,
        location: newLocation.trim() || null,
        category_id: newCategoryId || null,
        status: "planned",
      });
      setAddDate(null);
      getDashboardCalendar(toYM(currentDate))
        .then((data) => setEvents(data.events))
        .catch(() => {});
      if (navigate) {
        router.push(`/activities/${created.id}`);
      }
    } catch (err: unknown) {
      setSaveError(err instanceof Error ? err.message : "활동 생성 실패");
    } finally {
      setSaving(false);
    }
  }

  function prev() {
    setCurrentDate((d) => new Date(d.getFullYear(), d.getMonth() - 1, 1));
  }
  function next() {
    setCurrentDate((d) => new Date(d.getFullYear(), d.getMonth() + 1, 1));
  }

  // Build calendar grid
  const year = currentDate.getFullYear();
  const month = currentDate.getMonth();
  const firstDow = new Date(year, month, 1).getDay(); // 0=Sun
  const daysInMonth = new Date(year, month + 1, 0).getDate();

  // cells: null = empty, number = date
  const cells: (number | null)[] = [];
  for (let i = 0; i < firstDow; i++) cells.push(null);
  for (let d = 1; d <= daysInMonth; d++) cells.push(d);
  // pad to full weeks
  while (cells.length % 7 !== 0) cells.push(null);

  function eventsForDay(day: number): CalendarEvent[] {
    const ds = `${year}-${String(month + 1).padStart(2, "0")}-${String(day).padStart(2, "0")}`;
    return events.filter((e) => e.date === ds);
  }

  const isToday = (day: number) =>
    today.getFullYear() === year && today.getMonth() === month && today.getDate() === day;

  return (
    <>
    <div className="rounded-2xl overflow-hidden" style={{ border: "1px solid var(--border-soft)", background: "var(--surface)" }}>
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3" style={{ borderBottom: "1px solid var(--border-soft)" }}>
        <button
          onClick={prev}
          className="p-1.5 rounded-lg transition-all hover:opacity-75"
          style={{ color: "var(--text-muted)", background: "var(--surface-soft)", border: "1px solid var(--border-soft)" }}
        >
          <ChevronLeft className="h-4 w-4" />
        </button>
        <div className="text-center">
          <p className="text-sm font-semibold" style={{ color: "var(--text-main)" }}>
            {year}년 {month + 1}월
          </p>
          {loading && <p className="text-xs" style={{ color: "var(--text-muted)" }}>로딩 중…</p>}
          {!loading && (
            <p className="text-xs" style={{ color: "var(--text-muted)" }}>
              활동 {events.length}건
            </p>
          )}
        </div>
        <button
          onClick={next}
          className="p-1.5 rounded-lg transition-all hover:opacity-75"
          style={{ color: "var(--text-muted)", background: "var(--surface-soft)", border: "1px solid var(--border-soft)" }}
        >
          <ChevronRight className="h-4 w-4" />
        </button>
      </div>

      {/* Calendar grid — scrollable on mobile */}
      <div className="overflow-x-auto">
        <div style={{ minWidth: 320 }}>
          {/* Weekday header */}
          <div className="grid grid-cols-7">
            {WEEKDAYS.map((wd, i) => (
              <div key={wd} className="py-2 text-center text-xs font-medium"
                style={{ color: i === 0 ? "var(--danger)" : i === 6 ? "var(--primary)" : "var(--text-muted)" }}>
                {wd}
              </div>
            ))}
          </div>

          {/* Date cells */}
          <div className="grid grid-cols-7" style={{ borderTop: "1px solid var(--border-soft)" }}>
            {cells.map((day, idx) => {
              const dow = idx % 7;
              const dayEvents = day ? eventsForDay(day) : [];
              const isT = day !== null && isToday(day);
              return (
                <div
                  key={idx}
                  className="p-1.5 min-h-[72px] text-xs"
                  style={{
                    borderRight: dow < 6 ? "1px solid var(--border-soft)" : "none",
                    borderBottom: idx < cells.length - 7 ? "1px solid var(--border-soft)" : "none",
                    background: isT ? "var(--primary-soft, rgba(99,102,241,0.06))" : "transparent",
                  }}
                >
                  {day !== null && (
                    <>
                      <div className="flex items-center justify-between mb-1">
                        <span
                          className="inline-flex items-center justify-center h-5 w-5 rounded-full text-xs font-medium cursor-pointer hover:opacity-75 transition-opacity"
                          style={{
                            background: isT ? "var(--primary)" : "transparent",
                            color: isT ? "#fff" : dow === 0 ? "var(--danger)" : dow === 6 ? "var(--primary)" : "var(--text-main)",
                          }}
                          onClick={() => {
                            const ds = `${year}-${String(month + 1).padStart(2, "0")}-${String(day).padStart(2, "0")}`;
                            openAddModal(ds);
                          }}
                          title="이 날짜에 활동 추가"
                        >
                          {day}
                        </span>
                        <span
                          className="h-3.5 w-3.5 rounded flex items-center justify-center opacity-0 hover:opacity-100 group-hover:opacity-60 cursor-pointer transition-opacity"
                          style={{ color: "var(--text-muted)" }}
                          onClick={() => {
                            const ds = `${year}-${String(month + 1).padStart(2, "0")}-${String(day).padStart(2, "0")}`;
                            openAddModal(ds);
                          }}
                        >
                          <Plus className="h-3 w-3" />
                        </span>
                      </div>
                      <div className="space-y-0.5">
                        {dayEvents.slice(0, 2).map((ev) => (
                          <Link key={ev.id} href={ev.url}>
                            <div
                              className="flex items-center gap-1 rounded px-1 py-0.5 truncate cursor-pointer hover:opacity-80 transition-opacity"
                              style={{ background: "var(--surface-soft)", border: "1px solid var(--border-soft)" }}
                              title={eventTooltip(ev)}
                            >
                              <span
                                className="shrink-0 h-1.5 w-1.5 rounded-full"
                                style={{ background: statusDot(ev) }}
                              />
                              <span className="truncate text-xs" style={{ color: "var(--text-main)", fontSize: 10 }}>
                                {ev.title}
                              </span>
                            </div>
                          </Link>
                        ))}
                        {dayEvents.length > 2 && (
                          <p className="text-xs" style={{ color: "var(--text-muted)", fontSize: 10 }}>
                            +{dayEvents.length - 2}개 더
                          </p>
                        )}
                      </div>
                    </>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Legend */}
      <div className="flex flex-wrap gap-3 px-4 py-2.5" style={{ borderTop: "1px solid var(--border-soft)" }}>
        {[
          { color: "var(--success)", label: "완료" },
          { color: "var(--primary)", label: "진행 중" },
          { color: "var(--warning)", label: "처리 필요" },
          { color: "var(--text-muted)", label: "예정" },
        ].map(({ color, label }) => (
          <div key={label} className="flex items-center gap-1">
            <span className="h-2 w-2 rounded-full shrink-0" style={{ background: color }} />
            <span className="text-xs" style={{ color: "var(--text-muted)" }}>{label}</span>
          </div>
        ))}
      </div>
    </div>

    {/* Add Activity Modal */}

    {addDate && (
      <div
        className="fixed inset-0 z-50 flex items-center justify-center"
        style={{ background: "rgba(31,31,36,0.45)" }}
        onClick={(e) => { if (e.target === e.currentTarget) setAddDate(null); }}
      >
        <div
          className="w-full max-w-md rounded-2xl p-6 space-y-4 shadow-lg"
          style={{ background: "var(--surface)", border: "1px solid var(--border-soft)" }}
        >
          <h3 className="text-base font-semibold" style={{ color: "var(--text-main)" }}>
            활동 추가 — {addDate}
          </h3>
          <div className="space-y-3">
            <div>
              <label className="block text-xs font-medium mb-1" style={{ color: "var(--text-muted)" }}>활동명 *</label>
              <input
                type="text"
                value={newTitle}
                onChange={(e) => setNewTitle(e.target.value)}
                placeholder="활동명 입력"
                className="w-full rounded-xl px-3 py-2 text-sm focus:outline-none min-h-[44px]"
                style={{ background: "var(--surface)", color: "var(--text-main)", border: "1px solid var(--border-soft)", fontSize: 16 }}
                autoFocus
              />
            </div>
            <div>
              <label className="block text-xs font-medium mb-1" style={{ color: "var(--text-muted)" }}>장소</label>
              <input
                type="text"
                value={newLocation}
                onChange={(e) => setNewLocation(e.target.value)}
                placeholder="장소 입력"
                className="w-full rounded-xl px-3 py-2 text-sm focus:outline-none min-h-[44px]"
                style={{ background: "var(--surface)", color: "var(--text-main)", border: "1px solid var(--border-soft)", fontSize: 16 }}
              />
            </div>
            {categories.length > 0 && (
              <div>
                <label className="block text-xs font-medium mb-1" style={{ color: "var(--text-muted)" }}>카테고리</label>
                <select
                  value={newCategoryId}
                  onChange={(e) => setNewCategoryId(e.target.value)}
                  className="w-full rounded-xl px-3 py-2 text-sm focus:outline-none min-h-[44px]"
                  style={{ background: "var(--surface)", color: "var(--text-main)", border: "1px solid var(--border-soft)", fontSize: 16 }}
                >
                  <option value="">카테고리 없음</option>
                  {categories.map((c) => (
                    <option key={c.id} value={c.id}>{c.name}</option>
                  ))}
                </select>
              </div>
            )}
          </div>
          {saveError && <p className="text-sm" style={{ color: "var(--danger)" }}>{saveError}</p>}
          <div className="flex flex-col sm:flex-row gap-2 pt-1">
            <button
              className="flex-1 rounded-xl px-4 py-2.5 text-sm font-medium min-h-[44px] transition-opacity hover:opacity-80"
              style={{ background: "var(--primary)", color: "#fff" }}
              disabled={saving || !newTitle.trim()}
              onClick={() => handleSave(false)}
            >
              {saving ? "저장 중…" : "저장"}
            </button>
            <button
              className="flex-1 rounded-xl px-4 py-2.5 text-sm font-medium min-h-[44px] transition-opacity hover:opacity-80"
              style={{ background: "var(--surface-soft)", color: "var(--text-main)", border: "1px solid var(--border-soft)" }}
              disabled={saving || !newTitle.trim()}
              onClick={() => handleSave(true)}
            >
              저장 후 상세 이동
            </button>
            <button
              className="rounded-xl px-4 py-2.5 text-sm font-medium min-h-[44px] transition-opacity hover:opacity-75"
              style={{ background: "transparent", color: "var(--text-muted)" }}
              disabled={saving}
              onClick={() => setAddDate(null)}
            >
              취소
            </button>
          </div>
        </div>
      </div>
    )}
    </>
  );
}
