"use client";

import { useState } from "react";
import { Header } from "@/components/layout/Header";
import { Sidebar } from "@/components/layout/Sidebar";

export function AppShell({ children }: { children: React.ReactNode }) {
  const [drawerOpen, setDrawerOpen] = useState(false);

  return (
    <div className="min-h-screen" style={{ background: "var(--background)" }}>
      {/* Desktop Sidebar (hidden on mobile) */}
      <div className="hidden lg:block">
        <Sidebar onNavigate={() => {}} />
      </div>

      {/* Mobile Drawer overlay */}
      {drawerOpen && (
        <>
          {/* Backdrop */}
          <div
            className="fixed inset-0 z-30 lg:hidden"
            style={{ background: "rgba(31,31,36,0.4)" }}
            onClick={() => setDrawerOpen(false)}
          />
          {/* Drawer */}
          <div className="fixed inset-y-0 left-0 z-40 lg:hidden"
            style={{ width: 300 }}>
            <Sidebar onNavigate={() => setDrawerOpen(false)} />
          </div>
        </>
      )}

      {/* Main content */}
      <div className="min-h-screen lg:pl-60">
        <Header onMenuClick={() => setDrawerOpen(true)} />
        <main className="px-4 py-6 sm:px-6 lg:px-8 max-w-screen-xl mx-auto">
          {children}
        </main>
      </div>
    </div>
  );
}
