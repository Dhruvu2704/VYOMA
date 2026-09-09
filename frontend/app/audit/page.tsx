'use client'

import { Panel, PanelHeader } from '@/components/panel'
import { PageContainer, PageHeader } from '@/components/page-header'
import { StatusBadge } from '@/components/status-badge'
import { hashChain, auditRecords } from '@/lib/mock-data'
import { Link2, FileCheck, ShieldCheck, Download } from 'lucide-react'
import { useToast } from '@/components/toast'

export default function AuditPage() {
  const { toast } = useToast()

  return (
    <PageContainer>
      <PageHeader
        title="Audit Trail"
        subtitle="Tamper-evident hash chain of every action in the inspection lifecycle"
        action={
          <button
            onClick={() => toast('Audit log exported — audit-2026-0512.json', 'success')}
            className="inline-flex items-center gap-2 rounded-md border border-border bg-card px-4 py-2 text-sm font-medium text-foreground transition-colors hover:bg-card-elevated"
          >
            <Download className="size-4" />
            Export Log
          </button>
        }
      />

      <div className="mb-6 grid grid-cols-2 gap-4 sm:grid-cols-4">
        {[
          { label: 'Chain Integrity', value: 'VERIFIED' },
          { label: 'Total Records', value: String(auditRecords.length) },
          { label: 'Chain Length', value: String(hashChain.length) },
          { label: 'Broken Links', value: '0' },
        ].map((s) => (
          <Panel key={s.label} className="p-4">
            <p className="text-xs uppercase tracking-widest text-muted-foreground">{s.label}</p>
            <p className="mt-1 font-mono text-xl font-bold text-foreground">{s.value}</p>
          </Panel>
        ))}
      </div>

      <Panel corners className="mb-6">
        <PanelHeader title="Cryptographic Hash Chain" icon={Link2} />
        <div className="flex gap-4 overflow-x-auto p-6">
          {hashChain.map((node, i) => (
            <div key={node.hash} className="flex items-center gap-4">
              <div className="w-44 shrink-0 rounded-md border border-safe/25 bg-safe/5 p-3">
                <div className="flex items-center gap-1.5">
                  <ShieldCheck className="size-3.5 text-safe" />
                  <span className="text-[10px] font-semibold uppercase tracking-wider text-safe">Verified</span>
                </div>
                <p className="mt-2 text-xs font-semibold text-foreground">{node.event}</p>
                <p className="mt-1 font-mono text-[11px] text-muted-foreground">{node.timestamp}</p>
                <div className="mt-2 rounded bg-background/60 px-2 py-1">
                  <p className="font-mono text-[11px] text-primary">0x{node.hash}</p>
                </div>
                <p className="mt-1.5 text-[10px] uppercase tracking-wide text-muted-foreground">{node.actor}</p>
              </div>
              {i < hashChain.length - 1 && (
                <Link2 className="size-4 shrink-0 rotate-90 text-border" aria-hidden />
              )}
            </div>
          ))}
        </div>
      </Panel>

      <Panel corners>
        <PanelHeader title="Audit Records" icon={FileCheck} />
        <div className="overflow-x-auto">
          <table className="w-full min-w-[720px] text-left text-sm">
            <thead>
              <tr className="border-b border-border text-xs uppercase tracking-wider text-muted-foreground">
                <th className="px-4 py-3 font-medium">Timestamp</th>
                <th className="px-4 py-3 font-medium">Event</th>
                <th className="px-4 py-3 font-medium">Actor</th>
                <th className="px-4 py-3 font-medium">Task</th>
                <th className="px-4 py-3 font-medium">Hash</th>
                <th className="px-4 py-3 font-medium">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {auditRecords.map((r, i) => (
                <tr key={i} className="transition-colors hover:bg-card-elevated/50">
                  <td className="px-4 py-3 font-mono text-xs text-muted-foreground tabular-nums">{r.timestamp}</td>
                  <td className="px-4 py-3 font-mono text-xs text-foreground">{r.event}</td>
                  <td className="px-4 py-3 text-xs text-foreground/80">{r.actor}</td>
                  <td className="px-4 py-3 font-mono text-xs text-muted-foreground">{r.task}</td>
                  <td className="px-4 py-3 font-mono text-xs text-primary">0x{r.hash}</td>
                  <td className="px-4 py-3">
                    <StatusBadge value={r.status} size="sm" />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Panel>
    </PageContainer>
  )
}
