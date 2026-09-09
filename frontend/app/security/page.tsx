'use client'

import { Panel, PanelHeader } from '@/components/panel'
import { PageContainer, PageHeader } from '@/components/page-header'
import { PacketFlow } from '@/components/three/packet-flow'
import { securityStatus, securityEvents } from '@/lib/mock-data'
import { ShieldCheck, Network, Ban, Activity, FileCheck, Lock } from 'lucide-react'

const statusItems = [
  { key: 'zeroEgress', label: 'Zero Egress', value: securityStatus.zeroEgress, icon: ShieldCheck, good: true },
  { key: 'externalEgress', label: 'External Egress', value: securityStatus.externalEgress, icon: Ban, good: true },
  { key: 'packetMonitoring', label: 'Packet Monitoring', value: securityStatus.packetMonitoring, icon: Activity, good: true },
  { key: 'securityPolicy', label: 'Security Policy', value: securityStatus.securityPolicy, icon: Lock, good: true },
  { key: 'auditChain', label: 'Audit Chain', value: securityStatus.auditChain, icon: FileCheck, good: true },
  { key: 'interfaceState', label: `Interface (${securityStatus.networkInterface})`, value: securityStatus.interfaceState, icon: Network, good: true },
]

export default function SecurityPage() {
  return (
    <PageContainer>
      <PageHeader
        title="Security Operations"
        subtitle="Zero-egress enforcement across the air-gapped inspection pipeline"
        action={
          <div className="flex items-center gap-2 rounded-md border border-safe/40 bg-safe/10 px-3 py-1.5">
            <span className="relative flex size-2">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-safe opacity-75" />
              <span className="relative inline-flex size-2 rounded-full bg-safe" />
            </span>
            <span className="font-mono text-xs font-semibold uppercase tracking-wider text-safe">
              {securityStatus.externalConnections} external connections
            </span>
          </div>
        }
      />

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <Panel corners className="overflow-hidden lg:col-span-2">
          <PanelHeader title="Network Topology — Live Packet Flow" icon={Network} />
          <div className="relative">
            <PacketFlow />
            <div className="pointer-events-none absolute bottom-3 left-4 flex gap-4 font-mono text-[10px] uppercase tracking-wider">
              <span className="flex items-center gap-1.5 text-safe">
                <span className="size-2 rounded-full bg-safe" /> Internal (allowed)
              </span>
              <span className="flex items-center gap-1.5 text-danger">
                <span className="size-2 rounded-full bg-danger" /> Egress (blocked)
              </span>
            </div>
          </div>
        </Panel>

        <Panel className="lg:col-span-1">
          <PanelHeader title="Security Posture" icon={ShieldCheck} />
          <div className="grid grid-cols-1 gap-px bg-border sm:grid-cols-2 lg:grid-cols-1">
            {statusItems.map((item) => (
              <div key={item.key} className="flex items-center gap-3 bg-card p-4">
                <div className="flex size-9 shrink-0 items-center justify-center rounded-md bg-safe/10">
                  <item.icon className="size-4 text-safe" />
                </div>
                <div className="min-w-0 flex-1">
                  <p className="truncate text-xs text-muted-foreground">{item.label}</p>
                  <p className="font-mono text-sm font-semibold text-foreground">{item.value}</p>
                </div>
              </div>
            ))}
          </div>
        </Panel>
      </div>

      <Panel corners className="mt-6">
        <PanelHeader title="Live Security Events" icon={Activity} />
        <div className="divide-y divide-border">
          {securityEvents.map((evt, i) => (
            <div key={i} className="flex items-center gap-4 px-4 py-3 font-mono text-sm">
              <span className="text-xs text-muted-foreground tabular-nums">{evt.time}</span>
              <span
                className={
                  'inline-flex w-20 shrink-0 items-center justify-center rounded px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider ' +
                  (evt.status === 'BLOCKED'
                    ? 'bg-danger/15 text-danger'
                    : 'bg-safe/15 text-safe')
                }
              >
                {evt.status}
              </span>
              <span className="flex-1 truncate text-foreground/90">{evt.event}</span>
              <span className="rounded bg-muted px-2 py-0.5 text-xs text-muted-foreground">{evt.iface}</span>
            </div>
          ))}
        </div>
      </Panel>
    </PageContainer>
  )
}
