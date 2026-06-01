"use client";

import Image from "next/image";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Activity,
  Bell,
  Bot,
  CreditCard,
  FileText,
  LayoutDashboard,
  PenLine,
  ReceiptText,
  Settings,
  Users,
  WalletCards,
} from "lucide-react";

type MenuItem = { label: string; href: string; icon: React.ElementType };

const menuGroups: Array<{ label: string; items: MenuItem[] }> = [
  {
    label: "MAIN",
    items: [
      { label: "Dashboard", href: "/dashboard", icon: LayoutDashboard },
      { label: "AI 작업실", href: "/assistant", icon: Bot },
    ],
  },
  {
    label: "OPERATIONS",
    items: [
      { label: "Activities", href: "/activities", icon: Activity },
      { label: "Members", href: "/members", icon: Users },
    ],
  },
  {
    label: "FINANCE",
    items: [
      { label: "Payments", href: "/payments", icon: CreditCard },
      { label: "Receipts", href: "/receipts", icon: ReceiptText },
      { label: "Transactions", href: "/transactions", icon: WalletCards },
    ],
  },
  {
    label: "DOCUMENTS",
    items: [
      { label: "Reports", href: "/reports", icon: PenLine },
      { label: "References", href: "/references", icon: FileText },
    ],
  },
  {
    label: "SYSTEM",
    items: [
      { label: "Notifications", href: "/notifications", icon: Bell },
      { label: "Settings", href: "/settings", icon: Settings },
    ],
  },
];

interface SidebarProps {
  onNavigate?: () => void;
}

export function Sidebar({ onNavigate }: SidebarProps) {
  const pathname = usePathname();

  return (
    <aside
      className="fixed inset-y-0 left-0 z-20 w-60 flex flex-col h-full"
      style={{ background: "var(--surface)", borderRight: "1px solid var(--border-soft)" }}
    >
      {/* Brand */}
      <div
        className="flex items-center gap-3 px-5 py-4"
        style={{ borderBottom: "1px solid var(--border-soft)" }}
      >
        <div
          className="shrink-0 rounded-full overflow-hidden"
          style={{ width: 40, height: 40, border: "1px solid var(--border-soft)" }}
        >
          <Image
            src="/brand/oui-parfum.png"
            alt="ClubAgent"
            width={40}
            height={40}
            className="object-cover w-full h-full"
            priority
          />
        </div>
        <div>
          <p className="text-sm font-semibold leading-tight" style={{ color: "var(--text-main)" }}>
            ClubAgent
          </p>
          <p className="text-xs leading-tight mt-0.5" style={{ color: "var(--text-muted)" }}>
            AI club assistant
          </p>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto px-3 py-3">
        {menuGroups.map((group, gi) => (
          <div key={group.label} className={gi > 0 ? "mt-3" : ""}>
            <p
              className="px-2 pb-1 text-xs font-semibold uppercase tracking-wider"
              style={{ color: "var(--text-muted)", opacity: 0.55 }}
            >
              {group.label}
            </p>
            <div className="space-y-0.5">
              {group.items.map((item) => {
                const Icon = item.icon;
                const active =
                  pathname === item.href ||
                  pathname.startsWith(item.href + "/");
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    className="flex items-center gap-2.5 rounded-xl px-2.5 py-2 text-sm font-medium transition-all duration-100 min-h-[44px]"
                    style={
                      active
                        ? { background: "var(--primary-soft)", color: "var(--primary)" }
                        : { color: "var(--text-muted)" }
                    }
                    onClick={onNavigate}
                  >
                    <Icon className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
                    {item.label}
                  </Link>
                );
              })}
            </div>
          </div>
        ))}
      </nav>
    </aside>
  );
}
