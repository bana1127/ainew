"use client";

import { useEffect, useMemo, useState } from "react";
import { Bot, X } from "lucide-react";
import { usePathname } from "next/navigation";
import { AssistantChatPanel } from "@/components/assistant/AssistantChatPanel";
import type { AssistantChatContext } from "@/lib/api";

function buildContext(pathname: string | null, tab: string | null): AssistantChatContext {
  const path = pathname || "/";
  const activityMatch = path.match(/^\/activities\/([^/?#]+)/);
  if (activityMatch?.[1]) {
    const activityId = decodeURIComponent(activityMatch[1]);
    return {
      page: "activity_detail",
      current_page: "activity_detail",
      activity_id: activityId,
      current_activity_id: activityId,
      current_tab: tab,
    };
  }
  if (path.startsWith("/budget")) return { page: "budget", current_page: "budget", current_tab: tab };
  if (path.startsWith("/payments")) return { page: "payments", current_page: "payments", current_tab: tab };
  if (path.startsWith("/transactions")) return { page: "transactions", current_page: "transactions", current_tab: tab };
  if (path.startsWith("/receipts")) return { page: "receipts", current_page: "receipts", current_tab: tab };
  if (path.startsWith("/members")) return { page: "members", current_page: "members", current_tab: tab };
  if (path.startsWith("/activities")) return { page: "activities", current_page: "activities", current_tab: tab };
  if (path.startsWith("/assistant")) return { page: "assistant", current_page: "assistant", current_tab: tab };
  return { page: "global", current_page: "global", current_tab: tab };
}

export function FloatingAssistant() {
  const [open, setOpen] = useState(false);
  const [tab, setTab] = useState<string | null>(null);
  const pathname = usePathname();

  useEffect(() => {
    const updateTab = () => {
      setTab(new URLSearchParams(window.location.search).get("tab"));
    };
    updateTab();
    window.addEventListener("popstate", updateTab);
    return () => window.removeEventListener("popstate", updateTab);
  }, [pathname]);

  const context = useMemo(() => buildContext(pathname, tab), [pathname, tab]);

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
