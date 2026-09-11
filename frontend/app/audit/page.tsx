'use client'

import { useEffect, useState } from 'react'
import { Panel, PanelHeader } from '@/components/panel'
import { PageContainer, PageHeader } from '@/components/page-header'
import { StatusBadge } from '@/components/status-badge'
import { Link2, FileCheck, ShieldCheck, Download, Loader2, AlertTriangle } from 'lucide-react'
import { useToast } from '@/components/toast'
import { getAuditFeed, verifyAuditChain, type AuditEvent } from '@/lib/api'
import { openAuth } from '@/components/auth-modal'

interface FeedRecord {
  audit_ref: string
  permit_id: string
  timestamp: string
  event: string
  actor: string
  task: string
  hash: string
  previous_hash: string
  sequence: number
}

function toRecord(e: AuditEvent): FeedRecord {
  return {
    audit_ref: e.audit_ref,
    permit_id: e.permit_id,
    timestamp: e.timestamp.replace('T', ' ').slice(0, 19),
    event: `KAVACH pipeline recorded for permit ${e.permit_id}`,
    actor: `Pipeline: ${e.pipeline.join(' \u2192 ')}`,
    task: e.permit_id || '—',
    hash: e.event_hash,
    previous_hash: e.previous_hash,
    sequence: e.sequence,
  }
}

export default function AuditPage() {
  const { push } = useToast()
  const [records, setRecords] = useState<FeedRecord[]>([])
  const [chainValid, setChainValid] = useState<boolean | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    let active = true
    Promise.all([getAuditFeed(), verifyAuditChain()])
      .then(([feed, verify]) => {
        if (!active) return
        setRecords(feed.map(toRecord))
        setChainValid(verify.valid)
      })
      .catch((err: unknown) => {
        if (!active) return
        const message = err instanceof Error ? err.message : 'Could not load the audit ledger.'
        if (message.toLowerCase().includes('authenticated') || message.includes('401')) {
          setError('The audit ledger requires officer clearance. Sign in with an officer account.')
        } else {
          setError(message)
        }
      })
      .finally(() => active && setLoading(false))
    return () => {
      active = false
    }
  }, [])

  const exportLog = () => {
    const payload = {
      exported_at: new Date().toISOString(),
      chain_verified: chainValid ?? false,
      records: records.map((r) => ({
        audit_ref: r.audit_ref,
        permit_id: r.permit_id,
        timestamp: r.timestamp,
        pipeline: r.actor,
        sequence: r.sequence,
        event_hash: r.hash,
        previous_hash: r.previous_hash,
      })),
    }
    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `audit-export-${Date.now()}.json`
    document.body.appendChild(a)
    a.click()
    a.remove()
    URL.revokeObjectURL(url)
    push({ kind: 'success', title: 'Audit log exported', message: 'Live records exported to JSON.' })
  }

  const total = records.length
  const chainLength = records.length
  const brokenLinks = chainValid ? '0' : total > 0 ? '>0' : '—'

  return (
    <PageContainer>
      <PageHeader
        title="Audit Trail"
        subtitle="Tamper-evident hash chain of every decision recorded by the KAVACH pipeline"
        action={
          <button
            onClick={exportLog}
            disabled={!total}
            className="inline-flex items-center gap-2 rounded-md border border-border bg-card px-4 py-2 text-sm font-medium text-foreground transition-colors hover:bg-card-elevated disabled:opacity-50"
          >
            <Download className="size-4" />
            Export Log
          </button>
        }
      />

      {loading && (
        <Panel className="flex flex-col items-center gap-3 p-12">
          <Loader2 className="size-6 animate-spin text-info" />
          <p className="text-sm text-muted-foreground">Loading audit chain…</p>
        </Panel>
      )}

      {!loading && error && (
        <Panel className="flex flex-col items-center gap-4 border-warning/40 bg-warning/5 p-10 text-center">
          <AlertTriangle className="size-8 text-warning" />
          <div>
            <h3 className="text-lg font-bold text-foreground">Audit ledger unavailable</h3>
            <p className="mt-1 text-sm text-muted-foreground">{error}</p>
          </div>
          <button
            onClick={openAuth}
            className="mt-2 inline-flex items-center gap-2 rounded-md bg-primary px-5 py-2.5 text-sm font-semibold text-primary-foreground transition-colors hover:bg-primary/90"
          >
            Sign In
          </button>
        </Panel>
      )}

      {!loading && !error && (
        <>
          <div className="mb-6 grid grid-cols-2 gap-4 sm:grid-cols-4">
            {[
              { label: 'Chain Integrity', value: chainValid === false ? 'VIOLATION' : 'VERIFIED' },
              { label: 'Total Records', value: String(total) },
              { label: 'Chain Length', value: String(chainLength) },
              { label: 'Broken Links', value: brokenLinks },
            ].map((s) => (
              <Panel key={s.label} className="p-4">
                <p className="text-xs uppercase tracking-widest text-muted-foreground">{s.label}</p>
                <p className="mt-1 font-mono text-xl font-bold text-foreground">{s.value}</p>
              </Panel>
            ))}
          </div>

          {records.length === 0 && (
            <Panel className="p-10 text-center">
              <p className="text-sm text-muted-foreground">
                No audit records yet. Records are written when the KAVACH pipeline records a decision.
              </p>
            </Panel>
          )}

          {records.length > 0 && (
            <Panel corners className="mb-6">
              <PanelHeader title="Cryptographic Hash Chain" icon={Link2} />
              <div className="flex gap-4 overflow-x-auto p-6">
                {records.map((node, i) => (
                  <div key={node.hash} className="flex items-center gap-4">
                    <div className="w-52 shrink-0 rounded-md border border-safe/25 bg-safe/5 p-3">
                      <div className="flex items-center gap-1.5">
                        <ShieldCheck className="size-3.5 text-safe" />
                        <span className="text-[10px] font-semibold uppercase tracking-wider text-safe">
                          Verified
                        </span>
                      </div>
                      <p className="mt-2 text-xs font-semibold text-foreground">{node.event}</p>
                      <p className="mt-1 font-mono text-[11px] text-muted-foreground">{node.timestamp}</p>
                      <div className="mt-2 rounded bg-background/60 px-2 py-1">
                        <p className="truncate font-mono text-[11px] text-primary">0x{node.hash}</p>
                      </div>
                      <p className="mt-1.5 text-[10px] uppercase tracking-wide text-muted-foreground">
                        seq {node.sequence}
                      </p>
                    </div>
                    {i < records.length - 1 && (
                      <Link2 className="size-4 shrink-0 rotate-90 text-border" aria-hidden />
                    )}
                  </div>
                ))}
              </div>
            </Panel>
          )}

          {records.length > 0 && (
            <Panel corners>
              <PanelHeader title="Audit Records" icon={FileCheck} />
              <div className="overflow-x-auto">
                <table className="w-full min-w-[760px] text-left text-sm">
                  <thead>
                    <tr className="border-b border-border text-xs uppercase tracking-wider text-muted-foreground">
                      <th className="px-4 py-3 font-medium">Timestamp</th>
                      <th className="px-4 py-3 font-medium">Event</th>
                      <th className="px-4 py-3 font-medium">Pipeline</th>
                      <th className="px-4 py-3 font-medium">Sequence</th>
                      <th className="px-4 py-3 font-medium">Event Hash</th>
                      <th className="px-4 py-3 font-medium">Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border">
                    {records.map((r) => (
                      <tr key={r.hash} className="transition-colors hover:bg-card-elevated/50">
                        <td className="whitespace-nowrap px-4 py-3 font-mono text-xs text-muted-foreground tabular-nums">
                          {r.timestamp}
                        </td>
                        <td className="px-4 py-3 font-mono text-xs text-foreground">{r.event}</td>
                        <td className="px-4 py-3 text-xs text-foreground/80">{r.actor}</td>
                        <td className="px-4 py-3 font-mono text-xs text-muted-foreground">{r.sequence}</td>
                        <td className="px-4 py-3 font-mono text-xs text-primary">0x{r.hash}</td>
                        <td className="px-4 py-3">
                          <StatusBadge value={chainValid === false ? 'VIOLATION' : 'VERIFIED'} size="sm" />
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Panel>
          )}
        </>
      )}
    </PageContainer>
  )
}