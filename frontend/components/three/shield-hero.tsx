'use client'

import dynamic from 'next/dynamic'

const ShieldScene = dynamic(() => import('./shield-scene').then((m) => m.ShieldScene), {
  ssr: false,
  loading: () => (
    <div className="flex h-full w-full items-center justify-center">
      <div className="size-16 animate-status-pulse rounded-full bg-primary/20 ring-1 ring-primary/40" />
    </div>
  ),
})

export function ShieldHero({ className }: { className?: string }) {
  return (
    <div className={className}>
      <ShieldScene />
    </div>
  )
}
