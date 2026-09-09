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
} from 'lucide-react'
import { PageContainer, PageHeader } from '@/components/page-header'
import { Panel } from '@/components/panel'
import { AnalysisCard } from '@/components/verdict/analysis-card'
import { ReviewPanel } from '@/components/verdict/review-panel'
import { StatusBadge } from '@/components/status-badge'
import { getVerdict } from '@/lib/api'
import { cn } from '@/lib/utils'

export default async function VerdictPage() {
  const v = await getVerdict()
  const agree = v.agreement === 'AGREE'

  return (
    <PageContainer>
      <PageHeader
        title="Safety Verification Result"
        subtitle={`${v.asset}`}
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
          agree ? 'border-safe/40 bg-safe/5' : 'border-warning/40 bg-warning/5',
        )}
      >
        <div className="pointer-events-none absolute inset-0 bg-engineering-grid-fine opacity-30" />
        <div className="relative flex items-center gap-4">
          <span
            className={cn(
              'flex size-14 shrink-0 items-center justify-center rounded-full border',
              agree ? 'border-safe/50 bg-safe/15 text-safe glow-safe' : 'border-warning/50 bg-warning/15 text-warning glow-warning',
            )}
          >
            {agree ? <Check className="size-7" /> : <AlertTriangle className="size-7" />}
          </span>
          <div>
            <h3 className={cn('text-xl font-bold tracking-tight', agree ? 'text-safe' : 'text-warning')}>
              {agree ? 'SYSTEMS AGREE' : 'SYSTEM DISAGREEMENT'}
            </h3>
            <p className="mt-0.5 text-sm text-muted-foreground">
              {agree
                ? 'Rule engine and AI analysis produced the same result.'
                : 'Rule engine and AI analysis produced different results. Human review is required.'}
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
          result={v.ruleResult}
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
              agree ? 'border-safe/50 bg-card text-safe' : 'border-warning/50 bg-card text-warning',
            )}
          >
            {agree ? <Check className="size-3.5" /> : <AlertTriangle className="size-3.5" />}
            {v.agreement}
          </span>
        </div>

        <AnalysisCard
          title="AI / LLM Analysis"
          subtitle="Context-aware reasoning"
          icon={Cpu}
          result={v.llmResult}
          bodyTitle="AI Reasoning Summary"
          body={v.llmReasoning}
          issues={v.llmIssues}
        />
      </div>

      {/* Final decision + explanation */}
      <div className="mt-6 grid gap-6 lg:grid-cols-3">
        <Panel corners className="flex flex-col justify-center border-danger/40 p-6 lg:col-span-1">
          <div className="mb-2 flex items-center gap-2 text-xs font-semibold uppercase tracking-widest text-muted-foreground">
            <Gavel className="size-4" /> Final Decision
          </div>
          <p className="text-2xl font-bold text-danger">{v.finalDecision}</p>
          <div className="mt-3">
            <StatusBadge value="REVIEW" />
          </div>
          <p className="mt-3 text-sm text-muted-foreground">
            Status: Human review required before this permit can be authorized.
          </p>
        </Panel>

        <Panel className="p-6 lg:col-span-2">
          <div className="mb-2 flex items-center gap-2 text-xs font-semibold uppercase tracking-widest text-muted-foreground">
            <MessageSquareText className="size-4" /> Safety Explanation
          </div>
          <p className="text-sm leading-relaxed text-foreground/90">{v.explanation}</p>
          <Link
            href="/annotated"
            className="mt-4 inline-flex items-center gap-2 rounded-md border border-border bg-secondary px-4 py-2 text-sm font-medium text-foreground transition-colors hover:bg-accent"
          >
            <Map className="size-4" /> View Annotated P&ID <ArrowRight className="size-4" />
          </Link>
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
