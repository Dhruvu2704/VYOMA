const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://127.0.0.1:8000'

const TOKEN_KEY = 'vyoma_token'
const USER_KEY = 'vyoma_user'

function authHeaders(): Record<string, string> {
  const token = getToken()
  return token ? { Authorization: `Bearer ${token}` } : {}
}

function unwrap<T>(res: Response): Promise<T> {
  if (!res.ok) {
    return res.json().then(
      (body) => {
        const detail = (body as Record<string, unknown>)?.detail
        throw new Error(typeof detail === 'string' ? detail : `Request failed (${res.status})`)
      },
      () => {
        throw new Error(`Request failed (${res.status})`)
      },
    )
  }
  return res.json() as Promise<T>
}

// ---------------------------------------------------------------------------
// Auth helpers (sessionStorage — browser only)
// ---------------------------------------------------------------------------

export function getToken(): string | null {
  if (typeof window === 'undefined') return null
  return sessionStorage.getItem(TOKEN_KEY)
}

export function getCurrentUser(): string | null {
  if (typeof window === 'undefined') return null
  return sessionStorage.getItem(USER_KEY)
}

export function isAuthed(): boolean {
  return !!getToken()
}

export function logout(): void {
  if (typeof window === 'undefined') return
  sessionStorage.removeItem(TOKEN_KEY)
  sessionStorage.removeItem(USER_KEY)
}

// ---------------------------------------------------------------------------
// Auth API
// ---------------------------------------------------------------------------

interface LoginResponse {
  message: string
  access_token: string
  token_type: string
}

interface RegisterResponse {
  message: string
  user_id: number
  username: string
  role: string
}

export async function login(username: string, password: string): Promise<LoginResponse> {
  const res = await fetch(`${API_BASE_URL}/api/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password }),
  })
  const data = await unwrap<LoginResponse>(res)
  sessionStorage.setItem(TOKEN_KEY, data.access_token)
  sessionStorage.setItem(USER_KEY, username)
  return data
}

export async function register(username: string, password: string): Promise<RegisterResponse> {
  const res = await fetch(`${API_BASE_URL}/api/auth/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password }),
  })
  return unwrap<RegisterResponse>(res)
}

// ---------------------------------------------------------------------------
// Health
// ---------------------------------------------------------------------------

interface HealthResponse {
  status: string
}

export async function getHealth(): Promise<HealthResponse> {
  return unwrap<HealthResponse>(await fetch(`${API_BASE_URL}/api/health`))
}

// ---------------------------------------------------------------------------
// Tasks
// ---------------------------------------------------------------------------

export interface BackendDeliverable {
  filename: string
  file_type: string
  file_path: string
  sha256: string
}

export interface BackendTaskResult {
  deterministic_safety_evaluated: boolean
  rule_result: string | null
  rules_triggered: string[]
  conflicting_permit_ids: string[]
  rule_explanation: string
  llm_result: string | null
  reasoning_provider: string | null
  reasoning_explanation: string
  agreement: string
  final_decision: string
  requires_human_review: boolean
  explanation: string
  generated_at: string | null
}

export interface BackendTask {
  task_id: string
  filename: string
  status: string
  created_by: number | null
  created_at: string | null
  updated_at: string | null
  permit_id: string
  scenario: string
  audit_ref: string | null
  error: string | null
  result: BackendTaskResult | null
  deliverables: BackendDeliverable[]
}

interface UploadResponse {
  task_id: string
  filename: string
  status: string
  message: string
}

export async function uploadTask(file: File): Promise<UploadResponse> {
  const form = new FormData()
  form.append('file', file)
  const res = await fetch(`${API_BASE_URL}/api/tasks/upload`, {
    method: 'POST',
    headers: authHeaders(),
    body: form,
  })
  return unwrap<UploadResponse>(res)
}

export async function startProcessing(taskId: string): Promise<BackendTask> {
  const res = await fetch(`${API_BASE_URL}/api/tasks/${encodeURIComponent(taskId)}/process`, {
    method: 'POST',
    headers: authHeaders(),
  })
  return unwrap<BackendTask>(res)
}

export async function getTask(taskId: string): Promise<BackendTask> {
  const res = await fetch(`${API_BASE_URL}/api/tasks/${encodeURIComponent(taskId)}`, {
    headers: authHeaders(),
  })
  return unwrap<BackendTask>(res)
}

export async function getTaskStatus(taskId: string): Promise<BackendTask> {
  return getTask(taskId)
}

export async function getActiveTasks(limit = 10): Promise<BackendTask[]> {
  return unwrap<BackendTask[]>(
    await fetch(`${API_BASE_URL}/api/tasks?limit=${limit}`, { headers: authHeaders() }),
  )
}

// ---------------------------------------------------------------------------
// Audit
// ---------------------------------------------------------------------------

export interface AuditEvent {
  audit_ref: string
  permit_id: string
  timestamp: string
  pipeline: string[]
  sequence: number
  previous_hash: string
  event_hash: string
}

export interface AuditVerifyResponse {
  valid: boolean
}

export async function getAuditFeed(): Promise<AuditEvent[]> {
  return unwrap<AuditEvent[]>(await fetch(`${API_BASE_URL}/api/audit/`, { headers: authHeaders() }))
}

export async function verifyAuditChain(): Promise<AuditVerifyResponse> {
  return unwrap<AuditVerifyResponse>(
    await fetch(`${API_BASE_URL}/api/audit/verify`, { headers: authHeaders() }),
  )
}

// ---------------------------------------------------------------------------
// Deliverables
// ---------------------------------------------------------------------------

export interface DeliverableListResponse {
  task_id: string
  deliverables: BackendDeliverable[]
}

export async function getDeliverables(taskId: string): Promise<DeliverableListResponse> {
  return unwrap<DeliverableListResponse>(
    await fetch(`${API_BASE_URL}/api/tasks/${encodeURIComponent(taskId)}/deliverables`, {
      headers: authHeaders(),
    }),
  )
}

export async function downloadDeliverable(taskId: string, filename: string): Promise<void> {
  const res = await fetch(
    `${API_BASE_URL}/api/tasks/${encodeURIComponent(taskId)}/deliverables/${encodeURIComponent(filename)}`,
    { headers: authHeaders() },
  )
  if (!res.ok) throw new Error(`Download failed (${res.status})`)
  const blob = await res.blob()
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  a.remove()
  URL.revokeObjectURL(url)
}

// ---------------------------------------------------------------------------
// Workbench (public, read-only system introspection)
// ---------------------------------------------------------------------------

export interface WorkbenchStatus {
  application: { name: string; components: string[] }
  orchestrator: {
    stages: string[]
    reasoning_provider: string
    provider_base_url: string
    provider_timeout_s: number
  }
  ollama: {
    status: 'online' | 'unreachable'
    base_url: string
    model_count: number
    models: string[]
    detail: string | null
  }
  tools: {
    registered: string[]
    deliverable_generators: { name: string; file_type: string; purpose: string }[]
  }
}

export async function getWorkbenchStatus(): Promise<WorkbenchStatus> {
  return unwrap<WorkbenchStatus>(await fetch(`${API_BASE_URL}/api/workbench/status`))
}

// ---------------------------------------------------------------------------
// Review (client-side only — no backend review endpoint exists)
// ---------------------------------------------------------------------------

export async function submitReview(
  decision: string,
  notes: string,
): Promise<{ recorded: true; note: string }> {
  return {
    recorded: true,
    note: `Sign-off recorded client-side (${decision}). A backend review endpoint does not yet exist.`,
  }
}
