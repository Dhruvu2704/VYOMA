'use client'

import { useState } from 'react'
import { CheckCircle2, ShieldCheck, ShieldX, Loader2, AlertTriangle } from 'lucide-react'
import { Panel } from '@/components/panel'
import { StatusBadge } from '@/components/status-badge'
import { cn } from '@/lib/utils'
import { useToast } from '@/components/toast'
import { getCurrentUser, submitReview } from '@/lib/api'

export function ReviewPanel({
  ruleResult,
  llmResult,
  agreement,
}: {
  ruleResult: string
  llmResult: string
  agreement: string
}) {
  const toast = useToast()
  const [decision, setDecision] = useState<'APPROVE' | 'REJECT' | null>(null)
  const [notes, setNotes] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [done, setDone] = useState(false)
  const [resultNote, setResultNote] = useState('')

  const officer = getCurrentUser()

  const submit = async () => {
    if (!decision || notes.trim().length < 5) {
      toast.push({ kind: 'warning', title: 'Justification required', message: 'Enter a decision and justification note.' })
      return
    }
    setSubmitting(true)
    try {
      const result = await submitReview(decision, notes)
      setResultNote(result.note)
      setDone(true)
      toast.push({ kind: 'success', title: 'Decision recorded', message: 'Recorded locally; sign-off reaches the audit ledger through the plant system.' })
    } catch (error) {
      toast.push({
        kind: 'error',
        title: 'Could not record decision',
        message: error instanceof Error ? error.message : 'Unknown error.',
      })
    } finally {
      setSubmitting(false)
    }
  }

  if (done) {
    return (
      <Panel className="border-safe/40 p-6 glow-safe">
        <div className="flex items-center gap-3">
          <CheckCircle2 className="size-8 text-safe" />
          <div>
            <p className="text-lg font-bold text-foreground">Decision recorded</p>
            <p className="text-sm text-muted-foreground">
              Sign-off by {officer ? officer.toUpperCase() : 'anonymous'} was recorded in this session.
            </p>
          </div>
        </div>
        <div className="mt-4 flex flex-wrap items-center gap-3 rounded-md border border-border bg-background/50 p-3 font-mono text-xs">
          <span className="text-muted-foreground">DECISION</span>
          <StatusBadge value={decision === 'APPROVE' ? 'APPROVED' : 'REJECTED'} size="sm" />
          <span className="text-foreground">{resultNote || 'Client-side record'}</span>
        </div>
      </Panel>
    )
  }

  return (
    <Panel className="border-warning/40" corners>
      <div className="flex items-center gap-3 border-b border-warning/30 bg-warning/10 p-4">
        <AlertTriangle className="size-6 text-warning" />
        <div>
          <h3 className="text-sm font-bold uppercase tracking-wide text-warning">
            Safety Officer Review Required
          </h3>
          <p className="text-xs text-muted-foreground">
            Automated systems flagged this permit — manual authorization is required.
          </p>
        </div>
      </div>

      <div className="grid gap-4 p-4 lg:grid-cols-3">
        <div className="grid grid-cols-3 gap-3 lg:col-span-3">
          <MiniStat label="Rule Engine" value={ruleResult} />
          <MiniStat label="AI Analysis" value={llmResult} />
          <MiniStat label="Agreement" value={agreement} />
        </div>

        {/* Decision */}
        <div className="lg:col-span-3">
          <p className="mb-2 text-xs font-semibold uppercase tracking-widest text-muted-foreground">
            Officer Decision
          </p>
          <div className="grid gap-3 sm:grid-cols-2">
            <button
              onClick={() => setDecision('APPROVE')}
              className={cn(
                'flex items-center justify-center gap-2 rounded-md border py-3 text-sm font-bold uppercase tracking-wide transition-all',
                decision === 'APPROVE'
                  ? 'border-safe bg-safe/15 text-safe glow-safe'
                  : 'border-border bg-background/40 text-foreground hover:border-safe/50',
              )}
            >
              <ShieldCheck className="size-4" /> Approve Permit
            </button>
            <button
              onClick={() => setDecision('REJECT')}
              className={cn(
                'flex items-center justify-center gap-2 rounded-md border py-3 text-sm font-bold uppercase tracking-wide transition-all',
                decision === 'REJECT'
                  ? 'border-danger bg-danger/15 text-danger glow-danger'
                  : 'border-border bg-background/40 text-foreground hover:border-danger/50',
              )}
            >
              <ShieldX className="size-4" /> Reject Permit
            </button>
          </div>
        </div>

        {/* Notes */}
        <div className="lg:col-span-3">
          <label
            htmlFor="officer-notes"
            className="mb-2 block text-xs font-semibold uppercase tracking-widest text-muted-foreground"
          >
            Officer Notes <span className="text-danger">*</span>
          </label>
          <textarea
            id="officer-notes"
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            rows={3}
            placeholder="Enter justification for your decision…"
            className="w-full resize-none rounded-md border border-border bg-background/60 p-3 text-sm text-foreground outline-none transition-colors placeholder:text-muted-foreground focus:border-primary focus:ring-1 focus:ring-primary"
          />
          <div className="mt-2 flex items-center justify-between">
            <span className="font-mono text-xs text-muted-foreground">
              Officer ID: {officer ? officer.toUpperCase() : 'NOT SIGNED IN'}
            </span>
            <button
              onClick={submit}
              disabled={submitting}
              className="inline-flex items-center gap-2 rounded-md bg-primary px-5 py-2.5 text-sm font-semibold text-primary-foreground transition-colors hover:bg-primary/90 disabled:opacity-60"
            >
              {submitting ? <Loader2 className="size-4 animate-spin" /> : <CheckCircle2 className="size-4" />}
              Submit Safety Decision
            </button>
          </div>
        </div>
      </div>
    </Panel>
  )
}

function MiniStat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border border-border bg-background/40 p-3 text-center">
      <p className="mb-1.5 text-[10px] uppercase tracking-widest text-muted-foreground">{label}</p>
      <StatusBadge value={value} size="sm" />
    </div>
  )
}