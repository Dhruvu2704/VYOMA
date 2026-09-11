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
import { getCurrentUser, isAuthed, uploadTask } from '@/lib/api'
import { openAuth } from '@/components/auth-modal'

interface FileState {
  file: File
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
    onSelect({ file: f, name: f.name, size: `${(f.size / 1024 / 1024).toFixed(1)} MB` })
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
  const [starting, setStarting] = useState(false)

  const officer = getCurrentUser()
  const ready = ptw !== null && ptw.file.name.toLowerCase().endsWith('.json')

  const start = async () => {
    if (!ready) return

    if (!isAuthed()) {
      openAuth()
      return
    }

    setStarting(true)

    toast.push({
      kind: 'info',
      title: 'Analysis started',
      message: 'Verification pipeline initializing…',
    })

    try {
      const result = await uploadTask(ptw.file)

      toast.push({
        kind: 'success',
        title: 'Task created',
        message: result.task_id,
      })

      sessionStorage.setItem('vyoma_task_id', result.task_id)
      router.push('/processing')
    } catch (error) {
      toast.push({
        kind: 'error',
        title: 'Upload failed',
        message: error instanceof Error ? error.message : 'File upload failed.',
      })
    } finally {
      setStarting(false)
    }
  }

  return (
    <PageContainer>
      <PageHeader
        title="New Safety Inspection"
        subtitle="Upload a Permit-to-Work contract envelope for automated verification against the local KAVACH pipeline."
      />

      {!officer && (
        <div className="mb-6 flex flex-wrap items-center justify-between gap-3 rounded-md border border-warning/40 bg-warning/5 px-4 py-3">
          <p className="text-sm text-foreground">
            Sign in to the local backend before submitting an envelope for verification.
          </p>
          <button
            onClick={openAuth}
            className="inline-flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground transition-colors hover:bg-primary/90"
          >
            Sign In
          </button>
        </div>
      )}

      <div className="grid gap-6 lg:grid-cols-2">
        <UploadZone
          index="01"
          title="Permit to Work"
          supported="JSON (KAVACH envelope)"
          hint="Drop PTW contract envelope here"
          icon={FileText}
          file={ptw}
          onSelect={setPtw}
          onRemove={() => setPtw(null)}
        />
        <Panel corners className="flex flex-col gap-4 p-4">
          <PanelHeader title="02 — P&ID Drawing" icon={Map} />
          <div className="flex items-start gap-3 rounded-md border border-border bg-background/40 p-4">
            <ScanSearch className="mt-0.5 size-5 shrink-0 text-primary" />
            <div>
              <p className="text-sm font-medium text-foreground">Included in the contract envelope</p>
              <p className="mt-1 text-xs leading-relaxed text-muted-foreground">
                The P&ID topology (structured_pid) travels inside the PTW envelope JSON — no separate
                drawing upload is required. The pipeline cross-checks permit work zones against the
                diagram automatically.
              </p>
            </div>
          </div>
        </Panel>
      </div>

      {/* Inspection summary */}
      <Panel className="mt-6" corners>
        <PanelHeader title="Inspection Summary" />
        <div className="grid gap-6 p-5 md:grid-cols-2">
          <dl className="space-y-3 text-sm">
            <SummaryRow label="Permit" value={ptw ? ptw.name.replace(/\.[^.]+$/, '') : '—'} />
            <SummaryRow label="P&ID" value="Included in envelope" />
            <SummaryRow label="Inspection Type" value="Full Safety Verification" />
            <SummaryRow label="Officer" value={officer ? officer.toUpperCase() : 'NOT SIGNED IN'} />
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
          Envelopes stay within the controlled local processing environment.
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
