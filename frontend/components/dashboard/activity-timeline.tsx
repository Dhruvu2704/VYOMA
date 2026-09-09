import { Panel, PanelHeader } from '@/components/panel'
import { cn } from '@/lib/utils'
import { CheckCircle2, FileUp, Gavel, ScanSearch, ShieldX, type LucideIcon } from 'lucide-react'
import type { ActivityEvent } from '@/lib/mock-data'

const kindConfig: Record<ActivityEvent['kind'], { icon: LucideIcon; cls: string }> = {
  review: { icon: CheckCircle2, cls: 'text-safe border-safe/40 bg-safe/10' },
  verdict: { icon: Gavel, cls: 'text-warning border-warning/40 bg-warning/10' },
  analysis: { icon: ScanSearch, cls: 'text-info border-info/40 bg-info/10' },
  upload: { icon: FileUp, cls: 'text-primary border-primary/40 bg-primary/10' },
  security: { icon: ShieldX, cls: 'text-danger border-danger/40 bg-danger/10' },
}

export function ActivityTimeline({ events }: { events: ActivityEvent[] }) {
  return (
    <Panel className="h-full">
      <PanelHeader title="Recent Safety Activity" />
      <ol className="relative px-4 py-4">
        <span className="absolute bottom-6 left-[27px] top-7 w-px bg-border" aria-hidden />
        {events.map((e, i) => {
          const { icon: Icon, cls } = kindConfig[e.kind]
          return (
            <li key={i} className="relative flex gap-3 pb-4 last:pb-0">
              <span
                className={cn(
                  'relative z-10 flex size-6 shrink-0 items-center justify-center rounded-full border',
                  cls,
                )}
              >
                <Icon className="size-3" />
              </span>
              <div className="min-w-0 pt-0.5">
                <p className="font-mono text-[11px] text-muted-foreground">{e.time}</p>
                <p className="text-sm text-foreground">{e.label}</p>
              </div>
            </li>
          )
        })}
      </ol>
    </Panel>
  )
}
