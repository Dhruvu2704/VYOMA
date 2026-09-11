'use client'

import { useEffect, useState } from 'react'
import { Panel, PanelHeader } from '@/components/panel'
import { PageContainer, PageHeader } from '@/components/page-header'
import { StatusBadge, StatusDot } from '@/components/status-badge'
import { getSecurityStatus, type SecurityStatus } from '@/lib/api'
import { ShieldCheck, Network, Ban, Activity, FileCheck, Loader2, AlertTriangle, ServerCog } from 'lucide-react'

export default function SecurityPage() {
  const [status, setStatus] = useState<SecurityStatus | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    getSecurityStatus()
      .then(setStatus)
      .catch((err: unknown) =>
        setError(err instanceof Error ? err.message : 'Failed to load security status'),
      )
      .finally(() => setLoading(false))
  }, [])

  return (
    <PageContainer>
      <PageHeader
        title="Security Operations"
        subtitle="Live runtime egress evidence — real connection sampling, not static labels"
        action={
          loading ? (
            <span className="flex items-center gap-2 font-mono text-xs uppercase tracking-wider text-muted-foreground">
              <Loader2 className="size-4 animate-spin" /> sampling
            </span>
          ) : (
            <div className="flex items-center gap-2 rounded-md border border-safe/40 bg-safe/10 px-3 py-1.5">
              <StatusDot tone={status ? 'safe' : 'danger'} pulse={!!status} />
              <span className="font-mono text-xs font-semibold uppercase tracking-wider text-safe">
                {status ? `${status.external_observed_since_start} external since start` : 'unavailable'}
              </span>
            </div>
          )
        }
      />

      {loading && (
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
          <Panel corners className="lg:col-span-3">
            <PanelHeader title="Zero-Egress Evidence" icon={Loader2} />
            <div className="flex items-center gap-3 px-4 py-10">
              <Loader2 className="size-5 animate-spin text-muted-foreground" />
              <p className="text-sm text-muted-foreground">Sampling the running process&apos;s connections…</p>
            </div>
          </Panel>
        </div>
      )}

      {!loading && error && (
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
          <Panel corners className="lg:col-span-3">
            <PanelHeader title="Zero-Egress Evidence" icon={AlertTriangle} />
            <div className="flex items-center gap-3 px-4 py-10">
              <AlertTriangle className="size-5 shrink-0 text-warning" />
              <p className="text-sm text-foreground">
                Could not reach the security endpoint: <span className="font-mono">{error}</span>
              </p>
            </div>
          </Panel>
        </div>
      )}

      {status && (
        <>
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
            <Panel corners className="lg:col-span-2">
              <PanelHeader
                title="Active Connections"
                icon={Network}
                action={<StatusBadge value="SAMPLED" size="sm" />}
              />
              <div className="divide-y divide-border">
                <div className="px-4 py-3">
                  <p className="mb-2 flex items-center gap-2 text-xs uppercase tracking-wider text-muted-foreground">
                    <span className="size-2 rounded-full bg-safe" /> Local (loopback — e.g. Ollama)
                    <span className="font-mono normal-case text-muted-foreground/80">
                      {status.local_connection_count} active
                    </span>
                  </p>
                  {status.local_connections.length === 0 ? (
                    <p className="font-mono text-xs text-muted-foreground">None observed in this sample</p>
                  ) : (
                    <ul className="space-y-1.5 font-mono text-xs">
                      {status.local_connections.map((conn, i) => (
                        <li
                          key={i}
                          className="flex items-center gap-3 rounded border border-border bg-background/60 px-3 py-1.5"
                        >
                          <span className="text-muted-foreground">
                            {conn.laddr ? `${conn.laddr.ip}:${conn.laddr.port}` : '—'}
                          </span>
                          <span className="text-muted-foreground/60">→</span>
                          <span className="text-foreground">
                            {conn.raddr ? `${conn.raddr.ip}:${conn.raddr.port}` : 'listen'}
                          </span>
                          <span className="ml-auto rounded bg-muted px-1.5 py-0.5 text-[10px] text-muted-foreground">
                            {conn.status}
                          </span>
                        </li>
                      ))}
                    </ul>
                  )}
                </div>

                <div className="px-4 py-3">
                  <p className="mb-2 flex items-center gap-2 text-xs uppercase tracking-wider text-muted-foreground">
                    <span className="size-2 rounded-full bg-danger" /> External destination
                    <span className="font-mono normal-case text-muted-foreground/80">
                      {status.external_connection_count} active
                    </span>
                  </p>
                  {status.external_connections.length === 0 ? (
                    <p className="font-mono text-xs text-muted-foreground">
                      None observed — the only destinations seen are loopback
                    </p>
                  ) : (
                    <ul className="space-y-1.5 font-mono text-xs">
                      {status.external_connections.map((conn, i) => (
                        <li
                          key={i}
                          className="flex items-center gap-3 rounded border border-danger/30 bg-danger/10 px-3 py-1.5"
                        >
                          <span className="text-foreground">
                            {conn.raddr ? `${conn.raddr.ip}:${conn.raddr.port}` : '—'}
                          </span>
                          <span className="ml-auto rounded bg-muted px-1.5 py-0.5 text-[10px] text-muted-foreground">
                            {conn.status}
                          </span>
                        </li>
                      ))}
                    </ul>
                  )}
                  <p className="mt-2 font-mono text-[10px] text-muted-foreground">
                    sampled at {status.sampled_at.replace('T', ' ').slice(0, 19)}Z · {status.method} ·
                    {status.connect_error ? ` error: ${status.connect_error}` : ''}
                  </p>
                </div>
              </div>
            </Panel>

            <Panel>
              <PanelHeader title="Security Posture" icon={ShieldCheck} />
              <div className="grid grid-cols-1 gap-px bg-border">
                <PostureItem
                  label="Zero Egress"
                  value={status.external_observed_since_start === 0 ? 'ACTIVE' : 'BREACHED'}
                  icon={ShieldCheck}
                  tone={status.external_observed_since_start === 0 ? 'good' : 'bad'}
                />
                <PostureItem
                  label="External Egress"
                  value={`${status.external_connection_count} active`}
                  icon={Ban}
                  tone={status.external_connection_count === 0 ? 'good' : 'bad'}
                />
                <PostureItem
                  label="External observed"
                  value={String(status.external_observed_since_start)}
                  icon={Ban}
                  tone="good"
                />
                <PostureItem
                  label="Monitor"
                  value="psutil (live)"
                  icon={Activity}
                  tone="good"
                />
                <PostureItem
                  label="Server PID"
                  value={String(status.pid)}
                  icon={ServerCog}
                  tone="good"
                />
                <PostureItem
                  label="Audit Chain"
                  value={status.audit_chain.valid ? 'HEALTHY' : 'INVALID'}
                  icon={FileCheck}
                  tone={status.audit_chain.valid ? 'good' : 'bad'}
                />
              </div>
            </Panel>
          </div>

          <Panel corners className="mt-6">
            <PanelHeader title="Network Interfaces (psutil)" icon={Network} />
            <div className="grid grid-cols-1 gap-px bg-border md:grid-cols-2">
              {status.interfaces.map((iface) => (
                <div key={iface.name} className="bg-card p-4">
                  <div className="flex items-center gap-2 font-mono text-sm font-semibold text-foreground">
                    {iface.name}
                    {iface.is_up ? (
                      <StatusBadge value="ACTIVE" size="sm" />
                    ) : (
                      <span className="rounded border border-dashed border-border bg-background/60 px-1.5 py-0.5 font-mono text-[10px] uppercase tracking-wider text-muted-foreground">
                        down
                      </span>
                    )}
                  </div>
                  {iface.addresses.length === 0 ? (
                    <p className="mt-2 font-mono text-xs text-muted-foreground">No addresses configured</p>
                  ) : (
                    <ul className="mt-2 space-y-1">
                      {iface.addresses.map((addr, i) => (
                        <li key={i} className="font-mono text-xs text-muted-foreground">
                          <span className="text-[10px] uppercase text-muted-foreground/70">{addr.family}</span>{' '}
                          <span className="text-foreground">{addr.address}</span>
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              ))}
            </div>
          </Panel>
        </>
      )}
    </PageContainer>
  )
}

function PostureItem({
  label,
  value,
  icon: Icon,
  tone,
}: {
  label: string
  value: string
  icon: typeof ShieldCheck
  tone: 'good' | 'bad'
}) {
  return (
    <div className="flex items-center gap-3 bg-card p-4">
      <div
        className={
          tone === 'good'
            ? 'flex size-9 shrink-0 items-center justify-center rounded-md bg-safe/10'
            : 'flex size-9 shrink-0 items-center justify-center rounded-md bg-danger/10'
        }
      >
        <Icon className={tone === 'good' ? 'size-4 text-safe' : 'size-4 text-danger'} />
      </div>
      <div className="min-w-0 flex-1">
        <p className="truncate text-xs text-muted-foreground">{label}</p>
        <p className="font-mono text-sm font-semibold text-foreground">{value}</p>
      </div>
    </div>
  )
}