"use client";

import { useState } from "react";
import { Button } from "@/components/ui/Button";
import { DOCUMENT_TYPE_LABELS } from "./EvidenceDocumentTypeBadge";

type ReceiptRow = {
  id: string;
  document_type: string;
  title?: string | null;
  store_name?: string | null;
  amount: number | null;
  receipt_date?: string | null;
  payment_method?: string | null;
  category?: string | null;
  parsed_data?: Record<string, unknown> | null;
  manual_data?: Record<string, unknown> | null;
  reason?: string | null;
  evidence_status?: string;
  need_check?: boolean;
};

interface Props {
  receipt: ReceiptRow;
  onClose: () => void;
  onSaved: (receiptId: string, manualData: Record<string, unknown>, docType: string) => Promise<void>;
}

const DOCUMENT_TYPE_OPTIONS = Object.entries(DOCUMENT_TYPE_LABELS).map(([v, l]) => ({ value: v, label: l }));

function Field({
  label,
  name,
  value,
  onChange,
  type = "text",
  placeholder,
}: {
  label: string;
  name: string;
  value: string;
  onChange: (name: string, val: string) => void;
  type?: string;
  placeholder?: string;
}) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
      <label style={{ fontSize: 12, fontWeight: 500, color: "var(--text-sub)" }}>{label}</label>
      <input
        type={type}
        value={value}
        onChange={(e) => onChange(name, e.target.value)}
        placeholder={placeholder}
        style={{
          padding: "7px 10px",
          borderRadius: 8,
          border: "1px solid var(--border-soft)",
          background: "var(--surface)",
          color: "var(--text-main)",
          fontSize: 13,
        }}
      />
    </div>
  );
}

function getDisplayData(receipt: ReceiptRow): Record<string, string> {
  const base = receipt.manual_data ?? receipt.parsed_data ?? {};
  const result: Record<string, string> = {};
  for (const [k, v] of Object.entries(base)) {
    if (v !== null && v !== undefined) result[k] = String(v);
  }
  return result;
}

export function EvidenceDetailEditModal({ receipt, onClose, onSaved }: Props) {
  const [docType, setDocType] = useState(receipt.document_type || "unknown");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Initialize editable fields from manual_data > parsed_data > model fields
  const initial = getDisplayData(receipt);
  const [fields, setFields] = useState<Record<string, string>>({
    title: receipt.title || receipt.store_name || initial.title || initial.store_name || "",
    amount: String(receipt.amount || initial.amount || ""),
    receipt_date: receipt.receipt_date || initial.receipt_date || "",
    vendor_name: initial.vendor_name || receipt.store_name || initial.store_name || "",
    payment_method: receipt.payment_method || initial.payment_method || "",
    // business_registration fields
    business_registration_number: initial.business_registration_number || "",
    business_name: initial.business_name || "",
    representative_name: initial.representative_name || "",
    business_address: initial.business_address || "",
    business_type: initial.business_type || "",
    business_item: initial.business_item || "",
    opening_date: initial.opening_date || "",
    tax_office: initial.tax_office || "",
    // bankbook_copy fields
    bank_name: initial.bank_name || "",
    account_holder: initial.account_holder || "",
    account_number_masked: initial.account_number_masked || "",
    account_type: initial.account_type || "",
    // transfer_confirmation fields
    transfer_date: initial.transfer_date || initial.receipt_date || "",
    sender_name: initial.sender_name || "",
    receiver_name: initial.receiver_name || "",
    sender_account_masked: initial.sender_account_masked || "",
    receiver_account_masked: initial.receiver_account_masked || "",
    transfer_amount: initial.transfer_amount || String(receipt.amount || ""),
    transaction_memo: initial.transaction_memo || "",
    // receipt fields
    approval_number: initial.approval_number || "",
    card_number_masked: initial.card_number_masked || "",
    tax_amount: initial.tax_amount || "",
    supply_amount: initial.supply_amount || "",
    // general
    memo: initial.memo || receipt.reason || "",
  });

  function handleChange(name: string, val: string) {
    setFields((prev) => ({ ...prev, [name]: val }));
  }

  async function handleSave() {
    setSaving(true);
    setError(null);
    try {
      const manual_data: Record<string, unknown> = {};
      for (const [k, v] of Object.entries(fields)) {
        if (v !== "") manual_data[k] = v;
      }
      await onSaved(receipt.id, manual_data, docType);
      onClose();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "저장 실패");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div
      style={{
        position: "fixed", inset: 0, zIndex: 10000,
        background: "rgba(0,0,0,0.5)",
        display: "flex", alignItems: "center", justifyContent: "center",
        padding: 16,
      }}
      onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
    >
      <div
        style={{
          background: "var(--surface)", borderRadius: 16,
          width: "100%", maxWidth: 560, maxHeight: "90vh",
          overflow: "hidden", display: "flex", flexDirection: "column",
          boxShadow: "0 12px 40px rgba(0,0,0,0.25)",
        }}
      >
        {/* Header */}
        <div style={{ padding: "16px 20px", borderBottom: "1px solid var(--border-soft)", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <h3 style={{ fontWeight: 600, fontSize: 15, color: "var(--text-main)" }}>증빙 수정</h3>
          <button onClick={onClose} style={{ background: "none", border: "none", cursor: "pointer", color: "var(--text-muted)", fontSize: 18 }}>✕</button>
        </div>

        {/* Body - scrollable */}
        <div style={{ flex: 1, overflowY: "auto", padding: 20, display: "flex", flexDirection: "column", gap: 14 }}>
          {/* Document type selector */}
          <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
            <label style={{ fontSize: 12, fontWeight: 500, color: "var(--text-sub)" }}>문서 유형</label>
            <select
              value={docType}
              onChange={(e) => setDocType(e.target.value)}
              style={{ padding: "7px 10px", borderRadius: 8, border: "1px solid var(--border-soft)", background: "var(--surface)", color: "var(--text-main)", fontSize: 13 }}
            >
              {DOCUMENT_TYPE_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>{o.label}</option>
              ))}
            </select>
          </div>

          {/* Common fields */}
          <Field label="제목 / 상호" name="title" value={fields.title} onChange={handleChange} placeholder="문서 제목 또는 업체명" />
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
            <Field label="날짜 / 발급일" name="receipt_date" value={fields.receipt_date} onChange={handleChange} type="date" />
            <Field label="금액 (원)" name="amount" value={fields.amount} onChange={handleChange} type="number" placeholder="0" />
          </div>

          {/* Receipt-specific fields */}
          {(docType === "receipt") && (
            <>
              <Field label="가맹점명" name="vendor_name" value={fields.vendor_name} onChange={handleChange} />
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
                <Field label="승인번호" name="approval_number" value={fields.approval_number} onChange={handleChange} />
                <Field label="카드번호 일부" name="card_number_masked" value={fields.card_number_masked} onChange={handleChange} placeholder="**** 1234" />
              </div>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
                <Field label="공급가액" name="supply_amount" value={fields.supply_amount} onChange={handleChange} type="number" />
                <Field label="부가세" name="tax_amount" value={fields.tax_amount} onChange={handleChange} type="number" />
              </div>
            </>
          )}

          {/* Business registration fields */}
          {docType === "business_registration" && (
            <>
              <Field label="상호 / 법인명" name="business_name" value={fields.business_name} onChange={handleChange} />
              <Field label="사업자등록번호" name="business_registration_number" value={fields.business_registration_number} onChange={handleChange} placeholder="000-00-00000" />
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
                <Field label="대표자명" name="representative_name" value={fields.representative_name} onChange={handleChange} />
                <Field label="개업연월일" name="opening_date" value={fields.opening_date} onChange={handleChange} type="date" />
              </div>
              <Field label="사업장 소재지" name="business_address" value={fields.business_address} onChange={handleChange} />
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
                <Field label="업태" name="business_type" value={fields.business_type} onChange={handleChange} />
                <Field label="종목" name="business_item" value={fields.business_item} onChange={handleChange} />
              </div>
              <Field label="관할 세무서" name="tax_office" value={fields.tax_office} onChange={handleChange} />
            </>
          )}

          {/* Bankbook copy fields */}
          {docType === "bankbook_copy" && (
            <>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
                <Field label="은행명" name="bank_name" value={fields.bank_name} onChange={handleChange} />
                <Field label="예금주" name="account_holder" value={fields.account_holder} onChange={handleChange} />
              </div>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
                <Field label="계좌번호" name="account_number_masked" value={fields.account_number_masked} onChange={handleChange} placeholder="000-000-000000" />
                <Field label="계좌 유형" name="account_type" value={fields.account_type} onChange={handleChange} placeholder="보통예금, 저축예금" />
              </div>
            </>
          )}

          {/* Transfer confirmation fields */}
          {docType === "transfer_confirmation" && (
            <>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
                <Field label="이체일시" name="transfer_date" value={fields.transfer_date} onChange={handleChange} type="date" />
                <Field label="이체금액" name="transfer_amount" value={fields.transfer_amount} onChange={handleChange} type="number" />
              </div>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
                <Field label="보내는 사람" name="sender_name" value={fields.sender_name} onChange={handleChange} />
                <Field label="받는 사람" name="receiver_name" value={fields.receiver_name} onChange={handleChange} />
              </div>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
                <Field label="출금 계좌" name="sender_account_masked" value={fields.sender_account_masked} onChange={handleChange} />
                <Field label="입금 계좌" name="receiver_account_masked" value={fields.receiver_account_masked} onChange={handleChange} />
              </div>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
                <Field label="은행명" name="bank_name" value={fields.bank_name} onChange={handleChange} />
                <Field label="거래 메모" name="transaction_memo" value={fields.transaction_memo} onChange={handleChange} />
              </div>
            </>
          )}

          {/* Memo for all types */}
          <Field label="메모 / 비고" name="memo" value={fields.memo} onChange={handleChange} placeholder="추가 메모를 입력하세요" />

          {error && (
            <p style={{ fontSize: 13, color: "var(--danger)" }}>{error}</p>
          )}
        </div>

        {/* Footer */}
        <div style={{ padding: "14px 20px", borderTop: "1px solid var(--border-soft)", display: "flex", gap: 8, justifyContent: "flex-end" }}>
          <Button variant="ghost" size="sm" onClick={onClose}>취소</Button>
          <Button variant="primary" size="sm" onClick={handleSave} disabled={saving}>
            {saving ? "저장 중..." : "저장"}
          </Button>
        </div>
      </div>
    </div>
  );
}
