# Homepage depth review — 2026-10-23

## Decision

Taste assessment supports the requested depth treatment within the existing celestial identity. The language field supplies a subject-specific middle plane; adding another shader background would compete with it. React Bits is used for the opening wordmark only, fetched from the live DepthText registry, with source and license hashes recorded alongside the component. No new runtime dependency was needed.

The homepage now explicitly selects full motion, following the user's preference even when the system requests reduced motion. Workbench policy is unchanged. Native scrolling controls the story; entry remains a deliberate click/tap or keyboard action.

## Screenshot critique

ROUND 1

Seen in one second: an animated language field, without a visible product title at the initial rest point.

Idea (one sentence): multilingual messages travel through reading, checking and human approval before becoming an order.

Live thing: orbit interaction and workspace entry already exist, but the scroll relationship is mostly fading.

Layout words by section: hero=celestial field / story=overlaid paragraphs / close=statement.

Scores: design 6.0 · usability 6.0 · creativity 7.0 · content 8.0 → overall 6.4.

Caps applied: missing initial title limits usability; fewer than four real pictures limits design. The incumbent hero is intentionally retained under the single-section exception.

Top three problems (most visible first), each with the screenshot it shows in and the fix:

1. Product purpose is deferred until scrolling (`screenshots/depth-before-desktop.jpg`). Put KiraOrder and its existing concrete purpose in the first rest state.
2. The scene moves as a largely shared field (same before image). Give the nebula, language field and foreground distinct Z positions and travel distances.
3. Paragraphs share the same arrival treatment (same before image). Introduce different local trajectories with stable reading holds and deliberate left/right placement.

ROUND 2

Seen in one second: KiraOrder leads; the nebula and languages establish the world behind it.

Idea (one sentence): scroll through a mixed-language space that resolves into reading, rules and people making decisions.

Live thing: native forward/reverse scroll, existing pointer response, restrained opening text depth and real workspace entry.

Layout words by section: hero=wordmark over field / read=left reading plane / check=right reading plane / approve=left reading plane / close=centered statement.

Scores: design 6.5 · usability 8.0 · creativity 7.0 · content 8.0 → overall 6.5 after cap.

Caps applied: retained orbit hairlines and fewer than four real images keep the strict Taste overall cap at 6.5. This is a conscious scope/identity choice, not a claim of an award-level redesign or a passed automated inspector.

Top three problems (most visible first), each with the screenshot it shows in and the fix:

1. A greeting could compete with the phone's opening description (`evidence/intro-depth/phone-welcome.jpg`). Reduced the phone language field to 60% opacity; retained its motion and video brightness. The evidence image is the corrected state.
2. The system media preference originally flattened the test scene despite the normal-motion simulation. Aligned CSS perspective with the actual root motion state; final desktop captures show 1200px perspective and distinct Z transforms. The final homepage additionally applies the user's explicit full-motion policy.
3. The final composition still repeats a left reading plane and retains celestial rather than photographic proof (`desktop-read.jpg`, `desktop-approve.jpg`). Keep these for this scoped animation request; a broader content/identity revision would need a separate brief. No extra decorative sections were added to inflate a score.

## Verification

- Live source: production build passes, frozen contract generation check passes, 57/57 tests pass. Two new tests cover exact forward/reverse chapter boundaries, clamping and readable nonoverlapping windows.
- Taste source lint: four new/rewritten owned implementation files checked, **0 FAIL, 0 WARN**. This is not a whole-project result. Existing workbench code has separate findings outside this request.
- Taste's standalone browser inspector/scenes scripts were not run because this session uses its permitted browser-control API. Equivalent viewport, DOM transform and screenshot checks were made through that API. No clean inspector result is claimed.
- Checked 1440×900, 768×1024 and 390×844. Captured reading states have no horizontal document overflow and one fully visible reading plane. Mobile text stays within 24px side margins.
- At 25% desktop scroll, background travel is −20px at Z −330; middle travel is −52.5px at Z −40. At completion those planes reach Z −240 and +140. Foreground rests at Z +120 with local entries/exits. Perspective is 1200px in the actual homepage after the user override.
- Forward chapters and reverse return to the rules chapter were checked. Exact 18/40/62/84% boundaries are also tested independently.
- Enter, Space and page click reached the rendered workspace. Space's browser dispatch returned a timeout after the route changed; the following state inspection confirmed the workspace. Scrolling to the end alone stayed on the intro.
- Hidden-page harness: triggers disabled, backdrop paused, cursor loop stopped and DepthText unmounted. On return these restored. App unmount left zero ScrollTriggers and zero active GSAP animations.
- Final actual-app captures confirm the full policy, three nonidentity plane transforms, one H1 and a ready, playing video buffer. Earlier fallback captures are explicitly identified as pre-policy evidence in `browser-checks.json`.
- Registry source and license SHA256 values match `src/components/reactbits/SOURCE.json`. The intro remains a lazy chunk: approximately 69.26kB JS / 28.09kB gzip and 4.63kB CSS / 1.47kB gzip. The existing Three.js chunk is unchanged.

Evidence is stored in `docs/evidence/intro-depth/`. No physical-device FPS, battery, Safari or touch-hardware performance claim is made. Temporary QA entry files were removed after verification.
