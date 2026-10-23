# Homepage depth composition

## Taste assessment before implementation

The requested three-plane motion fits this existing homepage. Its subject already has a spatial idea: different languages orbit before becoming one checked order. Let that language field become the middle plane, rather than adding unrelated shader backgrounds. Keep the existing navy/mint world, Cormorant/Marcellus pairing, nebula loop and pointer spring.

Concept: **KiraOrder's mixed-language message field becomes a scroll-through space that resolves into reading, checking and human approval.** The live interaction is native scrolling through this space, with the current pointer response; the real action enters the workspace.

Before screenshot: `docs/screenshots/depth-before-desktop.jpg`. The main weaknesses are a missing visible product title at the initial rest point, a scroll treatment that primarily fades the middle scene rather than giving planes different speeds, and identical travel on each paragraph. This is a scoped revision of the existing hero, so Taste's single-section exception applies: keep the incumbent direction rather than draw a new visual identity or add unrelated photographs.

## Content and proof

- Opening: KiraOrder. From a WhatsApp message to a checked delivery order. Existing product purpose and real workspace destination.
- AI reads: preserve the existing multilingual intake and clarification explanation.
- Rules check: preserve the existing catalogue, tier-price and stock explanation.
- People approve: preserve the existing clerk/owner decision and stock-limit explanation.
- Closing: preserve the existing brand promise and manual-decision explanation. Explicit `Enter workspace` action remains available throughout.

## Plane specification

| Plane | Material and independent motion | Native-scroll relationship |
| --- | --- | --- |
| Background | Existing continuous nebula video; broad, slow drift and shallow rotation. | Approximately 80px vertical travel on desktop over the complete hold; Z −360→−240, oversized to cover the viewport. |
| Middle | Existing 3D language rings; retain their idle rotation and spring hover. Move through the scene and change lateral position to clear the current paragraph. | Approximately 210px vertical travel, Z −100→140. Shift right for left-aligned content, left for rules, then settle behind the close. |
| Foreground | Clear reading planes; React Bits DepthText gives only the opening wordmark a restrained extrusion. | Fast local entry/exit, with a long readable hold. Read/check/approve/close thresholds approximately 18/40/62/84%. |

Native scroll remains authoritative. There is no wheel capture, snap, automatic workspace navigation or artificial scroll smoothing. A single GSAP timeline owns layer transforms; the existing pointer spring acts inside the background plane and Three.js owns the ring's local transforms, preventing competing writers.

## React Bits choice

Fetch the real `DepthText-TS-CSS` registry files and inspect their prop types. Use eight shallow layers, regular display weight, restrained tilt, no glow/shadow, no auto orbit and no separate intro. Keep this effect on the opening wordmark only. The fetched component requires no new dependency. Unmount its interactive implementation outside the welcome chapter or while hidden, leaving equivalent plain text.

Rejected directions: a second WebGL background, extruding paragraph text, three copies of the nebula moving at different speeds, and full-screen text that crosses other readable text. These weaken the existing image or make depth compete with the message.

## Validation and boundaries

Verify actual Z transforms and relative travel at intermediate scroll positions, forward/reverse threshold behavior, readable holds, zero text collisions, the real workspace action and full-page click/keyboard behavior. Inspect 1440, 768 and 390px widths, plus system-preference behavior and hidden-page/unmount lifecycle. The user explicitly selected full homepage motion after the initial fallback test; the final homepage therefore opts into full motion even when the system requests reduction. Workbench policy is unchanged. Run the current test suite and production build.

Use Taste's critique rubric and source lint for the affected surface. Its browser scripts cannot be used through this session's permitted browser-control interface; perform the equivalent viewport/scroll measurements and screenshots through the available browser API, and report that distinction. This is not a claim of a clean whole-project Taste inspector result: unrelated workbench styling is outside this request, and existing celestial artwork/ring geometry remains intentional brand material.

## Final mobile refinement

At 390px, the language field starts at 60% opacity and travels 95px vertically, keeping text readable in the narrower composition. Desktop keeps the full field and 210px travel. Entry is always a real 44px-high action; scroll never changes route.
