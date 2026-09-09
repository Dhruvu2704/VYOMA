'use client'

import dynamic from 'next/dynamic'
import { Network } from 'lucide-react'

const PacketFlowScene = dynamic(
  () => import('./packet-flow-scene').then((m) => m.PacketFlowScene),
  {
    ssr: false,
    loading: () => (
      <div className="flex h-full w-full items-center justify-center">
        <div className="flex items-center gap-2 text-muted-foreground">
          <Network className="size-4 animate-pulse" />
          <span className="font-mono text-xs uppercase tracking-widest">
            Initializing secure topology…
          </span>
        </div>
      </div>
    ),
  },
)

export function PacketFlow() {
  return (
    <div className="relative h-[420px] w-full bg-[#0d1219]">
      <PacketFlowScene />
    </div>
  )
}
