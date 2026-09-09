// Thin API service layer. Currently backed by mock fixtures.
// Swap the bodies for real fetch() calls when the backend is available;
// the screens consume only these functions and never touch fixtures directly.

import {
  activeTasks,
  annotations,
  auditRecords,
  deliverables,
  hashChain,
  processingLog,
  processingStages,
  recentActivity,
  securityEvents,
  securityStatus,
  stats,
  verdict,
} from './mock-data'

const delay = (ms: number) => new Promise((r) => setTimeout(r, ms))

export async function createTask() {
  await delay(400)
  return { taskId: 'task-2026-0512', status: 'PROCESSING' as const }
}

export async function getDashboard() {
  await delay(200)
  return { stats, activeTasks, recentActivity, securityStatus }
}

export async function getTaskStatus() {
  await delay(150)
  return { stages: processingStages, log: processingLog }
}

export async function getVerdict() {
  await delay(200)
  return verdict
}

export async function getAnnotations() {
  await delay(200)
  return annotations
}

export async function getSecurityStatus() {
  await delay(200)
  return { securityStatus, securityEvents, hashChain }
}

export async function getAuditFeed() {
  await delay(200)
  return auditRecords
}

export async function getDeliverables() {
  await delay(200)
  return deliverables
}

export async function submitReview(_decision: 'APPROVE' | 'REJECT', _notes: string) {
  await delay(600)
  return { recorded: true }
}
