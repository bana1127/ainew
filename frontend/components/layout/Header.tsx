"use client";

import { usePathname } from "next/navigation";
import { Menu } from "lucide-react";

const PAGE_META: Record<string, { title: string; description: string }> = {
  "/dashboard": { title: "Dashboard", description: "오늘 처리해야 할 동아리 운영 업무를 확인하세요." },
  "/assistant": { title: "AI 작업실", description: "파일과 요청을 입력하면 ClubAgent가 적절한 작업을 실행합니다." },
  "/members": { title: "부원 관리", description: "부원 명부를 등록·수정·관리합니다." },
  "/activities": { title: "활동 관리", description: "활동을 만들고 참여자, 보고서, 활동비, 증빙을 한 곳에서 관리하세요." },
  "/activities/new": { title: "새 활동 만들기", description: "활동 정보를 입력하고 저장하세요." },
  "/reports": { title: "보고서 모아보기", description: "전체 활동 보고서를 모아보고 복사하거나 내보낼 수 있습니다." },
  "/references": { title: "레퍼런스 보고서", description: "활동 보고서 작성 시 참고할 레퍼런스를 관리합니다." },
  "/receipts": { title: "영수증 분석", description: "영수증을 업로드하고 AI로 증빙 적합성을 분석합니다." },
  "/transactions": { title: "거래내역", description: "거래내역서를 업로드하여 입출금 내역을 관리합니다." },
  "/payments": { title: "납부 현황", description: "회비 및 활동비 납부 현황을 확인하고 관리합니다." },
  "/notifications": { title: "알림", description: "시스템 알림 및 자동 점검 결과를 조회합니다." },
  "/settings": { title: "설정", description: "활동 카테고리 및 OpenAI 설정을 관리합니다." },
};

interface HeaderProps {
  onMenuClick?: () => void;
}

export function Header({ onMenuClick }: HeaderProps) {
  const pathname = usePathname();
  // Match exact or prefix (e.g. /activities/some-id)
  const meta = PAGE_META[pathname]
    ?? Object.entries(PAGE_META).find(([k]) => pathname.startsWith(k + "/"))?.[1]
    ?? { title: "ClubAgent", description: "동아리 운영 AI 비서" };

  return (
    <header
      className="sticky top-0 z-10 backdrop-blur-md"
      style={{ background: "rgba(248,245,239,0.92)", borderBottom: "1px solid var(--border-soft)" }}
    >
      <div className="flex h-14 sm:h-16 items-center justify-between px-4 sm:px-6">
        <div className="flex items-center gap-3 min-w-0">
          <button
            className="lg:hidden rounded-xl p-2 transition-colors hover:bg-mist shrink-0 min-h-[44px] min-w-[44px] flex items-center justify-center"
            onClick={onMenuClick}
            aria-label="메뉴 열기"
          >
            <Menu className="h-5 w-5" style={{ color: "var(--text-main)" }} />
          </button>
          <div className="min-w-0">
            <h1 className="text-sm sm:text-base font-semibold leading-tight truncate"
              style={{ color: "var(--text-main)" }}>
              {meta.title}
            </h1>
            <p className="text-xs leading-tight mt-0.5 hidden sm:block truncate"
              style={{ color: "var(--text-muted)" }}>
              {meta.description}
            </p>
          </div>
        </div>
      </div>
    </header>
  );
}
