import { Suspense, useEffect, useMemo, useRef, useState } from "react";
import * as THREE from "three";
import { Canvas, useFrame, useThree } from "@react-three/fiber";
import { Html, Stars } from "@react-three/drei";
import type { PerspectiveCamera } from "three";
import { SeamlessBackdrop } from "./SeamlessBackdrop";
import { useIntroMotion } from "./useIntroMotion";
import { usePageVisibility } from "./usePageVisibility";
import { advanceSpring } from "../lib/spring";
import { useIntroChoreography } from "./useIntroChoreography";
import { IntroDepthForeground } from "./IntroDepthForeground";
import "../styles/intro-depth.css";

const VIDEO_URL =
  "https://d8j0ntlcm91z4.cloudfront.net/user_38xzZboKViGWJOttwIXH07lWA1P/hf_20260806_133255_956f653f-5d80-4b06-abd5-0f46c98b60fa.mp4";
const POSTER_URL =
  "https://d8j0ntlcm91z4.cloudfront.net/user_38xzZboKViGWJOttwIXH07lWA1P/hf_20260806_132328_5f9029c8-218f-4489-82b6-29ff2849920e.png";

const RING_RADIUS = 3.4;
const BASE_Z = 8.2;
const BASE_FOV = 46;
const IDLE_SPIN = 0.2;
const RING_COUNT = 3;
const PER_RING = 10;
const STAGES = 5;

const SERIF = '"Cormorant Garamond", Georgia, "Times New Roman", serif';

type Greeting = { text: string; lang: string; region: string };

const GREETINGS: Greeting[] = [
  { text: "Hello", lang: "English", region: "United Kingdom" },
  { text: "你好", lang: "Chinese", region: "Mandarin · China" },
  { text: "Hola", lang: "Spanish", region: "Spain" },
  { text: "Bonjour", lang: "French", region: "France" },
  { text: "Hallo", lang: "German", region: "Germany" },
  { text: "Ciao", lang: "Italian", region: "Italy" },
  { text: "Olá", lang: "Portuguese", region: "Portugal" },
  { text: "Привет", lang: "Russian", region: "Russia" },
  { text: "こんにちは", lang: "Japanese", region: "Japan" },
  { text: "안녕하세요", lang: "Korean", region: "South Korea" },
  { text: "مرحبا", lang: "Arabic", region: "Saudi Arabia" },
  { text: "नमस्ते", lang: "Hindi", region: "India" },
  { text: "Merhaba", lang: "Turkish", region: "Türkiye" },
  { text: "Selamat pagi", lang: "Malay", region: "Malaysia" },
  { text: "Halo", lang: "Indonesian", region: "Indonesia" },
  { text: "Hej", lang: "Swedish", region: "Sweden" },
  { text: "Hei", lang: "Norwegian", region: "Norway" },
  { text: "Dav", lang: "Danish", region: "Denmark" },
  { text: "Moi", lang: "Finnish", region: "Finland" },
  { text: "Cześć", lang: "Polish", region: "Poland" },
  { text: "Ahoj", lang: "Czech", region: "Czechia" },
  { text: "Szia", lang: "Hungarian", region: "Hungary" },
  { text: "Bună", lang: "Romanian", region: "Romania" },
  { text: "Здравей", lang: "Bulgarian", region: "Bulgaria" },
  { text: "Γεια σου", lang: "Greek", region: "Greece" },
  { text: "שלום", lang: "Hebrew", region: "Israel" },
  { text: "สวัสดี", lang: "Thai", region: "Thailand" },
  { text: "Xin chào", lang: "Vietnamese", region: "Vietnam" },
  { text: "Kumusta", lang: "Filipino", region: "Philippines" },
  { text: "Jambo", lang: "Swahili", region: "Kenya" },
];

const RING_TILTS: [number, number, number][] = [
  [0.05, 0, 0.12],
  [Math.PI / 3, 0, 0.42],
  [-Math.PI / 4, 0.3, -0.5],
];

const damp = THREE.MathUtils.damp;
const clamp = THREE.MathUtils.clamp;

type Node = { greeting: Greeting; ring: number; index: number; angle: number };

function buildNodes(): Node[][] {
  const rings: Node[][] = Array.from({ length: RING_COUNT }, () => []);
  GREETINGS.forEach((greeting, i) => {
    const ring = i % RING_COUNT;
    const index = rings[ring].length;
    const angle = (index / PER_RING) * Math.PI * 2;
    rings[ring].push({ greeting, ring, index, angle });
  });
  return rings;
}

type SceneProps = {
  htmlPortal: React.RefObject<HTMLDivElement | null>;
  rings: Node[][];
  orbit: React.RefObject<THREE.Group | null>;
  spin: React.RefObject<number>;
  target: React.RefObject<number>;
  push: React.RefObject<number>;
  spinImpulse: React.RefObject<number>;
  pushImpulse: React.RefObject<number>;
  labelRefs: React.RefObject<(HTMLDivElement | null)[]>;
  anchorRefs: React.RefObject<(THREE.Group | null)[]>;
  hovered: number | null;
  setHovered: React.Dispatch<React.SetStateAction<number | null>>;
};

function Scene({
  htmlPortal,
  rings,
  orbit,
  spin,
  target,
  push,
  spinImpulse,
  pushImpulse,
  labelRefs,
  anchorRefs,
  hovered,
  setHovered,
  motionPaused,
  pointer,
}: SceneProps & {
  motionPaused: boolean;
  pointer: React.RefObject<{ x: number; y: number }>;
}) {
  const { camera } = useThree();
  const worldPos = useMemo(() => new THREE.Vector3(), []);
  const motionTime = useRef(0);
  const hoverSprings = useMemo(
    () => rings.flat().map(() => ({ value: 1, velocity: 0 })),
    [rings],
  );

  useFrame((_, rawDt) => {
    const dt = Math.min(rawDt, 0.05);
    if (!motionPaused) {
      motionTime.current += dt;
      target.current = clamp(target.current + spinImpulse.current, -3.2, 3.2);
      spinImpulse.current = 0;
      target.current = damp(target.current, IDLE_SPIN, 1.1, dt);
      spin.current = damp(
        spin.current,
        hovered === null ? target.current : IDLE_SPIN * 0.35,
        3.2,
        dt,
      );
      if (orbit.current) {
        orbit.current.rotation.y += spin.current * dt;
        orbit.current.rotation.x =
          0.18 + Math.sin(motionTime.current * 0.38) * 0.1;
        orbit.current.rotation.z = Math.sin(motionTime.current * 0.3) * 0.07;
      }
    }
    push.current = motionPaused
      ? 0
      : damp(push.current + pushImpulse.current, 0, 2.2, dt);
    pushImpulse.current = 0;
    const cam = camera as PerspectiveCamera;
    cam.position.x = pointer.current.x * 0.22;
    cam.position.y = -pointer.current.y * 0.14;
    cam.lookAt(0, 0, 0);
    cam.position.z = damp(cam.position.z, BASE_Z - push.current, 4, dt);
    const fov = BASE_FOV + push.current * 4;
    if (Math.abs(cam.fov - fov) > 0.01) {
      cam.fov = damp(cam.fov, fov, 4, dt);
      cam.updateProjectionMatrix();
    }
    const anchors = anchorRefs.current;
    const labels = labelRefs.current;
    if (anchors && labels) {
      for (let i = 0; i < anchors.length; i++) {
        const a = anchors[i];
        const el = labels[i];
        if (!a || !el) continue;
        a.getWorldPosition(worldPos);
        const t = clamp((worldPos.z / RING_RADIUS + 1) / 2, 0, 1);
        const op = 0.14 + 0.86 * t;
        el.style.opacity = String(op);
        el.style.pointerEvents = op < 0.4 ? "none" : "auto";
        const face = el.firstElementChild as HTMLElement | null;
        const scale = advanceSpring(
          hoverSprings[i],
          hovered === i ? 1.35 : 1,
          dt,
          240,
          17,
        );
        if (face) face.style.transform = `scale(${scale})`;
      }
    }
  });

  let flat = -1;
  return (
    <>
      <Stars
        radius={70}
        depth={40}
        count={2600}
        factor={3}
        saturation={0}
        fade
        speed={motionPaused ? 0 : 1.5}
      />
      <group ref={orbit} rotation={[0.18, 0, 0]}>
        {rings.map((ring, r) => (
          <group key={r} rotation={RING_TILTS[r]}>
            <mesh rotation={[Math.PI / 2, 0, 0]}>
              <torusGeometry args={[RING_RADIUS, 0.004, 6, 160]} />
              <meshBasicMaterial
                color="#7fe9c0"
                transparent
                opacity={0.08}
                toneMapped={false}
              />
            </mesh>
            {ring.map((node) => {
              const i = ++flat;
              const x = Math.cos(node.angle) * RING_RADIUS;
              const z = Math.sin(node.angle) * RING_RADIUS;
              const active = hovered === i;
              return (
                <group
                  key={i}
                  position={[x, 0, z]}
                  ref={(el) => {
                    anchorRefs.current![i] = el;
                  }}
                >
                  <Html
                    portal={htmlPortal as React.RefObject<HTMLElement>}
                    center
                    distanceFactor={6.5}
                    zIndexRange={[20, 0]}
                    style={{ pointerEvents: "none" }}
                  >
                    <div
                      data-greeting=""
                      ref={(el) => {
                        labelRefs.current![i] = el;
                      }}
                      onPointerEnter={() => setHovered(i)}
                      onPointerLeave={() =>
                        setHovered((h) => (h === i ? null : h))
                      }
                      style={{
                        pointerEvents: "auto",
                      }}
                      className="cursor-pointer text-center will-change-transform"
                    >
                      <div
                        style={{
                          transform: "scale(1)",
                          transition: "color .3s ease, text-shadow .3s ease",
                          color: active ? "#ffffff" : "rgba(226,235,233,0.9)",
                          textShadow: active
                            ? "0 0 22px rgba(165,230,199,0.85)"
                            : "0 2px 14px rgba(3,7,12,0.9)",
                          fontSize: "21px",
                          fontWeight: 400,
                          lineHeight: 1.1,
                          whiteSpace: "nowrap",
                          fontFamily: SERIF,
                        }}
                      >
                        {node.greeting.text}
                      </div>
                      <div
                        style={{
                          maxHeight: active ? "40px" : "0px",
                          opacity: active ? 1 : 0,
                          marginTop: active ? "6px" : "0px",
                          transition:
                            "max-height .35s cubic-bezier(.16,1,.3,1), opacity .3s ease",
                          overflow: "hidden",
                          fontFamily: SERIF,
                        }}
                        className="text-[12px] tracking-[0.18em] whitespace-nowrap uppercase"
                      >
                        <span style={{ color: "#a5e6c7" }}>
                          {node.greeting.lang}
                        </span>
                        <span style={{ color: "rgba(180,197,207,0.75)" }}>
                          {" "}
                          · {node.greeting.region}
                        </span>
                      </div>
                    </div>
                  </Html>
                </group>
              );
            })}
          </group>
        ))}
      </group>
    </>
  );
}

export default function PlanetGreeting({ onEnter }: { onEnter: () => void }) {
  // Keep the visible experience continuous; pause work only while the page is hidden.
  const motionPaused = !usePageVisibility();
  const introRef = useRef<HTMLDivElement | null>(null);
  const atmosphereRef = useRef<HTMLDivElement | null>(null);
  const enterHintRef = useRef<HTMLButtonElement | null>(null);
  const entryDockRef = useRef<HTMLDivElement | null>(null);
  const backgroundRef = useRef<HTMLDivElement | null>(null);
  const foregroundRef = useRef<HTMLDivElement | null>(null);
  const openingRef = useRef<HTMLElement | null>(null);
  const { ringRef, dotRef, pointer } = useIntroMotion(
    introRef,
    atmosphereRef,
    enterHintRef,
    motionPaused,
  );
  const entering = useRef(false);
  const orbit = useRef<THREE.Group | null>(null);
  const spin = useRef(0);
  const target = useRef(IDLE_SPIN);
  const push = useRef(0);
  const spinImpulse = useRef(0);
  const pushImpulse = useRef(0);
  const labelRefs = useRef<(HTMLDivElement | null)[]>([]);
  const anchorRefs = useRef<(THREE.Group | null)[]>([]);
  const noteRefs = useRef<(HTMLElement | null)[]>([]);
  const closingRef = useRef<HTMLDivElement | null>(null);
  const canvasWrapRef = useRef<HTMLDivElement | null>(null);
  const htmlPortal = useRef<HTMLDivElement | null>(null);
  const [hovered, setHovered] = useState<number | null>(null);
  const rings = useMemo(buildNodes, []);
  const { chapter, reduced } = useIntroChoreography(introRef, {
    background: backgroundRef, scene: canvasWrapRef, foreground: foregroundRef,
    opening: openingRef, notes: noteRefs, closing: closingRef, entry: entryDockRef, stages: STAGES,
  });

  useEffect(() => {
    const intro = introRef.current;
    if (!intro) return;
    let pointer: {
      x: number;
      y: number;
      scroll: number;
      moved: boolean;
    } | null = null;
    let cancelled = false;
    const enter = () => {
      if (entering.current) return;
      entering.current = true;
      onEnter();
    };
    const start = (event: PointerEvent) => {
      cancelled = false;
      pointer = {
        x: event.clientX,
        y: event.clientY,
        scroll: window.scrollY,
        moved: false,
      };
    };
    const move = (event: PointerEvent) => {
      if (
        pointer &&
        Math.hypot(event.clientX - pointer.x, event.clientY - pointer.y) > 10
      )
        pointer.moved = true;
    };
    const cancel = () => {
      cancelled = true;
    };
    const click = (event: MouseEvent) => {
      if (
        event.button !== 0 ||
        event.metaKey ||
        event.ctrlKey ||
        event.altKey ||
        event.shiftKey
      )
        return;
      // Native keyboard activation of the real entry button is never a drag.
      if (event.detail === 0) { pointer = null; enter(); return; }
      const dragged =
        cancelled ||
        (pointer &&
          (pointer.moved || Math.abs(window.scrollY - pointer.scroll) > 10));
      pointer = null;
      if (!dragged) enter();
    };
    const key = (event: KeyboardEvent) => {
      if (
        event.target instanceof Element &&
        event.target.closest("button, a, input, select, textarea")
      )
        return;
      if (
        event.repeat ||
        event.metaKey ||
        event.ctrlKey ||
        event.altKey ||
        event.shiftKey
      )
        return;
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        enter();
      }
    };
    // Capture also covers greeting labels rendered through the canvas HTML portal.
    intro.addEventListener("pointerdown", start, true);
    intro.addEventListener("pointermove", move, true);
    intro.addEventListener("pointercancel", cancel, true);
    intro.addEventListener("click", click, true);
    window.addEventListener("keydown", key);
    return () => {
      intro.removeEventListener("pointerdown", start, true);
      intro.removeEventListener("pointermove", move, true);
      intro.removeEventListener("pointercancel", cancel, true);
      intro.removeEventListener("click", click, true);
      window.removeEventListener("keydown", key);
    };
  }, [onEnter]);

  useEffect(() => {
    let last = window.scrollY;
    const onScroll = () => {
      const y = window.scrollY;
      const d = y - last;
      last = y;
      spinImpulse.current += d * 0.0006;
      pushImpulse.current = clamp(pushImpulse.current + d * 0.002, -1.4, 1.4);
    };
    addEventListener("scroll", onScroll, { passive: true });
    return () => removeEventListener("scroll", onScroll);
  }, []);

  return (
    <>
      <div
        ref={introRef}
        data-motion-paused={motionPaused}
        data-motion-policy="full"
        data-intro-chapter={chapter}
        data-reduced-motion={reduced}
        role="main"
        tabIndex={-1}
        aria-label="KiraOrder introduction"
        aria-describedby="intro-enter-hint"
        className="intro-root group relative cursor-pointer text-[#e2ebe9] outline-none"
        style={{ background: "#05090f" }}
      >
        <div className="intro-depth-viewport">
        <div className="intro-depth-stage">
        {/* The background plane contains the independent spring atmosphere. */}
        <div ref={backgroundRef} className="intro-depth-background" data-depth-layer="background">
          <div ref={atmosphereRef} className="intro-atmosphere">
            <div
              className="absolute inset-0"
              style={{
                background:
                  "radial-gradient(ellipse at 50% 40%, #16283a, #05090f 75%)",
              }}
            />
            <SeamlessBackdrop
              src={VIDEO_URL}
              poster={POSTER_URL}
              paused={motionPaused}
            />
            <div
              className="absolute inset-0"
              style={{
                background:
                  "radial-gradient(ellipse at 50% 45%, rgba(5,9,15,0) 0%, rgba(5,9,15,0.18) 55%, rgba(5,9,15,0.62) 100%)",
              }}
            />
            <div className="absolute inset-x-0 top-0 h-32 bg-gradient-to-b from-[#05090f]/80 to-transparent" />
            <div className="absolute inset-x-0 bottom-0 h-32 bg-gradient-to-t from-[#05090f]/80 to-transparent" />
          </div>
        </div>

        {/* Orbiting greetings */}
        <div ref={canvasWrapRef} className="intro-depth-middle" data-depth-layer="middle">
          <div data-intro-welcome="" className="absolute inset-0">
          <div
            ref={htmlPortal}
            className="pointer-events-none absolute inset-0 z-20"
          />
          <Canvas
            dpr={[1, 1.5]}
            frameloop={motionPaused ? "demand" : "always"}
            gl={{ antialias: true, alpha: true }}
            camera={{ position: [0, 0, BASE_Z], fov: BASE_FOV }}
          >
            <Suspense fallback={null}>
              <Scene
                htmlPortal={htmlPortal}
                rings={rings}
                orbit={orbit}
                spin={spin}
                target={target}
                push={push}
                spinImpulse={spinImpulse}
                pushImpulse={pushImpulse}
                labelRefs={labelRefs}
                anchorRefs={anchorRefs}
                hovered={hovered}
                setHovered={setHovered}
                motionPaused={motionPaused}
                pointer={pointer}
              />
            </Suspense>
          </Canvas>
          </div>
        </div>

        <IntroDepthForeground
          foreground={foregroundRef} opening={openingRef} notes={noteRefs} closing={closingRef}
          chapter={chapter} paused={motionPaused} reduced={reduced}
        />
        </div>
        </div>

        {/* Topline */}
        <div className="intro-masthead" data-intro-brand="">
          KiraOrder for Orbyte
        </div>

        <div
          ref={entryDockRef}
          id="intro-enter-hint"
          data-intro-prompt=""
          className="intro-entry-dock"
        >
          <div className="intro-entry-anchor" data-intro-entry-anchor="">
          <button
            type="button"
            ref={enterHintRef}
            className="intro-enter-label"
          >
            Enter workspace
          </button>
          </div>
          <span className="intro-scroll-hint" data-intro-scroll-hint="" aria-hidden={chapter === "close"}>
            <span className="hidden md:inline">
              Scroll to explore · Enter / Space
            </span>
            <span className="md:hidden">Swipe to explore</span>
          </span>
        </div>

        {/* Scroll length */}
        <div style={{ height: `${STAGES * 100}svh` }} />
      </div>
      <div ref={ringRef} className="intro-cursor-ring" aria-hidden="true">
        <span />
      </div>
      <div ref={dotRef} className="intro-cursor-dot" aria-hidden="true" />
    </>
  );
}
