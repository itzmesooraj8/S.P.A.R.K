import { Canvas } from '@react-three/fiber';
import { useRef, useMemo } from 'react';
import { useFrame } from '@react-three/fiber';
import * as THREE from 'three';

function Globe() {
  const meshRef = useRef<THREE.Mesh>(null);
  const wireRef = useRef<THREE.Mesh>(null);

  useFrame((_, delta) => {
    if (meshRef.current) meshRef.current.rotation.y += delta * 0.3;
    if (wireRef.current) wireRef.current.rotation.y += delta * 0.3;
  });

  const arcPoints = useMemo(() => {
    const connections = [
      { from: [40.7, -74], to: [51.5, 0] },
      { from: [35.7, 139.7], to: [22.3, 114.2] },
      { from: [48.9, 2.3], to: [55.8, 37.6] },
      { from: [-33.9, 151.2], to: [1.3, 103.8] },
      { from: [19.4, -99.1], to: [40.7, -74] },
    ];

    return connections.map(({ from, to }) => {
      const points: THREE.Vector3[] = [];
      const latFrom = (from[0] * Math.PI) / 180;
      const lonFrom = (from[1] * Math.PI) / 180;
      const latTo = (to[0] * Math.PI) / 180;
      const lonTo = (to[1] * Math.PI) / 180;

      for (let i = 0; i <= 30; i++) {
        const t = i / 30;
        const lat = latFrom + (latTo - latFrom) * t;
        const lon = lonFrom + (lonTo - lonFrom) * t;
        const r = 1.02 + Math.sin(t * Math.PI) * 0.15;
        points.push(new THREE.Vector3(
          r * Math.cos(lat) * Math.cos(lon),
          r * Math.sin(lat),
          r * Math.cos(lat) * Math.sin(lon),
        ));
      }
      return points;
    });
  }, []);

  return (
    <group>
      {/* Earth sphere */}
      <mesh ref={meshRef}>
        <sphereGeometry args={[1, 64, 64]} />
        <meshStandardMaterial
          color="#001a33"
          emissive="#003366"
          emissiveIntensity={0.3}
          wireframe={false}
        />
      </mesh>

      {/* Wireframe overlay */}
      <mesh ref={wireRef}>
        <sphereGeometry args={[1.01, 32, 32]} />
        <meshBasicMaterial color="#00f5ff" wireframe opacity={0.15} transparent />
      </mesh>

      {/* Connection arcs */}
      {arcPoints.map((points, i) => {
        const curve = new THREE.CatmullRomCurve3(points);
        const tubeGeom = new THREE.TubeGeometry(curve, 30, 0.005, 8, false);
        return (
          <mesh key={i} geometry={tubeGeom}>
            <meshBasicMaterial color="#00f5ff" transparent opacity={0.7} />
          </mesh>
        );
      })}

      {/* Atmosphere glow */}
      <mesh>
        <sphereGeometry args={[1.08, 32, 32]} />
        <meshBasicMaterial color="#003366" transparent opacity={0.1} side={THREE.BackSide} />
      </mesh>

      {/* Pole indicators */}
      <mesh position={[0, 1.05, 0]}>
        <sphereGeometry args={[0.015, 8, 8]} />
        <meshBasicMaterial color="#ff3b3b" />
      </mesh>
      <mesh position={[0, -1.05, 0]}>
        <sphereGeometry args={[0.015, 8, 8]} />
        <meshBasicMaterial color="#00f5ff" />
      </mesh>
    </group>
  );
}

export default function GlobeVisualization() {
  return (
    <div className="relative w-full h-full">
      <Canvas camera={{ position: [0, 0, 2.8], fov: 45 }}>
        <ambientLight intensity={0.3} />
        <directionalLight position={[5, 3, 5]} intensity={1} color="#00f5ff" />
        <pointLight position={[-5, -3, -5]} intensity={0.5} color="#0066ff" />
        <Globe />
      </Canvas>
      {/* Overlay labels */}
      <div className="absolute top-2 left-2 font-orbitron text-[8px] text-hud-cyan/60">GLOBAL NETWORK</div>
      <div className="absolute bottom-2 right-2 font-mono-tech text-[8px] text-hud-cyan/40">LIVE TRACKING</div>
      {/* Scan line */}
      <div className="absolute inset-0 pointer-events-none"
        style={{ background: 'repeating-linear-gradient(0deg, transparent, transparent 2px, rgba(0,245,255,0.02) 2px, rgba(0,245,255,0.02) 4px)' }} />
    </div>
  );
}
