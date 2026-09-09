import { cn } from '@/lib/utils'
import { Panel } from '@/components/panel'
import { StatusDot } from '@/components/status-badge'
import type { LucideIcon } from 'lucide-react'

type Tone = 'safe' | 'danger' | 'warning' | 'info'

const toneText: Record<Tone, string> = {
  safe: 'text-safe',
  danger: 'text-danger',
  warning: 'text-warning',
  info: 'text-info',
}
const toneBg: Record<Tone, string> = {
  safe: 'bg-safe/10 text-safe ring-safe/25',
  danger: 'bg-danger/10 text-danger ring-danger/25',
  warning: 'bg-warning/10 text-warning ring-warning/25',
  info: 'bg-info/10 text-info ring-info/25',
}

export function StatCard({
  label,
  value,
  desc,
  icon: Icon,
  tone,
  isStatus = false,
}: {
  label: string
  value: string
  desc: string
  icon: LucideIcon
  tone: Tone
  isStatus?: boolean
}) {
  return (
    <Panel className="group p-4 transition-colors hover:border-border/80 hover:bg-card-elevated">
      <div className="flex items-start justify-between">
        <div className={cn('flex size-9 items-center justify-center rounded-md ring-1', toneBg[tone])}>
          <Icon className="size-4.5" />
        </div>
        <StatusDot tone={tone} pulse={tone !== 'safe' ? true : isStatus} />
      </div>
      <p className="mt-3 text-[10px] font-semibold uppercase tracking-widest text-muted-foreground">
        {label}
      </p>
      <p
        className={cn(
          'mt-1 tabular-nums',
          isStatus ? cn('font-mono text-xl font-bold', toneText[tone]) : 'text-3xl font-bold text-foreground',
        )}
      >
        {value}
      </p>
      <p className="mt-1 text-xs text-muted-foreground">{desc}</p>
    </Panel>
  )
}
