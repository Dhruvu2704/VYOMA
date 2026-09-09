'use client'

import { useMemo, useRef } from 'react'
import { Canvas, useFrame } from '@react-three/fiber'
import { Line, RoundedBox, Text } from '@react-three/drei'
import * as THREE from 'three'

const SAFE = '#3ad07f'
const INFO = '#5bb0ff'
const DANGER = '#ff5a52'

const nodes = [
  { label: 'FRONTEND', y: 2.3 },
  { label: 'BACKEND', y: 0.8 },
  { label: 'AI AGENT', y: -0.7 },
  { label: 'LOCAL SVCS', y: -2.2 },
]
const NODE_X = -1.6

function Node({ y, label }: { y: number; label: string }) {
  return (
    <group position={[NODE_X, y, 0]}>
      <RoundedBox args={[2.6, 0.9, 0.4]} radius={0.08} smoothness={4}>
        <meshStandardMaterial
          color="#243244"
          emissive={INFO}
          emissiveIntensity={0.55}
          metalness={0.3}
          roughness={0.4}
        />
      </RoundedBox>
      <lineSegments>
        <edgesGeometry args={[new THREE.BoxGeometry(2.6, 0.9, 0.4)]} />
        <lineBasicMaterial color={INFO} transparent opacity={0.9} />
      </lineSegments>
      <Text position={[0, 0, 0.22]} fontSize={0.24} color="#ffffff" anchorX="center" anchorY="middle" letterSpacing={0.06}>
        {label}
      </Text>
    </group>
  )
}

function InternalFlow() {
  const packets = useRef<THREE.Mesh[]>([])
  const total = nodes.length - 1

  useFrame((state) => {
    const t = state.clock.elapsedTime
    packets.current.forEach((p, i) => {
      if (!p) return
      const local = (t * 0.45 + i / total) % 1
      const seg = Math.min(total - 1, Math.floor(local * total))
      const segT = local * total - seg
      const y = THREE.MathUtils.lerp(nodes[seg].y - 0.45, nodes[seg + 1].y + 0.45, segT)
      p.position.set(NODE_X, y, 0.4)
      const mat = p.material as THREE.MeshBasicMaterial
      mat.opacity = 0.6 + Math.sin(local * Math.PI) * 0.4
    })
  })

  return (
    <>
      <Line
        points={nodes.map((n) => [NODE_X, n.y, 0] as [number, number, number])}
        color={SAFE}
        lineWidth={2.5}
        transparent
        opacity={0.6}
      />
      {[0, 1, 2, 3, 4].map((i) => (
        <mesh key={i} ref={(el) => { if (el) packets.current[i] = el }}>
          <sphereGeometry args={[0.12, 16, 16]} />
          <meshBasicMaterial color={SAFE} transparent />
        </mesh>
      ))}
    </>
  )
}

function BlockedEgress() {
  const packet = useRef<THREE.Mesh>(null)
  const flash = useRef<THREE.Mesh>(null)
  const barrierX = 0.5
  const startX = NODE_X + 0.6

  useFrame((state) => {
    const t = (state.clock.elapsedTime * 0.55) % 1.4
    if (packet.current) {
      const p = Math.min(1, t / 0.7)
      const x = THREE.MathUtils.lerp(startX, barrierX, p)
      packet.current.position.set(x, 0.05, 0.45)
      const mat = packet.current.material as THREE.MeshBasicMaterial
      mat.opacity = t < 0.7 ? 1 : 0
    }
    if (flash.current) {
      const mat = flash.current.material as THREE.MeshBasicMaterial
      const show = t >= 0.63 && t < 0.9
      mat.opacity = show ? 0.9 : 0
      if (show) flash.current.scale.setScalar(1 + (t - 0.63) * 5)
    }
  })

  const wallPoints = useMemo(
    () => [
      [barrierX, 3.1, 0],
      [barrierX, -3.1, 0],
    ] as [number, number, number][],
    [],
  )

  return (
    <group>
      <mesh ref={packet}>
        <sphereGeometry args={[0.13, 16, 16]} />
        <meshBasicMaterial color={DANGER} transparent />
      </mesh>
      <mesh ref={flash} position={[barrierX, 0.05, 0.45]}>
        <ringGeometry args={[0.12, 0.22, 24]} />
        <meshBasicMaterial color={DANGER} transparent side={THREE.DoubleSide} />
      </mesh>

      <Line points={wallPoints} color={DANGER} lineWidth={3} dashed dashSize={0.18} gapSize={0.12} transparent opacity={0.95} />
      <mesh position={[barrierX, 0, -0.05]}>
        <planeGeometry args={[0.08, 6.2]} />
        <meshBasicMaterial color={DANGER} transparent opacity={0.14} side={THREE.DoubleSide} />
      </mesh>
      <Text position={[barrierX, 2.85, 0]} fontSize={0.2} color={DANGER} anchorX="center" letterSpacing={0.08}>
        EGRESS BLOCKED
      </Text>

      <group position={[2.5, 0, 0]}>
        <mesh>
          <icosahedronGeometry args={[0.7, 1]} />
          <meshStandardMaterial color="#3a1a1e" emissive={DANGER} emissiveIntensity={0.5} wireframe />
        </mesh>
        <Text position={[0, -1.15, 0]} fontSize={0.2} color="#e8b8b8" anchorX="center">
          EXTERNAL
        </Text>
        <Text position={[0, -1.45, 0]} fontSize={0.2} color="#e8b8b8" anchorX="center">
          INTERNET
        </Text>
      </group>
    </group>
  )
}

export function PacketFlowScene() {
  return (
    <Canvas camera={{ position: [0.3, 0, 7.6], fov: 44 }} dpr={[1, 2]} gl={{ antialias: true }}>
      <color attach="background" args={['#0d1219']} />
      <fog attach="fog" args={['#0d1219', 9, 16]} />
      <ambientLight intensity={1.1} />
      <pointLight position={[2, 3, 5]} intensity={2.2} color={INFO} />
      <pointLight position={[-4, -2, 4]} intensity={1.4} color={SAFE} />
      <pointLight position={[4, 0, 3]} intensity={1.2} color={DANGER} />
      {nodes.map((n) => (
        <Node key={n.label} y={n.y} label={n.label} />
      ))}
      <InternalFlow />
      <BlockedEgress />
    </Canvas>
  )
}
