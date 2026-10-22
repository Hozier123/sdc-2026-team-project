# KiraOrder product context

Confirmed from the existing README, implemented routes and the user's accepted UI decisions. This records current product facts; it does not add backend promises.

- **Purpose:** turn a mixed-language customer order message into a checked draft, an explicit human approval and a traceable delivery order.
- **Users:** order clerks create and review drafts; owners decide escalated approvals; warehouse users receive a restricted picking view.
- **Tasks:** intake a message, resolve product/quantity/price questions, save changes, request or perform an allowed approval, and inspect or print the resulting delivery record.
- **Authority:** the frozen Gate 0 API contract governs real-session fields, permissions, inventory, state changes and allowed actions. Local catalogue matching is a synthetic demonstration, not a real AI endpoint.
- **Safety of work:** preserve unsaved changes, expose recoverable errors, lock terminal records and retain version/conflict checks. Customer messages and generated replies are not automatically sent.
- **Privacy:** do not upload private project materials. Real-session tokens stay in memory. The demo masks private contact/identity details before storage.
- **Voice:** concise, task-oriented English in the interface; retain multilingual customer evidence. Do not introduce fabricated urgency, SLA, data or marketing claims.
- **Implementation:** React 19, Vite, TypeScript, local font assets and custom CSS with Tailwind v4. The separate immersive introduction uses a lazy-loaded WebGL scene and crossfaded video.

Current refinement scope and visual authority are recorded in DESIGN.md. Real backend/AI integration, physical-device performance and full accessibility certification remain separate validation work.
