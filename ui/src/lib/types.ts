// ── Auth ──
export interface User {
  id: number;
  email: string;
  plan: string;
  api_key: string;
  is_active: boolean;
  created_at: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface RegisterRequest {
  email: string;
  password: string;
}

// ── Documents ──
export interface DocumentUploadResponse {
  document_id: number;
  job_id: number;
  status: string;
  message: string;
}

export interface DocumentItem {
  id: number;
  filename: string;
  file_format: string;
  page_count: number;
  mode: string;
  status: string;
  created_at: string;
  completed_at: string | null;
}

export interface DocumentListResponse {
  documents: DocumentItem[];
  total: number;
}

export interface DocumentDetailResponse extends DocumentItem {
  result: Record<string, unknown> | null;
  error: string | null;
}

// ── Jobs ──
export interface JobResponse {
  id: number;
  document_id: number;
  status: string;
  result_json: Record<string, unknown> | null;
  error: string | null;
  processing_time_seconds: number | null;
  created_at: string;
  completed_at: string | null;
}

export interface JobListResponse {
  jobs: JobResponse[];
  total: number;
}

// ── Results ──
export interface PageResult {
  page: number;
  content: string;
  has_extracted_text: boolean;
}

export interface DocumentResultResponse {
  pages: PageResult[];
  format: string;
}

// ── Usage ──
export interface UsageResponse {
  plan: string;
  pages_used: number;
  pages_limit: number;
  period: string;
}

export interface UsageHistoryItem {
  month: number;
  year: number;
  pages_processed: number;
}

export interface UsageHistoryResponse {
  records: UsageHistoryItem[];
  total: number;
}