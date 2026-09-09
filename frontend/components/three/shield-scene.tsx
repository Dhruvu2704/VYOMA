'use client'

import { useMemo, useRef } from 'react'
import { Canvas, useFrame } from '@react-three/fiber'
import { Icosahedron, Line, Torus } from '@react-three/drei'
import * as THREE from 'three'

const SAFE = '#3ad07f'
const INFO = '#4aa3ff'
const CORE = '#6bb8ff'

function ShieldCore() {
  const core = useRef<THREE.Mesh>(null)
  const wire = useRef<THREE.Mesh>(null)
  const outer = useRef<THREE.Mesh>(null)
  const scan = useRef<THREE.Group>(null)

  useFrame((state, delta) => {
    if (core.current) core.current.rotation.y += delta * 0.4
    if (wire.current) {
      wire.current.rotation.y -= delta * 0.15
      wire.current.rotation.x += delta * 0.05
    }
    if (outer.current) {
      outer.current.rotation.y += delta * 0.1
      const s = 1 + Math.sin(state.clock.elapsedTime * 1.2) * 0.02
      outer.current.scale.setScalar(s)
    }
    if (scan.current) scan.current.rotation.x += delta * 0.8
  })

  return (
    <group>
      {/* Glowing core */}
      <Icosahedron ref={core} args={[0.85, 1]}>
        <meshStandardMaterial
          color={CORE}
          emissive={INFO}
          emissiveIntensity={0.9}
          metalness={0.6}
          roughness={0.2}
          flatShading
        />
      </Icosahedron>

      {/* Inner wireframe shield */}
      <Icosahedron ref={wire} args={[1.35, 2]}>
        <meshBasicMaterial color={INFO} wireframe transparent opacity={0.35} />
      </Icosahedron>

      {/* Outer protective geodesic shell */}
      <Icosahedron ref={outer} args={[1.9, 3]}>
        <meshBasicMaterial color={SAFE} wireframe transparent opacity={0.14} />
      </Icosahedron>

      {/* Scanning rings */}
      <group ref={scan}>
        <Torus args={[1.9, 0.012, 12, 80]}>
          <meshBasicMaterial color={SAFE} transparent opacity={0.7} />
        </Torus>
        <Torus args={[1.9, 0.012, 12, 80]} rotation={[Math.PI / 2, 0, 0]}>
          <meshBasicMaterial color={INFO} transparent opacity={0.5} />
        </Torus>
      </group>
    </group>
  )
}

function OrbitParticles({ count = 60 }: { count?: number }) {
  const ref = useRef<THREE.Group>(null)
  const positions = useMemo(() => {
    const arr: [number, number, number][] = []
    for (let i = 0; i < count; i++) {
      const r = 2.2 + Math.random() * 0.6
      const theta = Math.random() * Math.PI * 2
      const phi = Math.acos(2 * Math.random() - 1)
      arr.push([
        r * Math.sin(phi) * Math.cos(theta),
        r * Math.sin(phi) * Math.sin(theta),
        r * Math.cos(phi),
      ])
    }
    return arr
  }, [count])

  useFrame((_, delta) => {
    if (ref.current) ref.current.rotation.y += delta * 0.06
  })

  return (
    <group ref={ref}>
      {positions.map((p, i) => (
        <mesh key={i} position={p}>
          <sphereGeometry args={[0.015, 6, 6]} />
          <meshBasicMaterial color={i % 3 === 0 ? SAFE : INFO} />
        </mesh>
      ))}
    </group>
  )
}

function LatitudeRing({ y, radius }: { y: number; radius: number }) {
  const points = useMemo(() => {
    const pts: [number, number, number][] = []
    for (let i = 0; i <= 64; i++) {
      const a = (i / 64) * Math.PI * 2
      pts.push([Math.cos(a) * radius, y, Math.sin(a) * radius])
    }
    return pts
  }, [y, radius])
  return <Line points={points} color={INFO} lineWidth={1} transparent opacity={0.18} />
}

export function ShieldScene() {
  return (
    <Canvas
      camera={{ position: [0, 0, 6], fov: 42 }}
      dpr={[1, 2]}
      gl={{ antialias: true, alpha: true }}
    >
      <ambientLight intensity={0.4} />
      <pointLight position={[4, 4, 4]} intensity={1.2} color={INFO} />
      <pointLight position={[-4, -2, -2]} intensity={0.6} color={SAFE} />
      <ShieldCore />
      <OrbitParticles />
      <LatitudeRing y={0.9} radius={1.68} />
      <LatitudeRing y={0} radius={1.9} />
      <LatitudeRing y={-0.9} radius={1.68} />
    </Canvas>
  )
}
