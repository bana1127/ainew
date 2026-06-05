"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { CalendarDays, ChevronLeft, ChevronRight, Clock, MapPin, Trash2 } from "lucide-react";
import type { ReactNode } from "react";
import { useEffect, useMemo, useState } from "react";
import {
  createActivity,
  createCalendarEvent,
  deleteCalendarEvent,
  getActivityCategoriesTyped,
  getCalendarEvents,
  updateCalendarEvent,
  type ActivityCategory,
  type CalendarEvent,
  type CalendarEventPayload,
} from "@/lib/api";

const WEEKDAYS = ["일", "월", "화", "수", "목", "금", "토"];

const EVENT_TYPE_LABELS: Record<string, string> = {
  activity: "활동",
  general: "일반",
  deadline: "마감",
  meeting: "회의",
};

const STATUS_OPTIONS = [
  { value: "planned", label: "예정" },
  { value: "in_progress", label: "진행 중" },
  { value: "completed", label: "완료" },
  { value: "cancelled", label: "취소" },
];

function toYM(d: Date): string {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
}

function eventColor(event: CalendarEvent): string {
  if (event.event_type === "activity") return event.status === "completed" ? "var(--success)" : "var(--primary)";
  if (event.event_type === "deadline") return "var(--danger)";
  if (event.event_type === "meeting") return "var(--warning)";
  return "var(--text-muted)";
}

function eventLabel(event: CalendarEvent): string {
  return EVENT_TYPE_LABELS[event.event_type] ?? "일정";
}

function eventTooltip(ev: CalendarEvent): string {
  const parts = [`[${eventLabel(ev)}] ${ev.title}`];
  if (ev.location) parts.push(ev.location);
  if (ev.start_time && !ev.is_all_day) parts.push(ev.end_time ? `${ev.start_time}-${ev.end_time}` : ev.start_time);
  if (ev.fee_status === "unpaid") parts.push("활동비 미납");
  return parts.join(" · ");
}

function emptyPayload(date: string): CalendarEventPayload {
  return {
    title: "",
    event_type: "general",
    event_date: date,
    start_time: null,
    end_time: null,
    location: "",
    description: "",
    status: "planned",
    is_all_day: true,
  };
}

function ModalShell({
  children,
  onClose,
  maxWidth = "max-w-md",
}: {
  children: ReactNode;
  onClose: () => void;
  maxWidth?: string;
}) {
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center px-4"
      style={{ background: "rgba(31,31,36,0.45)" }}
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div
        className={`w-full ${maxWidth} rounded-2xl p-5 shadow-lg`}
        style={{ background: "var(--surface)", border: "1px solid var(--border-soft)" }}
      >
        {children}
      </div>
    </div>
  );
}

export function DashboardCalendar() {
  const today = new Date();
  const router = useRouter();
  const [currentDate, setCurrentDate] = useState(new Date(today.getFullYear(), today.getMonth(), 1));
  const [events, setEvents] = useState<CalendarEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [choiceDate, setChoiceDate] = useState<string | null>(null);
  const [activityDate, setActivityDate] = useState<string | null>(null);
  const [eventForm, setEventForm] = useState<CalendarEventPayload | null>(null);
  const [editingEventId, setEditingEventId] = useState<string | null>(null);
  const [categories, setCategories] = useState<ActivityCategory[]>([]);
  const [newTitle, setNewTitle] = useState("");
  const [newLocation, setNewLocation] = useState("");
  const [newCategoryId, setNewCategoryId] = useState("");
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  const year = currentDate.getFullYear();
  const month = currentDate.getMonth();

  async function refetch() {
    setLoading(true);
    try {
      const data = await getCalendarEvents(year, month + 1);
      setEvents(data.items);
    } catch {
      setEvents([]);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    refetch();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [year, month]);

  useEffect(() => {
    if (activityDate) {
      getActivityCategoriesTyped().then(setCategories).catch(() => {});
    }
  }, [activityDate]);

  function openChoice(day: number) {
    setChoiceDate(`${year}-${String(month + 1).padStart(2, "0")}-${String(day).padStart(2, "0")}`);
  }

  function openActivity(date: string) {
    setChoiceDate(null);
    setActivityDate(date);
    setNewTitle("");
    setNewLocation("");
    setNewCategoryId("");
    setSaveError(null);
  }

  function openGeneral(date: string) {
    setChoiceDate(null);
    setEditingEventId(null);
    setEventForm(emptyPayload(date));
    setSaveError(null);
  }

  function openEventDetail(event: CalendarEvent) {
    setEditingEventId(event.id);
    setEventForm({
      title: event.title,
      event_type: event.event_type,
      event_date: event.date,
      start_time: event.start_time ?? null,
      end_time: event.end_time ?? null,
      location: event.location ?? "",
      description: event.description ?? "",
      status: event.status,
      is_all_day: event.is_all_day ?? true,
    });
    setSaveError(null);
  }

  async function saveActivity(navigate: boolean) {
    if (!activityDate || !newTitle.trim()) return;
    setSaving(true);
    setSaveError(null);
    try {
      const created = await createActivity({
        title: newTitle.trim(),
        activity_date: activityDate,
        location: newLocation.trim() || null,
        category_id: newCategoryId || null,
        status: "planned",
      });
      setActivityDate(null);
      await refetch();
      if (navigate) router.push(`/activities/${created.id}`);
    } catch (err: unknown) {
      setSaveError(err instanceof Error ? err.message : "활동 생성 실패");
    } finally {
      setSaving(false);
    }
  }

  async function saveCalendarEvent() {
    if (!eventForm?.title.trim()) return;
    setSaving(true);
    setSaveError(null);
    try {
      const payload = {
        ...eventForm,
        title: eventForm.title.trim(),
        location: eventForm.location?.trim() || null,
        description: eventForm.description?.trim() || null,
        start_time: eventForm.is_all_day ? null : eventForm.start_time || null,
        end_time: eventForm.is_all_day ? null : eventForm.end_time || null,
      };
      if (editingEventId) {
        await updateCalendarEvent(editingEventId, payload);
      } else {
        await createCalendarEvent(payload);
      }
      setEventForm(null);
      setEditingEventId(null);
      await refetch();
    } catch (err: unknown) {
      setSaveError(err instanceof Error ? err.message : "일정 저장 실패");
    } finally {
      setSaving(false);
    }
  }

  async function removeCalendarEvent() {
    if (!editingEventId) return;
    setSaving(true);
    setSaveError(null);
    try {
      await deleteCalendarEvent(editingEventId);
      setEditingEventId(null);
      setEventForm(null);
      await refetch();
    } catch (err: unknown) {
      setSaveError(err instanceof Error ? err.message : "일정 삭제 실패");
    } finally {
      setSaving(false);
    }
  }

  const cells = useMemo(() => {
    const firstDow = new Date(year, month, 1).getDay();
    const daysInMonth = new Date(year, month + 1, 0).getDate();
    const items: (number | null)[] = [];
    for (let i = 0; i < firstDow; i++) items.push(null);
    for (let d = 1; d <= daysInMonth; d++) items.push(d);
    while (items.length % 7 !== 0) items.push(null);
    return items;
  }, [year, month]);

  function eventsForDay(day: number): CalendarEvent[] {
    const ds = `${year}-${String(month + 1).padStart(2, "0")}-${String(day).padStart(2, "0")}`;
    return events.filter((e) => e.date === ds);
  }

  function isToday(day: number) {
    return today.getFullYear() === year && today.getMonth() === month && today.getDate() === day;
  }

  const activityCount = events.filter((e) => e.event_type === "activity").length;
  const generalCount = events.length - activityCount;

  return (
    <>
      <div className="rounded-2xl overflow-hidden" style={{ border: "1px solid var(--border-soft)", background: "var(--surface)" }}>
        <div className="flex items-center justify-between px-4 py-3" style={{ borderBottom: "1px solid var(--border-soft)" }}>
          <button
            onClick={() => setCurrentDate((d) => new Date(d.getFullYear(), d.getMonth() - 1, 1))}
            className="p-1.5 rounded-lg transition-all hover:opacity-75"
            style={{ color: "var(--text-muted)", background: "var(--surface-soft)", border: "1px solid var(--border-soft)" }}
            title="이전 달"
          >
            <ChevronLeft className="h-4 w-4" />
          </button>
          <div className="text-center">
            <p className="text-sm font-semibold" style={{ color: "var(--text-main)" }}>
              {year}년 {month + 1}월
            </p>
            <p className="text-xs" style={{ color: "var(--text-muted)" }}>
              {loading ? "로딩 중..." : `활동 ${activityCount}건 · 일정 ${generalCount}건`}
            </p>
          </div>
          <button
            onClick={() => setCurrentDate((d) => new Date(d.getFullYear(), d.getMonth() + 1, 1))}
            className="p-1.5 rounded-lg transition-all hover:opacity-75"
            style={{ color: "var(--text-muted)", background: "var(--surface-soft)", border: "1px solid var(--border-soft)" }}
            title="다음 달"
          >
            <ChevronRight className="h-4 w-4" />
          </button>
        </div>

        <div className="overflow-x-auto">
          <div style={{ minWidth: 340 }}>
            <div className="grid grid-cols-7">
              {WEEKDAYS.map((wd, i) => (
                <div key={wd} className="py-2 text-center text-xs font-medium"
                  style={{ color: i === 0 ? "var(--danger)" : i === 6 ? "var(--primary)" : "var(--text-muted)" }}>
                  {wd}
                </div>
              ))}
            </div>
            <div className="grid grid-cols-7" style={{ borderTop: "1px solid var(--border-soft)" }}>
              {cells.map((day, idx) => {
                const dow = idx % 7;
                const dayEvents = day ? eventsForDay(day) : [];
                const todayCell = day !== null && isToday(day);
                return (
                  <div
                    key={idx}
                    className="p-1.5 min-h-[82px] text-xs"
                    style={{
                      borderRight: dow < 6 ? "1px solid var(--border-soft)" : "none",
                      borderBottom: idx < cells.length - 7 ? "1px solid var(--border-soft)" : "none",
                      background: todayCell ? "var(--primary-soft, rgba(99,102,241,0.06))" : "transparent",
                    }}
                  >
                    {day !== null && (
                      <>
                        <div className="flex items-center mb-1">
                          <button
                            className="inline-flex items-center justify-center h-5 w-5 rounded-full text-xs font-medium transition-opacity hover:opacity-75"
                            style={{
                              background: todayCell ? "var(--primary)" : "transparent",
                              color: todayCell ? "#fff" : dow === 0 ? "var(--danger)" : dow === 6 ? "var(--primary)" : "var(--text-main)",
                            }}
                            onClick={() => openChoice(day)}
                          >
                            {day}
                          </button>
                        </div>
                        <div className="space-y-0.5">
                          {dayEvents.slice(0, 3).map((ev) => {
                            const content = (
                              <div
                                className="flex items-center gap-1 rounded px-1 py-0.5 truncate cursor-pointer hover:opacity-80 transition-opacity"
                                style={{ background: "var(--surface-soft)", border: "1px solid var(--border-soft)" }}
                                title={eventTooltip(ev)}
                                onClick={ev.event_type === "activity" ? undefined : () => openEventDetail(ev)}
                              >
                                <span className="shrink-0 h-1.5 w-1.5 rounded-full" style={{ background: eventColor(ev) }} />
                                <span className="shrink-0" style={{ color: eventColor(ev), fontSize: 10 }}>
                                  [{eventLabel(ev)}]
                                </span>
                                <span className="truncate" style={{ color: "var(--text-main)", fontSize: 10 }}>
                                  {ev.title}
                                </span>
                              </div>
                            );
                            return ev.event_type === "activity" && ev.target_url ? (
                              <Link key={ev.id} href={ev.target_url}>{content}</Link>
                            ) : (
                              <div key={ev.id}>{content}</div>
                            );
                          })}
                          {dayEvents.length > 3 && (
                            <p className="text-xs" style={{ color: "var(--text-muted)", fontSize: 10 }}>
                              +{dayEvents.length - 3}개 더
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

        <div className="flex flex-wrap gap-3 px-4 py-2.5" style={{ borderTop: "1px solid var(--border-soft)" }}>
          {[
            { color: "var(--primary)", label: "활동" },
            { color: "var(--danger)", label: "마감" },
            { color: "var(--warning)", label: "회의" },
            { color: "var(--text-muted)", label: "일반" },
          ].map(({ color, label }) => (
            <div key={label} className="flex items-center gap-1">
              <span className="h-2 w-2 rounded-full shrink-0" style={{ background: color }} />
              <span className="text-xs" style={{ color: "var(--text-muted)" }}>{label}</span>
            </div>
          ))}
        </div>
      </div>

      {choiceDate && (
        <ModalShell onClose={() => setChoiceDate(null)}>
          <div className="space-y-4">
            <h3 className="text-base font-semibold" style={{ color: "var(--text-main)" }}>
              이 날짜에 무엇을 추가할까요?
            </h3>
            <div className="grid gap-2">
              <button
                className="flex items-center gap-3 rounded-xl px-4 py-3 text-left transition-opacity hover:opacity-80"
                style={{ background: "var(--surface-soft)", color: "var(--text-main)", border: "1px solid var(--border-soft)" }}
                onClick={() => openActivity(choiceDate)}
              >
                <CalendarDays className="h-4 w-4" />
                <span className="text-sm font-medium">활동 만들기</span>
              </button>
              <button
                className="flex items-center gap-3 rounded-xl px-4 py-3 text-left transition-opacity hover:opacity-80"
                style={{ background: "var(--surface-soft)", color: "var(--text-main)", border: "1px solid var(--border-soft)" }}
                onClick={() => openGeneral(choiceDate)}
              >
                <Clock className="h-4 w-4" />
                <span className="text-sm font-medium">일반 일정 추가</span>
              </button>
            </div>
            <button
              className="w-full rounded-xl px-4 py-2.5 text-sm font-medium"
              style={{ color: "var(--text-muted)", background: "transparent" }}
              onClick={() => setChoiceDate(null)}
            >
              취소
            </button>
          </div>
        </ModalShell>
      )}

      {activityDate && (
        <ModalShell onClose={() => setActivityDate(null)}>
          <div className="space-y-4">
            <h3 className="text-base font-semibold" style={{ color: "var(--text-main)" }}>
              활동 추가 - {activityDate}
            </h3>
            <div className="space-y-3">
              <input
                type="text"
                value={newTitle}
                onChange={(e) => setNewTitle(e.target.value)}
                placeholder="활동명"
                className="w-full rounded-xl px-3 py-2 text-sm focus:outline-none min-h-[44px]"
                style={{ background: "var(--surface)", color: "var(--text-main)", border: "1px solid var(--border-soft)", fontSize: 16 }}
                autoFocus
              />
              <input
                type="text"
                value={newLocation}
                onChange={(e) => setNewLocation(e.target.value)}
                placeholder="장소"
                className="w-full rounded-xl px-3 py-2 text-sm focus:outline-none min-h-[44px]"
                style={{ background: "var(--surface)", color: "var(--text-main)", border: "1px solid var(--border-soft)", fontSize: 16 }}
              />
              {categories.length > 0 && (
                <select
                  value={newCategoryId}
                  onChange={(e) => setNewCategoryId(e.target.value)}
                  className="w-full rounded-xl px-3 py-2 text-sm focus:outline-none min-h-[44px]"
                  style={{ background: "var(--surface)", color: "var(--text-main)", border: "1px solid var(--border-soft)", fontSize: 16 }}
                >
                  <option value="">카테고리 없음</option>
                  {categories.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
                </select>
              )}
            </div>
            {saveError && <p className="text-sm" style={{ color: "var(--danger)" }}>{saveError}</p>}
            <div className="flex flex-col sm:flex-row gap-2">
              <button className="flex-1 rounded-xl px-4 py-2.5 text-sm font-medium" style={{ background: "var(--primary)", color: "#fff" }} disabled={saving || !newTitle.trim()} onClick={() => saveActivity(false)}>
                {saving ? "저장 중..." : "저장"}
              </button>
              <button className="flex-1 rounded-xl px-4 py-2.5 text-sm font-medium" style={{ background: "var(--surface-soft)", color: "var(--text-main)", border: "1px solid var(--border-soft)" }} disabled={saving || !newTitle.trim()} onClick={() => saveActivity(true)}>
                저장 후 상세 이동
              </button>
            </div>
          </div>
        </ModalShell>
      )}

      {eventForm && (
        <ModalShell onClose={() => { setEventForm(null); setEditingEventId(null); }} maxWidth="max-w-lg">
          <div className="space-y-4">
            <div className="flex items-center justify-between gap-3">
              <h3 className="text-base font-semibold" style={{ color: "var(--text-main)" }}>
                {editingEventId ? "일정 수정" : "일반 일정 추가"}
              </h3>
              {editingEventId && (
                <button className="p-2 rounded-lg" style={{ color: "var(--danger)", background: "var(--surface-soft)" }} onClick={removeCalendarEvent} disabled={saving} title="삭제">
                  <Trash2 className="h-4 w-4" />
                </button>
              )}
            </div>
            <div className="grid gap-3 sm:grid-cols-2">
              <input
                className="sm:col-span-2 w-full rounded-xl px-3 py-2 text-sm focus:outline-none min-h-[44px]"
                style={{ background: "var(--surface)", color: "var(--text-main)", border: "1px solid var(--border-soft)", fontSize: 16 }}
                value={eventForm.title}
                onChange={(e) => setEventForm({ ...eventForm, title: e.target.value })}
                placeholder="일정 제목"
                autoFocus
              />
              <select
                className="w-full rounded-xl px-3 py-2 text-sm focus:outline-none min-h-[44px]"
                style={{ background: "var(--surface)", color: "var(--text-main)", border: "1px solid var(--border-soft)", fontSize: 16 }}
                value={eventForm.event_type}
                onChange={(e) => setEventForm({ ...eventForm, event_type: e.target.value })}
              >
                <option value="general">일반</option>
                <option value="deadline">마감</option>
                <option value="meeting">회의</option>
              </select>
              <input
                type="date"
                className="w-full rounded-xl px-3 py-2 text-sm focus:outline-none min-h-[44px]"
                style={{ background: "var(--surface)", color: "var(--text-main)", border: "1px solid var(--border-soft)", fontSize: 16 }}
                value={eventForm.event_date}
                onChange={(e) => setEventForm({ ...eventForm, event_date: e.target.value })}
              />
              <label className="sm:col-span-2 flex items-center gap-2 text-sm" style={{ color: "var(--text-main)" }}>
                <input
                  type="checkbox"
                  checked={eventForm.is_all_day}
                  onChange={(e) => setEventForm({ ...eventForm, is_all_day: e.target.checked })}
                />
                하루 종일
              </label>
              {!eventForm.is_all_day && (
                <>
                  <input
                    type="time"
                    className="w-full rounded-xl px-3 py-2 text-sm focus:outline-none min-h-[44px]"
                    style={{ background: "var(--surface)", color: "var(--text-main)", border: "1px solid var(--border-soft)", fontSize: 16 }}
                    value={eventForm.start_time ?? ""}
                    onChange={(e) => setEventForm({ ...eventForm, start_time: e.target.value || null })}
                  />
                  <input
                    type="time"
                    className="w-full rounded-xl px-3 py-2 text-sm focus:outline-none min-h-[44px]"
                    style={{ background: "var(--surface)", color: "var(--text-main)", border: "1px solid var(--border-soft)", fontSize: 16 }}
                    value={eventForm.end_time ?? ""}
                    onChange={(e) => setEventForm({ ...eventForm, end_time: e.target.value || null })}
                  />
                </>
              )}
              <div className="sm:col-span-2 relative">
                <MapPin className="absolute left-3 top-3 h-4 w-4" style={{ color: "var(--text-muted)" }} />
                <input
                  className="w-full rounded-xl pl-9 pr-3 py-2 text-sm focus:outline-none min-h-[44px]"
                  style={{ background: "var(--surface)", color: "var(--text-main)", border: "1px solid var(--border-soft)", fontSize: 16 }}
                  value={eventForm.location ?? ""}
                  onChange={(e) => setEventForm({ ...eventForm, location: e.target.value })}
                  placeholder="장소"
                />
              </div>
              <select
                className="sm:col-span-2 w-full rounded-xl px-3 py-2 text-sm focus:outline-none min-h-[44px]"
                style={{ background: "var(--surface)", color: "var(--text-main)", border: "1px solid var(--border-soft)", fontSize: 16 }}
                value={eventForm.status}
                onChange={(e) => setEventForm({ ...eventForm, status: e.target.value })}
              >
                {STATUS_OPTIONS.map((opt) => <option key={opt.value} value={opt.value}>{opt.label}</option>)}
              </select>
              <textarea
                className="sm:col-span-2 w-full rounded-xl px-3 py-2 text-sm focus:outline-none min-h-[88px]"
                style={{ background: "var(--surface)", color: "var(--text-main)", border: "1px solid var(--border-soft)", fontSize: 16 }}
                value={eventForm.description ?? ""}
                onChange={(e) => setEventForm({ ...eventForm, description: e.target.value })}
                placeholder="메모"
              />
            </div>
            {saveError && <p className="text-sm" style={{ color: "var(--danger)" }}>{saveError}</p>}
            <div className="flex gap-2">
              <button className="flex-1 rounded-xl px-4 py-2.5 text-sm font-medium" style={{ background: "var(--primary)", color: "#fff" }} disabled={saving || !eventForm.title.trim()} onClick={saveCalendarEvent}>
                {saving ? "저장 중..." : "저장"}
              </button>
              <button className="rounded-xl px-4 py-2.5 text-sm font-medium" style={{ background: "transparent", color: "var(--text-muted)" }} disabled={saving} onClick={() => { setEventForm(null); setEditingEventId(null); }}>
                취소
              </button>
            </div>
          </div>
        </ModalShell>
      )}
    </>
  );
}
