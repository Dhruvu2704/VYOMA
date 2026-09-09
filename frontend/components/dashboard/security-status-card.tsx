import Link from 'next/link'
import { ArrowRight, ShieldHalf } from 'lucide-react'
import { Panel, PanelHeader } from '@/components/panel'
import { StatusBadge, StatusDot } from '@/components/status-badge'

const rows = [
  { label: 'Network Interface', value: 'eth0', mono: true },
  { label: 'External Egress', value: 'BLOCKED', badge: true },
  { label: 'Packet Monitoring', value: 'ACTIVE', badge: true },
  { label: 'Audit Chain', value: 'HEALTHY', badge: true },
]

export function SecurityStatusCard() {
  return (
    <Panel className="h-full" corners>
      <PanelHeader title="Zero-Egress Status" icon={ShieldHalf} />
      <div className="p-4">
        <div className="mb-4 flex items-center gap-3 rounded-md border border-info/25 bg-info/10 p-3">
          <StatusDot tone="info" />
          <div>
            <p className="font-mono text-sm font-bold tracking-wide text-info">ACTIVE</p>
            <p className="text-xs text-muted-foreground">No external traffic permitted</p>
          </div>
        </div>
        <dl className="space-y-2.5">
          {rows.map((r) => (
            <div key={r.label} className="flex items-center justify-between text-sm">
              <dt className="text-muted-foreground">{r.label}</dt>
              <dd>
                {r.badge ? (
                  <StatusBadge value={r.value} size="sm" />
                ) : (
                  <span className="font-mono text-xs text-foreground">{r.value}</span>
                )}
              </dd>
            </div>
          ))}
        </dl>
        <Link
          href="/security"
          className="mt-4 flex w-full items-center justify-center gap-2 rounded-md border border-border bg-secondary py-2 text-sm font-medium text-foreground transition-colors hover:bg-accent"
        >
          View Security Dashboard <ArrowRight className="size-4" />
        </Link>
      </div>
    </Panel>
  )
}
