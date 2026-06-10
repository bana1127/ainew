"use client";

import { FormEvent, useEffect, useRef, useState } from "react";
import { ExternalLink, Loader2, Send, X } from "lucide-react";
import {
  getAssistantChatSuggestions,
  sendAssistantChat,
  type AssistantChatContext,
  type AssistantChatLink,
} from "@/lib/api";

type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  text: string;
  links?: AssistantChatLink[];
  summary?: Array<{ label: string; value: string }>;
  items?: Array<{
    title?: string | null;
    subtitle?: string | null;
    status?: string | null;
    url?: string | null;
    meta?: Record<string, string | number | null | undefined>;
  }>;
  zeroReasons?: string[];
  scope?: string | null;
};

type AssistantChatPanelProps = {
  context: AssistantChatContext;
  onClose: () => void;
};

function makeId() {
  return `${Date.now()}-${Math.random().toString(36).slice(2)}`;
}

export function AssistantChatPanel({ context, onClose }: AssistantChatPanelProps) {
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [lastActivityId, setLastActivityId] = useState<string | null>(context.activity_id ?? null);
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: "hello",
      role: "assistant",
      text: "운영 현황을 바로 조회할 수 있어요. 부원, 활동, 회비, 활동비, 예산, 증빙 상태를 물어보세요.",
    },
  ]);
  const scrollRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    let mounted = true;
    getAssistantChatSuggestions()
      .then((items) => {
        if (mounted) setSuggestions(items);
      })
      .catch(() => {
        if (mounted) setSuggestions([]);
      });
    return () => {
      mounted = false;
    };
  }, []);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, loading]);

  async function submitMessage(message: string) {
    const trimmed = message.trim();
    if (!trimmed || loading) return;
    setInput("");
    setLoading(true);
    setMessages((prev) => [
      ...prev,
      { id: makeId(), role: "user", text: trimmed },
    ]);
    try {
      const response = await sendAssistantChat({
        message: trimmed,
        context: {
          ...context,
          last_activity_id: lastActivityId ?? context.activity_id ?? null,
          current_activity_id: context.current_activity_id ?? context.activity_id ?? lastActivityId ?? null,
        },
      });
      const activityLink = response.links.find((link) => link.url.match(/^\/activities\/([^/?#]+)/));
      const activityId = activityLink?.url.match(/^\/activities\/([^/?#]+)/)?.[1];
      if (activityId) setLastActivityId(decodeURIComponent(activityId));
      setMessages((prev) => [
        ...prev,
        {
          id: makeId(),
          role: "assistant",
          text: response.answer,
          links: response.links,
          summary: response.summary,
          items: response.items,
          zeroReasons: response.zero_reasons,
          scope: response.scope,
        },
      ]);
    } catch (error) {
      const detail = error instanceof Error ? error.message : "알 수 없는 오류";
      setMessages((prev) => [
        ...prev,
        {
          id: makeId(),
          role: "assistant",
          text: `답변을 가져오지 못했습니다. ${detail}`,
        },
      ]);
    } finally {
      setLoading(false);
    }
  }

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    void submitMessage(input);
  }

  return (
    <section
      className="fixed bottom-4 right-4 z-50 flex h-[min(640px,calc(100vh-2rem))] w-[calc(100vw-2rem)] max-w-[420px] flex-col overflow-hidden rounded-2xl shadow-2xl sm:bottom-6 sm:right-6"
      style={{
        background: "var(--surface)",
        border: "1px solid var(--border-soft)",
        color: "var(--text-main)",
      }}
      aria-label="운영 챗봇"
    >
      <div
        className="flex items-center justify-between px-4 py-3"
        style={{ borderBottom: "1px solid var(--border-soft)" }}
      >
        <div>
          <div className="text-sm font-semibold">ClubAgent 운영 챗봇</div>
          <div className="text-xs" style={{ color: "var(--text-muted)" }}>
            조회 전용
          </div>
        </div>
        <button
          type="button"
          onClick={onClose}
          className="inline-flex h-9 w-9 items-center justify-center rounded-full transition hover:bg-mist"
          aria-label="챗봇 닫기"
          title="닫기"
        >
          <X size={18} />
        </button>
      </div>

      <div ref={scrollRef} className="flex-1 space-y-3 overflow-y-auto px-4 py-3">
        {messages.map((message) => (
          <div
            key={message.id}
            className={`flex ${message.role === "user" ? "justify-end" : "justify-start"}`}
          >
            <div
              className="max-w-[86%] rounded-2xl px-3 py-2 text-sm leading-6"
              style={{
                background: message.role === "user" ? "var(--primary)" : "var(--background)",
                color: message.role === "user" ? "#fff" : "var(--text-main)",
                border: message.role === "user" ? "1px solid transparent" : "1px solid var(--border-soft)",
              }}
            >
              <p className="whitespace-pre-wrap break-words">{message.text}</p>
              {message.scope && (
                <p
                  className="mt-2 rounded-lg px-2 py-1 text-[11px] leading-4"
                  style={{ background: "var(--surface-soft)", color: "var(--text-muted)" }}
                >
                  기준: {message.scope}
                </p>
              )}
              {message.summary && message.summary.length > 0 && (
                <div className="mt-2 grid grid-cols-2 gap-1.5">
                  {message.summary.slice(0, 4).map((item) => (
                    <div
                      key={`${message.id}-${item.label}`}
                      className="rounded-lg px-2 py-1.5"
                      style={{ background: "var(--surface-soft)", border: "1px solid var(--border-soft)" }}
                    >
                      <p className="text-[10px] leading-3" style={{ color: "var(--text-muted)" }}>{item.label}</p>
                      <p className="text-xs font-semibold" style={{ color: "var(--text-main)" }}>{item.value}</p>
                    </div>
                  ))}
                </div>
              )}
              {message.items && message.items.length > 0 && (
                <div className="mt-2 space-y-1.5">
                  {message.items.slice(0, 5).map((item, index) => {
                    const body = (
                      <div
                        className="rounded-lg px-2 py-1.5 transition hover:bg-primary-soft"
                        style={{ background: "var(--surface-soft)", border: "1px solid var(--border-soft)" }}
                      >
                        <div className="flex items-start justify-between gap-2">
                          <p className="min-w-0 flex-1 truncate text-xs font-semibold" style={{ color: "var(--text-main)" }}>
                            {index + 1}. {item.title ?? "항목"}
                          </p>
                          {item.status && (
                            <span className="shrink-0 text-[10px]" style={{ color: "var(--text-muted)" }}>
                              {item.status}
                            </span>
                          )}
                        </div>
                        {item.subtitle && (
                          <p className="mt-0.5 truncate text-[11px]" style={{ color: "var(--text-muted)" }}>{item.subtitle}</p>
                        )}
                        {item.meta && Object.keys(item.meta).length > 0 && (
                          <div className="mt-1 flex flex-wrap gap-x-2 gap-y-0.5">
                            {Object.entries(item.meta).slice(0, 4).map(([key, value]) => (
                              <span key={key} className="text-[10px]" style={{ color: "var(--text-muted)" }}>
                                {key} {String(value ?? "-")}
                              </span>
                            ))}
                          </div>
                        )}
                      </div>
                    );
                    return item.url ? (
                      <a key={`${message.id}-item-${index}`} href={item.url} className="block">
                        {body}
                      </a>
                    ) : (
                      <div key={`${message.id}-item-${index}`}>{body}</div>
                    );
                  })}
                </div>
              )}
              {message.zeroReasons && message.zeroReasons.length > 0 && (
                <div
                  className="mt-2 space-y-1 rounded-lg px-2 py-1.5"
                  style={{ background: "var(--surface-soft)", border: "1px solid var(--border-soft)" }}
                >
                  <p className="text-[11px] font-semibold" style={{ color: "var(--text-main)" }}>가능한 이유</p>
                  {message.zeroReasons.slice(0, 4).map((reason) => (
                    <p key={reason} className="text-[11px] leading-4" style={{ color: "var(--text-muted)" }}>
                      {reason}
                    </p>
                  ))}
                </div>
              )}
              {message.links && message.links.length > 0 && (
                <div className="mt-2 flex flex-col gap-1.5">
                  {message.links.map((link) => (
                    <a
                      key={`${message.id}-${link.url}-${link.label}`}
                      href={link.url}
                      className="inline-flex items-center gap-1.5 rounded-lg px-2 py-1 text-xs font-medium transition hover:bg-primary-soft"
                      style={{ color: "var(--primary)" }}
                    >
                      {link.label}
                      <ExternalLink size={13} />
                    </a>
                  ))}
                </div>
              )}
            </div>
          </div>
        ))}
        {loading && (
          <div className="flex justify-start">
            <div
              className="inline-flex items-center gap-2 rounded-2xl px-3 py-2 text-sm"
              style={{ background: "var(--background)", border: "1px solid var(--border-soft)" }}
            >
              <Loader2 size={15} className="animate-spin" />
              확인 중...
            </div>
          </div>
        )}
      </div>

      {suggestions.length > 0 && (
        <div
          className="flex gap-2 overflow-x-auto px-4 py-2"
          style={{ borderTop: "1px solid var(--border-soft)" }}
        >
          {suggestions.map((item) => (
            <button
              key={item}
              type="button"
              onClick={() => void submitMessage(item)}
              className="shrink-0 rounded-full px-3 py-1.5 text-xs font-medium transition hover:bg-primary-soft"
              style={{ border: "1px solid var(--border-soft)", color: "var(--text-main)" }}
            >
              {item}
            </button>
          ))}
        </div>
      )}

      <form onSubmit={handleSubmit} className="flex items-end gap-2 px-4 py-3">
        <textarea
          value={input}
          onChange={(event) => setInput(event.target.value)}
          rows={1}
          placeholder="질문 입력"
          className="min-h-10 flex-1 resize-none rounded-xl px-3 py-2 text-sm outline-none"
          style={{
            background: "var(--background)",
            border: "1px solid var(--border-soft)",
            color: "var(--text-main)",
          }}
          onKeyDown={(event) => {
            if (event.key === "Enter" && !event.shiftKey) {
              event.preventDefault();
              void submitMessage(input);
            }
          }}
        />
        <button
          type="submit"
          disabled={loading || !input.trim()}
          className="inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-full text-white transition disabled:cursor-not-allowed disabled:opacity-50"
          style={{ background: "var(--primary)" }}
          aria-label="메시지 보내기"
          title="보내기"
        >
          {loading ? <Loader2 size={17} className="animate-spin" /> : <Send size={17} />}
        </button>
      </form>
    </section>
  );
}
