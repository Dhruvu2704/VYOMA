import { Panel } from '@/components/panel'
import { StatusBadge } from '@/components/status-badge'
import { cn } from '@/lib/utils'
import type { DetectedIssue, SafetyResult } from '@/lib/mock-data'
import type { LucideIcon } from 'lucide-react'

export function AnalysisCard({
  title,
  subtitle,
  icon: Icon,
  result,
  bodyTitle,
  body,
  checks,
  issues,
}: {
  title: string
  subtitle: string
  icon: LucideIcon
  result: SafetyResult
  bodyTitle: string
  body: string
  checks?: string[]
  issues: DetectedIssue[]
}) {
  const tone = result === 'SAFE' ? 'safe' : 'danger'
  return (
    <Panel corners className="flex flex-col">
      <div className="flex items-center justify-between border-b border-border p-4">
        <div className="flex items-center gap-3">
          <span
            className={cn(
              'flex size-10 items-center justify-center rounded-md border',
              tone === 'safe' ? 'border-safe/40 bg-safe/10 text-safe' : 'border-danger/40 bg-danger/10 text-danger',
            )}
          >
            <Icon className="size-5" />
          </span>
          <div>
            <h3 className="text-sm font-bold uppercase tracking-wide text-foreground">{title}</h3>
            <p className="text-xs text-muted-foreground">{subtitle}</p>
          </div>
        </div>
      </div>

      <div className="flex items-center justify-between border-b border-border bg-background/40 px-4 py-3">
        <span className="text-xs uppercase tracking-widest text-muted-foreground">Result</span>
        <StatusBadge value={result} />
      </div>

      <div className="flex-1 space-y-4 p-4">
        <div>
          <p className="mb-1.5 text-xs font-semibold uppercase tracking-widest text-muted-foreground">
            {bodyTitle}
          </p>
          <p className="text-sm leading-relaxed text-foreground/90">{body}</p>
        </div>

        {checks && (
          <div>
            <p className="mb-1.5 text-xs font-semibold uppercase tracking-widest text-muted-foreground">
              Safety Constraints
            </p>
            <ul className="space-y-1.5">
              {checks.map((c) => (
                <li key={c} className="flex items-start gap-2 text-sm text-foreground/90">
                  <span className="mt-1.5 size-1.5 shrink-0 rounded-full bg-primary" />
                  {c}
                </li>
              ))}
            </ul>
          </div>
        )}

        <div>
          <p className="mb-2 text-xs font-semibold uppercase tracking-widest text-muted-foreground">
            Detected Issues
          </p>
          <ul className="space-y-2">
            {issues.map((iss) => (
              <li
                key={iss.title}
                className="rounded-md border border-border bg-background/40 p-3"
              >
                <div className="flex items-center justify-between gap-2">
                  <span className="text-sm font-medium text-foreground">{iss.title}</span>
                  <StatusBadge value={iss.severity} size="sm" />
                </div>
                <p className="mt-1 text-xs leading-relaxed text-muted-foreground">{iss.detail}</p>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </Panel>
  )
}
