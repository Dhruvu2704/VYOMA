// Shared types and purely visual fixtures for the VYOMA KAVACH platform.
//
// Safety-affecting data (verdicts, tasks, audit, deliverables) is NEVER declared
// here: it comes exclusively from the local backend API. The objects that remain
// in this file are decorative only (annotated-drawing overlays and the zero-egress
// security scene) and do not claim backend-reported facts.

export type SafetyResult = 'SAFE' | 'PASS' | 'FLAGGED' | 'REJECTED' | 'UNAVAILABLE'
export type Agreement = 'AGREE' | 'DISAGREE' | 'UNAVAILABLE'
export type TaskStatus = 'VERIFIED' | 'REVIEW' | 'FLAGGED' | 'PROCESSING' | 'CREATED' | 'FAILED'
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

export interface ActivityEvent {
  time: string
  label: string
  kind: 'review' | 'verdict' | 'analysis' | 'upload' | 'security'
}

export interface SecurityEvent {
  time: string
  event: string
  iface: string
  status: 'BLOCKED' | 'VERIFIED'
}

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

export interface DetectedIssue {
  title: string
  severity: Severity
  detail: string
}

// Decorative annotated-P&ID overlays (no backend annotation endpoint exists yet).
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

// Decorative zero-egress security scene (visual showcase; not backend data).
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

export const securityEvents: SecurityEvent[] = [
  { time: '12:01:47', event: 'External connection blocked', iface: 'eth0', status: 'BLOCKED' },
  { time: '12:00:12', event: 'Packet inspection', iface: 'eth0', status: 'VERIFIED' },
  { time: '11:59:58', event: 'External DNS query blocked', iface: 'eth0', status: 'BLOCKED' },
  { time: '11:58:31', event: 'Local service handshake', iface: 'lo', status: 'VERIFIED' },
  { time: '11:57:04', event: 'Egress policy re-validated', iface: 'eth0', status: 'VERIFIED' },
]