"use client";

import { Button } from "@/components/ui/Button";

const INTENT_DETAIL: Record<string, string> = {
  bank_statement_import: "파싱된 거래내역을 bank_transactions에 저장합니다.",
  bank_statement_preview: "파싱된 거래내역을 bank_transactions에 저장합니다.",
  payment_matching: "현재 납부 매칭 결과를 payment_records와 bank_transactions에 반영합니다.",
  payment_matching_preview: "현재 납부 매칭 결과를 payment_records와 bank_transactions에 반영합니다.",
  receipt_analysis: "분석 결과를 receipts에 저장합니다.",
  activity_report_generate: "생성된 초안을 activity_reports에 저장합니다.",
  activity_report_draft: "생성된 초안을 activity_reports에 저장합니다.",
};

interface Props {
  isOpen: boolean;
  intent: string;
  onConfirm: () => void;
  onClose: () => void;
  loading?: boolean;
}

export function ApplyConfirmDialog({ isOpen, intent, onConfirm, onClose, loading }: Props) {
  if (!isOpen) return null;

  const detail = INTENT_DETAIL[intent] ?? "";

  return (
    <div className="fixed inset-0 flex items-center justify-center z-50"
      style={{ background: "rgba(31,31,36,0.45)" }}>
      <div className="rounded-2xl w-full max-w-sm p-6 space-y-4"
        style={{ background: "var(--surface)", border: "1px solid var(--border-soft)", boxShadow: "0 8px 32px rgba(31,31,36,0.15)" }}>
        <h3 className="text-base font-semibold" style={{ color: "var(--text-main)" }}>
          반영 확인
        </h3>
        <p className="text-sm" style={{ color: "var(--text-muted)" }}>
          이 결과를 실제 데이터에 반영하시겠습니까?
          <br />
          반영 후에는 각 관리 페이지에서 수정할 수 있습니다.
        </p>
        {detail && (
          <div className="rounded-xl px-4 py-3 text-sm"
            style={{ background: "var(--primary-soft)", color: "var(--primary)", border: "1px solid rgba(124,108,242,0.15)" }}>
            {detail}
          </div>
        )}
        <div className="flex gap-3 pt-1">
          <Button className="flex-1" onClick={onConfirm} loading={loading}>
            반영하기
          </Button>
          <Button className="flex-1" variant="secondary" onClick={onClose} disabled={loading}>
            취소
          </Button>
        </div>
      </div>
    </div>
  );
}
