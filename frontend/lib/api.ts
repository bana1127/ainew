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
  unread_notifications: number;
};

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
}): Promise<Member[]> {
  return apiFetch<Member[]>(`/api/members${buildQuery(params ?? {})}`);
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
  created_at: string;
  updated_at: string;
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
  status?: "unpaid" | "paid" | "partial" | "need_check" | "exempt";
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
  | "activity_link"
  | "activity_create"
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
  | "activity_linked_result"
  | "general_message"
  | "error";

export type ActivityContextMode = "linked" | "candidate" | "create_draft" | "needs_confirmation" | "none";

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

export async function executeAssistant(
  formData: FormData,
): Promise<AssistantExecuteResponse> {
  return apiFetch<AssistantExecuteResponse>("/api/assistant/execute", {
    method: "POST",
    body: formData,
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
  created_at: string | null;
  updated_at: string | null;
};

export type ActivityParticipantInfo = {
  id: string;
  member_id: string;
  name: string | null;
  student_id: string | null;
  department: string | null;
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
): Promise<{ ok: boolean; created: number; skipped: number; total: number; period_key: string }> {
  return apiFetch(`/api/activities/${activityId}/activity-fees/generate`, {
    method: "POST",
    body: JSON.stringify({ fee_amount: feeAmount }),
  });
}

export async function updateActivityFeeRecord(
  activityId: string,
  recordId: string,
  payload: { paid_amount?: number; status?: string; required_amount?: number },
): Promise<ActivityFeeRecord> {
  return apiFetch<ActivityFeeRecord>(
    `/api/activities/${activityId}/activity-fees/${recordId}`,
    { method: "PATCH", body: JSON.stringify(payload) },
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
