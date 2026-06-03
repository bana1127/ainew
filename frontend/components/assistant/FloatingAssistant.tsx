"use client";

import { useMemo, useState } from "react";
import { Bot, X } from "lucide-react";
import { usePathname } from "next/navigation";
import { AssistantChatPanel } from "@/components/assistant/AssistantChatPanel";
import type { AssistantChatContext } from "@/lib/api";

function buildContext(pathname: string | null): AssistantChatContext {
  const path = pathname || "/";
  const activityMatch = path.match(/^\/activities\/([^/?#]+)/);
  if (activityMatch?.[1]) {
    return {
      page: "activity_detail",
      activity_id: decodeURIComponent(activityMatch[1]),
    };
  }
  if (path.startsWith("/budget")) return { page: "budget" };
  if (path.startsWith("/payments")) return { page: "payments" };
  if (path.startsWith("/transactions")) return { page: "transactions" };
  if (path.startsWith("/receipts")) return { page: "receipts" };
  if (path.startsWith("/members")) return { page: "members" };
  if (path.startsWith("/activities")) return { page: "activities" };
  if (path.startsWith("/assistant")) return { page: "assistant" };
  return { page: "global" };
}

export function FloatingAssistant() {
  const [open, setOpen] = useState(false);
  const pathname = usePathname();
  const context = useMemo(() => buildContext(pathname), [pathname]);

  return (
    <>
      {open && <AssistantChatPanel context={context} onClose={() => setOpen(false)} />}
      <button
        type="button"
        onClick={() => setOpen((value) => !value)}
        className="fixed bottom-4 right-4 z-40 inline-flex h-14 w-14 items-center justify-center rounded-full text-white shadow-xl transition hover:scale-105 sm:bottom-6 sm:right-6"
        style={{ background: "var(--primary)" }}
        aria-label={open ? "운영 챗봇 닫기" : "운영 챗봇 열기"}
        title={open ? "닫기" : "운영 챗봇"}
      >
        {open ? <X size={22} /> : <Bot size={24} />}
      </button>
    </>
  );
}
