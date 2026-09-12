'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { Activity, Plus, ShieldAlert, ShieldCheck, UserCheck, ShieldHalf } from 'lucide-react'
import { PageContainer, PageHeader } from '@/components/page-header'
import { StatCard } from '@/components/dashboard/stat-card'
import { ActiveTasksTable } from '@/components/dashboard/active-tasks-table'
import { ActivityTimeline } from '@/components/dashboard/activity-timeline'
import { SecurityStatusCard } from '@/components/dashboard/security-status-card'
import { ShieldHero } from '@/components/three/shield-hero'
import { getActiveTasks, getHealth, getSecurityStatus, getWorkbenchStatus, isAuthed, type BackendTask, type SecurityStatus } from '@/lib/api'
import { openAuth } from '@/components/auth-modal'
import type { ActiveTask, ActivityEvent } from '@/lib/mock-data'

function formatStamp(iso: string | null | undefined): string {
  if (!iso) return '—'
  const t = new Date(iso)
  if (Number.isNaN(t.getTime())) return iso.replace('T', ' ').slice(0, 19)
  return t.toLocaleString(undefined, { hour12: false })
}

function toActiveTask(task: BackendTask): ActiveTask {
  const result = task.result
  let status: ActiveTask['status'] = 'PROCESSING'
  if (task.status === 'COMPLETED') {
    status = result?.requires_human_review
      ? 'REVIEW'
      : result?.rule_result === 'FLAGGED'
        ? 'FLAGGED'
        : 'VERIFIED'
  } else if (task.status === 'FAILED') {
    status = 'FAILED'
  } else if (task.status === 'CREATED') {
    status = 'CREATED'
  }
  return {
    taskId: task.task_id,
    permitId: task.permit_id || '—',
    asset: task.scenario || task.filename || '—',
    status,
    ruleResult: (result?.rule_result ?? '—') as ActiveTask['ruleResult'],
    llmResult: (result?.llm_result ?? '—') as ActiveTask['llmResult'],
    agreement: (result?.agreement ?? '—') as ActiveTask['agreement'],
    updated: formatStamp(task.updated_at ?? task.created_at),
  }
}

function toActivity(task: BackendTask, index: number): ActivityEvent {
  if (task.status === 'COMPLETED') {
    return {
      time: formatStamp(task.updated_at),
      label: `Verdict recorded for permit ${task.permit_id || task.task_id}`,
      kind: 'verdict',
    }
  }
  if (task.status === 'PROCESSING') {
    return {
      time: formatStamp(task.updated_at),
      label: `Analysis running for permit ${task.permit_id || task.task_id}`,
      kind: 'analysis',
    }
  }
  void index
  return {
    time: formatStamp(task.created_at),
    label: `Envelope uploaded: ${task.filename}`,
    kind: 'upload',
  }
}

export default function DashboardPage() {
  const [authed, setAuthed] = useState(isAuthed())
  const [apiUp, setApiUp] = useState<boolean | null>(null)
  const [tasks, setTasks] = useState<BackendTask[]>([])
  const [egress, setEgress] = useState<SecurityStatus | null>(null)
  const [loadError, setLoadError] = useState('')

  useEffect(() => {
    getHealth()
      .then(() => setApiUp(true))
      .catch(() => setApiUp(false))

    getSecurityStatus()
      .then(setEgress)
      .catch(() => setEgress(null))

    if (!isAuthed()) return

    getActiveTasks(10)
      .then((rows) => setTasks(rows))
      .catch((error: unknown) => {
        setAuthed(isAuthed())
        setLoadError(error instanceof Error ? error.message : 'Could not load tasks.')
      })
  }, [])

  const active = tasks.filter((t) => t.status === 'CREATED' || t.status === 'PROCESSING').length
  const flagged = tasks.filter((t) => t.result?.rule_result === 'FLAGGED').length
  const humanReviews = tasks.filter((t) => t.result?.requires_human_review).length
  const verified = tasks.filter((t) => t.status === 'COMPLETED').length

  const activeTasks = tasks.map(toActiveTask)
  const recentActivity = tasks.map(toActivity).slice(0, 6)

  return (
    <PageContainer>
      <PageHeader
        title="Overview"
        subtitle="Sovereign Industrial AI Workbench — live operating posture across the VYOMA platform and its KAVACH app"
        action={
          <Link
            href="/new-inspection"
            className="inline-flex items-center gap-2 rounded-md bg-primary px-4 py-2.5 text-sm font-semibold text-primary-foreground shadow-sm transition-colors hover:bg-primary/90"
          >
            <Plus className="size-4" /> New Inspection
          </Link>
        }
      />

      {/* Hero with 3D shield */}
      <div className="relative mb-6 overflow-hidden rounded-lg border border-border bg-card">
        <div className="pointer-events-none absolute inset-0 bg-engineering-grid-fine opacity-40" />
        <div className="relative grid items-center gap-4 lg:grid-cols-[1fr_360px]">
          <div className="p-6 sm:p-8">
            <div className="mb-3 inline-flex items-center gap-2 rounded-full border border-primary/30 bg-primary/10 px-3 py-1 font-mono text-[11px] uppercase tracking-widest text-primary">
              <ShieldHalf className="size-3.5" /> VYOMA · KAVACH
            </div>
            <h3 className="max-w-xl text-balance text-2xl font-bold leading-tight text-foreground sm:text-3xl">
              AI-verified Permit-to-Work &amp; P&amp;ID safety intelligence
            </h3>
            <p className="mt-3 max-w-lg text-pretty text-sm leading-relaxed text-muted-foreground">
              Dual-engine verification cross-checks rule-based safety constraints against LLM
              reasoning inside a zero-egress environment. Every decision is written to a tamper-evident
              audit ledger.
            </p>
            <div className="mt-5 flex flex-wrap gap-6">
              <div>
                <p className="font-mono text-2xl font-bold text-safe tabular-nums">
                  {String(active).padStart(2, '0')}
                </p>
                <p className="text-xs text-muted-foreground">Active inspections</p>
              </div>
              <div>
                <p className="font-mono text-2xl font-bold text-foreground tabular-nums">
                  {String(verified).padStart(2, '0')}
                </p>
                <p className="text-xs text-muted-foreground">Permits verified</p>
              </div>
              <div>
                <p className="font-mono text-2xl font-bold text-info tabular-nums">
                  {String(egress?.external_connection_count ?? '—')}
                </p>
                <p className="text-xs text-muted-foreground">External connections</p>
              </div>
            </div>
          </div>
          <div className="relative h-56 w-full lg:h-full lg:min-h-[280px]">
            <ShieldHero className="absolute inset-0 h-full w-full" />
          </div>
        </div>
      </div>

      {/* API / auth notice */}
      {apiUp === false && (
        <div className="mb-6 rounded-md border border-danger/40 bg-danger/5 px-4 py-3 text-sm text-danger">
          Backend API is unreachable at the configured local address. Start the KAVACH backend to see live data.
        </div>
      )}
      {apiUp !== false && !authed && !loadError && (
        <div className="mb-6 flex flex-wrap items-center justify-between gap-3 rounded-md border border-warning/40 bg-warning/5 px-4 py-3">
          <p className="text-sm text-foreground">
            Sign in to the local backend to view live tasks, results, and the audit ledger.
          </p>
          <button
            onClick={openAuth}
            className="inline-flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground transition-colors hover:bg-primary/90"
          >
            Sign In
          </button>
        </div>
      )}
      {authed && loadError && (
        <div className="mb-6 rounded-md border border-warning/40 bg-warning/5 px-4 py-3 text-sm text-warning">
          {loadError}
        </div>
      )}

      {/* Stats row */}
      <div className="mb-6 grid grid-cols-2 gap-4 md:grid-cols-3 lg:grid-cols-5">
        <StatCard label="Active Inspections" value={String(active).padStart(2, '0')} desc="Currently in pipeline" icon={Activity} tone="info" />
        <StatCard label="Flagged Permits" value={String(flagged).padStart(2, '0')} desc="Require attention" icon={ShieldAlert} tone="danger" />
        <StatCard label="Human Reviews" value={String(humanReviews).padStart(2, '0')} desc="Awaiting officer" icon={UserCheck} tone="warning" />
        <StatCard label="Verified Today" value={String(verified).padStart(2, '0')} desc="Cleared for work" icon={ShieldCheck} tone="safe" />
        <StatCard label="Zero-Egress" value="ACTIVE" desc="Network isolated" icon={ShieldHalf} tone="info" isStatus />
      </div>

      {/* Main grid */}
      <div className="grid gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <ActiveTasksTable tasks={activeTasks} />
        </div>
        <div className="space-y-6">
          <SecurityStatusCard />
        </div>
      </div>

      <div className="mt-6 grid gap-6 lg:grid-cols-3">
        <div className="lg:col-span-1">
          <ActivityTimeline events={recentActivity} />
        </div>
        <div className="lg:col-span-2">
          <ModuleHealth />
        </div>
      </div>
    </PageContainer>
  )
}

function ModuleHealth() {
  const [backend, setBackend] = useState<'ONLINE' | 'OFFLINE'>('ONLINE')
  const [ollama, setOllama] = useState<'unreachable' | 'online' | null>(null)
  const [provider, setProvider] = useState<string | null>(null)
  const [zeroEgress, setZeroEgress] = useState<boolean | null>(null)
  const [auditValid, setAuditValid] = useState<boolean | null>(null)

  useEffect(() => {
    getHealth()
      .then(() => setBackend('ONLINE'))
      .catch(() => setBackend('OFFLINE'))
    getWorkbenchStatus()
      .then((s) => {
        setOllama(s.ollama.status)
        setProvider(s.orchestrator.reasoning_provider)
      })
      .catch(() => setOllama('unreachable'))
    getSecurityStatus()
      .then((s) => {
        setZeroEgress(s.external_observed_since_start === 0)
        setAuditValid(s.audit_chain.valid)
      })
      .catch(() => {
        setZeroEgress(false)
        setAuditValid(false)
      })
  }, [])

  const llmOnline = ollama === 'online'
  const items = [
    { label: 'Backend API', value: backend, tone: backend === 'ONLINE' ? 'text-safe' : 'text-danger' },
    {
      label: 'Local Reasoning Engine',
      value: provider ?? (ollama === null ? 'PROBING' : llmOnline ? 'LOCAL' : 'OFFLINE'),
      tone: ollama === null || llmOnline ? 'text-safe' : 'text-danger',
    },
    {
      label: 'Zero-Egress',
      value: zeroEgress === null ? 'PROBING' : zeroEgress ? 'ENFORCED' : 'BREACHED',
      tone: zeroEgress ? 'text-safe' : 'text-danger',
    },
    {
      label: 'Audit Chain',
      value: auditValid === null ? 'PROBING' : auditValid ? 'SYNCED' : 'INVALID',
      tone: auditValid ? 'text-safe' : 'text-danger',
    },
  ]
  return (
    <div className="relative h-full overflow-hidden rounded-md border border-border bg-card">
      <div className="border-b border-border px-4 py-3">
        <h3 className="text-xs font-semibold uppercase tracking-widest text-muted-foreground">
          Module Health
        </h3>
      </div>
      <div className="grid grid-cols-2 gap-px bg-border sm:grid-cols-4">
        {items.map((it) => (
          <div key={it.label} className="bg-card p-4">
            <p className="text-xs text-muted-foreground">{it.label}</p>
            <p className={`mt-1 truncate font-mono text-sm font-bold ${it.tone}`}>{it.value}</p>
          </div>
        ))}
      </div>
    </div>
  )
}