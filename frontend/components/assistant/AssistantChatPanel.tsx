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
      const response = await sendAssistantChat({ message: trimmed, context });
      setMessages((prev) => [
        ...prev,
        {
          id: makeId(),
          role: "assistant",
          text: response.answer,
          links: response.links,
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
