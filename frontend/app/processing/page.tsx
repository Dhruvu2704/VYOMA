'use client'

import { useEffect, useRef, useState } from 'react'
import Link from 'next/link'
import {
  CheckCircle2,
  Loader2,
  Circle,
  ArrowRight,
  Terminal,
  FileCheck2,
  FileText,
  ShieldCheck,
  Cpu,
  ScanSearch,
  Gavel,
  AlertTriangle,
} from 'lucide-react'
import { PageContainer, PageHeader } from '@/components/page-header'
import { Panel, PanelHeader } from '@/components/panel'
import { StatusBadge } from '@/components/status-badge'
import { cn } from '@/lib/utils'
import { getTaskStatus, startProcessing } from '@/lib/api'

const stages = [
  { id: 1, label: 'File Received', icon: FileCheck2 },
  { id: 2, label: 'Document Processing', icon: FileText },
  { id: 3, label: 'Rule Validation', icon: ShieldCheck },
  { id: 4, label: 'AI Analysis', icon: Cpu },
  { id: 5, label: 'P&ID Cross-Check', icon: ScanSearch },
  { id: 6, label: 'Final Verdict', icon: Gavel },
]

function useNow() {
  const [, setTick] = useState(0)
  useEffect(() => {
    const t = setInterval(() => setTick((n) => n + 1), 1000)
    return () => clearInterval(t)
  }, [])
}

function now(): string {
  return new Date().toLocaleTimeString(undefined, { hour12: false })
}

export default function ProcessingPage() {
  const [taskId, setTaskId] = useState('')
  const [noTask, setNoTask] = useState(false)
  const [progress, setProgress] = useState(8)
  const [taskStatus, setTaskStatus] = useState('CREATED')
  const [failedError, setFailedError] = useState('')
  const [log, setLog] = useState<{ time: string; msg: string }[]>([])
  const logRef = useRef<HTMLDivElement>(null)
  const startedRef = useRef(false)
  useNow()

  // Load the task id handed over by the New Inspection flow.
  useEffect(() => {
    const savedTaskId = sessionStorage.getItem('vyoma_task_id')
    if (savedTaskId) {
      setTaskId(savedTaskId)
    } else {
      setNoTask(true)
    }
  }, [])

  // Build the live log purely from real backend transitions.
  const pushLog = (msg: string) => setLog((prev) => [...prev, { time: now(), msg }])

  // Once the task id exists, start processing (if CREATED) and poll status.
  useEffect(() => {
    const id = taskId
    if (!id) return

    let active = true

    const handleTask = async (task: Awaited<ReturnType<typeof getTaskStatus>>) => {
      if (!active) return
      setTaskStatus(task.status)

      if (task.status === 'CREATED') {
        setProgress(12)
        if (!startedRef.current) {
          startedRef.current = true
          pushLog(`Contract envelope ${task.task_id} received`)
          pushLog('KAVACH AgentOrchestrator invoked (local pipeline)')
          setProgress(25)
          try {
            const processed = await startProcessing(task.task_id)
            if (!active) return
            setTaskStatus(processed.status)
            if (processed.status === 'COMPLETED') {
              setProgress(100)
              const provider = processed.result?.reasoning_provider
              pushLog(
                provider
                  ? `Verification complete via ${provider}`
                  : 'Verification complete (deterministic rule result stands)',
              )
              if (processed.audit_ref) pushLog(`Audit record written: ${processed.audit_ref}`)
              pushLog('Final verdict recorded')
            } else if (processed.status === 'FAILED') {
              setProgress(0)
              setFailedError(processed.error ?? 'KAVACH processing failed')
            }
          } catch (error) {
            if (!active) return
            setProgress(0)
            setTaskStatus('FAILED')
            setFailedError(error instanceof Error ? error.message : 'KAVACH processing failed')
          }
        } else {
          pushLog('Task already queued — awaiting worker')
        }
      } else if (task.status === 'PROCESSING') {
        setProgress((p) => Math.min(90, Math.max(p, 45)))
      } else if (task.status === 'COMPLETED') {
        setProgress(100)
        if (task.audit_ref) pushLog(`Audit record written: ${task.audit_ref}`)
        pushLog('Final verdict recorded')
      } else if (task.status === 'FAILED') {
        setProgress(0)
        setFailedError(task.error ?? 'KAVACH processing failed')
      }
    }

    getTaskStatus(id)
      .then(handleTask)
      .catch((error) => {
        if (active) {
          setTaskStatus('FAILED')
          setFailedError(error instanceof Error ? error.message : 'Could not reach the API')
        }
      })

    const t = setInterval(() => {
      getTaskStatus(id)
        .then(handleTask)
        .catch(() => {
          /* transient poll error — keep trying */
        })
    }, 2000)

    return () => {
      active = false
      clearInterval(t)
    }
  }, [taskId])

  useEffect(() => {
    if (logRef.current) logRef.current.scrollTop = logRef.current.scrollHeight
  }, [log])

  const done = taskStatus === 'COMPLETED'
  const failed = taskStatus === 'FAILED'
  const activeStage = Math.min(6, Math.floor((progress / 100) * 6) + (done ? 0 : 1))

  const stageStatus = (id: number): 'complete' | 'processing' | 'waiting' => {
    if (id < activeStage || done) return 'complete'
    if (id === activeStage) return 'processing'
    return 'waiting'
  }

  const radius = 78
  const circ = 2 * Math.PI * radius
  const offset = circ - (progress / 100) * circ

  return (
    <PageContainer>
      <PageHeader
        title="Safety Analysis in Progress"
        subtitle="Analysis runs automatically inside the controlled environment. You may keep this window open."
        action={
          <div className="flex items-center gap-2 rounded-md border border-border bg-card px-3 py-2 font-mono text-xs">
            <span className="text-muted-foreground">Task</span>
            <span className="text-foreground">{taskId || '—'}</span>
            <StatusBadge
              value={failed ? 'FAILED' : done ? 'VERIFIED' : 'PROCESSING'}
              size="sm"
            />
          </div>
        }
      />

      {noTask && (
        <Panel className="flex flex-col items-center gap-4 border-warning/40 bg-warning/5 p-10 text-center">
          <AlertTriangle className="size-8 text-warning" />
          <div>
            <h3 className="text-lg font-bold text-foreground">No task in progress</h3>
            <p className="mt-1 text-sm text-muted-foreground">
              Start a new inspection to upload a permit envelope and run the verification pipeline.
            </p>
          </div>
          <Link
            href="/new-inspection"
            className="mt-2 inline-flex items-center gap-2 rounded-md bg-primary px-5 py-2.5 text-sm font-semibold text-primary-foreground transition-colors hover:bg-primary/90"
          >
            Start an Inspection <ArrowRight className="size-4" />
          </Link>
        </Panel>
      )}

      <div className="grid gap-6 lg:grid-cols-[340px_1fr]">
        {/* Circular progress */}
        <Panel corners className="flex flex-col items-center justify-center p-8">
          <div className="relative flex size-52 items-center justify-center">
            <svg className="size-full -rotate-90" viewBox="0 0 200 200">
              <circle cx="100" cy="100" r={radius} fill="none" stroke="var(--border)" strokeWidth="6" />
              <circle
                cx="100"
                cy="100"
                r={radius}
                fill="none"
                stroke={failed ? 'var(--danger)' : 'var(--primary)'}
                strokeWidth="6"
                strokeLinecap="round"
                strokeDasharray={circ}
                strokeDashoffset={offset}
                className="transition-[stroke-dashoffset] duration-700 ease-out"
                style={{ filter: 'drop-shadow(0 0 6px var(--primary))' }}
              />
            </svg>
            <div className="absolute flex flex-col items-center">
              <span className="font-mono text-4xl font-bold tabular-nums text-foreground">
                {failed ? 0 : Math.round(progress)}%
              </span>
              <span className="mt-1 text-xs text-muted-foreground">
                {failed ? 'Analysis failed' : done ? 'Analysis complete' : 'Analyzing permit…'}
              </span>
            </div>
          </div>

          {done ? (
            <Link
              href="/verdict"
              className="mt-6 inline-flex w-full items-center justify-center gap-2 rounded-md bg-primary px-4 py-2.5 text-sm font-semibold text-primary-foreground transition-colors hover:bg-primary/90"
            >
              View Verdict <ArrowRight className="size-4" />
            </Link>
          ) : failed ? (
            <Link
              href="/new-inspection"
              className="mt-6 inline-flex w-full items-center justify-center gap-2 rounded-md border border-border bg-secondary px-4 py-2.5 text-sm font-medium text-foreground transition-colors hover:bg-accent"
            >
              Start New Inspection <ArrowRight className="size-4" />
            </Link>
          ) : (
            <p className="mt-6 flex items-center gap-2 font-mono text-xs text-info">
              <Loader2 className="size-3.5 animate-spin" /> Live analysis running
            </p>
          )}
        </Panel>

        {/* Pipeline */}
        <Panel>
          <PanelHeader title="Process Pipeline" />
          <ol className="grid gap-px bg-border sm:grid-cols-2 lg:grid-cols-3">
            {stages.map((s) => {
              const st = stageStatus(s.id)
              const Icon = s.icon
              return (
                <li
                  key={s.id}
                  className={cn(
                    'flex items-center gap-3 bg-card p-4 transition-colors',
                    st === 'processing' && 'bg-info/5',
                  )}
                >
                  <span
                    className={cn(
                      'flex size-10 shrink-0 items-center justify-center rounded-md border',
                      st === 'complete' && 'border-safe/40 bg-safe/10 text-safe',
                      st === 'processing' && 'border-info/40 bg-info/10 text-info',
                      st === 'waiting' && 'border-border bg-secondary text-muted-foreground',
                    )}
                  >
                    <Icon className="size-5" />
                  </span>
                  <div className="min-w-0">
                    <p className="font-mono text-[10px] uppercase tracking-wider text-muted-foreground">
                      Stage {s.id}
                    </p>
                    <p className="truncate text-sm font-medium text-foreground">{s.label}</p>
                    <p className="mt-0.5 flex items-center gap-1 text-xs">
                      {st === 'complete' && (
                        <>
                          <CheckCircle2 className="size-3 text-safe" />
                          <span className="text-safe">Complete</span>
                        </>
                      )}
                      {st === 'processing' && (
                        <>
                          <Loader2 className="size-3 animate-spin text-info" />
                          <span className="text-info">Processing</span>
                        </>
                      )}
                      {st === 'waiting' && (
                        <>
                          <Circle className="size-3 text-muted-foreground" />
                          <span className="text-muted-foreground">Waiting</span>
                        </>
                      )}
                    </p>
                  </div>
                </li>
              )
            })}
          </ol>

          {/* Live log */}
          <div className="border-t border-border p-4">
            <div className="mb-2 flex items-center gap-2 text-xs font-semibold uppercase tracking-widest text-muted-foreground">
              <Terminal className="size-4" /> Live System Log
            </div>
            <div
              ref={logRef}
              className="h-44 overflow-y-auto rounded-md border border-border bg-background/70 p-3 font-mono text-xs leading-relaxed"
            >
              {log.length === 0 && !failed && (
                <p className="text-muted-foreground">Awaiting system output…</p>
              )}
              {log.length === 0 && failed && (
                <p className="text-danger">Pipeline stopped: {failedError}</p>
              )}
              {log.map((l, i) => (
                <div key={i} className="flex gap-3">
                  <span className="shrink-0 text-muted-foreground">{l.time}</span>
                  <span className="text-safe">›</span>
                  <span className="text-foreground/90">{l.msg}</span>
                </div>
              ))}
              {failed && (
                <div className="flex gap-3">
                  <span className="shrink-0 text-muted-foreground">{now()}</span>
                  <span className="text-danger">›</span>
                  <span className="text-danger">{failedError}</span>
                </div>
              )}
              {!done && !failed && log.length > 0 && (
                <span className="ml-6 inline-block h-3 w-1.5 animate-status-pulse bg-info align-middle" />
              )}
            </div>
          </div>
        </Panel>
      </div>
    </PageContainer>
  )
}