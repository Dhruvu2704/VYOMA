import { cn } from '@/lib/utils'

/**
 * Panel — the base graphite surface used across the app.
 * Optional technical corner ticks give it an engineering-drawing feel.
 */
export function Panel({
  children,
  className,
  corners = false,
  elevated = false,
}: {
  children: React.ReactNode
  className?: string
  corners?: boolean
  elevated?: boolean
}) {
  return (
    <div
      className={cn(
        'relative rounded-md border border-border',
        elevated ? 'bg-card-elevated' : 'bg-card',
        className,
      )}
    >
      {corners && (
        <>
          <span className="pointer-events-none absolute left-0 top-0 size-2.5 border-l border-t border-primary/50" />
          <span className="pointer-events-none absolute right-0 top-0 size-2.5 border-r border-t border-primary/50" />
          <span className="pointer-events-none absolute bottom-0 left-0 size-2.5 border-b border-l border-primary/50" />
          <span className="pointer-events-none absolute bottom-0 right-0 size-2.5 border-b border-r border-primary/50" />
        </>
      )}
      {children}
    </div>
  )
}

export function PanelHeader({
  title,
  action,
  className,
  icon: Icon,
}: {
  title: string
  action?: React.ReactNode
  className?: string
  icon?: React.ComponentType<{ className?: string }>
}) {
  return (
    <div className={cn('flex items-center justify-between border-b border-border px-4 py-3', className)}>
      <div className="flex items-center gap-2">
        {Icon && <Icon className="size-4 text-muted-foreground" />}
        <h3 className="text-xs font-semibold uppercase tracking-widest text-muted-foreground">
          {title}
        </h3>
      </div>
      {action}
    </div>
  )
}
