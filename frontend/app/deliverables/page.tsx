'use client'

import Link from 'next/link'
import { FileText, FileSpreadsheet, FileType2, Map, Download, Eye, Clock } from 'lucide-react'
import { PageContainer, PageHeader } from '@/components/page-header'
import { Panel } from '@/components/panel'
import { useToast } from '@/components/toast'
import { deliverables } from '@/lib/mock-data'
import { cn } from '@/lib/utils'

const iconMap: Record<string, { icon: typeof FileText; tone: string }> = {
  docx: { icon: FileText, tone: 'border-info/40 bg-info/10 text-info' },
  xlsx: { icon: FileSpreadsheet, tone: 'border-safe/40 bg-safe/10 text-safe' },
  pdf: { icon: FileType2, tone: 'border-danger/40 bg-danger/10 text-danger' },
  pid: { icon: Map, tone: 'border-warning/40 bg-warning/10 text-warning' },
}

export default function DeliverablesPage() {
  const toast = useToast()

  return (
    <PageContainer>
      <PageHeader
        title="Inspection Deliverables"
        subtitle="Generated reports and analysis outputs for task-2026-0512."
      />

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {deliverables.map((d) => {
          const { icon: Icon, tone } = iconMap[d.id]
          return (
            <Panel key={d.id} corners className="flex flex-col p-5 transition-colors hover:bg-card-elevated">
              <div className={cn('flex size-12 items-center justify-center rounded-md border', tone)}>
                <Icon className="size-6" />
              </div>
              <h3 className="mt-4 text-base font-semibold text-foreground">{d.title}</h3>
              <p className="mt-1 text-sm text-muted-foreground">{d.desc}</p>

              <dl className="mt-4 space-y-1.5 border-t border-border pt-3 font-mono text-xs">
                <div className="flex justify-between">
                  <dt className="text-muted-foreground">Type</dt>
                  <dd className="text-foreground">{d.type}</dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-muted-foreground">Size</dt>
                  <dd className="text-foreground">{d.size}</dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-muted-foreground">Generated</dt>
                  <dd className="flex items-center gap-1 text-foreground">
                    <Clock className="size-3" /> {d.generated}
                  </dd>
                </div>
              </dl>

              <div className="mt-4 flex gap-2">
                {d.action === 'view' && (
                  <Link
                    href="/annotated"
                    className="flex flex-1 items-center justify-center gap-1.5 rounded-md border border-border bg-secondary py-2 text-xs font-medium text-foreground transition-colors hover:bg-accent"
                  >
                    <Eye className="size-3.5" /> View
                  </Link>
                )}
                <button
                  onClick={() =>
                    toast.push({
                      kind: 'success',
                      title: 'Download started',
                      message: `${d.title} (${d.type})`,
                    })
                  }
                  className="flex flex-1 items-center justify-center gap-1.5 rounded-md bg-primary py-2 text-xs font-semibold text-primary-foreground transition-colors hover:bg-primary/90"
                >
                  <Download className="size-3.5" /> {d.type}
                </button>
              </div>
            </Panel>
          )
        })}
      </div>

      <Panel className="mt-6 flex flex-col items-start gap-3 p-5 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="text-sm font-medium text-foreground">Bundle export</p>
          <p className="text-xs text-muted-foreground">
            Download all deliverables as a single signed archive with audit manifest.
          </p>
        </div>
        <button
          onClick={() => toast.push({ kind: 'info', title: 'Preparing bundle', message: 'Signing archive…' })}
          className="inline-flex items-center gap-2 rounded-md border border-border bg-secondary px-4 py-2.5 text-sm font-medium text-foreground transition-colors hover:bg-accent"
        >
          <Download className="size-4" /> Download All (.zip)
        </button>
      </Panel>
    </PageContainer>
  )
}
