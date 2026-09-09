import { cn } from '@/lib/utils'
import {
  ShieldCheck,
  ShieldAlert,
  ShieldX,
  Loader2,
  Check,
  X,
  AlertTriangle,
  type LucideIcon,
} from 'lucide-react'

type Tone = 'safe' | 'danger' | 'warning' | 'info' | 'muted'

const toneClasses: Record<Tone, string> = {
  safe: 'border-safe/30 bg-safe/10 text-safe',
  danger: 'border-danger/30 bg-danger/10 text-danger',
  warning: 'border-warning/30 bg-warning/10 text-warning',
  info: 'border-info/30 bg-info/10 text-info',
  muted: 'border-border bg-muted text-muted-foreground',
}

// Map a domain value to a tone + icon + label
const map: Record<string, { tone: Tone; icon: LucideIcon; label: string }> = {
  SAFE: { tone: 'safe', icon: ShieldCheck, label: 'SAFE' },
  VERIFIED: { tone: 'safe', icon: Check, label: 'VERIFIED' },
  APPROVED: { tone: 'safe', icon: ShieldCheck, label: 'APPROVED' },
  ACTIVE: { tone: 'safe', icon: Check, label: 'ACTIVE' },
  AGREE: { tone: 'safe', icon: Check, label: 'AGREE' },
  HEALTHY: { tone: 'safe', icon: Check, label: 'HEALTHY' },
  UP: { tone: 'safe', icon: Check, label: 'UP' },

  FLAGGED: { tone: 'danger', icon: ShieldAlert, label: 'FLAGGED' },
  REJECTED: { tone: 'danger', icon: ShieldX, label: 'REJECTED' },
  BLOCKED: { tone: 'danger', icon: X, label: 'BLOCKED' },
  HIGH: { tone: 'danger', icon: AlertTriangle, label: 'HIGH' },

  REVIEW: { tone: 'warning', icon: AlertTriangle, label: 'REVIEW' },
  DISAGREE: { tone: 'warning', icon: AlertTriangle, label: 'DISAGREE' },
  PENDING: { tone: 'warning', icon: AlertTriangle, label: 'PENDING' },
  MEDIUM: { tone: 'warning', icon: AlertTriangle, label: 'MEDIUM' },

  PROCESSING: { tone: 'info', icon: Loader2, label: 'PROCESSING' },
  ENFORCED: { tone: 'info', icon: ShieldCheck, label: 'ENFORCED' },
  MONITORED: { tone: 'info', icon: Check, label: 'MONITORED' },
  LOW: { tone: 'info', icon: Check, label: 'LOW' },
}

export function StatusBadge({
  value,
  className,
  size = 'md',
}: {
  value: string
  className?: string
  size?: 'sm' | 'md'
}) {
  const entry = map[value] ?? { tone: 'muted' as Tone, icon: Check, label: value }
  const Icon = entry.icon
  const spin = value === 'PROCESSING'
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 rounded border font-mono font-medium uppercase tracking-wide',
        size === 'sm' ? 'px-1.5 py-0.5 text-[10px]' : 'px-2 py-1 text-xs',
        toneClasses[entry.tone],
        className,
      )}
    >
      <Icon className={cn(size === 'sm' ? 'size-3' : 'size-3.5', spin && 'animate-spin')} aria-hidden />
      {entry.label}
    </span>
  )
}

export function StatusDot({
  tone = 'safe',
  pulse = true,
  className,
}: {
  tone?: Tone
  pulse?: boolean
  className?: string
}) {
  const dotColor: Record<Tone, string> = {
    safe: 'bg-safe',
    danger: 'bg-danger',
    warning: 'bg-warning',
    info: 'bg-info',
    muted: 'bg-muted-foreground',
  }
  return (
    <span className={cn('relative inline-flex size-2 items-center justify-center', className)}>
      {pulse && (
        <span
          className={cn('absolute inline-flex size-2 rounded-full opacity-60 animate-ping', dotColor[tone])}
        />
      )}
      <span className={cn('relative inline-flex size-2 rounded-full', dotColor[tone])} />
    </span>
  )
}
