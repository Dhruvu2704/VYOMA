'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import {
  ShieldCheck,
  Cpu,
  Check,
  AlertTriangle,
  Gavel,
  MessageSquareText,
  ArrowRight,
  Map,
  FileDown,
  Loader2,
} from 'lucide-react'
import { PageContainer, PageHeader } from '@/components/page-header'
import { Panel } from '@/components/panel'
import { AnalysisCard } from '@/components/verdict/analysis-card'
import { ReviewPanel } from '@/components/verdict/review-panel'
import { StatusBadge } from '@/components/status-badge'
import { getTask } from '@/lib/api'
import { buildVerdictModel, type VerdictModel } from '@/lib/result-model'
import { cn } from '@/lib/utils'

export default function VerdictPage() {
  const [v, setV] = useState<VerdictModel | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const taskId = sessionStorage.getItem('vyoma_task_id')
    if (!taskId) {
      setError('No inspection is in progress. Run an inspection to produce a verdict.')
      setLoading(false)
      return
    }
    getTask(taskId)
      .then((task) => setV(buildVerdictModel(task)))
      .catch((e: unknown) => {
        setError(e instanceof Error ? e.message : 'Could not load the verdict.')
      })
      .finally(() => setLoading(false))
  }, [])

  if (loading) {
    return (
      <PageContainer>
        <Panel className="flex flex-col items-center gap-3 p-12">
          <Loader2 className="size-6 animate-spin text-info" />
          <p className="text-sm text-muted-foreground">Loading safety verification result…</p>
        </Panel>
      </PageContainer>
    )
  }

  if (error || !v) {
    return (
      <PageContainer>
        <Panel className="flex flex-col items-center gap-4 border-warning/40 bg-warning/5 p-10 text-center">
          <AlertTriangle className="size-8 text-warning" />
          <div>
            <h3 className="text-lg font-bold text-foreground">Verdict unavailable</h3>
            <p className="mt-1 text-sm text-muted-foreground">{error ?? 'No result to display.'}</p>
          </div>
          <Link
            href="/new-inspection"
            className="mt-2 inline-flex items-center gap-2 rounded-md bg-primary px-5 py-2.5 text-sm font-semibold text-primary-foreground transition-colors hover:bg-primary/90"
          >
            Start an Inspection <ArrowRight className="size-4" />
          </Link>
        </Panel>
      </PageContainer>
    )
  }

  const agree = v.agreement === 'AGREE'
  const unavailable = v.agreement === 'UNAVAILABLE'
  const safeDecision = v.status === 'COMPLETED' && v.finalDecision === 'PASS'
  const banner = unavailable ? 'UNAVAILABLE' : agree ? 'AGREE' : 'DISAGREE'

  return (
    <PageContainer>
      <PageHeader
        title="Safety Verification Result"
        subtitle={`Scenario: ${v.asset}`}
        action={
          <div className="flex flex-wrap items-center gap-2 font-mono text-xs">
            <span className="rounded-md border border-border bg-card px-3 py-2 text-foreground">
              Permit: {v.permitId}
            </span>
            <span className="rounded-md border border-border bg-card px-3 py-2 text-muted-foreground">
              {v.taskId}
            </span>
          </div>
        }
      />

      {/* Verdict banner */}
      <div
        className={cn(
          'relative mb-6 overflow-hidden rounded-lg border p-6',
          banner === 'AGREE' ? 'border-safe/40 bg-safe/5' : 'border-warning/40 bg-warning/5',
        )}
      >
        <div className="pointer-events-none absolute inset-0 bg-engineering-grid-fine opacity-30" />
        <div className="relative flex items-center gap-4">
          <span
            className={cn(
              'flex size-14 shrink-0 items-center justify-center rounded-full border',
              banner === 'AGREE'
                ? 'border-safe/50 bg-safe/15 text-safe glow-safe'
                : 'border-warning/50 bg-warning/15 text-warning glow-warning',
            )}
          >
            {banner === 'AGREE' ? <Check className="size-7" /> : <AlertTriangle className="size-7" />}
          </span>
          <div>
            <h3 className={cn('text-xl font-bold tracking-tight', banner === 'AGREE' ? 'text-safe' : 'text-warning')}>
              {banner === 'AGREE'
                ? 'SYSTEMS AGREE'
                : unavailable
                  ? 'LLM UNAVAILABLE'
                  : 'SYSTEM DISAGREEMENT'}
            </h3>
            <p className="mt-0.5 text-sm text-muted-foreground">
              {banner === 'AGREE' && 'Rule engine and AI analysis produced the same result.'}
              {!banner || banner === 'UNAVAILABLE' && 'The local reasoning service was not reachable; the deterministic rule result stands.'}
              {banner === 'DISAGREE' && 'Rule engine and AI analysis produced different results. Human review is required.'}
            </p>
          </div>
        </div>
      </div>

      {/* Side by side */}
      <div className="relative grid gap-6 lg:grid-cols-2">
        <AnalysisCard
          title="Rule Engine"
          subtitle="Deterministic safety constraints"
          icon={ShieldCheck}
          result={v.ruleResult as 'SAFE' | 'PASS' | 'FLAGGED' | 'REJECTED'}
          bodyTitle="Rule Assessment"
          body="Deterministic safety constraint evaluation against the extracted permit scope and P&ID topology."
          checks={v.ruleChecks}
          issues={v.ruleIssues}
        />

        {/* Center connector */}
        <div className="pointer-events-none absolute left-1/2 top-14 z-10 hidden -translate-x-1/2 lg:block">
          <span
            className={cn(
              'flex items-center gap-1.5 rounded-full border px-3 py-1.5 font-mono text-xs font-bold shadow-lg',
              banner === 'AGREE'
                ? 'border-safe/50 bg-card text-safe'
                : 'border-warning/50 bg-card text-warning',
            )}
          >
            {banner === 'AGREE' ? <Check className="size-3.5" /> : <AlertTriangle className="size-3.5" />}
            {v.agreement}
          </span>
        </div>

        <AnalysisCard
          title="AI / LLM Analysis"
          subtitle="Context-aware reasoning"
          icon={Cpu}
          result={v.llmResult as 'SAFE' | 'FLAGGED' | 'REJECTED' | 'UNAVAILABLE'}
          bodyTitle="AI Reasoning Summary"
          body={v.llmReasoning}
          issues={v.llmIssues}
        />
      </div>

      {/* Final decision + explanation */}
      <div className="mt-6 grid gap-6 lg:grid-cols-3">
        <Panel
          corners
          className={cn(
            'flex flex-col justify-center border p-6 lg:col-span-1',
            safeDecision ? 'border-safe/40' : 'border-danger/40',
          )}
        >
          <div className="mb-2 flex items-center gap-2 text-xs font-semibold uppercase tracking-widest text-muted-foreground">
            <Gavel className="size-4" /> Final Decision
          </div>
          <p className={cn('text-2xl font-bold', safeDecision ? 'text-safe' : 'text-danger')}>
            {v.finalDecision}
          </p>
          <div className="mt-3">
            <StatusBadge value={safeDecision ? 'APPROVED' : 'REVIEW'} />
          </div>
          <p className="mt-3 text-sm text-muted-foreground">
            {safeDecision
              ? 'Status: Permit approved by the KAVACH pipeline. No human review required.'
              : v.requiresHumanReview
                ? 'Status: Human review required before this permit can be authorized.'
                : `Status: ${v.finalDecision}.`}
          </p>
        </Panel>

        <Panel className="p-6 lg:col-span-2">
          <div className="mb-2 flex items-center gap-2 text-xs font-semibold uppercase tracking-widest text-muted-foreground">
            <MessageSquareText className="size-4" /> Safety Explanation
          </div>
          <p className="text-sm leading-relaxed text-foreground/90">{v.explanation}</p>
          <div className="mt-4 flex flex-wrap items-center gap-x-6 gap-y-2 font-mono text-xs text-muted-foreground">
            <span>
              Deterministic evaluation: <span className="text-foreground">{v.deterministicEvaluated ? 'yes' : 'no'}</span>
            </span>
            <span>
              Reasoning provider:{' '}
              <span className="text-foreground">{v.reasoningProvider ?? 'none'}</span>
            </span>
            <span>
              Audit ref: <span className="text-foreground">{v.auditRef ?? '—'}</span>
            </span>
          </div>
          <div className="mt-4 flex flex-wrap gap-2">
            <Link
              href="/annotated"
              className="inline-flex items-center gap-2 rounded-md border border-border bg-secondary px-4 py-2 text-sm font-medium text-foreground transition-colors hover:bg-accent"
            >
              <Map className="size-4" /> View Annotated P&ID <ArrowRight className="size-4" />
            </Link>
            <Link
              href="/deliverables"
              className="inline-flex items-center gap-2 rounded-md border border-border bg-secondary px-4 py-2 text-sm font-medium text-foreground transition-colors hover:bg-accent"
            >
              <FileDown className="size-4" /> View Deliverables
            </Link>
          </div>
        </Panel>
      </div>

      {/* Human review */}
      {v.requiresHumanReview && (
        <div className="mt-6">
          <ReviewPanel ruleResult={v.ruleResult} llmResult={v.llmResult} agreement={v.agreement} />
        </div>
      )}
    </PageContainer>
  )
}