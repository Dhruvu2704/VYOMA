'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { ArrowRight, Loader2, ShieldHalf } from 'lucide-react'
import { Panel, PanelHeader } from '@/components/panel'
import { StatusDot } from '@/components/status-badge'
import { getSecurityStatus, type SecurityStatus } from '@/lib/api'

export function SecurityStatusCard() {
  const [status, setStatus] = useState<SecurityStatus | null>(null)

  useEffect(() => {
    getSecurityStatus()
      .then(setStatus)
      .catch(() => setStatus(null))
  }, [])

  const zeroObserved = status !== null && status.external_observed_since_start === 0
  const iface = status?.interfaces.find((i) => i.is_up)?.name ?? '—'

  return (
    <Panel className="h-full" corners>
      <PanelHeader title="Zero-Egress Status" icon={ShieldHalf} />
      <div className="p-4">
        {status === null ? (
          <div className="flex items-center gap-3 rounded-md border border-border bg-background/40 p-3">
            <Loader2 className="size-4 animate-spin text-muted-foreground" />
            <p className="text-xs text-muted-foreground">Sampling live connections…</p>
          </div>
        ) : (
          <>
            <div
              className={`mb-4 flex items-center gap-3 rounded-md border p-3 ${
                zeroObserved ? 'border-info/25 bg-info/10' : 'border-danger/25 bg-danger/10'
              }`}
            >
              <StatusDot tone={zeroObserved ? 'info' : 'danger'} />
              <div>
                <p
                  className={`font-mono text-sm font-bold tracking-wide ${
                    zeroObserved ? 'text-info' : 'text-danger'
                  }`}
                >
                  {zeroObserved ? 'ACTIVE' : 'BREACHED'}
                </p>
                <p className="text-xs text-muted-foreground">
                  {status.external_observed_since_start} external destination(s) since process start
                </p>
              </div>
            </div>
            <dl className="space-y-2.5">
              <div className="flex items-center justify-between text-sm">
                <dt className="text-muted-foreground">Network Interface</dt>
                <dd className="font-mono text-xs text-foreground">{iface}</dd>
              </div>
              <div className="flex items-center justify-between text-sm">
                <dt className="text-muted-foreground">External Egress</dt>
                <dd className="font-mono text-xs text-foreground">
                  {status.external_connection_count} active
                </dd>
              </div>
              <div className="flex items-center justify-between text-sm">
                <dt className="text-muted-foreground">Connections sampled</dt>
                <dd className="font-mono text-xs text-foreground">{status.local_connection_count} local</dd>
              </div>
              <div className="flex items-center justify-between text-sm">
                <dt className="text-muted-foreground">Audit Chain</dt>
                <dd className="font-mono text-xs text-foreground">
                  {status.audit_chain.valid ? 'SYNCED' : 'INVALID'}
                </dd>
              </div>
            </dl>
          </>
        )}
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