# GSAP motion refinement

## Scope and identity

Refine the existing intro and workbench with the official GSAP core, React, timeline, ScrollTrigger and performance skills. Preserve Marcellus UI text, Cormorant display text, navy surfaces, mint actions, factual counts, permissions and API behavior. Preserve the seamless background loop, orbital animation and existing pointer spring. Do not restore scroll-to-enter or the removed motion toggle.

## Motion direction

The intro is an Experience surface: language moves into an ordered workflow. Its focal sequence brings the existing orbit into focus, then establishes the brand and the enter prompt. The workbench is an Operate surface: motion explains priority and anchors floating controls to their triggers, without delaying tasks.

| Surface | Implementation | Timing / budget |
| --- | --- | --- |
| Intro welcome | A scoped GSAP timeline resolves the orbit layer, brand and enter prompt; interaction works throughout. | 700–800ms total, once per intro mount; transforms/opacity on separate wrappers. |
| Intro scroll story | ScrollTrigger scrubs a single timeline through AI reads, rules check, people approve and the existing closing panel. Retain native scrolling and avoid overlapping paragraphs on phones. | No pinning or scroll interception; viewport-based start/end; cleanup on unmount. |
| Workbench overview | Show real state cards as a group, then the recommended task and queue, with a tightly capped stagger. | Routine 220–300ms; total sequence under 500ms; no animated/fabricated counts. |
| Floating selectors | Shared placement hook reveals each menu from the actual trigger direction; focus and selection remain immediate. | 180ms, maximum 6px travel; no delayed dismissal. |
| Dialogs | Dim the backdrop while the dialog settles into the foreground; preserve focus trapping and Escape. | 220ms; remove competing CSS entrance. |

## Runtime requirements

- Use `useGSAP` with a scoped ref, automatic revert and scoped matchMedia. Respect reduced motion with short opacity feedback and no spatial choreography.
- Avoid controlling transforms already owned by Three.js, the pointer spring or CSS hover states. Use separate wrappers or disjoint properties.
- Stop transient work when hidden. Do not replay completed entrances on visibility changes. ScrollTrigger and listeners must be removed on unmount.
- No heavy plugins, layout animation or permanent will-change. Split the scroll plugin into the existing lazy intro chunk.
- Default content remains visible if animation setup fails. All actions stay enabled during entrance motion.

## Verification gates

1. Production build, frozen contract type check and current test suite pass.
2. Render both surfaces at desktop and 375px phone widths; no overflow or clipped controls.
3. Verify scroll story sequencing and closing, clicking and Enter/Space entry, and continued visible background motion.
4. Verify company/role/customer/language/unit menus, keyboard selection and dismissal, repeated opening and a dialog focus/Escape cycle.
5. Check reduced-motion alternatives, hidden-page cleanup and repeated intro/workbench navigation for stale tweens/ScrollTriggers.
6. Save rendered evidence and a concise implementation/validation record; do not claim physical-device FPS from desktop emulation.
