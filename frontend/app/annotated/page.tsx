'use client'

import { useEffect, useRef, useState } from 'react'
import Image from 'next/image'
import { Minus, Plus, Maximize2, Scan, Download, MapPin, Loader2 } from 'lucide-react'
import { PageContainer, PageHeader } from '@/components/page-header'
import { Panel, PanelHeader } from '@/components/panel'
import { StatusBadge } from '@/components/status-badge'
import { cn } from '@/lib/utils'
import { useToast } from '@/components/toast'
import { getDeliverables, downloadDeliverable, isAuthed } from '@/lib/api'
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
  const [annotatedName, setAnnotatedName] = useState<string | null>(null)
  const [downloading, setDownloading] = useState(false)
  const viewerRef = useRef<HTMLDivElement>(null)

  const clampZoom = (z: number) => Math.max(50, Math.min(200, z))

  useEffect(() => {
    const taskId = sessionStorage.getItem('vyoma_task_id')
    if (!taskId || !isAuthed()) return
    getDeliverables(taskId)
      .then((response) => {
        const pdf = response.deliverables.find((d) => d.file_type === 'ANNOTATED_PDF')
        if (pdf) setAnnotatedName(pdf.filename)
      })
      .catch(() => setAnnotatedName(null))
  }, [])

  const download = async () => {
    const taskId = sessionStorage.getItem('vyoma_task_id')
    if (!taskId) {
      toast.push({ kind: 'warning', title: 'No task selected', message: 'Upload and process a permit before exporting.' })
      return
    }
    if (!isAuthed()) {
      toast.push({ kind: 'warning', title: 'Sign in required', message: 'Sign in to the local backend to export deliverables.' })
      return
    }
    if (!annotatedName) {
      toast.push({
        kind: 'error',
        title: 'No annotated export yet',
        message: 'This task has no annotated P&ID deliverable. Processes with a P&ID envelope generate one.',
      })
      return
    }
    setDownloading(true)
    try {
      await downloadDeliverable(taskId, annotatedName)
      toast.push({ kind: 'success', title: 'Export downloaded', message: annotatedName })
    } catch (error) {
      toast.push({
        kind: 'error',
        title: 'Download failed',
        message: error instanceof Error ? error.message : 'The export could not be downloaded.',
      })
    } finally {
      setDownloading(false)
    }
  }

  const toggleFullscreen = () => {
    if (document.fullscreenElement) {
      void document.exitFullscreen().catch(() => {})
      return
    }
    viewerRef.current?.requestFullscreen?.().catch(() =>
      toast.push({ kind: 'info', title: 'Fullscreen unavailable', message: 'Your browser blocked fullscreen for this viewer.' }),
    )
  }

  return (
    <PageContainer>
      <PageHeader
        title="Annotated P&ID"
        subtitle="Safety-relevant areas identified during analysis."
        action={
          <button
            onClick={download}
            disabled={downloading}
            className="inline-flex items-center gap-2 rounded-md bg-primary px-4 py-2.5 text-sm font-semibold text-primary-foreground transition-colors hover:bg-primary/90 disabled:opacity-60"
          >
            {downloading ? <Loader2 className="size-4 animate-spin" /> : <Download className="size-4" />}
            Download Annotated P&ID
          </button>
        }
      />

      <div className="grid gap-6 lg:grid-cols-[1fr_320px]">
        {/* Viewer */}
        <Panel corners className="overflow-hidden">
          <div className="flex items-center justify-between border-b border-border px-3 py-2">
            <span className="font-mono text-xs text-muted-foreground">{annotatedName ?? 'Unit_A_PID.pdf'}</span>
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
                onClick={toggleFullscreen}
                className="flex items-center gap-1 rounded px-2 py-1.5 text-xs text-muted-foreground transition-colors hover:bg-secondary hover:text-foreground"
              >
                <Maximize2 className="size-4" /> Fullscreen
              </button>
            </div>
          </div>

          <div className="relative aspect-[4/3] w-full overflow-auto bg-background">
            <div
              ref={viewerRef}
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
