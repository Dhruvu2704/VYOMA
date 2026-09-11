'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { Panel, PanelHeader } from '@/components/panel'
import { PageContainer, PageHeader } from '@/components/page-header'
import { StatusBadge, StatusDot } from '@/components/status-badge'
import { getWorkbenchStatus, type WorkbenchStatus } from '@/lib/api'
import { cn } from '@/lib/utils'
import {
  Cpu,
  ServerCog,
  Wrench,
  FileBox,
  Boxes,
  ExternalLink,
  Loader2,
  AlertTriangle,
  ShieldHalf,
  FileText,
  Table,
  FileType,
  ShieldCheck,
  Network,
} from 'lucide-react'

const generatorIcons: Record<string, typeof FileText> = {
  word: FileText,
  excel: Table,
  pdf: FileType,
  audit: ShieldCheck,
}

export default function WorkbenchPage() {
  const [status, setStatus] = useState<WorkbenchStatus | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    getWorkbenchStatus()
      .then(setStatus)
      .catch((err: unknown) =>
        setError(err instanceof Error ? err.message : 'Failed to load workbench status'),
      )
      .finally(() => setLoading(false))
  }, [])

  return (
    <PageContainer>
      <PageHeader
        title="System Workbench"
        subtitle="Live read-only view of the pipeline stack, reasoning provider, and registered tool surface"
        action={
          loading ? (
            <span className="flex items-center gap-2 font-mono text-xs uppercase tracking-wider text-muted-foreground">
              <Loader2 className="size-4 animate-spin" /> probing
            </span>
          ) : (
            <span className="flex items-center gap-2 rounded-md border border-border bg-card px-3 py-1.5 font-mono text-xs uppercase tracking-wider text-muted-foreground">
              <StatusDot tone={status ? 'safe' : 'danger'} pulse={!!status} />
              {status ? `${status.application.name} ONLINE` : 'UNAVAILABLE'}
            </span>
          )
        }
      />

      {loading && (
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
          <Panel corners className="lg:col-span-3">
            <PanelHeader title="Workbench Status" icon={Loader2} />
            <div className="flex items-center gap-3 px-4 py-10">
              <Loader2 className="size-5 animate-spin text-muted-foreground" />
              <p className="text-sm text-muted-foreground">Querying backend introspection…</p>
            </div>
          </Panel>
        </div>
      )}

      {!loading && error && (
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
          <Panel corners className="lg:col-span-3">
            <PanelHeader title="Workbench Status" icon={AlertTriangle} />
            <div className="flex items-center gap-3 px-4 py-10">
              <AlertTriangle className="size-5 shrink-0 text-warning" />
              <p className="text-sm text-foreground">
                Could not reach the workbench endpoint: <span className="font-mono">{error}</span>
              </p>
            </div>
          </Panel>
        </div>
      )}

      {status && (
        <>
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
            <Panel corners className="lg:col-span-2">
              <PanelHeader title="Orchestrator Pipeline" icon={Cpu} />
              <div className="divide-y divide-border">
                <div className="flex flex-wrap items-center gap-x-6 gap-y-3 px-4 py-3 font-mono text-sm">
                  <span className="text-xs uppercase tracking-wider text-muted-foreground">
                    Reasoning Provider
                  </span>
                  <span className="rounded border border-safe/30 bg-safe/10 px-2 py-0.5 text-xs font-semibold text-safe">
                    {status.orchestrator.reasoning_provider}
                  </span>
                  <span className="text-xs text-muted-foreground">
                    {status.orchestrator.provider_base_url} · timeout{' '}
                    {status.orchestrator.provider_timeout_s}s
                  </span>
                </div>
                <div className="grid grid-cols-1 gap-px bg-border sm:grid-cols-3 lg:grid-cols-5">
                  {status.orchestrator.stages.map((stage, i) => (
                    <div key={stage} className="flex items-center gap-2 bg-card px-4 py-3">
                      <span className="font-mono text-[10px] tabular-nums text-muted-foreground">
                        {String(i + 1).padStart(2, '0')}
                      </span>
                      <span className="truncate font-mono text-sm text-foreground">{stage}</span>
                    </div>
                  ))}
                </div>
              </div>
            </Panel>

            <Panel corners>
              <PanelHeader
                title="Ollama Inference Server"
                icon={ServerCog}
                action={
                  <StatusBadge
                    value={status.ollama.status === 'online' ? 'ONLINE' : 'OFFLINE'}
                    size="sm"
                  />
                }
              />
              <div className="divide-y divide-border">
                <div>
                  <div className="flex items-center justify-between px-4 py-3">
                    <span className="text-xs uppercase tracking-wider text-muted-foreground">
                      Endpoint
                    </span>
                    <span className="font-mono text-xs text-foreground">
                      {status.ollama.base_url}
                    </span>
                  </div>
                  <div className="flex items-center justify-between px-4 pb-3">
                    <span className="text-xs uppercase tracking-wider text-muted-foreground">
                      Model Count
                    </span>
                    <span className="font-mono text-sm font-semibold text-foreground">
                      {status.ollama.model_count}
                    </span>
                  </div>
                </div>
                <div className="px-4 py-3">
                  <p className="mb-2 text-xs uppercase tracking-wider text-muted-foreground">
                    Installed Models
                  </p>
                  {status.ollama.models.length === 0 ? (
                    <p className="font-mono text-xs text-muted-foreground">
                      {status.ollama.status === 'unreachable'
                        ? `Unreachable — ${status.ollama.detail ?? 'no response'}`
                        : 'No models installed'}
                    </p>
                  ) : (
                    <ul className="space-y-2">
                      {status.ollama.models.map((model) => (
                        <li
                          key={model}
                          className="flex items-center gap-2 rounded border border-border bg-background/60 px-3 py-2 font-mono text-xs text-foreground"
                        >
                          <span className="size-1.5 rounded-full bg-safe" />
                          {model}
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              </div>
            </Panel>
          </div>

          <Panel corners className="mt-6">
            <PanelHeader
              title="Model Router"
              icon={Network}
              action={
                <span className="font-mono text-[10px] uppercase tracking-wider text-muted-foreground">
                  {status.router.registered_providers.join(', ') || 'no providers'}
                </span>
              }
            />
            <div className="divide-y divide-border">
              {status.router.routing.map((entry) => (
                <div key={entry.capability} className="flex items-start gap-4 px-4 py-3">
                  <span className="w-44 shrink-0 pt-0.5 font-mono text-sm font-semibold text-foreground">
                    {entry.capability}
                  </span>
                  {entry.provider ? (
                    <StatusBadge value={entry.provider} size="sm" />
                  ) : (
                    <span className="inline-flex items-center gap-1.5 rounded border border-dashed border-border bg-background/60 px-2 py-0.5 font-mono text-[10px] uppercase tracking-wider text-muted-foreground">
                      not configured
                    </span>
                  )}
                  <p className="min-w-0 flex-1 text-xs text-muted-foreground">{entry.logic}</p>
                </div>
              ))}
            </div>
          </Panel>

          <Panel corners className="mt-6">
            <PanelHeader
              title={`Applications Running on ${status.application.name}`}
              icon={Boxes}
            />
            <div className="grid grid-cols-1 gap-px bg-border md:grid-cols-2">
              <div className="flex items-center gap-4 bg-card p-4">
                <div className="flex size-10 shrink-0 items-center justify-center rounded-md bg-primary/15">
                  <ShieldHalf className="size-5 text-primary" />
                </div>
                <div className="min-w-0 flex-1">
                  <p className="font-mono text-sm font-bold text-foreground">KAVACH</p>
                  <p className="text-xs text-muted-foreground">
                    Safety verification engine — runs the orchestrator pipeline above.
                  </p>
                </div>
                <Link
                  href="/new-inspection"
                  className="shrink-0 rounded-md border border-border bg-background/60 px-3 py-1.5 font-mono text-xs uppercase tracking-wider text-foreground transition-colors hover:bg-secondary"
                >
                  Start inspection <ExternalLink className="ml-1 inline size-3" />
                </Link>
              </div>
              <div className="flex items-center gap-4 bg-card p-4">
                <div className="flex size-10 shrink-0 items-center justify-center rounded-md bg-safe/10">
                  <Boxes className="size-5 text-safe" />
                </div>
                <div className="min-w-0 flex-1">
                  <p className="font-mono text-sm font-bold text-foreground">
                    {status.application.name}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    Platform shell — auth, task processing, audit ledger, and deliverables.
                  </p>
                </div>
                <span className="shrink-0 rounded border border-safe/30 bg-safe/10 px-2 py-1 font-mono text-[10px] uppercase tracking-wider text-safe">
                  Host
                </span>
              </div>
            </div>
          </Panel>

          <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-2">
            <Panel corners>
              <PanelHeader title="Registered Tools" icon={Wrench} />
              <div className="px-4 py-3">
                <div className="flex flex-wrap gap-2">
                  {status.tools.registered.map((tool) => (
                    <span
                      key={tool}
                      className={cn(
                        'rounded border border-border bg-background/60 px-2 py-1 font-mono text-xs text-foreground',
                      )}
                    >
                      {tool}
                    </span>
                  ))}
                </div>
              </div>
            </Panel>

            <Panel corners>
              <PanelHeader title="Deliverable Generators" icon={FileBox} />
              <div className="divide-y divide-border">
                {status.tools.deliverable_generators.map((gen) => {
                  const Icon = generatorIcons[gen.name] ?? FileBox
                  return (
                    <div key={gen.name} className="flex items-start gap-3 px-4 py-3">
                      <div className="flex size-8 shrink-0 items-center justify-center rounded-md bg-muted">
                        <Icon className="size-4 text-muted-foreground" />
                      </div>
                      <div className="min-w-0 flex-1">
                        <p className="font-mono text-sm font-semibold text-foreground">
                          {gen.name}
                          <span className="ml-2 rounded bg-muted px-1.5 py-0.5 font-mono text-[10px] font-normal text-muted-foreground">
                            {gen.file_type}
                          </span>
                        </p>
                        <p className="mt-0.5 text-xs text-muted-foreground">{gen.purpose}</p>
                      </div>
                    </div>
                  )
                })}
              </div>
            </Panel>
          </div>
        </>
      )}
    </PageContainer>
  )
}