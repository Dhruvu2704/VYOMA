// Mock fixture data for the VYOMA KAVACH platform.
// Designed so the shape matches an eventual real backend API.

export type SafetyResult = 'SAFE' | 'FLAGGED' | 'REJECTED'
export type Agreement = 'AGREE' | 'DISAGREE'
export type TaskStatus = 'VERIFIED' | 'REVIEW' | 'FLAGGED' | 'PROCESSING'
export type Severity = 'HIGH' | 'MEDIUM' | 'LOW'

export interface ActiveTask {
  taskId: string
  permitId: string
  asset: string
  status: TaskStatus
  ruleResult: SafetyResult
  llmResult: SafetyResult
  agreement: Agreement
  updated: string
}

export const stats = {
  activeInspections: 12,
  flaggedPermits: 4,
  humanReviews: 2,
  verifiedToday: 27,
  zeroEgress: 'ACTIVE' as const,
}

export const activeTasks: ActiveTask[] = [
  {
    taskId: 'task-2026-0512',
    permitId: 'PTW-2026-014',
    asset: 'Unit A — Crude Distillation',
    status: 'REVIEW',
    ruleResult: 'FLAGGED',
    llmResult: 'FLAGGED',
    agreement: 'AGREE',
    updated: '2 min ago',
  },
  {
    taskId: 'task-2026-0511',
    permitId: 'PTW-2026-013',
    asset: 'Unit C — Hydrocracker',
    status: 'REVIEW',
    ruleResult: 'FLAGGED',
    llmResult: 'SAFE',
    agreement: 'DISAGREE',
    updated: '9 min ago',
  },
  {
    taskId: 'task-2026-0510',
    permitId: 'PTW-2026-012',
    asset: 'Unit B — Amine Treating',
    status: 'VERIFIED',
    ruleResult: 'SAFE',
    llmResult: 'SAFE',
    agreement: 'AGREE',
    updated: '21 min ago',
  },
  {
    taskId: 'task-2026-0509',
    permitId: 'PTW-2026-011',
    asset: 'Tank Farm 4 — Storage',
    status: 'FLAGGED',
    ruleResult: 'REJECTED',
    llmResult: 'REJECTED',
    agreement: 'AGREE',
    updated: '34 min ago',
  },
  {
    taskId: 'task-2026-0508',
    permitId: 'PTW-2026-010',
    asset: 'Unit A — Compressor House',
    status: 'VERIFIED',
    ruleResult: 'SAFE',
    llmResult: 'SAFE',
    agreement: 'AGREE',
    updated: '52 min ago',
  },
  {
    taskId: 'task-2026-0507',
    permitId: 'PTW-2026-009',
    asset: 'Unit D — Sulphur Recovery',
    status: 'PROCESSING',
    ruleResult: 'SAFE',
    llmResult: 'SAFE',
    agreement: 'AGREE',
    updated: '1 hr ago',
  },
]

export interface ActivityEvent {
  time: string
  label: string
  kind: 'review' | 'verdict' | 'analysis' | 'upload' | 'security'
}

export const recentActivity: ActivityEvent[] = [
  { time: '12:05', label: 'Human review submitted — OFFICER-07', kind: 'review' },
  { time: '12:02', label: 'Verdict generated for PTW-2026-014', kind: 'verdict' },
  { time: '12:01', label: 'P&ID analysis completed', kind: 'analysis' },
  { time: '11:58', label: 'PTW-2026-014 uploaded', kind: 'upload' },
  { time: '11:47', label: 'External connection blocked on eth0', kind: 'security' },
]

export const securityStatus = {
  zeroEgress: 'ACTIVE',
  networkInterface: 'eth0',
  externalEgress: 'BLOCKED',
  packetMonitoring: 'ACTIVE',
  securityPolicy: 'ENFORCED',
  auditChain: 'HEALTHY',
  interfaceState: 'UP',
  externalConnections: 0,
}

export interface SecurityEvent {
  time: string
  event: string
  iface: string
  status: 'BLOCKED' | 'VERIFIED'
}

export const securityEvents: SecurityEvent[] = [
  { time: '12:01:47', event: 'External connection blocked', iface: 'eth0', status: 'BLOCKED' },
  { time: '12:00:12', event: 'Packet inspection', iface: 'eth0', status: 'VERIFIED' },
  { time: '11:59:58', event: 'External DNS query blocked', iface: 'eth0', status: 'BLOCKED' },
  { time: '11:58:31', event: 'Local service handshake', iface: 'lo', status: 'VERIFIED' },
  { time: '11:57:04', event: 'Egress policy re-validated', iface: 'eth0', status: 'VERIFIED' },
]

export interface HashNode {
  event: string
  timestamp: string
  hash: string
  actor: string
}

export const hashChain: HashNode[] = [
  { event: 'TASK CREATED', timestamp: '11:58:02', hash: 'a91f04c7e2', actor: 'SYSTEM' },
  { event: 'PTW PROCESSED', timestamp: '11:58:44', hash: 'b7c3d1908a', actor: 'DOC-ENGINE' },
  { event: 'RULE VERDICT', timestamp: '11:59:51', hash: 'c2e88ffa10', actor: 'RULE-ENGINE' },
  { event: 'LLM VERDICT', timestamp: '12:01:22', hash: 'd54ab0c9f3', actor: 'AI-AGENT' },
  { event: 'HUMAN REVIEW', timestamp: '12:05:21', hash: 'e18d772b45', actor: 'OFFICER-07' },
  { event: 'FINAL DECISION', timestamp: '12:05:39', hash: 'f0a4c61de8', actor: 'OFFICER-07' },
]

export interface AuditRecord {
  timestamp: string
  event: string
  actor: string
  task: string
  hash: string
  status: 'VERIFIED' | 'PENDING'
}

export const auditRecords: AuditRecord[] = [
  { timestamp: '12:05:21', event: 'REVIEW_SUBMITTED', actor: 'OFFICER-07', task: 'task-2026-0512', hash: 'e18d772b45', status: 'VERIFIED' },
  { timestamp: '12:02:03', event: 'VERDICT_GENERATED', actor: 'AI-AGENT', task: 'task-2026-0512', hash: 'd54ab0c9f3', status: 'VERIFIED' },
  { timestamp: '12:01:48', event: 'PID_ANALYSIS_COMPLETE', actor: 'GRAPH-ENGINE', task: 'task-2026-0512', hash: 'c9a01b7742', status: 'VERIFIED' },
  { timestamp: '11:59:51', event: 'RULE_VERDICT', actor: 'RULE-ENGINE', task: 'task-2026-0512', hash: 'c2e88ffa10', status: 'VERIFIED' },
  { timestamp: '11:58:44', event: 'PTW_PROCESSED', actor: 'DOC-ENGINE', task: 'task-2026-0512', hash: 'b7c3d1908a', status: 'VERIFIED' },
  { timestamp: '11:58:02', event: 'TASK_CREATED', actor: 'SYSTEM', task: 'task-2026-0512', hash: 'a91f04c7e2', status: 'VERIFIED' },
  { timestamp: '11:47:19', event: 'EGRESS_BLOCKED', actor: 'NET-MONITOR', task: '—', hash: '77b2ecaa91', status: 'VERIFIED' },
]

export interface Annotation {
  id: number
  label: string
  severity: Severity
  detail: string
  // relative coordinates (0-100) on the drawing
  x: number
  y: number
  w: number
  h: number
}

export const annotations: Annotation[] = [
  {
    id: 1,
    label: 'Isolation overlap',
    severity: 'HIGH',
    detail:
      'Permit isolation boundary overlaps an active process line (V-104 to E-210). Energy isolation cannot be guaranteed under the current permit scope.',
    x: 22,
    y: 30,
    w: 20,
    h: 16,
  },
  {
    id: 2,
    label: 'Permit boundary conflict',
    severity: 'MEDIUM',
    detail:
      'Declared work boundary extends past the isolation valve HV-221 defined in the P&ID. Recommend restricting the boundary to upstream of HV-221.',
    x: 58,
    y: 48,
    w: 18,
    h: 14,
  },
  {
    id: 3,
    label: 'Equipment reference',
    severity: 'LOW',
    detail:
      'Pump P-118 referenced in the permit is present on the drawing and correctly tagged. No action required.',
    x: 40,
    y: 68,
    w: 16,
    h: 12,
  },
]

export interface DetectedIssue {
  title: string
  severity: Severity
  detail: string
}

export const verdict = {
  permitId: 'PTW-2026-014',
  taskId: 'task-2026-0512',
  asset: 'Unit A — Crude Distillation',
  ruleResult: 'FLAGGED' as SafetyResult,
  llmResult: 'FLAGGED' as SafetyResult,
  agreement: 'AGREE' as Agreement,
  finalDecision: 'FLAGGED FOR REVIEW',
  requiresHumanReview: true,
  explanation:
    'Isolation overlap detected between the permit requirements and the identified P&ID isolation boundary. The permit scope extends past isolation valve HV-221, which cannot guarantee energy isolation for the requested hot work. The permit should remain on hold until the conflict is reviewed and authorized by a safety officer.',
  ruleChecks: [
    'Energy isolation boundary validated against P&ID topology',
    'Hot-work clearance cross-referenced with adjacent live lines',
    'Simultaneous operations (SIMOPS) constraint evaluated',
    'Isolation valve HV-221 state verified',
  ],
  llmReasoning:
    'The permit requests hot work within a zone whose isolation boundary, per the P&ID, includes a live hydrocarbon line. The model assessed the isolation plan as insufficient because valve HV-221 lies inside the declared work boundary, creating a credible ignition pathway.',
  ruleIssues: [
    { title: 'Isolation Conflict', severity: 'HIGH', detail: 'Isolation boundary overlaps live process line V-104 → E-210.' },
    { title: 'Permit Scope Mismatch', severity: 'MEDIUM', detail: 'Declared boundary extends past isolation valve HV-221.' },
  ] as DetectedIssue[],
  llmIssues: [
    { title: 'Equipment Overlap', severity: 'HIGH', detail: 'Hot-work zone overlaps live hydrocarbon service.' },
    { title: 'Missing Safety Control', severity: 'MEDIUM', detail: 'No secondary isolation declared for HV-221.' },
  ] as DetectedIssue[],
}

export const deliverables = [
  { id: 'docx', title: 'Word Report', desc: 'Safety verification report', type: 'DOCX', size: '482 KB', generated: '12:05', action: 'download' },
  { id: 'xlsx', title: 'Excel Report', desc: 'Detailed analysis data', type: 'XLSX', size: '96 KB', generated: '12:05', action: 'download' },
  { id: 'pdf', title: 'PDF Report', desc: 'Final safety report', type: 'PDF', size: '1.2 MB', generated: '12:05', action: 'download' },
  { id: 'pid', title: 'Annotated P&ID', desc: 'Marked-up engineering drawing', type: 'PNG', size: '3.4 MB', generated: '12:04', action: 'view' },
] as const

export const processingStages = [
  { id: 1, label: 'File Received', status: 'complete' },
  { id: 2, label: 'Document Processing', status: 'complete' },
  { id: 3, label: 'Rule Validation', status: 'complete' },
  { id: 4, label: 'AI Analysis', status: 'processing' },
  { id: 5, label: 'P&ID Cross-Check', status: 'waiting' },
  { id: 6, label: 'Final Verdict', status: 'waiting' },
] as const

export const processingLog = [
  { time: '12:01:31', msg: 'PTW successfully received' },
  { time: '12:01:35', msg: 'Document extraction completed' },
  { time: '12:01:42', msg: 'Rule engine analysis started' },
  { time: '12:01:48', msg: 'Safety constraints evaluated' },
  { time: '12:01:51', msg: 'LLM analysis in progress...' },
]
