import { Suspense, useEffect, useMemo, useRef, useState } from "react";
import * as THREE from "three";
import { Canvas, useFrame, useThree } from "@react-three/fiber";
import { Html, Stars } from "@react-three/drei";
import type { PerspectiveCamera } from "three";
import { SeamlessBackdrop } from "./SeamlessBackdrop";
import { useIntroMotion } from "./useIntroMotion";
import { usePageVisibility } from "./usePageVisibility";
import { advanceSpring } from "../lib/spring";

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

const NOTES = [
  {
    n: "001",
    title: "AI reads.",
    body: "English, Malay and Chinese messages become one order draft. Unclear specifications go back to the customer.",
    side: "left",
  },
  {
    n: "002",
    title: "Rules check.",
    body: "Catalogue, customer tier prices and stock are checked. A quoted price is never applied automatically.",
    side: "right",
  },
  {
    n: "003",
    title: "People approve.",
    body: "Routine orders go to the clerk. Discounts, large orders and credit notices go to the owner. Stock limits always apply.",
    side: "left",
  },
] as const;

const NOTE_POS: { top: string }[] = [
  { top: "18%" },
  { top: "42%" },
  { top: "64%" },
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
  const enterHintRef = useRef<HTMLSpanElement | null>(null);
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

  useEffect(() => {
    const apply = () => {
      const vh = window.innerHeight || 1;
      const total = (STAGES - 1) * vh;
      const p = total > 0 ? clamp(window.scrollY / total, 0, 1) : 0;
      const sf = p * (STAGES - 1);
      const closingW = clamp(sf - (STAGES - 2), 0, 1);
      noteRefs.current.forEach((el, i) => {
        if (!el) return;
        const reveal = clamp((sf - (0.7 + i * 0.8)) / 0.8, 0, 1);
        const w = reveal * (1 - closingW);
        el.style.opacity = String(w);
        el.style.transform = `translateY(${(1 - reveal) * 26}px)`;
      });
      if (closingRef.current) {
        closingRef.current.style.opacity = String(closingW);
        closingRef.current.style.pointerEvents =
          closingW > 0.5 ? "auto" : "none";
      }
      if (canvasWrapRef.current)
        canvasWrapRef.current.style.opacity = String(1 - closingW * 0.55);
    };
    apply();
    addEventListener("scroll", apply, { passive: true });
    addEventListener("resize", apply);
    return () => {
      removeEventListener("scroll", apply);
      removeEventListener("resize", apply);
    };
  }, []);

  return (
    <>
      <div
        ref={introRef}
        data-motion-paused={motionPaused}
        role="button"
        tabIndex={0}
        aria-label="Enter KiraOrder workspace"
        aria-describedby="intro-enter-hint"
        className="intro-root group relative cursor-pointer text-[#e2ebe9] outline-none"
        style={{ background: "#05090f" }}
      >
        {/* Blended full-page backdrop: nebula base + generated animation, no hard planet frame */}
        <div className="fixed inset-0 z-0 overflow-hidden">
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
        <div ref={canvasWrapRef} className="fixed inset-0 z-10">
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

        {/* Scroll-revealed side story notes */}
        {NOTES.map((note, i) => (
          <aside
            key={note.n}
            ref={(el) => {
              noteRefs.current[i] = el;
            }}
            className={`pointer-events-none fixed z-20 w-[min(340px,27vw)] opacity-0 ${
              note.side === "left"
                ? "left-[5vw] text-left"
                : "right-[5vw] text-right"
            }`}
            style={{ top: NOTE_POS[i].top, textShadow: "0 2px 16px #03070c" }}
          >
            <div
              className="text-[15px] tracking-[0.16em] text-[#a5e6c7]"
              style={{ fontFamily: SERIF }}
            >
              {note.n}
            </div>
            <h2
              className="my-3 text-[clamp(34px,3vw,46px)] leading-[1.1] text-[#e2ebe9]"
              style={{ fontFamily: SERIF }}
            >
              {note.title}
            </h2>
            <p
              className="text-[22px] leading-[1.55] text-[#b4c5cf]"
              style={{ fontFamily: SERIF, textWrap: "pretty" }}
            >
              {note.body}
            </p>
            <div
              className={`mt-5 h-px w-14 bg-[#a5e6c7]/40 ${note.side === "right" ? "ml-auto" : ""}`}
            />
          </aside>
        ))}

        {/* Closing / entry */}
        <div
          ref={closingRef}
          className="pointer-events-none fixed inset-0 z-20 flex flex-col items-center justify-center px-10 text-center opacity-0"
          style={{
            background:
              "radial-gradient(ellipse at 50% 40%, rgba(16,30,42,0.45), rgba(5,9,15,0.72) 78%)",
          }}
        >
          <h1
            className="text-[clamp(68px,7vw,112px)] leading-[1.05] tracking-[-0.035em] text-[#e2ebe9]"
            style={{ fontFamily: SERIF }}
          >
            KiraOrder
          </h1>
          <p
            className="mt-4 text-[clamp(24px,2.2vw,34px)] text-[#e2ebe9]"
            style={{ fontFamily: SERIF }}
          >
            Every order, in the right hands.
          </p>
          <p
            className="mt-4 max-w-[620px] text-[22px] leading-[1.55] text-[#b4c5cf]"
            style={{ fontFamily: SERIF, textWrap: "pretty" }}
          >
            From a WhatsApp message to a checked delivery order. You make the
            decisions.
          </p>
        </div>

        {/* Topline */}
        <div className="pointer-events-none fixed inset-x-0 top-0 z-30 flex items-center justify-between px-6 py-5 md:px-10">
          <div
            className="flex items-center gap-3 text-[13px] tracking-[0.3em] text-[#b4c5cf] uppercase"
            style={{ fontFamily: SERIF }}
          >
            <span className="inline-block h-1.5 w-1.5 rounded-full bg-[#a5e6c7]" />
            KiraOrder for Orbyte
          </div>
        </div>

        <div
          id="intro-enter-hint"
          className="pointer-events-none fixed inset-x-0 bottom-0 z-30 flex flex-col items-center gap-2 bg-gradient-to-t from-[#05090f]/90 to-transparent px-5 pt-12 pb-[max(28px,env(safe-area-inset-bottom))] text-center"
          style={{ fontFamily: SERIF }}
        >
          <span className="mb-1 h-7 w-px bg-gradient-to-b from-transparent to-[#a5e6c7]/60" />
          <span
            ref={enterHintRef}
            className="intro-enter-label rounded-sm px-3 py-1 text-[20px] tracking-[0.04em] text-[#c8f8e2] group-focus-visible:ring-1 group-focus-visible:ring-[#a5e6c7]"
          >
            <span className="hidden md:inline">Click anywhere to enter</span>
            <span className="md:hidden">Tap anywhere to enter</span>
          </span>
          <span className="text-[13px] tracking-[0.12em] text-[#b4c5cf]">
            <span className="hidden md:inline">
              Scroll to explore · Enter / Space
            </span>
            <span className="md:hidden">Swipe to explore</span>
          </span>
        </div>

        {/* Scroll length */}
        <div style={{ height: `${STAGES * 100}vh` }} />
      </div>
      <div ref={ringRef} className="intro-cursor-ring" aria-hidden="true">
        <span />
      </div>
      <div ref={dotRef} className="intro-cursor-dot" aria-hidden="true" />
    </>
  );
}
