import Link from "next/link";
import {
  Activity,
  Bell,
  CreditCard,
  FileText,
  LayoutDashboard,
  ReceiptText,
  Settings,
  Users,
  WalletCards,
} from "lucide-react";

const menu = [
  { label: "Dashboard", href: "/dashboard", icon: LayoutDashboard },
  { label: "Members", href: "/dashboard#members", icon: Users },
  { label: "Activities", href: "/dashboard#activities", icon: Activity },
  { label: "References", href: "/dashboard#references", icon: FileText },
  { label: "Reports", href: "/dashboard#reports", icon: FileText },
  { label: "Receipts", href: "/dashboard#receipts", icon: ReceiptText },
  { label: "Transactions", href: "/dashboard#transactions", icon: WalletCards },
  { label: "Payments", href: "/dashboard#payments", icon: CreditCard },
  { label: "Notifications", href: "/dashboard#notifications", icon: Bell },
  { label: "Settings", href: "/dashboard#settings", icon: Settings },
];

export function Sidebar() {
  return (
    <aside className="fixed inset-y-0 left-0 z-20 hidden w-64 border-r border-line bg-white lg:block">
      <div className="flex h-16 items-center border-b border-line px-5">
        <span className="text-lg font-semibold text-ink">ClubAgent</span>
      </div>
      <nav className="space-y-1 px-3 py-4">
        {menu.map((item) => {
          const Icon = item.icon;
          const active = item.label === "Dashboard";

          return (
            <Link
              key={item.label}
              href={item.href}
              className={`flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium ${
                active
                  ? "bg-pine text-white"
                  : "text-gray-600 hover:bg-mist hover:text-ink"
              }`}
            >
              <Icon className="h-4 w-4" aria-hidden="true" />
              {item.label}
            </Link>
          );
        })}
      </nav>
    </aside>
  );
}

