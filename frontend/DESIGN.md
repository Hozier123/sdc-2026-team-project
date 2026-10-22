# KiraOrder design system

## Authority

The current interface and user decisions are the visual authority. This is a refinement of that system. Preserve the dark navy surfaces, mint primary actions, amber decision state, blue owner state, four concise statistic cards and the immersive animated introduction.

The user selected **Marcellus** for default interface text, including navigation, buttons, forms, descriptions and statistic labels. **Cormorant Garamond** remains the display face for existing headings and large counts. Keep natural case in descriptive copy. Marcellus Regular is self-hosted; distinguish hierarchy with scale, space and tone rather than unavailable bold weights.

## Tokens and ownership

`src/styles/tokens.css` is the shared token source. The base root remains 14px for the dense workbench.

| Role | Token | Current value |
|---|---|---|
| Body | `--type-body` | 14px |
| Caption | `--type-caption` | 12.5px |
| Metadata | `--type-meta` | 12px |
| Phone input | `--type-input` | 16px |
| Placeholder | `--text-placeholder` | #8b9cab |
| Touch target | `--target-touch` | 44px |
| Fast/standard feedback | `--motion-fast` / `--motion-standard` | 160ms / 220ms |

- `src/styles/workflow.css`: the shared four-stage progress indicator. One 12px label scale on intake and review, horizontal desktop flow and four-column mobile arrangement. `aria-current="step"` identifies the current stage.
- `src/styles/header.css`: connection status, avatar, identity text and role trigger. Phone hit areas are separate 44px targets; the role button covers the name/role text unit without overlapping the avatar.
- `src/styles/form-select.css`: customer, message-language and unit-confirmation selectors. Dark portal lists reuse the company/role placement and keyboard hook, with labelled listbox options, selection checks, typeahead and space-aware scroll limits. Customer tiers and credit notices remain factual labels; language and unit values retain the existing API codes. Unit controls keep 44px touch targets and enough column width for the confirmation placeholder; disable them while saving.
- `src/styles/typography.css`: screen metadata, status/count labels, document screen captions and placeholder-related type roles. Keep print-document typography independent.
- `src/styles/overview.css`: workspace composition. Desktop keeps the queue and side rail. Mobile places the compact next task ahead of the queue in both DOM and visual order.
- Existing base and business styles continue to own unrelated components. Migrate a component by removing its old overrides, not by appending another arbitrary patch.

## Layout and meaning

- The four statistics retain their label, state icon and large count. Do not restore explanatory paragraphs inside them.
- Recommend blocked drafts first, then ready drafts, oldest first within each stage. The overview list and recommendation share `overviewQueue`; do not fabricate a business urgency score.
- On phones, users should find a concrete review action in the first viewport. Recent activity follows the queue.
- Every state has words as well as color. Preserve field labels, visible keyboard focus and explicit permission/read-only feedback.
- Raise readability by wrapping and reflowing before shrinking captions. Do not restore 6–8px workflow or decision labels.

## Motion

- The visible intro keeps the existing video loop, overlap blend, orbit motion, spring response and custom cursor.
- Pause video, WebGL, CSS animation and pointer animation while the document is hidden; resume the same scene on return.
- Start the cursor animation loop only for a fine pointer with hover support. A small viewport alone does not identify touch hardware.
- Do not add the removed motion toggle or the reverted scroll-to-workspace transition. Clicking/tapping and Enter/Space remain the entry actions.
- Workbench feedback is short and state-driven. Toasts use a thin border and a 220ms decelerating entrance.

## Validation boundaries

Desktop and mobile viewport checks prove rendered layout, not physical touch, Safari behavior, battery use or measured FPS. Keep those limitations explicit. Preserve print rules and backend contracts during UI changes.
