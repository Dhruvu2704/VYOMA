import Link from 'next/link'
import { Activity, Plus, ShieldAlert, ShieldCheck, UserCheck, ShieldHalf } from 'lucide-react'
import { PageContainer, PageHeader } from '@/components/page-header'
import { StatCard } from '@/components/dashboard/stat-card'
import { ActiveTasksTable } from '@/components/dashboard/active-tasks-table'
import { ActivityTimeline } from '@/components/dashboard/activity-timeline'
import { SecurityStatusCard } from '@/components/dashboard/security-status-card'
import { ShieldHero } from '@/components/three/shield-hero'
import { getDashboard } from '@/lib/api'

export default async function DashboardPage() {
  const { stats, activeTasks, recentActivity } = await getDashboard()

  return (
    <PageContainer>
      <PageHeader
        title="Safety Operations Center"
        subtitle="Permit verification and industrial safety monitoring"
        action={
          <Link
            href="/new-inspection"
            className="inline-flex items-center gap-2 rounded-md bg-primary px-4 py-2.5 text-sm font-semibold text-primary-foreground shadow-sm transition-colors hover:bg-primary/90"
          >
            <Plus className="size-4" /> New Inspection
          </Link>
        }
      />

      {/* Hero with 3D shield */}
      <div className="relative mb-6 overflow-hidden rounded-lg border border-border bg-card">
        <div className="pointer-events-none absolute inset-0 bg-engineering-grid-fine opacity-40" />
        <div className="relative grid items-center gap-4 lg:grid-cols-[1fr_360px]">
          <div className="p-6 sm:p-8">
            <div className="mb-3 inline-flex items-center gap-2 rounded-full border border-primary/30 bg-primary/10 px-3 py-1 font-mono text-[11px] uppercase tracking-widest text-primary">
              <ShieldHalf className="size-3.5" /> Vyoma Kavach v2.6
            </div>
            <h3 className="max-w-xl text-balance text-2xl font-bold leading-tight text-foreground sm:text-3xl">
              AI-verified Permit-to-Work &amp; P&amp;ID safety intelligence
            </h3>
            <p className="mt-3 max-w-lg text-pretty text-sm leading-relaxed text-muted-foreground">
              Dual-engine verification cross-checks rule-based safety constraints against LLM
              reasoning inside a zero-egress environment. Every decision is written to a tamper-evident
              audit ledger.
            </p>
            <div className="mt-5 flex flex-wrap gap-6">
              <div>
                <p className="font-mono text-2xl font-bold text-safe tabular-nums">99.98%</p>
                <p className="text-xs text-muted-foreground">Analysis uptime</p>
              </div>
              <div>
                <p className="font-mono text-2xl font-bold text-foreground tabular-nums">1,284</p>
                <p className="text-xs text-muted-foreground">Permits verified</p>
              </div>
              <div>
                <p className="font-mono text-2xl font-bold text-info tabular-nums">0</p>
                <p className="text-xs text-muted-foreground">External connections</p>
              </div>
            </div>
          </div>
          <div className="relative h-56 w-full lg:h-full lg:min-h-[280px]">
            <ShieldHero className="absolute inset-0 h-full w-full" />
          </div>
        </div>
      </div>

      {/* Stats row */}
      <div className="mb-6 grid grid-cols-2 gap-4 md:grid-cols-3 lg:grid-cols-5">
        <StatCard label="Active Inspections" value="12" desc="Currently in pipeline" icon={Activity} tone="info" />
        <StatCard label="Flagged Permits" value="04" desc="Require attention" icon={ShieldAlert} tone="danger" />
        <StatCard label="Human Reviews" value="02" desc="Awaiting officer" icon={UserCheck} tone="warning" />
        <StatCard label="Verified Today" value="27" desc="Cleared for work" icon={ShieldCheck} tone="safe" />
        <StatCard label="Zero-Egress" value="ACTIVE" desc="Network isolated" icon={ShieldHalf} tone="info" isStatus />
      </div>

      {/* Main grid */}
      <div className="grid gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <ActiveTasksTable tasks={activeTasks} />
        </div>
        <div className="space-y-6">
          <SecurityStatusCard />
        </div>
      </div>

      <div className="mt-6 grid gap-6 lg:grid-cols-3">
        <div className="lg:col-span-1">
          <ActivityTimeline events={recentActivity} />
        </div>
        <div className="lg:col-span-2">
          <ActiveActivitySummary />
        </div>
      </div>
    </PageContainer>
  )
}

function ActiveActivitySummary() {
  const items = [
    { label: 'Rule Engine', value: 'ONLINE', tone: 'text-safe' },
    { label: 'AI / LLM Agent', value: 'ONLINE', tone: 'text-safe' },
    { label: 'P&ID Graph Engine', value: 'ONLINE', tone: 'text-safe' },
    { label: 'Audit Ledger', value: 'SYNCED', tone: 'text-safe' },
    { label: 'Document OCR', value: 'ONLINE', tone: 'text-safe' },
    { label: 'Net Monitor', value: 'ENFORCED', tone: 'text-info' },
  ]
  return (
    <div className="relative h-full overflow-hidden rounded-md border border-border bg-card">
      <div className="border-b border-border px-4 py-3">
        <h3 className="text-xs font-semibold uppercase tracking-widest text-muted-foreground">
          Module Health
        </h3>
      </div>
      <div className="grid grid-cols-2 gap-px bg-border sm:grid-cols-3">
        {items.map((it) => (
          <div key={it.label} className="bg-card p-4">
            <p className="text-xs text-muted-foreground">{it.label}</p>
            <p className={`mt-1 font-mono text-sm font-bold ${it.tone}`}>{it.value}</p>
          </div>
        ))}
      </div>
    </div>
  )
}
