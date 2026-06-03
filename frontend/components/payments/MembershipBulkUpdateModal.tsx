"use client";

import { useEffect, useState } from "react";

import {
  MembershipBulkUpdatePreviewResult,
  PaymentRecord,
  confirmMembershipBulkUpdate,
  previewMembershipBulkUpdate,
} from "@/lib/api";
import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
import { StatusBadge } from "@/components/ui/StatusBadge";

type BulkOperation =
  | "mark_paid"
  | "mark_unpaid"
  | "mark_need_check"
  | "mark_exempt"
  | "set_paid_amount"
  | "recalculate_required_amount";

const OPERATIONS: Array<{ value: BulkOperation; label: string; description: string }> = [
  { value: "mark_paid", label: "납부 완료", description: "필요 금액과 같은 금액으로 납부 처리" },
  { value: "set_paid_amount", label: "납부 금액 지정", description: "같은 납부 금액을 입력하고 상태 자동 계산" },
  { value: "mark_unpaid", label: "미납", description: "납부 금액을 0원으로 변경" },
  { value: "mark_need_check", label: "확인 필요", description: "금액은 유지하고 상태만 확인 필요로 변경" },
  { value: "mark_exempt", label: "면제", description: "필요 금액과 납부 금액을 0원으로 변경" },
  { value: "recalculate_required_amount", label: "필요 금액 재계산", description: "부원 정책에 따라 필요 금액을 다시 계산하고 납부 금액은 유지" },
];

function fmt(n: number | null | undefined): string {
  if (n == null) return "-";
  return n.toLocaleString("ko-KR");
}

interface MembershipBulkUpdateModalProps {
  isOpen: boolean;
  period: string;
  selectedRecords: PaymentRecord[];
  onClose: () => void;
  onCompleted: () => Promise<void> | void;
}

export function MembershipBulkUpdateModal({
  isOpen,
  period,
  selectedRecords,
  onClose,
  onCompleted,
}: MembershipBulkUpdateModalProps) {
  const [operation, setOperation] = useState<BulkOperation>("mark_paid");
  const [paidAmountValue, setPaidAmountValue] = useState(0);
  const [preview, setPreview] = useState<MembershipBulkUpdatePreviewResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [previewing, setPreviewing] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const [confirmedMessage, setConfirmedMessage] = useState<string | null>(null);

  useEffect(() => {
    if (!isOpen) {
      setPreview(null);
      setError(null);
      setConfirmedMessage(null);
      setOperation("mark_paid");
      setPaidAmountValue(0);
    }
  }, [isOpen]);

  function resetPreview(nextOperation: BulkOperation) {
    setOperation(nextOperation);
    setPreview(null);
    setError(null);
    setConfirmedMessage(null);
  }

  async function handlePreview() {
    setError(null);
    setConfirmedMessage(null);
    setPreviewing(true);
    try {
      const result = await previewMembershipBulkUpdate({
        period,
        payment_record_ids: selectedRecords.map((record) => record.id),
        operation,
        paid_amount_value: operation === "set_paid_amount" ? paidAmountValue : null,
      });
      setPreview(result);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setPreviewing(false);
    }
  }

  async function handleConfirm() {
    if (!preview?.action_id) return;
    setError(null);
    setConfirming(true);
    try {
      const result = await confirmMembershipBulkUpdate(preview.action_id);
      setConfirmedMessage(`${result.updated_count}건을 변경했습니다.`);
      await onCompleted();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setConfirming(false);
    }
  }

  const title = `선택 ${selectedRecords.length}건 일괄 변경`;

  return (
    <Modal isOpen={isOpen} onClose={onClose} title={title} size="lg">
      <div className="space-y-5">
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          {OPERATIONS.map((item) => (
            <label
              key={item.value}
              className="flex min-h-[72px] cursor-pointer items-start gap-3 rounded-lg p-3"
              style={{
                border: operation === item.value ? "1px solid var(--primary)" : "1px solid var(--border-soft)",
                background: operation === item.value ? "var(--primary-soft)" : "var(--surface)",
              }}
            >
              <input
                type="radio"
                className="mt-1 h-4 w-4"
                checked={operation === item.value}
                onChange={() => resetPreview(item.value)}
              />
              <span>
                <span className="block text-sm font-semibold" style={{ color: "var(--text-main)" }}>
                  {item.label}
                </span>
                <span className="mt-1 block text-xs leading-5" style={{ color: "var(--text-muted)" }}>
                  {item.description}
                </span>
              </span>
            </label>
          ))}
        </div>

        {operation === "set_paid_amount" && (
          <div>
            <label className="mb-1 block text-xs font-medium" style={{ color: "var(--text-muted)" }}>
              납부 금액 (원)
            </label>
            <input
              type="number"
              className="min-h-[44px] w-full rounded-lg px-3 py-2 text-sm focus:outline-none"
              style={{ background: "var(--surface)", color: "var(--text-main)", border: "1px solid var(--border-soft)" }}
              value={paidAmountValue}
              min={0}
              onChange={(event) => {
                setPaidAmountValue(Number(event.target.value));
                setPreview(null);
              }}
            />
          </div>
        )}

        <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg px-4 py-3"
          style={{ background: "var(--surface-soft)", border: "1px solid var(--border-soft)" }}>
          <div className="text-sm" style={{ color: "var(--text-muted)" }}>
            <span className="font-semibold" style={{ color: "var(--text-main)" }}>{period}</span>
            <span> 학기 회비 기록 {selectedRecords.length}건</span>
          </div>
          <Button onClick={handlePreview} loading={previewing} disabled={selectedRecords.length === 0 || confirming}>
            미리보기
          </Button>
        </div>

        {preview && (
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
              {[
                { label: "선택", value: preview.summary.selected },
                { label: "변경 예정", value: preview.summary.will_change },
                { label: "변경 없음", value: preview.summary.no_change },
                { label: "확인 필요", value: preview.summary.will_be_need_check },
              ].map((item) => (
                <div key={item.label} className="rounded-lg p-3"
                  style={{ background: "var(--surface-soft)", border: "1px solid var(--border-soft)" }}>
                  <p className="text-xs" style={{ color: "var(--text-muted)" }}>{item.label}</p>
                  <p className="mt-1 text-base font-semibold" style={{ color: "var(--text-main)" }}>{item.value}</p>
                </div>
              ))}
            </div>

            {preview.summary.danger && (
              <div className="rounded-lg px-4 py-3 text-sm"
                style={{ background: "var(--warning-soft)", color: "var(--warning)", border: "1px solid rgba(201,139,46,0.25)" }}>
                {preview.summary.danger_reason ?? "주의가 필요한 변경입니다."}
              </div>
            )}

            <div className="max-h-[300px] overflow-auto rounded-lg" style={{ border: "1px solid var(--border-soft)" }}>
              <table className="w-full min-w-[760px] text-sm">
                <thead>
                  <tr style={{ background: "var(--surface-soft)", borderBottom: "1px solid var(--border-soft)" }}>
                    {["부원명", "학번", "필요 금액", "납부 금액", "상태", "변경"].map((heading) => (
                      <th key={heading} className="whitespace-nowrap px-4 py-3 text-left text-xs font-semibold" style={{ color: "var(--text-muted)" }}>
                        {heading}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {preview.rows.map((row) => (
                    <tr key={row.payment_record_id} style={{ borderBottom: "1px solid var(--border-soft)" }}>
                      <td className="whitespace-nowrap px-4 py-2.5 font-medium" style={{ color: "var(--text-main)" }}>
                        {row.member_name ?? "알 수 없는 부원"}
                      </td>
                      <td className="whitespace-nowrap px-4 py-2.5 text-xs" style={{ color: "var(--text-muted)" }}>
                        {row.student_id ?? "-"}
                      </td>
                      <td className="whitespace-nowrap px-4 py-2.5 text-right" style={{ color: "var(--text-main)" }}>
                        {fmt(row.before_required_amount)}원 → {fmt(row.after_required_amount)}원
                      </td>
                      <td className="whitespace-nowrap px-4 py-2.5 text-right" style={{ color: "var(--text-main)" }}>
                        {fmt(row.before_paid_amount)}원 → {fmt(row.after_paid_amount)}원
                      </td>
                      <td className="whitespace-nowrap px-4 py-2.5">
                        <div className="flex items-center gap-2">
                          <StatusBadge status={row.before_status} />
                          <span style={{ color: "var(--text-muted)" }}>→</span>
                          <StatusBadge status={row.after_status} />
                        </div>
                      </td>
                      <td className="whitespace-nowrap px-4 py-2.5 text-xs" style={{ color: row.will_change ? "var(--primary)" : "var(--text-muted)" }}>
                        {row.will_change ? "변경" : "변경 없음"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {error && (
          <div className="rounded-lg px-4 py-3 text-sm" style={{ background: "var(--danger-soft)", color: "var(--danger)" }}>
            {error}
          </div>
        )}

        {confirmedMessage && (
          <div className="rounded-lg px-4 py-3 text-sm" style={{ background: "var(--success-soft)", color: "var(--success)" }}>
            {confirmedMessage}
          </div>
        )}

        <div className="flex gap-3 pt-1">
          <Button className="flex-1 min-h-[44px]" onClick={handleConfirm} disabled={!preview?.action_id || confirming || previewing} loading={confirming}>
            확정 적용
          </Button>
          <Button className="flex-1 min-h-[44px]" variant="secondary" onClick={onClose} disabled={confirming}>
            닫기
          </Button>
        </div>
      </div>
    </Modal>
  );
}
