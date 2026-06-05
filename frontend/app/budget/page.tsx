"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import {
  ActivityReport,
  BankTransaction,
  BudgetActivitySettlement,
  BudgetCashflowRow,
  BudgetCategory,
  BudgetReviewItem,
  BudgetSummary,
  BudgetTransactionClassifyPreview,
  BudgetVsActualRow,
  confirmBudgetTransactionClassify,
  createBudgetCategory,
  getActivityReportsFiltered,
  getBudgetActivitySettlements,
  getBudgetCashflow,
  getBudgetCategories,
  getBudgetReviewItems,
  getBudgetSummary,
  getBudgetVsActual,
  getTransactionsTyped,
  previewBudgetTransactionClassify,
  resolveBudgetReviewItem,
  saveBudgetPlan,
  updateBudgetCategory,
  downloadQuarterCsv,
  downloadQuarterZip,
} from "@/lib/api";
import { QuarterFilter } from "@/components/budget/QuarterFilter";

import { AppShell } from "@/components/layout/AppShell";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorState } from "@/components/ui/ErrorState";
import { LoadingState } from "@/components/ui/LoadingState";
import { PageHeader } from "@/components/ui/PageHeader";
import { StatusBadge } from "@/components/ui/StatusBadge";

function fmt(n: number | null | undefined): string {
  if (n == null) return "-";
  return n.toLocaleString("ko-KR");
}

function todayYearTerm(): string {
  const now = new Date();
  return `${now.getFullYear()}-${now.getMonth() < 6 ? 1 : 2}`;
}

function csvEscape(value: unknown): string {
  const s = String(value ?? "");
  if (/[",\n]/.test(s)) return `"${s.replace(/"/g, '""')}"`;
  return s;
}

function downloadCsv(filename: string, rows: Array<Record<string, unknown>>) {
  if (rows.length === 0) return;
  const headers = Object.keys(rows[0]);
  const body = [
    headers.join(","),
    ...rows.map((row) => headers.map((header) => csvEscape(row[header])).join(",")),
  ].join("\n");
  const blob = new Blob(["\ufeff", body], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

const inputStyle: React.CSSProperties = {
  background: "var(--surface)",
  color: "var(--text-main)",
  border: "1px solid var(--border-soft)",
  borderRadius: "10px",
  padding: "8px 10px",
  fontSize: "14px",
};

function SectionTitle({ title, hint }: { title: string; hint?: string }) {
  return (
    <div className="flex flex-col gap-1 sm:flex-row sm:items-end sm:justify-between">
      <h2 className="text-base font-semibold" style={{ color: "var(--text-main)" }}>{title}</h2>
      {hint && <p className="text-xs" style={{ color: "var(--text-muted)" }}>{hint}</p>}
    </div>
  );
}

function amountTone(value: number): React.CSSProperties {
  if (value > 0) return { color: "var(--success)" };
  if (value < 0) return { color: "var(--danger)" };
  return { color: "var(--text-main)" };
}

function SummaryCards({ summary }: { summary: BudgetSummary | null }) {
  const cards = [
    { label: "현재 잔액", value: summary?.current_balance, tone: "main" },
    { label: "총 수입", value: summary?.total_income, tone: "success" },
    { label: "총 지출", value: summary?.total_expense, tone: "danger" },
    { label: "순증감", value: summary?.net_change, tone: "net" },
    { label: "받을 돈", value: summary?.receivable_amount, tone: "warning" },
    { label: "환불 예정", value: summary?.refund_scheduled_amount, tone: "warning" },
    { label: "확인 필요 거래", value: summary?.review_transaction_count, tone: "danger", suffix: "건" },
    { label: "증빙 누락", value: summary?.missing_evidence_count, tone: "danger", suffix: "건" },
  ];
  return (
    <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
      {cards.map((card) => (
        <Card key={card.label} padding="md">
          <p className="text-xs" style={{ color: "var(--text-muted)" }}>{card.label}</p>
          <p
            className="mt-2 text-xl font-semibold"
            style={
              card.tone === "success" ? { color: "var(--success)" }
                : card.tone === "danger" ? { color: "var(--danger)" }
                : card.tone === "warning" ? { color: "var(--warning)" }
                : card.tone === "net" ? amountTone(Number(card.value ?? 0))
                : { color: "var(--text-main)" }
            }
          >
            {summary ? `${fmt(card.value)}${card.suffix ?? "원"}` : "-"}
          </p>
        </Card>
      ))}
    </div>
  );
}

function CashflowTable({ rows }: { rows: BudgetCashflowRow[] }) {
  return (
    <Card padding="lg">
      <SectionTitle title="수입·지출 흐름" hint="월별 입금/출금 기준" />
      {rows.length === 0 ? (
        <div className="mt-4"><EmptyState message="기간 내 거래 흐름이 없습니다." /></div>
      ) : (
        <div className="mt-4 overflow-x-auto">
          <table className="w-full min-w-[520px] text-sm">
            <thead>
              <tr style={{ background: "var(--surface-soft)", borderBottom: "1px solid var(--border-soft)" }}>
                {["기간", "수입", "지출", "순증감"].map((h) => (
                  <th key={h} className="whitespace-nowrap px-4 py-3 text-left text-xs font-semibold" style={{ color: "var(--text-muted)" }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.bucket} style={{ borderBottom: "1px solid var(--border-soft)" }}>
                  <td className="whitespace-nowrap px-4 py-3 font-medium" style={{ color: "var(--text-main)" }}>{row.bucket}</td>
                  <td className="whitespace-nowrap px-4 py-3 text-right" style={{ color: "var(--success)" }}>{fmt(row.income)}원</td>
                  <td className="whitespace-nowrap px-4 py-3 text-right" style={{ color: "var(--danger)" }}>{fmt(row.expense)}원</td>
                  <td className="whitespace-nowrap px-4 py-3 text-right font-semibold" style={amountTone(row.net)}>{fmt(row.net)}원</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Card>
  );
}

function BudgetTable({
  rows,
  categories,
  period,
  onSaved,
}: {
  rows: BudgetVsActualRow[];
  categories: BudgetCategory[];
  period: string;
  onSaved: () => Promise<void>;
}) {
  const [newCategory, setNewCategory] = useState({ name: "", type: "expense" as "income" | "expense" });
  const [busy, setBusy] = useState<string | null>(null);

  async function saveAmount(row: BudgetVsActualRow, planned: number, note: string | null) {
    setBusy(row.category_id);
    try {
      await saveBudgetPlan({ period, category_id: row.category_id, planned_amount: planned, note });
      await onSaved();
    } finally {
      setBusy(null);
    }
  }

  async function addCategory() {
    if (!newCategory.name.trim()) return;
    setBusy("new-category");
    try {
      await createBudgetCategory({ name: newCategory.name.trim(), type: newCategory.type, sort_order: categories.length * 10 });
      setNewCategory({ name: "", type: "expense" });
      await onSaved();
    } finally {
      setBusy(null);
    }
  }

  return (
    <Card padding="lg">
      <SectionTitle title="예산 대비 실제" hint="계획 금액과 실제 거래 분류 금액 비교" />
      <div className="mt-4 flex flex-wrap gap-2">
        <input
          style={inputStyle}
          className="min-h-[40px] w-40"
          placeholder="새 예산 항목"
          value={newCategory.name}
          onChange={(event) => setNewCategory((v) => ({ ...v, name: event.target.value }))}
        />
        <select
          style={inputStyle}
          className="min-h-[40px]"
          value={newCategory.type}
          onChange={(event) => setNewCategory((v) => ({ ...v, type: event.target.value as "income" | "expense" }))}
        >
          <option value="income">수입</option>
          <option value="expense">지출</option>
        </select>
        <Button size="sm" onClick={addCategory} loading={busy === "new-category"}>항목 추가</Button>
      </div>
      <div className="mt-4 overflow-x-auto">
        <table className="w-full min-w-[920px] text-sm">
          <thead>
            <tr style={{ background: "var(--surface-soft)", borderBottom: "1px solid var(--border-soft)" }}>
              {["유형", "항목", "계획", "실제", "차이", "메모", "작업"].map((h) => (
                <th key={h} className="whitespace-nowrap px-4 py-3 text-left text-xs font-semibold" style={{ color: "var(--text-muted)" }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <BudgetRow key={row.category_id} row={row} busy={busy === row.category_id} onSave={saveAmount} onSaved={onSaved} />
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  );
}

function BudgetRow({
  row,
  busy,
  onSave,
  onSaved,
}: {
  row: BudgetVsActualRow;
  busy: boolean;
  onSave: (row: BudgetVsActualRow, planned: number, note: string | null) => Promise<void>;
  onSaved: () => Promise<void>;
}) {
  const [planned, setPlanned] = useState(row.planned_amount);
  const [note, setNote] = useState(row.note ?? "");
  useEffect(() => {
    setPlanned(row.planned_amount);
    setNote(row.note ?? "");
  }, [row.planned_amount, row.note]);

  async function deactivate() {
    await updateBudgetCategory(row.category_id, { is_active: false });
    await onSaved();
  }

  return (
    <tr style={{ borderBottom: "1px solid var(--border-soft)" }}>
      <td className="whitespace-nowrap px-4 py-3" style={{ color: "var(--text-muted)" }}>{row.type === "income" ? "수입" : "지출"}</td>
      <td className="whitespace-nowrap px-4 py-3 font-medium" style={{ color: "var(--text-main)" }}>{row.category_name}</td>
      <td className="whitespace-nowrap px-4 py-3">
        <input
          type="number"
          className="w-28 rounded-lg px-2 py-1 text-right"
          style={{ ...inputStyle, padding: "6px 8px" }}
          value={planned}
          onChange={(event) => setPlanned(Number(event.target.value))}
        />
      </td>
      <td className="whitespace-nowrap px-4 py-3 text-right" style={{ color: "var(--text-main)" }}>{fmt(row.actual_amount)}원</td>
      <td className="whitespace-nowrap px-4 py-3 text-right font-semibold" style={row.over_budget ? { color: "var(--danger)" } : amountTone(row.difference_amount)}>
        {fmt(row.difference_amount)}원
      </td>
      <td className="px-4 py-3">
        <input
          className="w-56 rounded-lg px-2 py-1"
          style={{ ...inputStyle, padding: "6px 8px" }}
          value={note}
          onChange={(event) => setNote(event.target.value)}
        />
      </td>
      <td className="whitespace-nowrap px-4 py-3">
        <div className="flex gap-2">
          <Button size="sm" variant="secondary" loading={busy} onClick={() => onSave(row, planned, note || null)}>저장</Button>
          <Button size="sm" variant="ghost" onClick={deactivate}>비활성화</Button>
        </div>
      </td>
    </tr>
  );
}

function ReviewItems({
  items,
  onResolved,
}: {
  items: BudgetReviewItem[];
  onResolved: () => Promise<void>;
}) {
  // Separate summary items from actionable review items
  const summaryItems = items.filter(
    (i) => i.type === "membership_fee_summary" || i.type === "activity_fee_summary"
  );
  const actionableItems = items
    .filter((i) => i.type !== "membership_fee_summary" && i.type !== "activity_fee_summary")
    .slice(0, 12);

  async function resolve(item: BudgetReviewItem) {
    await resolveBudgetReviewItem(item.id, "예산 관리 화면에서 검토 완료");
    await onResolved();
  }

  return (
    <Card padding="lg">
      <SectionTitle title="처리 필요 항목" hint="미분류, 확인 필요, 증빙 누락, 환불, 예산 초과" />

      {/* Summary cards: 회비 미납 / 활동비 미납 요약 */}
      {summaryItems.length > 0 && (
        <div className="mt-4 grid grid-cols-1 gap-2 sm:grid-cols-2">
          {summaryItems.map((item) => (
            <div key={item.id} className="flex items-center justify-between rounded-xl p-3"
              style={{ background: "var(--warning-soft)", border: "1px solid rgba(185,130,43,0.2)" }}>
              <div>
                <p className="text-sm font-semibold" style={{ color: "var(--warning)" }}>{item.label}</p>
                <p className="text-xs mt-0.5" style={{ color: "var(--warning)" }}>{item.title}</p>
              </div>
              <Link href={item.target_url}>
                <Button size="sm" variant="secondary">관리</Button>
              </Link>
            </div>
          ))}
        </div>
      )}

      {/* Actionable review items */}
      {actionableItems.length === 0 ? (
        <div className="mt-4"><EmptyState message={summaryItems.length > 0 ? "기타 처리 필요 항목이 없습니다." : "처리 필요 항목이 없습니다."} /></div>
      ) : (
        <div className="mt-4 space-y-2">
          {actionableItems.map((item) => (
            <div key={item.id} className="flex flex-col gap-3 rounded-lg p-3 sm:flex-row sm:items-center sm:justify-between"
              style={{ background: "var(--surface-soft)", border: "1px solid var(--border-soft)" }}>
              <div className="min-w-0">
                <p className="text-sm font-semibold" style={{ color: "var(--text-main)" }}>{item.label}</p>
                <p className="truncate text-xs" style={{ color: "var(--text-muted)" }}>{item.title ?? "-"} · {fmt(item.amount)}원</p>
              </div>
              <div className="flex flex-wrap gap-2">
                <Link href={item.target_url}><Button size="sm" variant="secondary">이동</Button></Link>
                {item.id.includes("transaction") && <Button size="sm" variant="ghost" onClick={() => resolve(item)}>검토 완료</Button>}
              </div>
            </div>
          ))}
        </div>
      )}
    </Card>
  );
}

function ActivitySettlements({ rows }: { rows: BudgetActivitySettlement[] }) {
  return (
    <Card padding="lg">
      <SectionTitle title="활동별 정산 현황" hint="활동비 수입, 지출, 증빙/보고서 상태" />
      <div className="mt-4 overflow-x-auto">
        <table className="w-full min-w-[1120px] text-sm">
          <thead>
            <tr style={{ background: "var(--surface-soft)", borderBottom: "1px solid var(--border-soft)" }}>
              {["활동명", "활동일", "참가자", "예정 수입", "실제 수입", "지출", "차액", "증빙", "보고서", "작업"].map((h) => (
                <th key={h} className="whitespace-nowrap px-4 py-3 text-left text-xs font-semibold" style={{ color: "var(--text-muted)" }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.activity_id} style={{ borderBottom: "1px solid var(--border-soft)" }}>
                <td className="whitespace-nowrap px-4 py-3 font-medium" style={{ color: "var(--text-main)" }}>{row.activity_title}</td>
                <td className="whitespace-nowrap px-4 py-3 text-xs" style={{ color: "var(--text-muted)" }}>{row.activity_date ?? "-"}</td>
                <td className="whitespace-nowrap px-4 py-3 text-right">{row.participant_count}</td>
                <td className="whitespace-nowrap px-4 py-3 text-right">{fmt(row.expected_income)}원</td>
                <td className="whitespace-nowrap px-4 py-3 text-right">{fmt(row.actual_income)}원</td>
                <td className="whitespace-nowrap px-4 py-3 text-right">{fmt(row.expense_amount)}원</td>
                <td className="whitespace-nowrap px-4 py-3 text-right font-semibold" style={amountTone(row.balance_amount)}>{fmt(row.balance_amount)}원</td>
                <td className="whitespace-nowrap px-4 py-3"><StatusBadge status={row.evidence_status} /></td>
                <td className="whitespace-nowrap px-4 py-3"><StatusBadge status={row.report_status} /></td>
                <td className="px-4 py-3">
                  <div className="flex flex-wrap gap-2">
                    <Link href={row.target_url}><Button size="sm" variant="ghost">상세</Button></Link>
                    <Link href={row.activity_fee_url}><Button size="sm" variant="ghost">활동비</Button></Link>
                    <Link href={row.evidence_url}><Button size="sm" variant="ghost">증빙</Button></Link>
                    <Link href={row.files_url}><Button size="sm" variant="ghost">파일함</Button></Link>
                    <Link href={row.audit_package_url}><Button size="sm" variant="ghost">감사자료</Button></Link>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  );
}

function TransactionReview({
  transactions,
  categories,
  activities,
  onCompleted,
}: {
  transactions: BankTransaction[];
  categories: BudgetCategory[];
  activities: ActivityReport[];
  onCompleted: () => Promise<void>;
}) {
  const [target, setTarget] = useState<BankTransaction | null>(null);
  const problemTransactions = transactions.filter((tx) =>
    tx.review_status !== "resolved" &&
    (!tx.payment_type || ["unmatched", "need_check", "amount_mismatch", "duplicate_candidate"].includes(tx.match_status)),
  ).slice(0, 15);
  return (
    <Card padding="lg">
      <SectionTitle title="거래 검토/수동 분류" hint="위험 작업은 미리보기 후 확정 적용" />
      {problemTransactions.length === 0 ? (
        <div className="mt-4"><EmptyState message="검토할 거래가 없습니다." /></div>
      ) : (
        <div className="mt-4 overflow-x-auto">
          <table className="w-full min-w-[860px] text-sm">
            <thead>
              <tr style={{ background: "var(--surface-soft)", borderBottom: "1px solid var(--border-soft)" }}>
                {["일시", "적요", "입금", "출금", "상태", "분류", "작업"].map((h) => (
                  <th key={h} className="whitespace-nowrap px-4 py-3 text-left text-xs font-semibold" style={{ color: "var(--text-muted)" }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {problemTransactions.map((tx) => (
                <tr key={tx.id} style={{ borderBottom: "1px solid var(--border-soft)" }}>
                  <td className="whitespace-nowrap px-4 py-3 text-xs" style={{ color: "var(--text-muted)" }}>{tx.transaction_datetime?.slice(0, 10) ?? "-"}</td>
                  <td className="max-w-[240px] truncate px-4 py-3" title={tx.memo ?? ""}>{tx.memo ?? "-"}</td>
                  <td className="whitespace-nowrap px-4 py-3 text-right" style={{ color: "var(--success)" }}>{tx.deposit_amount ? fmt(tx.deposit_amount) : "-"}</td>
                  <td className="whitespace-nowrap px-4 py-3 text-right" style={{ color: "var(--danger)" }}>{tx.withdraw_amount ? fmt(tx.withdraw_amount) : "-"}</td>
                  <td className="whitespace-nowrap px-4 py-3"><StatusBadge status={tx.match_status} /></td>
                  <td className="whitespace-nowrap px-4 py-3 text-xs" style={{ color: "var(--text-muted)" }}>{tx.payment_type ?? "미분류"}</td>
                  <td className="whitespace-nowrap px-4 py-3"><Button size="sm" variant="secondary" onClick={() => setTarget(tx)}>분류 변경</Button></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {target && (
        <ClassifyModal
          transaction={target}
          categories={categories}
          activities={activities}
          onClose={() => setTarget(null)}
          onCompleted={async () => {
            setTarget(null);
            await onCompleted();
          }}
        />
      )}
    </Card>
  );
}

function ClassifyModal({
  transaction,
  categories,
  activities,
  onClose,
  onCompleted,
}: {
  transaction: BankTransaction;
  categories: BudgetCategory[];
  activities: ActivityReport[];
  onClose: () => void;
  onCompleted: () => Promise<void>;
}) {
  const [paymentType, setPaymentType] = useState(transaction.payment_type ?? "");
  const [categoryId, setCategoryId] = useState(transaction.budget_category_id ?? "");
  const [activityId, setActivityId] = useState(transaction.linked_activity_id ?? "");
  const [note, setNote] = useState(transaction.review_note ?? "");
  const [preview, setPreview] = useState<BudgetTransactionClassifyPreview | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function doPreview() {
    setBusy(true);
    setError(null);
    try {
      setPreview(await previewBudgetTransactionClassify(transaction.id, {
        payment_type: paymentType || null,
        budget_category_id: categoryId || null,
        linked_activity_id: activityId || null,
        match_status: paymentType ? "classified" : transaction.match_status,
        review_status: "reviewed",
        review_note: note || null,
      }));
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  async function doConfirm() {
    if (!preview) return;
    setBusy(true);
    setError(null);
    try {
      await confirmBudgetTransactionClassify(preview.action_id);
      await onCompleted();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center sm:items-center" style={{ background: "rgba(31,31,36,0.45)" }}>
      <div className="w-full max-w-xl rounded-t-2xl p-6 sm:rounded-2xl" style={{ background: "var(--surface)", border: "1px solid var(--border-soft)" }}>
        <h3 className="text-base font-semibold" style={{ color: "var(--text-main)" }}>거래 수동 분류</h3>
        <p className="mt-1 text-xs" style={{ color: "var(--text-muted)" }}>{transaction.memo ?? "-"} · {fmt(transaction.deposit_amount || transaction.withdraw_amount)}원</p>
        <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2">
          <select style={inputStyle} value={paymentType} onChange={(event) => { setPaymentType(event.target.value); setPreview(null); }}>
            <option value="">거래 분류 선택</option>
            <option value="membership_fee">회비로 연결</option>
            <option value="activity_fee">특정 활동 활동비로 연결</option>
            <option value="activity_expense">특정 활동 지출로 연결</option>
            <option value="refund">환불</option>
            <option value="other">기타</option>
          </select>
          <select style={inputStyle} value={categoryId} onChange={(event) => { setCategoryId(event.target.value); setPreview(null); }}>
            <option value="">예산 항목 선택</option>
            {categories.map((category) => (
              <option key={category.id} value={category.id}>{category.type === "income" ? "수입" : "지출"} · {category.name}</option>
            ))}
          </select>
          <select style={inputStyle} value={activityId} onChange={(event) => { setActivityId(event.target.value); setPreview(null); }}>
            <option value="">활동 연결 없음</option>
            {activities.map((activity) => (
              <option key={activity.id} value={activity.id}>{activity.title}</option>
            ))}
          </select>
          <input style={inputStyle} value={note} placeholder="검토 메모" onChange={(event) => { setNote(event.target.value); setPreview(null); }} />
        </div>
        {preview && (
          <div className="mt-4 rounded-lg p-3 text-xs" style={{ background: "var(--surface-soft)", border: "1px solid var(--border-soft)", color: "var(--text-muted)" }}>
            미리보기 생성됨. 확정 전에는 DB가 수정되지 않습니다.
          </div>
        )}
        {error && <div className="mt-4"><ErrorState message={error} /></div>}
        <div className="mt-5 flex gap-2">
          <Button onClick={doPreview} loading={busy} variant="secondary">미리보기</Button>
          <Button onClick={doConfirm} disabled={!preview} loading={busy}>확정 적용</Button>
          <Button onClick={onClose} variant="ghost" disabled={busy}>닫기</Button>
        </div>
      </div>
    </div>
  );
}

export default function BudgetPage() {
  const [period, setPeriod] = useState(todayYearTerm());
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [operatingQuarter, setOperatingQuarter] = useState<string>("");
  const [summary, setSummary] = useState<BudgetSummary | null>(null);
  const [cashflow, setCashflow] = useState<BudgetCashflowRow[]>([]);
  const [categories, setCategories] = useState<BudgetCategory[]>([]);
  const [budgetRows, setBudgetRows] = useState<BudgetVsActualRow[]>([]);
  const [reviewItems, setReviewItems] = useState<BudgetReviewItem[]>([]);
  const [settlements, setSettlements] = useState<BudgetActivitySettlement[]>([]);
  const [transactions, setTransactions] = useState<BankTransaction[]>([]);
  const [activities, setActivities] = useState<ActivityReport[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [exportBusy, setExportBusy] = useState(false);

  const query = useMemo(() => ({
    period,
    start_date: operatingQuarter ? undefined : (startDate || undefined),
    end_date: operatingQuarter ? undefined : (endDate || undefined),
    operating_quarter: operatingQuarter || undefined,
  }), [period, startDate, endDate, operatingQuarter]);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const txParams = operatingQuarter
        ? { operating_quarter: operatingQuarter }
        : { start_date: startDate || undefined, end_date: endDate || undefined };

      const [s, cf, cats, rows, reviews, acts, txs, activityList] = await Promise.all([
        getBudgetSummary(query),
        getBudgetCashflow(query),
        getBudgetCategories({ include_inactive: true }),
        getBudgetVsActual(query),
        getBudgetReviewItems(query),
        getBudgetActivitySettlements(query),
        getTransactionsTyped(txParams),
        getActivityReportsFiltered(),
      ]);
      setSummary(s);
      setCashflow(cf);
      setCategories(cats);
      setBudgetRows(rows);
      setReviewItems(reviews);
      setSettlements(acts);
      setTransactions(txs);
      setActivities(activityList);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, []);

  const unpaidCsvRows = reviewItems
    .filter((item) => item.type === "membership_fee_summary" || item.type === "activity_fee_summary")
    .map((item) => ({ 유형: item.label, 대상: item.title, 금액: item.amount, 상태: item.status, 링크: item.target_url }));
  const reviewCsvRows = reviewItems.map((item) => ({ 유형: item.label, 제목: item.title, 금액: item.amount, 상태: item.status, 링크: item.target_url }));
  const exportBudgetRows = () => downloadCsv("budget-vs-actual.csv", budgetRows.map((row) => ({
    유형: row.type,
    항목: row.category_name,
    계획: row.planned_amount,
    실제: row.actual_amount,
    차이: row.difference_amount,
    메모: row.note,
  })));
  const exportSettlementRows = () => downloadCsv("activity-settlements.csv", settlements.map((row) => ({
    활동명: row.activity_title,
    활동일: row.activity_date,
    참가자수: row.participant_count,
    예정수입: row.expected_income,
    실제수입: row.actual_income,
    지출: row.expense_amount,
    차액: row.balance_amount,
    증빙: row.evidence_status,
    보고서: row.report_status,
  })));

  return (
    <AppShell>
      <div className="space-y-6">
        <PageHeader
          title="예산 관리"
          description="동아리 전체 예산, 수입·지출, 미납, 환불, 증빙, 활동별 정산을 한곳에서 확인합니다."
        />

        <Card padding="lg">
          <SectionTitle title="기간 필터" hint="거래/증빙은 운영 분기 기준, 회비 미납은 학기(period) 기준으로 집계합니다." />
          <div className="mt-4 flex flex-wrap gap-3 items-end">
            <QuarterFilter
              value={operatingQuarter}
              onChange={(q) => setOperatingQuarter(q)}
              label="운영 분기"
            />
            {!operatingQuarter && (
              <>
                <input type="date" style={{ ...inputStyle, minHeight: 44 }} value={startDate} onChange={(event) => setStartDate(event.target.value)} />
                <input type="date" style={{ ...inputStyle, minHeight: 44 }} value={endDate} onChange={(event) => setEndDate(event.target.value)} />
              </>
            )}
            <input style={{ ...inputStyle, minHeight: 44 }} value={period} onChange={(event) => setPeriod(event.target.value)} placeholder="회비 학기 (예: 2026-1)" title="회비 미납 집계에 사용되는 학기 기준" />
            <Button onClick={load} loading={loading}>조회</Button>
            {operatingQuarter && (
              <>
                <Button
                  variant="ghost" size="sm"
                  disabled={exportBusy}
                  onClick={async () => { setExportBusy(true); try { await downloadQuarterCsv(operatingQuarter); } finally { setExportBusy(false); } }}
                >
                  분기 CSV
                </Button>
                <Button
                  variant="ghost" size="sm"
                  disabled={exportBusy}
                  onClick={async () => { setExportBusy(true); try { await downloadQuarterZip(operatingQuarter); } finally { setExportBusy(false); } }}
                >
                  분기 증빙 ZIP
                </Button>
              </>
            )}
          </div>
        </Card>

        {error && <ErrorState message={error} onRetry={load} />}
        {loading && !summary ? <LoadingState /> : <SummaryCards summary={summary} />}

        <div className="grid grid-cols-1 gap-6 xl:grid-cols-2">
          <CashflowTable rows={cashflow} />
          <ReviewItems items={reviewItems} onResolved={load} />
        </div>

        <BudgetTable rows={budgetRows} categories={categories} period={period} onSaved={load} />
        <ActivitySettlements rows={settlements} />
        <TransactionReview transactions={transactions} categories={categories} activities={activities} onCompleted={load} />

        <Card padding="lg">
          <SectionTitle title="보고서/내보내기" hint="CSV로 내려받아 회계 보고서 작성에 사용합니다." />
          <div className="mt-4 flex flex-wrap gap-2">
            <Button variant="secondary" onClick={exportBudgetRows}>예산 대비 실제 CSV</Button>
            <Button variant="secondary" onClick={exportSettlementRows}>활동별 정산 CSV</Button>
            <Button variant="secondary" onClick={() => downloadCsv("unpaid-list.csv", unpaidCsvRows)}>미납자 목록 CSV</Button>
            <Button variant="secondary" onClick={() => downloadCsv("review-items.csv", reviewCsvRows)}>확인 필요 거래 CSV</Button>
          </div>
        </Card>
      </div>
    </AppShell>
  );
}
