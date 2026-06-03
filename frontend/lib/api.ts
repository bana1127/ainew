export type HealthResponse = {
  status: string;
  app: string;
  database: string;
  tables: Record<string, number>;
};

export type DashboardSummary = {
  total_members: number;
  active_members: number;
  total_activity_categories: number;
  total_reference_reports: number;
  total_activity_reports: number;
  draft_reports: number;
  total_receipts: number;
  pending_receipts: number;
  total_transactions: number;
  total_deposit_amount: number;
  total_withdraw_amount: number;
  total_payment_records: number;
  unpaid_count: number;
  unpaid_membership_fee_count: number;
  unpaid_activity_fee_count: number;
  unread_notifications: number;
};

export type CalendarEvent = {
  id: string;
  type: string;
  title: string;
  date: string;
  location: string;
  status: string;
  needs_report: boolean;
  needs_evidence: boolean;
  participant_count?: number;
  fee_status?: string;
  url: string;
};

export type DashboardCalendar = {
  month: string;
  events: CalendarEvent[];
};

export type DashboardTodo = {
  unpaid_membership_fee: number;
  unpaid_activity_fee: number;
  no_report_activities: number;
  no_evidence_activities: number;
  no_hwpx_activities: number;
};

export async function getDashboardCalendar(month?: string): Promise<DashboardCalendar> {
  const qs = month ? `?month=${month}` : "";
  return apiFetch<DashboardCalendar>(`/api/dashboard/calendar${qs}`);
}

export async function getDashboardTodo(): Promise<DashboardTodo> {
  return apiFetch<DashboardTodo>("/api/dashboard/todo");
}

export type ApiRecord = Record<string, unknown> & {
  id?: string;
  key?: string;
  name?: string;
  title?: string;
  status?: string;
  created_at?: string;
};

// API base URL.
// - Empty string (default) → uses Next.js /api/* rewrite → http://127.0.0.1:8001/api/*
// - Absolute URL (e.g. http://127.0.0.1:8001) → direct backend call (no rewrite needed)
// Set NEXT_PUBLIC_API_BASE_URL in .env.local to override.
const _raw = process.env.NEXT_PUBLIC_API_BASE_URL ?? "";
const API_BASE_URL = _raw.replace(/\/$/, "");

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    cache: "no-store",
    headers:
      options?.body instanceof FormData
        ? options.headers
        : {
            "Content-Type": "application/json",
            ...options?.headers,
          },
    ...options,
  });

  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || `API request failed with ${response.status}`);
  }

  return response.json();
}

export async function fetchHealth(): Promise<HealthResponse> {
  return apiFetch<HealthResponse>("/api/health");
}

export async function getDashboardSummary(): Promise<DashboardSummary> {
  return apiFetch<DashboardSummary>("/api/dashboard/summary");
}

export async function getMembers(): Promise<ApiRecord[]> {
  return apiFetch<ApiRecord[]>("/api/members");
}

export async function getActivityCategories(): Promise<ApiRecord[]> {
  return apiFetch<ApiRecord[]>("/api/activity-categories");
}

export async function getReferenceReports(): Promise<ApiRecord[]> {
  return apiFetch<ApiRecord[]>("/api/reference-reports");
}

export async function getActivityReports(): Promise<ApiRecord[]> {
  return apiFetch<ApiRecord[]>("/api/activity-reports");
}

export async function getReceipts(): Promise<ApiRecord[]> {
  return apiFetch<ApiRecord[]>("/api/receipts");
}

export async function getTransactions(): Promise<ApiRecord[]> {
  return apiFetch<ApiRecord[]>("/api/transactions");
}


export async function getNotifications(): Promise<ApiRecord[]> {
  return apiFetch<ApiRecord[]>("/api/notifications");
}

export async function getSettings(): Promise<ApiRecord[]> {
  return apiFetch<ApiRecord[]>("/api/settings");
}

export async function createRecord<T>(path: string, payload: unknown): Promise<T> {
  return apiFetch<T>(path, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function updateRecord<T>(path: string, payload: unknown): Promise<T> {
  return apiFetch<T>(path, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export async function deleteRecord<T>(path: string): Promise<T> {
  return apiFetch<T>(path, {
    method: "DELETE",
  });
}

export async function uploadFile(formData: FormData): Promise<ApiRecord> {
  return apiFetch<ApiRecord>("/api/files/upload", {
    method: "POST",
    body: formData,
  });
}

// ═══════════════════════════════════════════════════════════
// Task 4: Typed entities and CRUD API functions
// ═══════════════════════════════════════════════════════════

export type Member = {
  id: string;
  name: string;
  student_id: string | null;
  department: string | null;
  phone: string | null;
  email: string | null;
  status: string;
  memo: string | null;
  // Task 26-booster
  gender: string | null;
  grade: string | null;
  birth_year: number | null;
  joined_term: string | null;
  term_code: string | null;
  is_executive: boolean;
  role: string | null;
  is_officer: boolean;
  officer_role: "president" | "vice_president" | "officer" | null;
  created_at: string;
  updated_at: string;
};

export type MemberCreate = {
  name: string;
  student_id?: string | null;
  department?: string | null;
  phone?: string | null;
  email?: string | null;
  status?: string;
  memo?: string | null;
  gender?: string | null;
  grade?: string | null;
  birth_year?: number | null;
  joined_term?: string | null;
  term_code?: string | null;
  is_executive?: boolean;
  role?: string | null;
  is_officer?: boolean;
  officer_role?: "president" | "vice_president" | "officer" | null;
};

export type MemberUpdate = Partial<MemberCreate>;

export type ActivityCategory = {
  id: string;
  name: string;
  description: string | null;
  required_fields_json: Record<string, unknown> | null;
  report_template: string | null;
  created_at: string;
  updated_at: string;
};

export type ActivityCategoryCreate = {
  name: string;
  description?: string | null;
  required_fields_json?: Record<string, unknown> | null;
  report_template?: string | null;
};

export type ActivityCategoryUpdate = Partial<ActivityCategoryCreate>;

export type ReferenceReport = {
  id: string;
  category_id: string | null;
  title: string;
  content: string;
  tags: string[] | null;
  created_at: string;
  updated_at: string;
};

export type ReferenceReportCreate = {
  category_id?: string | null;
  title: string;
  content: string;
  tags?: string[] | null;
};

export type ReferenceReportUpdate = Partial<ReferenceReportCreate>;

export type ActivityReport = {
  id: string;
  category_id: string | null;
  title: string;
  activity_date: string | null;
  location: string | null;
  input_text: string | null;
  generated_content: string | null;
  final_content: string | null;
  status: string;
  created_at: string;
  updated_at: string;
};

export type ActivityReportCreate = {
  category_id?: string | null;
  title: string;
  activity_date?: string | null;
  location?: string | null;
  input_text?: string | null;
  generated_content?: string | null;
  final_content?: string | null;
  status?: string;
};

export type ActivityReportUpdate = Partial<ActivityReportCreate>;

export type ActivityParticipant = {
  id: string;
  activity_report_id: string;
  member_id: string;
  role: string | null;
  created_at: string;
  member?: {
    id: string;
    name: string;
    student_id: string | null;
  };
};

function buildQuery(params: Record<string, string | undefined>): string {
  const qs = Object.entries(params)
    .filter(([, v]) => v !== undefined && v !== "")
    .map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(v!)}`)
    .join("&");
  return qs ? `?${qs}` : "";
}

// Members CRUD

export async function getMembersFiltered(params?: {
  status?: string;
  q?: string;
  limit?: number;
  is_executive?: boolean;
  role?: string;
  is_officer?: boolean;
  officer_role?: string;
}): Promise<Member[]> {
  const p: Record<string, string | undefined> = {};
  if (params?.status) p.status = params.status;
  if (params?.q) p.q = params.q;
  if (params?.limit !== undefined) p.limit = String(params.limit);
  if (params?.is_executive !== undefined) p.is_executive = String(params.is_executive);
  if (params?.role) p.role = params.role;
  if (params?.is_officer !== undefined) p.is_officer = String(params.is_officer);
  if (params?.officer_role) p.officer_role = params.officer_role;
  return apiFetch<Member[]>(`/api/members${buildQuery(p)}`);
}

export async function createMember(data: MemberCreate): Promise<Member> {
  return apiFetch<Member>("/api/members", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function updateMember(id: string, data: MemberUpdate): Promise<Member> {
  return apiFetch<Member>(`/api/members/${id}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

export async function deleteMember(id: string): Promise<Member> {
  return apiFetch<Member>(`/api/members/${id}`, { method: "DELETE" });
}

// Activity Categories CRUD

export async function getActivityCategoriesTyped(): Promise<ActivityCategory[]> {
  return apiFetch<ActivityCategory[]>("/api/activity-categories");
}

export async function createActivityCategory(
  data: ActivityCategoryCreate,
): Promise<ActivityCategory> {
  return apiFetch<ActivityCategory>("/api/activity-categories", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function updateActivityCategory(
  id: string,
  data: ActivityCategoryUpdate,
): Promise<ActivityCategory> {
  return apiFetch<ActivityCategory>(`/api/activity-categories/${id}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

export async function deleteActivityCategory(id: string): Promise<ActivityCategory> {
  return apiFetch<ActivityCategory>(`/api/activity-categories/${id}`, {
    method: "DELETE",
  });
}

// Reference Reports CRUD

export async function getReferenceReportsFiltered(params?: {
  category_id?: string;
  q?: string;
}): Promise<ReferenceReport[]> {
  return apiFetch<ReferenceReport[]>(`/api/reference-reports${buildQuery(params ?? {})}`);
}

export async function createReferenceReport(
  data: ReferenceReportCreate,
): Promise<ReferenceReport> {
  return apiFetch<ReferenceReport>("/api/reference-reports", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function updateReferenceReport(
  id: string,
  data: ReferenceReportUpdate,
): Promise<ReferenceReport> {
  return apiFetch<ReferenceReport>(`/api/reference-reports/${id}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

export async function deleteReferenceReport(id: string): Promise<ReferenceReport> {
  return apiFetch<ReferenceReport>(`/api/reference-reports/${id}`, {
    method: "DELETE",
  });
}

// Activity Reports CRUD

export async function getActivityReportsFiltered(params?: {
  category_id?: string;
  status?: string;
  q?: string;
}): Promise<ActivityReport[]> {
  return apiFetch<ActivityReport[]>(`/api/activity-reports${buildQuery(params ?? {})}`);
}

export async function createActivityReport(
  data: ActivityReportCreate,
): Promise<ActivityReport> {
  return apiFetch<ActivityReport>("/api/activity-reports", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function updateActivityReport(
  id: string,
  data: ActivityReportUpdate,
): Promise<ActivityReport> {
  return apiFetch<ActivityReport>(`/api/activity-reports/${id}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

export async function deleteActivityReport(id: string): Promise<ActivityReport> {
  return apiFetch<ActivityReport>(`/api/activity-reports/${id}`, {
    method: "DELETE",
  });
}

// Activity Participants

export async function getActivityReportParticipants(
  reportId: string,
): Promise<ActivityParticipant[]> {
  return apiFetch<ActivityParticipant[]>(
    `/api/activity-reports/${reportId}/participants`,
  );
}

export async function updateActivityReportParticipants(
  reportId: string,
  participants: Array<{ member_id: string; role?: string }>,
): Promise<ActivityParticipant[]> {
  return apiFetch<ActivityParticipant[]>(
    `/api/activity-reports/${reportId}/participants`,
    {
      method: "PUT",
      body: JSON.stringify({ participants }),
    },
  );
}

// ═══════════════════════════════════════════════════════════
// Task 5: Bank statement types and API functions
// ═══════════════════════════════════════════════════════════

export type BankTransaction = {
  id: string;
  transaction_datetime: string | null;
  transaction_type: string | null;
  memo: string | null;
  withdraw_amount: number;
  deposit_amount: number;
  balance: number | null;
  branch: string | null;
  match_status: string;
  payment_type: string | null;
  matched_member_id: string | null;
  budget_category_id?: string | null;
  linked_activity_id?: string | null;
  review_status?: string | null;
  review_note?: string | null;
  created_at: string;
  updated_at: string;
};

export type ParsedBankTransaction = {
  row_index: number;
  transaction_datetime: string | null;
  transaction_type: string | null;
  memo: string | null;
  withdraw_amount: number;
  deposit_amount: number;
  balance: number | null;
  branch: string | null;
  warnings: string[];
};

export type BankStatementPreviewResponse = {
  file_id: string;
  total_rows: number;
  parsed_rows: number;
  skipped_rows: number;
  transactions: ParsedBankTransaction[];
  errors: string[];
  warnings: string[];
};

export type BankStatementImportResponse = {
  file_id: string;
  total_rows: number;
  parsed_rows: number;
  inserted_rows: number;
  skipped_rows: number;
  duplicate_rows: number;
  errors: string[];
  warnings: string[];
};

export type TransactionQueryParams = {
  skip?: number;
  limit?: number;
  match_status?: string;
  payment_type?: string;
  start_date?: string;
  end_date?: string;
  min_deposit?: number;
  max_deposit?: number;
  min_withdraw?: number;
  max_withdraw?: number;
  q?: string;
};

export async function parseTransactionPreview(
  file: File,
): Promise<BankStatementPreviewResponse> {
  const formData = new FormData();
  formData.append("file", file);
  return apiFetch<BankStatementPreviewResponse>(
    "/api/transactions/parse-preview",
    { method: "POST", body: formData },
  );
}

export async function importTransactions(
  file: File,
): Promise<BankStatementImportResponse> {
  const formData = new FormData();
  formData.append("file", file);
  return apiFetch<BankStatementImportResponse>("/api/transactions/import", {
    method: "POST",
    body: formData,
  });
}

export async function getTransactionsTyped(
  params?: TransactionQueryParams,
): Promise<BankTransaction[]> {
  const p: Record<string, string | undefined> = {};
  if (params) {
    if (params.match_status) p.match_status = params.match_status;
    if (params.payment_type) p.payment_type = params.payment_type;
    if (params.start_date) p.start_date = params.start_date;
    if (params.end_date) p.end_date = params.end_date;
    if (params.q) p.q = params.q;
    if (params.min_deposit !== undefined) p.min_deposit = String(params.min_deposit);
    if (params.max_deposit !== undefined) p.max_deposit = String(params.max_deposit);
    if (params.min_withdraw !== undefined) p.min_withdraw = String(params.min_withdraw);
    if (params.max_withdraw !== undefined) p.max_withdraw = String(params.max_withdraw);
    if (params.skip !== undefined) p.skip = String(params.skip);
    if (params.limit !== undefined) p.limit = String(params.limit);
  }
  return apiFetch<BankTransaction[]>(`/api/transactions${buildQuery(p)}`);
}

// ─── Budget management (Task 38) ─────────────────────────────────────────────

export type BudgetSummary = {
  current_balance: number;
  total_income: number;
  total_expense: number;
  net_change: number;
  receivable_amount: number;
  refund_scheduled_amount: number;
  review_transaction_count: number;
  missing_evidence_count: number;
  period: string | null;
  start_date: string | null;
  end_date: string | null;
};

export type BudgetCashflowRow = {
  bucket: string;
  income: number;
  expense: number;
  net: number;
};

export type BudgetCategory = {
  id: string;
  name: string;
  type: "income" | "expense";
  parent_id: string | null;
  sort_order: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
};

export type BudgetPlan = {
  id: string;
  period: string;
  category_id: string;
  planned_amount: number;
  note: string | null;
  created_at: string;
  updated_at: string;
};

export type BudgetVsActualRow = {
  category_id: string;
  category_name: string;
  type: "income" | "expense";
  is_active: boolean;
  planned_amount: number;
  actual_amount: number;
  difference_amount: number;
  over_budget: boolean;
  note: string | null;
};

export type BudgetReviewItem = {
  id: string;
  type: string;
  label: string;
  title: string | null;
  amount: number;
  status: string | null;
  target_url: string;
  severity: "danger" | "warning" | "info" | string;
  source_id: string;
};

export type BudgetActivitySettlement = {
  activity_id: string;
  activity_title: string;
  activity_date: string | null;
  participant_count: number;
  expected_income: number;
  actual_income: number;
  expense_amount: number;
  balance_amount: number;
  evidence_status: string;
  report_status: string;
  target_url: string;
  activity_fee_url: string;
  evidence_url: string;
  files_url: string;
  audit_package_url: string;
};

export type BudgetTransactionClassifyPreview = {
  ok: boolean;
  requires_confirmation: boolean;
  auto_apply: boolean;
  action_id: string;
  transaction_id: string;
  before: Record<string, string | null>;
  after: Record<string, string | null>;
};

function budgetQuery(params?: {
  period?: string;
  start_date?: string;
  end_date?: string;
  include_inactive?: boolean;
}) {
  const p: Record<string, string | undefined> = {};
  if (params?.period) p.period = params.period;
  if (params?.start_date) p.start_date = params.start_date;
  if (params?.end_date) p.end_date = params.end_date;
  if (params?.include_inactive !== undefined) p.include_inactive = String(params.include_inactive);
  return buildQuery(p);
}

export async function getBudgetSummary(params?: {
  period?: string;
  start_date?: string;
  end_date?: string;
}): Promise<BudgetSummary> {
  return apiFetch<BudgetSummary>(`/api/budget/summary${budgetQuery(params)}`);
}

export async function getBudgetCashflow(params?: {
  start_date?: string;
  end_date?: string;
}): Promise<BudgetCashflowRow[]> {
  return apiFetch<BudgetCashflowRow[]>(`/api/budget/cashflow${budgetQuery(params)}`);
}

export async function getBudgetCategories(params?: {
  include_inactive?: boolean;
}): Promise<BudgetCategory[]> {
  return apiFetch<BudgetCategory[]>(`/api/budget/categories${budgetQuery(params)}`);
}

export async function createBudgetCategory(payload: {
  name: string;
  type: "income" | "expense";
  parent_id?: string | null;
  sort_order?: number;
  is_active?: boolean;
}): Promise<BudgetCategory> {
  return apiFetch<BudgetCategory>("/api/budget/categories", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function updateBudgetCategory(
  id: string,
  payload: Partial<Pick<BudgetCategory, "name" | "type" | "parent_id" | "sort_order" | "is_active">>,
): Promise<BudgetCategory> {
  return apiFetch<BudgetCategory>(`/api/budget/categories/${id}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export async function getBudgetPlans(period?: string): Promise<BudgetPlan[]> {
  return apiFetch<BudgetPlan[]>(`/api/budget/plans${budgetQuery({ period })}`);
}

export async function saveBudgetPlan(payload: {
  period: string;
  category_id: string;
  planned_amount: number;
  note?: string | null;
}): Promise<BudgetPlan> {
  return apiFetch<BudgetPlan>("/api/budget/plans", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function updateBudgetPlan(
  id: string,
  payload: Partial<Pick<BudgetPlan, "period" | "category_id" | "planned_amount" | "note">>,
): Promise<BudgetPlan> {
  return apiFetch<BudgetPlan>(`/api/budget/plans/${id}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export async function getBudgetVsActual(params: {
  period: string;
  start_date?: string;
  end_date?: string;
}): Promise<BudgetVsActualRow[]> {
  return apiFetch<BudgetVsActualRow[]>(`/api/budget/budget-vs-actual${budgetQuery(params)}`);
}

export async function getBudgetActivitySettlements(params?: {
  start_date?: string;
  end_date?: string;
}): Promise<BudgetActivitySettlement[]> {
  return apiFetch<BudgetActivitySettlement[]>(`/api/budget/activity-settlements${budgetQuery(params)}`);
}

export async function getBudgetReviewItems(params?: {
  period?: string;
  start_date?: string;
  end_date?: string;
}): Promise<BudgetReviewItem[]> {
  return apiFetch<BudgetReviewItem[]>(`/api/budget/review-items${budgetQuery(params)}`);
}

export async function resolveBudgetReviewItem(
  itemId: string,
  note?: string,
): Promise<{ ok: boolean; id: string; status: string }> {
  return apiFetch(`/api/budget/review-items/${encodeURIComponent(itemId)}/resolve`, {
    method: "POST",
    body: JSON.stringify({ note: note ?? null }),
  });
}

export async function previewBudgetTransactionClassify(
  transactionId: string,
  payload: {
    payment_type?: string | null;
    budget_category_id?: string | null;
    linked_activity_id?: string | null;
    match_status?: string | null;
    review_status?: string | null;
    review_note?: string | null;
  },
): Promise<BudgetTransactionClassifyPreview> {
  return apiFetch<BudgetTransactionClassifyPreview>(
    `/api/budget/transactions/${transactionId}/classify-preview`,
    { method: "POST", body: JSON.stringify(payload) },
  );
}

export async function confirmBudgetTransactionClassify(
  actionId: string,
): Promise<Record<string, unknown>> {
  return apiFetch<Record<string, unknown>>("/api/budget/transactions/classify-confirm", {
    method: "POST",
    body: JSON.stringify({ action_id: actionId }),
  });
}

// ═══════════════════════════════════════════════════════════
// Task 6: Payment matching types and API functions
// ═══════════════════════════════════════════════════════════

export type TransactionMatchItem = {
  transaction_id: string;
  transaction_datetime: string | null;
  memo: string | null;
  deposit_amount: number;
  matched_member_id: string | null;
  matched_member_name: string | null;
  payment_type: string | null;
  match_status: string;
  score: number | null;
  reason: string | null;
  activity_id: string | null;
  activity_title: string | null;
  match_mode: string | null;
  expected_amount?: number | null;
  amount_difference?: number | null;
  amount_status?: string | null;
  auto_match?: boolean;
  fee_tier?: string | null;
};

export type MemberSummary = {
  member_id: string;
  name: string;
  student_id: string | null;
  department: string | null;
  required_amount: number;
  paid_amount: number;
  status: string;
};

export type UnpaidPaymentItem = {
  member_id: string;
  name: string;
  student_id: string | null;
  department: string | null;
  required_amount: number;
  paid_amount: number;
  status: string;
  payment_record_id?: string | null;
};

export type PaymentMatchingPayload = {
  period: string;
  payment_type?: string;
  required_amount?: number | null;
  start_date?: string | null;
  end_date?: string | null;
  match_mode?: string;  // auto | membership_fee | activity_fee | selected_activity_fee | none
  activity_id?: string | null;
};

export type PaymentMatchingPreview = {
  period: string;
  payment_type: string;
  required_amount: number;
  total_active_members: number;
  total_deposit_transactions: number;
  matched_count: number;
  need_check_count: number;
  excluded_count: number;
  unpaid_count: number;
  matched_items: TransactionMatchItem[];
  need_check_items: TransactionMatchItem[];
  excluded_items: TransactionMatchItem[];
  unpaid_members: MemberSummary[];
};

export type PaymentMatchingResult = PaymentMatchingPreview & {
  created_payment_records: number;
  updated_payment_records: number;
  updated_transactions: number;
};

export type PaymentSummary = {
  period: string;
  payment_type: string;
  required_amount: number;
  total_members: number;
  paid_count: number;
  partial_count: number;
  unpaid_count: number;
  need_check_count: number;
  exempt_count?: number;
  overpaid_count?: number;
  missing_record_count?: number;
  receivable_amount?: number;
  total_required_amount: number;
  total_paid_amount: number;
};

export type PaymentRecord = {
  id: string;
  member_id: string;
  member_name?: string | null;
  student_id?: string | null;
  department?: string | null;
  period: string;
  payment_type: string;
  required_amount: number;
  paid_amount: number;
  status: string;
  transaction_id: string | null;
  activity_report_id?: string | null;
  activity_title?: string | null;
  refund_status?: string | null;
  refund_amount?: number | null;
  fee_tier?: string | null;
  fee_rule_reason?: string | null;
  joined_term?: string | null;
  current_term?: string | null;
  payment_source?: "transaction_match" | "manual" | "imported" | string | null;
  manual_note?: string | null;
  created_at: string;
  updated_at: string;
};

export type MembershipPaymentHistoryItem = {
  id: string;
  created_at: string | null;
  payment_record_id: string;
  member_id: string;
  member_name: string;
  student_id: string | null;
  action: string;
  previous_status: string | null;
  new_status: string | null;
  previous_paid_amount: number | null;
  new_paid_amount: number | null;
  payment_source: string | null;
  manual_note: string | null;
  reason: string | null;
};

export type MembershipFeePreviewPayload = {
  period?: string | null;
  new_member_fee?: number;
  existing_member_fee?: number;
  executive_fee?: number;
};

export type MembershipFeePreviewRow = {
  member_id: string;
  member_name: string;
  student_id: string | null;
  department: string | null;
  joined_term: string | null;
  term_code: string | null;
  current_term: string;
  is_officer: boolean;
  officer_role: "president" | "vice_president" | "officer" | null;
  role_label: string;
  fee_tier: "new" | "existing" | "executive";
  required_amount: number;
  paid_amount: number;
  status: string;
  fee_rule_reason: string;
  existing_record_id: string | null;
  action: "create" | "update";
};

export type MembershipFeePreview = {
  period: string;
  payment_type: "membership_fee";
  current_term: string;
  new_member_fee: number;
  existing_member_fee: number;
  executive_fee: number;
  requires_confirmation: boolean;
  auto_apply: boolean;
  action_id: string | null;
  summary: {
    total_members: number;
    current_term: string;
    new_member_count: number;
    existing_member_count: number;
    executive_count: number;
    total_required_amount: number;
    total_paid_amount: number;
    created_count: number;
    updated_count: number;
    preserved_paid_count: number;
  };
  rows: MembershipFeePreviewRow[];
};

export async function previewPaymentMatching(
  payload: PaymentMatchingPayload,
): Promise<PaymentMatchingPreview> {
  return apiFetch<PaymentMatchingPreview>("/api/payments/match-preview", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function applyPaymentMatching(
  payload: PaymentMatchingPayload,
): Promise<PaymentMatchingResult> {
  return apiFetch<PaymentMatchingResult>("/api/payments/match-apply", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function confirmPaymentTransaction(
  transactionId: string,
  payload: {
    member_id: string;
    period: string;
    payment_type?: string;
    required_amount?: number;
    status?: string;
  },
): Promise<PaymentRecord> {
  return apiFetch<PaymentRecord>(
    `/api/payments/transactions/${transactionId}/confirm`,
    { method: "PATCH", body: JSON.stringify(payload) },
  );
}

export async function excludePaymentTransaction(
  transactionId: string,
  payload: { payment_type?: string; reason?: string },
): Promise<Record<string, unknown>> {
  return apiFetch<Record<string, unknown>>(
    `/api/payments/transactions/${transactionId}/exclude`,
    { method: "PATCH", body: JSON.stringify(payload) },
  );
}

export async function getPaymentSummary(params: {
  period: string;
  payment_type?: string;
}): Promise<PaymentSummary> {
  return apiFetch<PaymentSummary>(
    `/api/payments/summary${buildQuery(params)}`,
  );
}

export async function getMembershipSummary(period: string): Promise<PaymentSummary> {
  return apiFetch<PaymentSummary>(
    `/api/payments/membership/summary${buildQuery({ period })}`,
  );
}

export async function getMembershipHistory(params: {
  period: string;
  limit?: number;
}): Promise<MembershipPaymentHistoryItem[]> {
  return apiFetch<MembershipPaymentHistoryItem[]>(
    `/api/payments/membership/history${buildQuery({
      period: params.period,
      limit: params.limit !== undefined ? String(params.limit) : undefined,
    })}`,
  );
}

export async function getUnpaidPayments(params: {
  period: string;
  payment_type?: string;
}): Promise<UnpaidPaymentItem[]> {
  return apiFetch<UnpaidPaymentItem[]>(
    `/api/payments/unpaid${buildQuery(params)}`,
  );
}

export async function getPaymentRecords(params?: {
  period?: string;
  payment_type?: string;
  status?: string;
  member_id?: string;
}): Promise<PaymentRecord[]> {
  return apiFetch<PaymentRecord[]>(
    `/api/payment-records${buildQuery(params ?? {})}`,
  );
}

export type ManualPaymentRecordPayload = {
  member_id: string;
  period: string;
  payment_type: string;
  required_amount: number;
  paid_amount: number;
  status?: "unpaid" | "paid" | "partial" | "overpaid" | "need_check" | "exempt";
  manual_note?: string | null;
};

export async function updatePaymentRecord(
  id: string,
  payload: Partial<PaymentRecord>,
): Promise<PaymentRecord> {
  return apiFetch<PaymentRecord>(`/api/payment-records/${id}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export async function upsertManualPaymentRecord(
  payload: ManualPaymentRecordPayload,
): Promise<PaymentRecord> {
  return apiFetch<PaymentRecord>(`/api/payment-records/manual`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

export async function patchMembershipPaymentRecord(
  id: string,
  payload: {
    required_amount?: number | null;
    paid_amount?: number | null;
    status?: string | null;
    manual_note?: string | null;
  },
): Promise<PaymentRecord> {
  return apiFetch<PaymentRecord>(`/api/payments/membership/${id}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export async function previewMembershipSyncTargets(
  payload: MembershipFeePreviewPayload,
): Promise<MembershipFeePreview> {
  return apiFetch<MembershipFeePreview>("/api/payments/membership/sync-targets-preview", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function confirmMembershipSyncTargets(
  actionId: string,
): Promise<Record<string, unknown>> {
  return apiFetch<Record<string, unknown>>("/api/payments/membership/sync-targets-confirm", {
    method: "POST",
    body: JSON.stringify({ action_id: actionId }),
  });
}

// ─── Membership fee bulk update (Task 37) ────────────────────────────────────

export type MembershipBulkUpdateRow = {
  payment_record_id: string;
  member_id: string | null;
  member_name: string | null;
  student_id: string | null;
  before_required_amount: number;
  before_paid_amount: number;
  before_status: string;
  after_required_amount: number;
  after_paid_amount: number;
  after_status: string;
  will_change: boolean;
  note: string | null;
};

export type MembershipBulkUpdateSummary = {
  selected: number;
  will_change: number;
  no_change: number;
  will_be_paid: number;
  will_be_exempt: number;
  will_be_unpaid: number;
  will_be_need_check: number;
  danger: boolean;
  danger_reason: string | null;
};

export type MembershipBulkUpdatePreviewResult = {
  ok: boolean;
  requires_confirmation: boolean;
  auto_apply: boolean;
  action_id: string;
  operation: string;
  period: string;
  summary: MembershipBulkUpdateSummary;
  rows: MembershipBulkUpdateRow[];
};

export type MembershipBulkUpdateConfirmResult = {
  ok: boolean;
  operation: string;
  period: string;
  updated_count: number;
  skipped_count: number;
  rows_updated: string[];
};

export async function previewMembershipBulkUpdate(payload: {
  period: string;
  payment_record_ids: string[];
  operation: string;
  paid_amount_value?: number | null;
}): Promise<MembershipBulkUpdatePreviewResult> {
  return apiFetch<MembershipBulkUpdatePreviewResult>(
    "/api/payment-records/membership/bulk-preview",
    { method: "POST", body: JSON.stringify(payload) },
  );
}

export async function confirmMembershipBulkUpdate(
  actionId: string,
): Promise<MembershipBulkUpdateConfirmResult> {
  return apiFetch<MembershipBulkUpdateConfirmResult>(
    "/api/payment-records/membership/bulk-confirm",
    { method: "POST", body: JSON.stringify({ action_id: actionId }) },
  );
}

export async function previewMembershipFees(
  payload: MembershipFeePreviewPayload,
): Promise<MembershipFeePreview> {
  return apiFetch<MembershipFeePreview>("/api/payments/membership-fees/preview", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

// ═══════════════════════════════════════════════════════════
// Task 7: Activity report generation types and API functions
// ═══════════════════════════════════════════════════════════

export type ActivityReportGenerateRequest = {
  activity_report_id?: string | null;
  category_id: string;
  reference_report_id?: string | null;
  title: string;
  activity_date?: string | null;
  location?: string | null;
  input_text?: string | null;
  participant_ids?: string[];
  file_ids?: string[];
  save_to_db?: boolean;
};

export type ActivityReportGenerateResponse = {
  activity_report_id: string | null;
  title: string;
  summary: string;
  content: string;
  missing_fields: string[];
  confidence: number;
  model: string;
  saved: boolean;
};

export async function generateActivityReportDraft(
  payload: ActivityReportGenerateRequest,
): Promise<ActivityReportGenerateResponse> {
  return apiFetch<ActivityReportGenerateResponse>(
    "/api/agents/activity-report/generate",
    {
      method: "POST",
      body: JSON.stringify(payload),
    },
  );
}

// ═══════════════════════════════════════════════════════════
// Task 8: Receipt analysis types and API functions
// ═══════════════════════════════════════════════════════════

export type ReceiptExtractedData = {
  receipt_date: string | null;
  store_name: string | null;
  amount: number;
  payment_method: string;
  category: string | null;
  raw_text: string | null;
  confidence: number;
};

export type ReceiptPolicyCheckResult = {
  evidence_status: string;
  need_check: boolean;
  required_evidence: string[];
  reason: string;
  rule_key: string;
};

export type ReceiptAnalyzeResponse = {
  receipt_id: string | null;
  file_id: string | null;
  activity_report_id: string | null;
  extracted: ReceiptExtractedData;
  policy: ReceiptPolicyCheckResult;
  saved: boolean;
  model: string;
};

export type Receipt = {
  id: string;
  activity_report_id: string | null;
  file_id: string | null;
  receipt_date: string | null;
  store_name: string | null;
  amount: number;
  payment_method: string | null;
  category: string | null;
  evidence_status: string;
  need_check: boolean;
  reason: string | null;
  created_at: string;
  updated_at: string;
};

export type ReceiptQueryParams = {
  skip?: number;
  limit?: number;
  activity_report_id?: string;
  evidence_status?: string;
  need_check?: boolean;
  payment_method?: string;
  category?: string;
  start_date?: string;
  end_date?: string;
  q?: string;
};

export type ReceiptUpdate = {
  evidence_status?: string;
  need_check?: boolean;
  reason?: string;
  store_name?: string;
  amount?: number;
  payment_method?: string;
  category?: string;
  receipt_date?: string | null;
};

export async function analyzeReceipt(
  formData: FormData,
): Promise<ReceiptAnalyzeResponse> {
  return apiFetch<ReceiptAnalyzeResponse>("/api/agents/receipt/analyze", {
    method: "POST",
    body: formData,
  });
}

export async function getReceiptsTyped(
  params?: ReceiptQueryParams,
): Promise<Receipt[]> {
  const p: Record<string, string | undefined> = {};
  if (params) {
    if (params.activity_report_id) p.activity_report_id = params.activity_report_id;
    if (params.evidence_status) p.evidence_status = params.evidence_status;
    if (params.payment_method) p.payment_method = params.payment_method;
    if (params.category) p.category = params.category;
    if (params.start_date) p.start_date = params.start_date;
    if (params.end_date) p.end_date = params.end_date;
    if (params.q) p.q = params.q;
    if (params.need_check !== undefined) p.need_check = String(params.need_check);
    if (params.skip !== undefined) p.skip = String(params.skip);
    if (params.limit !== undefined) p.limit = String(params.limit);
  }
  return apiFetch<Receipt[]>(`/api/receipts${buildQuery(p)}`);
}

export async function updateReceiptTyped(
  id: string,
  payload: ReceiptUpdate,
): Promise<Receipt> {
  return apiFetch<Receipt>(`/api/receipts/${id}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export async function deleteReceipt(id: string): Promise<Receipt> {
  return apiFetch<Receipt>(`/api/receipts/${id}`, { method: "DELETE" });
}

// ═══════════════════════════════════════════════════════════
// Task 10: Assistant Command Center types and API functions
// ═══════════════════════════════════════════════════════════

export type AssistantIntent =
  | "receipt_analysis"
  | "bank_statement_import"
  | "payment_matching"
  | "activity_report_generate"
  | "activity_fee_generate"
  | "payment_manual_update"
  | "activity_link"
  | "activity_create"
  | "activity_create_with_roster"
  | "activity_create_with_application_form"
  | "activity_create_with_file"
  | "google_form_import"
  | "participant_import"
  | "unknown";

export type AssistantResultType =
  | "receipt_analysis"
  | "bank_statement_preview"
  | "bank_statement_import_result"
  | "payment_matching_preview"
  | "payment_matching_result"
  | "activity_report_draft"
  | "activity_candidate"
  | "activity_draft"
  | "activity_fee_generation_result"
  | "payment_manual_update_result"
  | "activity_import_result"
  | "google_form_import_preview"
  | "participant_import_preview"
  | "bulk_membership_fee_mark_paid_preview"
  | "activity_fee_transaction_match_preview"
  | "activity_linked_result"
  | "general_message"
  | "error";

export type ActivityContextMode = "linked" | "current_activity" | "created" | "candidate" | "create_draft" | "needs_confirmation" | "none";

export type ActivityContextInfo = {
  mode: ActivityContextMode;
  activity_id?: string;
  activity_title?: string;
  confidence: number;
};

export type ActivityCandidateInfo = {
  id: string;
  title: string;
  activity_date: string | null;
  location: string | null;
  score: number;
};

export type ActivityDraftInfo = {
  title: string;
  activity_date: string | null;
  location: string | null;
  description: string | null;
};

export type AssistantExecuteResponse = {
  intent: AssistantIntent;
  confidence: number;
  agent_flow: string[];
  result_type: AssistantResultType;
  result: Record<string, unknown>;
  requires_confirmation: boolean;
  message: string;
  apply_payload?: Record<string, unknown> | null;
  detail_url?: string | null;
  // Task 17: Activity context
  activity_context?: ActivityContextInfo | null;
  activity_candidates?: ActivityCandidateInfo[] | null;
  activity_draft?: ActivityDraftInfo | null;
};

export type AssistantActionApplyResult = {
  ok: boolean;
  action_id: string;
  action_type: string;
  status: string;
  activity_id: string | null;
  result?: Record<string, unknown>;
};

export type AssistantChatContext = {
  page?: string | null;
  activity_id?: string | null;
  period?: string | null;
};

export type AssistantChatLink = {
  label: string;
  url: string;
};

export type AssistantChatResponse = {
  answer: string;
  intent:
    | "member_count"
    | "activity_count"
    | "activity_participant_count"
    | "membership_fee_status"
    | "activity_fee_status"
    | "budget_summary"
    | "cashflow_summary"
    | "activity_settlement_status"
    | "evidence_missing"
    | "report_missing"
    | "audit_readiness"
    | "document_summary"
    | "receipt_summary"
    | "unknown";
  data_sources: string[];
  links: AssistantChatLink[];
  confidence: number;
};

export async function getAssistantChatSuggestions(): Promise<string[]> {
  const response = await apiFetch<{ suggestions: string[] }>("/api/assistant/chat/suggestions");
  return response.suggestions;
}

export async function sendAssistantChat(payload: {
  message: string;
  context?: AssistantChatContext | null;
}): Promise<AssistantChatResponse> {
  return apiFetch<AssistantChatResponse>("/api/assistant/chat", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function executeAssistant(
  formData: FormData,
): Promise<AssistantExecuteResponse> {
  return apiFetch<AssistantExecuteResponse>("/api/assistant/execute", {
    method: "POST",
    body: formData,
  });
}

export async function confirmAssistantAction(actionId: string): Promise<AssistantActionApplyResult> {
  return apiFetch<AssistantActionApplyResult>(`/api/assistant/actions/${actionId}/confirm`, {
    method: "POST",
  });
}

export async function cancelAssistantAction(actionId: string): Promise<AssistantActionApplyResult> {
  return apiFetch<AssistantActionApplyResult>(`/api/assistant/actions/${actionId}/cancel`, {
    method: "POST",
  });
}

// ═══════════════════════════════════════════════════════════
// Task 16: Activity-centric API functions
// ═══════════════════════════════════════════════════════════

export type ActivitySummary = {
  id: string;
  title: string;
  activity_date: string | null;
  location: string | null;
  category_name: string | null;
  category_id: string | null;
  participant_count: number;
  report_status: string;
  activity_fee_status: string;
  receipt_count: number;
  need_check_count: number;
  status: string;
  deleted_at?: string | null;
  created_at: string | null;
  updated_at: string | null;
};

export type ActivityParticipantInfo = {
  id: string;
  member_id: string | null;
  name: string | null;
  student_id: string | null;
  department: string | null;
  is_external?: boolean;
  external_name?: string | null;
  external_student_id?: string | null;
  external_affiliation?: string | null;
  role: string | null;
};

export type ActivityFeeRecord = {
  id: string;
  member_id: string;
  member_name: string | null;
  student_id: string | null;
  required_amount: number;
  paid_amount: number;
  status: string;
  period: string;
  refund_status: string | null;
  transaction_id: string | null;
};

export type ActivityFeeInfo = {
  enabled: boolean;
  amount: number;
  period_key: string;
  paid_count: number;
  total_count: number;
  records: ActivityFeeRecord[];
};

export type ActivityReceiptInfo = {
  id: string;
  receipt_date: string | null;
  store_name: string | null;
  amount: number;
  payment_method: string | null;
  category: string | null;
  evidence_status: string;
  need_check: boolean;
  reason: string | null;
  file_id?: string | null;
};

export type ActivityChecklist = {
  key: string;
  label: string;
  done: boolean;
  count?: number;
  detail?: string | null;
};

export type ActivityDetail = {
  activity: {
    id: string;
    title: string;
    activity_date: string | null;
    location: string | null;
    category_id: string | null;
    category_name: string | null;
    input_text: string | null;
    generated_content: string | null;
    final_content: string | null;
    status: string;
    deleted_at?: string | null;
    created_at: string | null;
    updated_at: string | null;
  };
  participants: ActivityParticipantInfo[];
  receipts: ActivityReceiptInfo[];
  activity_fee: ActivityFeeInfo;
  checklist: ActivityChecklist[];
};

export type ActivityCreate = {
  title: string;
  category_id?: string | null;
  activity_date?: string | null;
  location?: string | null;
  description?: string | null;
  participant_member_ids?: string[];
  status?: string;
};

export type ActivityUpdate = Partial<ActivityCreate>;

export async function getActivities(params?: {
  category_id?: string;
  status?: string;
  q?: string;
  skip?: number;
  limit?: number;
}): Promise<ActivitySummary[]> {
  const p: Record<string, string | undefined> = {};
  if (params) {
    if (params.category_id) p.category_id = params.category_id;
    if (params.status) p.status = params.status;
    if (params.q) p.q = params.q;
    if (params.skip !== undefined) p.skip = String(params.skip);
    if (params.limit !== undefined) p.limit = String(params.limit);
  }
  return apiFetch<ActivitySummary[]>(`/api/activities${buildQuery(p)}`);
}

export async function createActivity(data: ActivityCreate): Promise<ActivitySummary> {
  return apiFetch<ActivitySummary>("/api/activities", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function getActivityDetail(id: string): Promise<ActivityDetail> {
  return apiFetch<ActivityDetail>(`/api/activities/${id}`);
}

export async function updateActivity(id: string, data: ActivityUpdate): Promise<ActivitySummary> {
  return apiFetch<ActivitySummary>(`/api/activities/${id}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

export async function archiveActivity(id: string): Promise<ActivitySummary> {
  return apiFetch<ActivitySummary>(`/api/activities/${id}`, { method: "DELETE" });
}

export async function deleteActivity(id: string): Promise<ActivitySummary> {
  return archiveActivity(id);
}

export async function addActivityParticipant(
  activityId: string,
  memberId: string,
  role?: string,
): Promise<ActivityParticipantInfo> {
  return apiFetch<ActivityParticipantInfo>(`/api/activities/${activityId}/participants`, {
    method: "POST",
    body: JSON.stringify({ member_id: memberId, role: role ?? "participant" }),
  });
}

export async function removeActivityParticipant(
  activityId: string,
  memberId: string,
): Promise<{ ok: boolean }> {
  return apiFetch<{ ok: boolean }>(
    `/api/activities/${activityId}/participants/${memberId}`,
    { method: "DELETE" },
  );
}

export async function generateActivityFees(
  activityId: string,
  feeAmount: number,
): Promise<{ ok: boolean; created: number; updated: number; skipped: number; total: number; period_key: string }> {
  return apiFetch(`/api/activities/${activityId}/activity-fees/generate`, {
    method: "POST",
    body: JSON.stringify({ fee_amount: feeAmount }),
  });
}

// Task 29: Activity-scoped fee matching (membership_fee is never touched)

export type ActivityFeeMatchPreview = {
  period: string;
  payment_type: string;
  activity_id: string;
  matched_count: number;
  need_check_count: number;
  unpaid_count: number;
  excluded_count: number;
  matched_items: Array<{
    transaction_id: string;
    memo: string | null;
    deposit_amount: number;
    matched_member_id: string | null;
    matched_member_name: string | null;
    match_status: string;
    score: number | null;
    reason: string | null;
  }>;
  need_check_items: Array<{
    transaction_id: string;
    memo: string | null;
    deposit_amount: number;
    matched_member_id: string | null;
    matched_member_name: string | null;
    match_status: string;
    score: number | null;
    reason: string | null;
  }>;
  action_id: string;
};

export type ActivityFeeMatchApplyResult = {
  ok: boolean;
  activity_id: string;
  period: string;
  payment_type: string;
  matched_count: number;
  created_payment_records: number;
  updated_payment_records: number;
  updated_transactions: number;
};

export async function previewActivityFeeMatch(
  activityId: string,
  params?: { start_date?: string; end_date?: string },
): Promise<ActivityFeeMatchPreview> {
  return apiFetch<ActivityFeeMatchPreview>(
    `/api/activities/${activityId}/activity-fees/match-preview`,
    { method: "POST", body: JSON.stringify(params ?? {}) },
  );
}

export async function applyActivityFeeMatch(
  activityId: string,
  params?: { start_date?: string; end_date?: string },
): Promise<ActivityFeeMatchApplyResult> {
  return apiFetch<ActivityFeeMatchApplyResult>(
    `/api/activities/${activityId}/activity-fees/match-apply`,
    { method: "POST", body: JSON.stringify(params ?? {}) },
  );
}

// Task 30: Proposal-based activity fee transaction matching

export type ActivityFeeMatchTransactionRow = {
  transaction_id: string;
  transaction_datetime: string | null;
  memo: string | null;
  deposit_amount: number;
  matched_member_id: string | null;
  matched_member_name: string | null;
  payment_record_id: string | null;
  required_amount: number | null;
  amount_difference: number | null;
  match_status: string; // auto_match_candidate | amount_mismatch | name_check_required | already_paid | already_matched | unmatched
  score: number | null;
  reason: string;
};

export type ActivityFeeMatchTransactionSummary = {
  total_transactions: number;
  auto_match_candidates: number;
  amount_mismatch: number;
  name_check_required: number;
  already_paid: number;
  already_matched: number;
  unmatched: number;
  excluded_transactions: number;
};

export type ActivityFeeMatchTransactionsPreview = {
  activity_id: string;
  requires_confirmation: boolean;
  auto_apply: boolean;
  summary: ActivityFeeMatchTransactionSummary;
  rows: ActivityFeeMatchTransactionRow[];
  confirm_payload: { action_id: string };
};

export type ActivityFeeMatchTransactionsConfirmResult = {
  ok: boolean;
  activity_id: string;
  matched_count: number;
  skipped_count: number;
  updated_payment_records: number;
  updated_transactions: number;
};

export async function previewActivityFeeMatchTransactions(
  activityId: string,
): Promise<ActivityFeeMatchTransactionsPreview> {
  return apiFetch<ActivityFeeMatchTransactionsPreview>(
    `/api/activities/${activityId}/activity-fees/match-transactions-preview`,
    { method: "POST", body: JSON.stringify({}) },
  );
}

export async function confirmActivityFeeMatchTransactions(
  activityId: string,
  actionId: string,
  confirmedRowIds?: string[],
): Promise<ActivityFeeMatchTransactionsConfirmResult> {
  return apiFetch<ActivityFeeMatchTransactionsConfirmResult>(
    `/api/activities/${activityId}/activity-fees/match-transactions-confirm`,
    {
      method: "POST",
      body: JSON.stringify({
        action_id: actionId,
        confirmed_row_ids: confirmedRowIds ?? null,
      }),
    },
  );
}

export async function cancelActivityFeeMatchTransactions(
  activityId: string,
  actionId: string,
): Promise<{ ok: boolean }> {
  return apiFetch<{ ok: boolean }>(
    `/api/activities/${activityId}/activity-fees/match-transactions-cancel`,
    { method: "POST", body: JSON.stringify({ action_id: actionId }) },
  );
}

export async function updateActivityFeeRecord(
  activityId: string,
  recordId: string,
  payload: { paid_amount?: number; status?: string; required_amount?: number; refund_status?: string },
): Promise<ActivityFeeRecord> {
  return apiFetch<ActivityFeeRecord>(
    `/api/activities/${activityId}/activity-fees/${recordId}`,
    { method: "PATCH", body: JSON.stringify(payload) },
  );
}

export async function unmatchActivityFeeRecord(
  activityId: string,
  recordId: string,
  keepPaidAmount: boolean = true,
): Promise<{ ok: boolean; status: string; paid_amount: number; transaction_id: null }> {
  return apiFetch(
    `/api/activities/${activityId}/activity-fees/${recordId}/unmatch`,
    { method: "POST", body: JSON.stringify({ keep_paid_amount: keepPaidAmount }) },
  );
}

export async function linkReceiptToActivity(
  receiptId: string,
  activityReportId: string | null,
): Promise<Receipt> {
  return apiFetch<Receipt>(`/api/receipts/${receiptId}/activity`, {
    method: "PATCH",
    body: JSON.stringify({ activity_report_id: activityReportId }),
  });
}

// Member summary (Task 16)
export type MemberSummaryDetail = {
  member: {
    id: string;
    name: string;
    student_id: string | null;
    department: string | null;
    phone: string | null;
    email: string | null;
    status: string;
    memo: string | null;
    gender: string | null;
    grade: string | null;
    birth_year: number | null;
    joined_term: string | null;
    term_code: string | null;
    is_executive: boolean;
    role: string | null;
    is_officer: boolean;
    officer_role: "president" | "vice_president" | "officer" | null;
  };
  activities: Array<{
    id: string;
    title: string;
    activity_date: string | null;
    location: string | null;
    status: string;
    role: string | null;
  }>;
  membership_payments: Array<{
    id: string;
    period: string;
    required_amount: number;
    paid_amount: number;
    status: string;
  }>;
  activity_fee_payments: Array<{
    id: string;
    period: string;
    payment_type: string;
    required_amount: number;
    paid_amount: number;
    status: string;
  }>;
  summary: {
    activity_count: number;
    membership_paid_count: number;
    unpaid_membership_count: number;
    unpaid_activity_fee_count: number;
  };
};

export async function getMemberSummary(memberId: string): Promise<MemberSummaryDetail> {
  return apiFetch<MemberSummaryDetail>(`/api/members/${memberId}/summary`);
}

// Activity fee payments (for Payments page activity_fee tab)
export async function getActivityFeePaymentRecords(params?: {
  period?: string;
  member_id?: string;
}): Promise<PaymentRecord[]> {
  const p: Record<string, string | undefined> = { payment_type: "activity_fee" };
  if (params?.period) p.period = params.period;
  if (params?.member_id) p.member_id = params.member_id;
  return apiFetch<PaymentRecord[]>(`/api/payment-records${buildQuery(p)}`);
}

// ═══════════════════════════════════════════════════════════
// Task 18: Google Form Import types and API functions
// ═══════════════════════════════════════════════════════════

export type FormImportActivityContext = {
  mode: string;
  activity_id: string | null;
  activity_title: string | null;
};

export type FormImportSummary = {
  total_rows: number;
  matched_members: number;
  new_member_candidates: number;
  needs_review: number;
  existing_participants: number;
  new_participants: number;
};

export type FormImportRow = {
  row_index: number;
  name: string | null;
  student_id: string | null;
  phone: string | null;
  email: string | null;
  department: string | null;
  submitted_at: string | null;
  member_match_status: string;
  member_id: string | null;
  participant_action: string;
  participant_status: string;
  raw_response: Record<string, unknown>;
};

export type FormImportPreview = {
  import_id: string;
  form_type: string;
  confidence: number;
  matched_columns: string[];
  activity_context: FormImportActivityContext;
  summary: FormImportSummary;
  rows: FormImportRow[];
  requires_confirmation: boolean;
};

export type FormImportApplyPayload = {
  import_id?: string | null;
  activity_id: string;
  form_type: string;
  rows: FormImportRow[];
};

export type FormImportApplyResult = {
  ok: boolean;
  activity_id: string;
  form_type: string;
  created_members: number;
  updated_members: number;
  created_participants: number;
  updated_participants: number;
  saved_feedbacks: number;
};

export async function previewFormImport(
  file: File,
  activityId?: string | null,
  formStage?: string,
): Promise<FormImportPreview> {
  const formData = new FormData();
  formData.append("file", file);
  if (activityId) formData.append("activity_id", activityId);
  if (formStage) formData.append("form_stage", formStage);
  return apiFetch<FormImportPreview>("/api/activity-form-imports/preview", {
    method: "POST",
    body: formData,
  });
}

export async function applyFormImport(
  payload: FormImportApplyPayload,
): Promise<FormImportApplyResult> {
  return apiFetch<FormImportApplyResult>("/api/activity-form-imports/apply", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

// ═══════════════════════════════════════════════════════════
// Task 19: File Vault types and API functions
// ═══════════════════════════════════════════════════════════

export type ActivityFile = {
  id: string;
  activity_report_id: string | null;
  original_filename: string;
  stored_filename: string | null;
  mime_type: string | null;
  file_ext: string | null;
  size_bytes: number | null;
  file_type: string | null;
  file_category: string | null;
  file_role: string | null;
  is_submission_file: boolean;
  submission_month: string | null;
  version: number;
  preview_status: string | null;
  preview_available: boolean;
  preview_metadata: Record<string, unknown> | null;
  related_entity_type: string | null;
  related_entity_id: string | null;
  deleted_at: string | null;
  created_at: string | null;
  download_url: string;
};

export type ExcelSheetPreview = {
  name: string;
  headers: string[];
  rows: string[][];
};

export type FilePreviewResult =
  | { type: "pdf"; preview_url: string }
  | { type: "image"; preview_url: string }
  | { type: "excel"; sheets: ExcelSheetPreview[] }
  | { type: "zip"; files: Array<{ filename: string; size_bytes: number }> }
  | { type: "hwp"; ext: string; size_bytes: number | null; message: string; download_url: string; doc_title?: string }
  | { type: "unsupported"; message: string }
  | { type: "error"; message: string };

export type SubmissionPackagePreview = {
  month: string;
  activities: Array<{
    activity_id: string;
    title: string;
    activity_date: string | null;
    submission_files: Array<{
      id: string;
      filename: string;
      category: string | null;
      role: string | null;
      size_bytes: number | null;
    }>;
    missing_items: string[];
  }>;
  summary: {
    activity_count: number;
    submission_file_count: number;
    missing_count: number;
  };
};

export type SubmissionPackageGeneratePayload = {
  month: string;
  include_categories?: string[];
};

export type SubmissionPackageGenerateResult = {
  ok: boolean;
  package_file_id: string;
  month: string;
  file_count: number;
  download_url: string;
};

export async function getActivityFiles(
  activityId: string,
  params?: { category?: string; role?: string; include_deleted?: boolean },
): Promise<ActivityFile[]> {
  const p: Record<string, string | undefined> = {};
  if (params?.category) p.category = params.category;
  if (params?.role) p.role = params.role;
  if (params?.include_deleted !== undefined) p.include_deleted = String(params.include_deleted);
  return apiFetch<ActivityFile[]>(`/api/activities/${activityId}/files${buildQuery(p)}`);
}

export async function uploadActivityFile(
  activityId: string,
  file: File,
  options?: {
    file_category?: string;
    file_role?: string;
    is_submission_file?: boolean;
    submission_month?: string;
  },
): Promise<ActivityFile> {
  const fd = new FormData();
  fd.append("file", file);
  if (options?.file_category) fd.append("file_category", options.file_category);
  if (options?.file_role) fd.append("file_role", options.file_role);
  if (options?.is_submission_file !== undefined)
    fd.append("is_submission_file", String(options.is_submission_file));
  if (options?.submission_month) fd.append("submission_month", options.submission_month);
  return apiFetch<ActivityFile>(`/api/activities/${activityId}/files`, {
    method: "POST",
    body: fd,
  });
}

export async function getFileDetail(fileId: string): Promise<ActivityFile> {
  return apiFetch<ActivityFile>(`/api/files/${fileId}`);
}

export async function getFilePreview(fileId: string): Promise<FilePreviewResult> {
  return apiFetch<FilePreviewResult>(`/api/files/${fileId}/preview`);
}

export async function softDeleteFile(fileId: string): Promise<{ ok: boolean; deleted_id: string }> {
  return apiFetch(`/api/files/${fileId}`, { method: "DELETE" });
}

export async function patchFileActivity(
  fileId: string,
  activityId: string | null,
): Promise<ActivityFile> {
  return apiFetch<ActivityFile>(`/api/files/${fileId}/activity`, {
    method: "PATCH",
    body: JSON.stringify({ activity_id: activityId }),
  });
}

export async function patchFileSubmission(
  fileId: string,
  payload: {
    is_submission_file?: boolean;
    submission_month?: string;
    file_category?: string;
    file_role?: string;
  },
): Promise<ActivityFile> {
  return apiFetch<ActivityFile>(`/api/files/${fileId}/submission`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export async function getSubmissionPackagePreview(month: string): Promise<SubmissionPackagePreview> {
  return apiFetch<SubmissionPackagePreview>(`/api/submission-packages/preview?month=${encodeURIComponent(month)}`);
}

export async function generateSubmissionPackage(
  payload: SubmissionPackageGeneratePayload,
): Promise<SubmissionPackageGenerateResult> {
  return apiFetch<SubmissionPackageGenerateResult>("/api/submission-packages/generate", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

// ═══════════════════════════════════════════════════════════
// Task 20: Document Template and HWPX generation types/API
// ═══════════════════════════════════════════════════════════

export type DocumentTemplate = {
  id: string;
  name: string;
  description: string;
  template_type: string;
  is_default: boolean;
  placeholder_fields: string[];
  original_filename: string;
  file_ext: string | null;
  size_bytes: number | null;
  created_at: string | null;
  download_url: string;
};

export type DocumentFieldMapping = {
  source: string;
  target: string;
  field: string;
};

export type DocumentPreviewResult = {
  activity_id: string;
  template_id: string;
  mode: "placeholder" | "legacy_form" | "mixed";
  mappings: DocumentFieldMapping[];
  mapped_fields: Record<string, string>;
  missing_fields: string[];
  warnings: string[];
  content_preview: {
    title: string;
    body: string;
  };
};

export type DocumentGeneratePayload = {
  template_id: string;
  document_title?: string;
  overrides?: Record<string, string>;
  mark_as_submission?: boolean;
  submission_month?: string;
};

export type DocumentGenerateResult = {
  ok: boolean;
  file_id?: string;
  generated_file_id: string;
  download_url: string;
  missing_fields: string[];
  activity_id: string;
  mode?: string;
  replaced_count?: number;
  participant_count?: number;
  warnings?: string[];
};

export type GeneratedDocument = {
  id: string;
  file_id: string;
  template_name: string;
  title: string;
  document_title: string;
  missing_fields: string[];
  is_submission_file: boolean;
  submission_month: string | null;
  created_at: string | null;
  download_url: string;
};

export async function getDocumentTemplates(params?: {
  template_type?: string;
}): Promise<DocumentTemplate[]> {
  return apiFetch<DocumentTemplate[]>(
    `/api/document-templates${buildQuery(params ?? {})}`,
  );
}

export async function uploadDocumentTemplate(
  file: File,
  options?: {
    name?: string;
    description?: string;
    template_type?: string;
    is_default?: boolean;
  },
): Promise<DocumentTemplate> {
  const fd = new FormData();
  fd.append("file", file);
  if (options?.name) fd.append("name", options.name);
  if (options?.description) fd.append("description", options.description);
  if (options?.template_type) fd.append("template_type", options.template_type);
  if (options?.is_default !== undefined) fd.append("is_default", String(options.is_default));
  return apiFetch<DocumentTemplate>("/api/document-templates", {
    method: "POST",
    body: fd,
  });
}

export async function getTemplateFields(templateId: string): Promise<{
  template_id: string;
  name: string;
  fields: string[];
  ext: string | null;
}> {
  return apiFetch(`/api/document-templates/${templateId}/fields`);
}

export async function previewDocument(
  activityId: string,
  payload: DocumentGeneratePayload,
): Promise<DocumentPreviewResult> {
  return apiFetch<DocumentPreviewResult>(
    `/api/activities/${activityId}/documents/preview`,
    { method: "POST", body: JSON.stringify(payload) },
  );
}

export async function generateDocument(
  activityId: string,
  payload: DocumentGeneratePayload,
): Promise<DocumentGenerateResult> {
  return apiFetch<DocumentGenerateResult>(
    `/api/activities/${activityId}/documents/generate`,
    { method: "POST", body: JSON.stringify(payload) },
  );
}

export async function getActivityDocuments(activityId: string): Promise<GeneratedDocument[]> {
  return apiFetch<GeneratedDocument[]>(`/api/activities/${activityId}/documents`);
}

// ═══════════════════════════════════════════════════════════
// Task 21: Settlement and refund management types/API
// ═══════════════════════════════════════════════════════════

export type SettlementSummary = {
  total_records: number;
  paid_count: number;
  unpaid_count: number;
  partial_count: number;
  overpaid_count: number;
  refund_required_count: number;
  refunded_count: number;
  need_check_count: number;
  cancelled_count: number;
  total_required_amount: number;
  total_paid_amount: number;
  total_overpaid_amount: number;
  total_refund_required_amount: number;
};

export type RefundRecord = {
  payment_record_id: string;
  member_id: string | null;
  member_name: string | null;
  student_id: string | null;
  activity_id: string | null;
  activity_title: string | null;
  participant_status: string | null;
  required_amount: number;
  paid_amount: number;
  overpaid_amount: number;
  refund_amount: number | null;
  refund_status: string;
  refund_reason: string | null;
  status: string;
  refunded_at: string | null;
};

export type AdjustmentLog = {
  id: string;
  action: string;
  previous_status: string | null;
  new_status: string | null;
  previous_paid_amount: number | null;
  new_paid_amount: number | null;
  refund_amount: number | null;
  reason: string | null;
  created_at: string | null;
};

export async function getSettlementSummary(params?: {
  activity_id?: string;
  period?: string;
  payment_type?: string;
}): Promise<SettlementSummary> {
  return apiFetch<SettlementSummary>(`/api/settlements/summary${buildQuery(params ?? {})}`);
}

export async function getRefundRecords(params?: {
  activity_id?: string;
  refund_status?: string;
}): Promise<RefundRecord[]> {
  return apiFetch<RefundRecord[]>(`/api/settlements/refunds${buildQuery(params ?? {})}`);
}

export async function setRefundRequired(
  paymentRecordId: string,
  payload: { refund_amount?: number; reason?: string },
): Promise<{ ok: boolean; payment_record_id: string; refund_status: string }> {
  return apiFetch(`/api/payment-records/${paymentRecordId}/refund-required`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function setRefundPending(
  paymentRecordId: string,
  payload: { refund_amount?: number; reason?: string },
): Promise<{ ok: boolean; payment_record_id: string; refund_status: string }> {
  return apiFetch(`/api/payment-records/${paymentRecordId}/refund-pending`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function setMarkRefunded(
  paymentRecordId: string,
  payload: { refund_transaction_id?: string; refund_amount?: number; reason?: string },
): Promise<{ ok: boolean; payment_record_id: string; refund_status: string; status: string }> {
  return apiFetch(`/api/payment-records/${paymentRecordId}/mark-refunded`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function setRefundCancel(
  paymentRecordId: string,
  payload: { reason?: string },
): Promise<{ ok: boolean; payment_record_id: string; refund_status: string; status: string }> {
  return apiFetch(`/api/payment-records/${paymentRecordId}/refund-cancel`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function getAdjustmentLogs(paymentRecordId: string): Promise<AdjustmentLog[]> {
  return apiFetch<AdjustmentLog[]>(`/api/payment-records/${paymentRecordId}/adjustment-logs`);
}

export async function matchRefundTransaction(
  transactionId: string,
  payload: { payment_record_id: string; refund_amount?: number },
): Promise<{ ok: boolean; transaction_id: string; payment_record_id: string; refund_status: string }> {
  return apiFetch(`/api/transactions/${transactionId}/match-refund`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function unmatchRefundTransaction(
  transactionId: string,
): Promise<{ ok: boolean; transaction_id: string; match_status: string; unmatched_refunds: number }> {
  return apiFetch(`/api/transactions/${transactionId}/unmatch-refund`, {
    method: "POST",
  });
}

// Task 18: Unmatch APIs
export async function unmatchPaymentRecord(
  paymentRecordId: string,
): Promise<{ ok: boolean; payment_record_id: string; status: string; paid_amount: number }> {
  return apiFetch(`/api/payment-records/${paymentRecordId}/unmatch`, {
    method: "POST",
  });
}

export async function unmatchTransaction(
  transactionId: string,
): Promise<{ ok: boolean; transaction_id: string; match_status: string; unmatched_records: number }> {
  return apiFetch(`/api/transactions/${transactionId}/unmatch`, {
    method: "POST",
  });
}

// ═══════════════════════════════════════════════════════════
// Task 26: Member import, merge, deactivate/restore
// ═══════════════════════════════════════════════════════════

export type MemberImportRowOut = {
  row_index: number;
  name: string | null;
  student_id: string | null;
  department: string | null;
  phone: string | null;
  email: string | null;
  // Oui Parfum extended fields
  gender: string | null;
  grade: string | null;
  birth_year: number | null;
  joined_term: string | null;
  term_code: string | null;
  is_executive: boolean;
  role: string | null;
  is_officer: boolean;
  officer_role: "president" | "vice_president" | "officer" | null;
  action: "new_member" | "update_existing" | "duplicate_candidate" | "needs_review" | "invalid";
  matched_member_id: string | null;
  diff: Record<string, { old: string; new: string }>;
  reason: string;
  available_actions: string[];
};

export type MemberImportSummaryOut = {
  total_rows: number;
  new_members: number;
  updates: number;
  duplicate_candidates: number;
  needs_review: number;
  invalid_rows: number;
};

export type MemberImportPreviewOut = {
  requires_confirmation: boolean;
  auto_apply: boolean;
  summary: MemberImportSummaryOut;
  rows: MemberImportRowOut[];
  action_id: string | null;
};

export type DuplicateGroup = {
  reason: string;
  members: Array<{
    id: string;
    name: string;
    student_id: string | null;
    phone: string | null;
    department: string | null;
    status: string;
    created_at: string | null;
  }>;
};

export async function previewMemberImport(file: File): Promise<MemberImportPreviewOut> {
  const fd = new FormData();
  fd.append("file", file);
  return apiFetch<MemberImportPreviewOut>("/api/members/import/preview", {
    method: "POST",
    body: fd,
  });
}

export async function getDuplicateMembers(): Promise<DuplicateGroup[]> {
  return apiFetch<DuplicateGroup[]>("/api/members/duplicates");
}

export async function mergeMembers(
  primaryId: string,
  duplicateId: string,
): Promise<{ ok: boolean; primary_id: string; duplicate_id: string; moved_participants: number; moved_payment_records: number }> {
  return apiFetch(`/api/members/merge`, {
    method: "POST",
    body: JSON.stringify({ primary_id: primaryId, duplicate_id: duplicateId }),
  });
}

export async function deactivateMember(id: string): Promise<Member> {
  return apiFetch<Member>(`/api/members/${id}/deactivate`, { method: "POST" });
}

export async function restoreMember(id: string): Promise<Member> {
  return apiFetch<Member>(`/api/members/${id}/restore`, { method: "POST" });
}

// ═══════════════════════════════════════════════════════════
// Task 27: Activity Participant Import types and API functions
// ═══════════════════════════════════════════════════════════

export type ParticipantImportPreviewRow = {
  row_index: number;
  name: string | null;
  student_id: string | null;
  department: string | null;
  phone: string | null;
  match_status: string; // matched_member | needs_review | duplicate_candidate | unregistered_candidate | already_participant
  matched_member_id: string | null;
  matched_member_name: string | null;
  participant_status: string; // will_create | will_update | already_participant | needs_review | invalid
  action: string;
  available_actions: string[];
  reason: string;
  selected_action: string | null;
};

export type ParticipantImportSummary = {
  total_rows: number;
  matched_members: number;
  unregistered_candidates: number;
  duplicate_candidates: number;
  needs_review: number;
  invalid_rows: number;
  already_participants: number;
  will_create_participants: number;
  will_update_participants: number;
};

export type ParticipantImportPreview = {
  requires_confirmation: boolean;
  auto_apply: boolean;
  activity_id: string;
  summary: ParticipantImportSummary;
  rows: ParticipantImportPreviewRow[];
  confirm_payload: { action_id: string };
};

export type ParticipantImportRowOverride = {
  row_index: number;
  selected_action: string;
  matched_member_id?: string | null;
};

export type ParticipantImportConfirmPayload = {
  action_id: string;
  row_overrides?: ParticipantImportRowOverride[];
};

export type ParticipantImportConfirmResult = {
  ok: boolean;
  activity_id: string;
  result: {
    created_participants: number;
    updated_participants: number;
    already_participants: number;
    external_participants: number;
    ignored_rows: number;
    created_members: number;
  };
};

export async function previewParticipantImport(
  activityId: string,
  file: File,
): Promise<ParticipantImportPreview> {
  const fd = new FormData();
  fd.append("file", file);
  return apiFetch<ParticipantImportPreview>(
    `/api/activities/${activityId}/participants/import/preview`,
    { method: "POST", body: fd },
  );
}

export async function confirmParticipantImport(
  activityId: string,
  payload: ParticipantImportConfirmPayload,
): Promise<ParticipantImportConfirmResult> {
  return apiFetch<ParticipantImportConfirmResult>(
    `/api/activities/${activityId}/participants/import/confirm`,
    { method: "POST", body: JSON.stringify(payload) },
  );
}

// ─── Activity Audit Checklist (Task 34) ──────────────────────────────────────

export type AuditCheckItem = {
  key: string;
  label: string;
  done: boolean;
  detail: string | null;
  count: number | null;
  warning: string | null;
};

export type ActivityAuditCheckResult = {
  activity_id: string;
  activity_title: string;
  total_done: number;
  total_items: number;
  ready_for_audit: boolean;
  items: AuditCheckItem[];
};

export async function getActivityAuditChecklist(
  activityId: string,
): Promise<ActivityAuditCheckResult> {
  return apiFetch<ActivityAuditCheckResult>(
    `/api/activities/${activityId}/audit-checklist`,
  );
}

export async function cancelParticipantImport(
  activityId: string,
  actionId: string,
): Promise<{ ok: boolean }> {
  return apiFetch<{ ok: boolean }>(
    `/api/activities/${activityId}/participants/import/cancel`,
    { method: "POST", body: JSON.stringify({ action_id: actionId }) },
  );
}

// ─── Activity Fee Transaction Exclusion (Task 32) ─────────────────────────────

export type TransactionExclusionResult = {
  ok: boolean;
  id?: string;
  transaction_id: string;
  activity_id: string;
  payment_type: string;
  is_active: boolean;
  created?: boolean;
};

export type ExcludedTransactionItem = {
  exclusion_id: string;
  transaction_id: string;
  activity_id: string;
  payment_type: string;
  reason: string | null;
  created_at: string | null;
  transaction: {
    id: string;
    memo: string | null;
    deposit_amount: number;
    transaction_datetime: string | null;
  } | null;
};

export async function excludeActivityFeeTransaction(
  activityId: string,
  transactionId: string,
  reason?: string,
): Promise<TransactionExclusionResult> {
  return apiFetch<TransactionExclusionResult>(
    `/api/activities/${activityId}/activity-fees/transactions/${transactionId}/exclude`,
    { method: "POST", body: JSON.stringify({ reason: reason ?? null }) },
  );
}

export async function includeActivityFeeTransaction(
  activityId: string,
  transactionId: string,
): Promise<TransactionExclusionResult> {
  return apiFetch<TransactionExclusionResult>(
    `/api/activities/${activityId}/activity-fees/transactions/${transactionId}/include`,
    { method: "POST", body: JSON.stringify({}) },
  );
}

export async function getExcludedActivityFeeTransactions(
  activityId: string,
): Promise<ExcludedTransactionItem[]> {
  return apiFetch<ExcludedTransactionItem[]>(
    `/api/activities/${activityId}/activity-fees/excluded-transactions`,
  );
}
