"use client";

export const DOCUMENT_TYPE_LABELS: Record<string, string> = {
  receipt: "영수증",
  business_registration: "사업자등록증",
  bankbook_copy: "통장 사본",
  transfer_confirmation: "계좌이체 확인서",
  invoice: "청구서",
  quote: "견적서",
  transaction_statement: "거래명세서",
  activity_photo: "활동 사진",
  other: "기타 증빙",
  unknown: "미분류",
};

const DOCUMENT_TYPE_COLORS: Record<string, { bg: string; text: string }> = {
  receipt: { bg: "#e0f2fe", text: "#0369a1" },
  business_registration: { bg: "#fef3c7", text: "#92400e" },
  bankbook_copy: { bg: "#d1fae5", text: "#065f46" },
  transfer_confirmation: { bg: "#ede9fe", text: "#5b21b6" },
  invoice: { bg: "#fee2e2", text: "#991b1b" },
  quote: { bg: "#fce7f3", text: "#831843" },
  transaction_statement: { bg: "#f3f4f6", text: "#374151" },
  activity_photo: { bg: "#dcfce7", text: "#166534" },
  other: { bg: "#f3f4f6", text: "#6b7280" },
  unknown: { bg: "#f9fafb", text: "#9ca3af" },
};

interface Props {
  documentType: string;
  size?: "sm" | "xs";
}

export function EvidenceDocumentTypeBadge({ documentType, size = "sm" }: Props) {
  const label = DOCUMENT_TYPE_LABELS[documentType] ?? documentType;
  const color = DOCUMENT_TYPE_COLORS[documentType] ?? DOCUMENT_TYPE_COLORS.unknown;
  const fontSize = size === "xs" ? 10 : 11;

  return (
    <span
      style={{
        display: "inline-block",
        padding: size === "xs" ? "1px 6px" : "2px 8px",
        borderRadius: 20,
        fontSize,
        fontWeight: 500,
        background: color.bg,
        color: color.text,
        whiteSpace: "nowrap",
      }}
    >
      {label}
    </span>
  );
}
