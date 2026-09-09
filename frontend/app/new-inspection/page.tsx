'use client'

import { useRef, useState } from 'react'
import { useRouter } from 'next/navigation'
import {
  FileText,
  Map,
  UploadCloud,
  CheckCircle2,
  X,
  Loader2,
  ShieldCheck,
  Cpu,
  ScanSearch,
  GitCompareArrows,
  ScrollText,
  Lock,
} from 'lucide-react'
import { PageContainer, PageHeader } from '@/components/page-header'
import { Panel, PanelHeader } from '@/components/panel'
import { cn } from '@/lib/utils'
import { useToast } from '@/components/toast'
import { createTask } from '@/lib/api'

interface FileState {
  name: string
  size: string
}

function UploadZone({
  index,
  title,
  supported,
  hint,
  icon: Icon,
  file,
  onSelect,
  onRemove,
}: {
  index: string
  title: string
  supported: string
  hint: string
  icon: React.ComponentType<{ className?: string }>
  file: FileState | null
  onSelect: (f: FileState) => void
  onRemove: () => void
}) {
  const [drag, setDrag] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)

  const handleFiles = (files: FileList | null) => {
    if (!files || files.length === 0) return
    const f = files[0]
    onSelect({ name: f.name, size: `${(f.size / 1024 / 1024).toFixed(1)} MB` })
  }

  return (
    <Panel corners className="flex flex-col">
      <PanelHeader
        title={`${index} — ${title}`}
        icon={Icon}
      />
      <div className="p-4">
        {file ? (
          <div className="flex items-center gap-3 rounded-md border border-safe/30 bg-safe/10 p-4 glow-safe">
            <CheckCircle2 className="size-6 shrink-0 text-safe" />
            <div className="min-w-0 flex-1">
              <p className="truncate font-mono text-sm text-foreground">{file.name}</p>
              <p className="text-xs text-muted-foreground">{file.size}</p>
            </div>
            <button
              onClick={onRemove}
              className="rounded p-1.5 text-muted-foreground transition-colors hover:bg-danger/15 hover:text-danger"
              aria-label={`Remove ${title} file`}
            >
              <X className="size-4" />
            </button>
          </div>
        ) : (
          <button
            type="button"
            onClick={() => inputRef.current?.click()}
            onDragOver={(e) => {
              e.preventDefault()
              setDrag(true)
            }}
            onDragLeave={() => setDrag(false)}
            onDrop={(e) => {
              e.preventDefault()
              setDrag(false)
              handleFiles(e.dataTransfer.files)
            }}
            className={cn(
              'flex w-full flex-col items-center justify-center gap-3 rounded-md border-2 border-dashed px-4 py-10 text-center transition-colors',
              drag
                ? 'border-primary bg-primary/10'
                : 'border-border bg-background/40 hover:border-primary/50 hover:bg-secondary/40',
            )}
          >
            <span
              className={cn(
                'flex size-12 items-center justify-center rounded-full border transition-colors',
                drag ? 'border-primary/50 bg-primary/15 text-primary' : 'border-border bg-secondary text-muted-foreground',
              )}
            >
              <UploadCloud className="size-6" />
            </span>
            <span className="text-sm font-medium text-foreground">{hint}</span>
            <span className="text-xs text-muted-foreground">or browse from your device</span>
            <span className="mt-1 font-mono text-[11px] uppercase tracking-wider text-muted-foreground">
              Supported: {supported}
            </span>
          </button>
        )}
        <input
          ref={inputRef}
          type="file"
          className="sr-only"
          onChange={(e) => handleFiles(e.target.files)}
        />
      </div>
    </Panel>
  )
}

const modules = [
  { label: 'Rule Validation', icon: ShieldCheck },
  { label: 'AI / LLM Analysis', icon: Cpu },
  { label: 'P&ID Analysis', icon: ScanSearch },
  { label: 'Safety Cross-Check', icon: GitCompareArrows },
  { label: 'Audit Logging', icon: ScrollText },
]

export default function NewInspectionPage() {
  const router = useRouter()
  const toast = useToast()
  const [ptw, setPtw] = useState<FileState | null>(null)
  const [pid, setPid] = useState<FileState | null>(null)
  const [starting, setStarting] = useState(false)

  const ready = ptw && pid

  const start = async () => {
    if (!ready) return
    setStarting(true)
    toast.push({ kind: 'info', title: 'Analysis started', message: 'Verification pipeline initializing…' })
    const { taskId } = await createTask()
    toast.push({ kind: 'success', title: 'Task created', message: taskId })
    router.push('/processing')
  }

  return (
    <PageContainer>
      <PageHeader
        title="New Safety Inspection"
        subtitle="Upload a Permit-to-Work and select the corresponding P&ID for automated verification."
      />

      <div className="grid gap-6 lg:grid-cols-2">
        <UploadZone
          index="01"
          title="Permit to Work"
          supported="PDF, DOCX"
          hint="Drop PTW file here"
          icon={FileText}
          file={ptw}
          onSelect={setPtw}
          onRemove={() => setPtw(null)}
        />
        <UploadZone
          index="02"
          title="P&ID Drawing"
          supported="PDF, PNG, JPG"
          hint="Drop P&ID drawing here"
          icon={Map}
          file={pid}
          onSelect={setPid}
          onRemove={() => setPid(null)}
        />
      </div>

      {/* Inspection summary */}
      <Panel className="mt-6" corners>
        <PanelHeader title="Inspection Summary" />
        <div className="grid gap-6 p-5 md:grid-cols-2">
          <dl className="space-y-3 text-sm">
            <SummaryRow label="Permit" value={ptw ? ptw.name.replace(/\.[^.]+$/, '') : '—'} />
            <SummaryRow label="P&ID" value={pid ? pid.name.replace(/\.[^.]+$/, '') : '—'} />
            <SummaryRow label="Inspection Type" value="Full Safety Verification" />
            <SummaryRow label="Officer" value="OFFICER-07" />
          </dl>
          <div>
            <p className="mb-3 text-xs font-semibold uppercase tracking-widest text-muted-foreground">
              Analysis Modules
            </p>
            <ul className="grid grid-cols-1 gap-2 sm:grid-cols-2">
              {modules.map((m) => {
                const Icon = m.icon
                return (
                  <li
                    key={m.label}
                    className="flex items-center gap-2 rounded border border-border bg-background/40 px-3 py-2 text-sm text-foreground"
                  >
                    <Icon className="size-4 text-safe" />
                    {m.label}
                  </li>
                )
              })}
            </ul>
          </div>
        </div>
      </Panel>

      {/* Start */}
      <div className="mt-6 flex flex-col items-center">
        <button
          onClick={start}
          disabled={!ready || starting}
          className={cn(
            'inline-flex w-full max-w-md items-center justify-center gap-2 rounded-md px-6 py-3.5 text-sm font-bold uppercase tracking-wide transition-all',
            ready
              ? 'bg-primary text-primary-foreground hover:bg-primary/90 glow-info'
              : 'cursor-not-allowed bg-secondary text-muted-foreground',
          )}
        >
          {starting ? (
            <>
              <Loader2 className="size-4 animate-spin" /> Initializing…
            </>
          ) : (
            <>
              <ShieldCheck className="size-4" /> Start Safety Analysis
            </>
          )}
        </button>
        <p className="mt-3 flex items-center gap-1.5 text-xs text-muted-foreground">
          <Lock className="size-3" />
          Your files remain within the controlled processing environment.
        </p>
      </div>
    </PageContainer>
  )
}

function SummaryRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between border-b border-border/60 pb-2">
      <dt className="text-muted-foreground">{label}</dt>
      <dd className="font-mono text-xs text-foreground">{value}</dd>
    </div>
  )
}
