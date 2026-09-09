'use client'

import { useState } from 'react'
import Image from 'next/image'
import { Minus, Plus, Maximize2, Scan, Download, MapPin } from 'lucide-react'
import { PageContainer, PageHeader } from '@/components/page-header'
import { Panel, PanelHeader } from '@/components/panel'
import { StatusBadge } from '@/components/status-badge'
import { cn } from '@/lib/utils'
import { useToast } from '@/components/toast'
import { annotations } from '@/lib/mock-data'

const severityRing: Record<string, string> = {
  HIGH: 'border-danger bg-danger/15 text-danger',
  MEDIUM: 'border-warning bg-warning/15 text-warning',
  LOW: 'border-info bg-info/15 text-info',
}

export default function AnnotatedPage() {
  const toast = useToast()
  const [zoom, setZoom] = useState(100)
  const [active, setActive] = useState<number | null>(1)

  const clampZoom = (z: number) => Math.max(50, Math.min(200, z))

  return (
    <PageContainer>
      <PageHeader
        title="Annotated P&ID"
        subtitle="Safety-relevant areas identified during analysis."
        action={
          <button
            onClick={() => toast.push({ kind: 'info', title: 'Download started', message: 'Annotated P&ID export' })}
            className="inline-flex items-center gap-2 rounded-md bg-primary px-4 py-2.5 text-sm font-semibold text-primary-foreground transition-colors hover:bg-primary/90"
          >
            <Download className="size-4" /> Download Annotated P&ID
          </button>
        }
      />

      <div className="grid gap-6 lg:grid-cols-[1fr_320px]">
        {/* Viewer */}
        <Panel corners className="overflow-hidden">
          <div className="flex items-center justify-between border-b border-border px-3 py-2">
            <span className="font-mono text-xs text-muted-foreground">Unit_A_PID.pdf</span>
            <div className="flex items-center gap-1">
              <button
                onClick={() => setZoom((z) => clampZoom(z - 10))}
                className="rounded p-1.5 text-muted-foreground transition-colors hover:bg-secondary hover:text-foreground"
                aria-label="Zoom out"
              >
                <Minus className="size-4" />
              </button>
              <span className="w-16 text-center font-mono text-xs text-foreground">Zoom {zoom}%</span>
              <button
                onClick={() => setZoom((z) => clampZoom(z + 10))}
                className="rounded p-1.5 text-muted-foreground transition-colors hover:bg-secondary hover:text-foreground"
                aria-label="Zoom in"
              >
                <Plus className="size-4" />
              </button>
              <span className="mx-1 h-5 w-px bg-border" />
              <button
                onClick={() => setZoom(100)}
                className="flex items-center gap-1 rounded px-2 py-1.5 text-xs text-muted-foreground transition-colors hover:bg-secondary hover:text-foreground"
              >
                <Scan className="size-4" /> Fit
              </button>
              <button
                className="flex items-center gap-1 rounded px-2 py-1.5 text-xs text-muted-foreground transition-colors hover:bg-secondary hover:text-foreground"
              >
                <Maximize2 className="size-4" /> Fullscreen
              </button>
            </div>
          </div>

          <div className="relative aspect-[4/3] w-full overflow-auto bg-background">
            <div
              className="relative mx-auto h-full origin-center transition-transform duration-200"
              style={{ transform: `scale(${zoom / 100})` }}
            >
              <Image
                src="/pid-drawing.png"
                alt="P&ID engineering drawing of Unit A crude distillation, with safety-relevant regions marked"
                fill
                className="object-contain"
                priority
              />

              {/* Annotation regions */}
              {annotations.map((a) => (
                <button
                  key={a.id}
                  onClick={() => setActive(a.id)}
                  className={cn(
                    'absolute rounded border-2 transition-all',
                    severityRing[a.severity],
                    active === a.id ? 'opacity-100 ring-2 ring-offset-2 ring-offset-background' : 'opacity-60 hover:opacity-90',
                  )}
                  style={{
                    left: `${a.x}%`,
                    top: `${a.y}%`,
                    width: `${a.w}%`,
                    height: `${a.h}%`,
                  }}
                  aria-label={`Annotation ${a.id}: ${a.label}`}
                >
                  <span className="absolute -left-2 -top-2 flex size-5 items-center justify-center rounded-full border border-current bg-background font-mono text-[10px] font-bold">
                    {a.id}
                  </span>
                </button>
              ))}
            </div>
          </div>
        </Panel>

        {/* Annotations list */}
        <Panel className="h-fit">
          <PanelHeader title="Annotations" icon={MapPin} />
          <ul className="divide-y divide-border">
            {annotations.map((a) => (
              <li key={a.id}>
                <button
                  onClick={() => setActive(a.id)}
                  className={cn(
                    'w-full p-4 text-left transition-colors',
                    active === a.id ? 'bg-secondary/60' : 'hover:bg-secondary/30',
                  )}
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className="flex items-center gap-2 text-sm font-medium text-foreground">
                      <span
                        className={cn(
                          'flex size-5 items-center justify-center rounded-full border font-mono text-[10px] font-bold',
                          severityRing[a.severity],
                        )}
                      >
                        {a.id}
                      </span>
                      {a.label}
                    </span>
                    <StatusBadge value={a.severity} size="sm" />
                  </div>
                  {active === a.id && (
                    <p className="mt-2 pl-7 text-xs leading-relaxed text-muted-foreground">
                      {a.detail}
                    </p>
                  )}
                </button>
              </li>
            ))}
          </ul>
        </Panel>
      </div>
    </PageContainer>
  )
}
