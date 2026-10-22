export type SpringState = { value: number; velocity: number };

/** Semi-implicit integration with bounded substeps, independent of display rate. */
export function advanceSpring(
  state: SpringState,
  target: number,
  elapsed: number,
  stiffness = 180,
  damping = 20,
) {
  const duration = Math.max(0, Math.min(elapsed, 0.064));
  const steps = Math.max(1, Math.ceil(duration * 120));
  const dt = duration / steps;
  for (let i = 0; i < steps; i++) {
    state.velocity +=
      ((target - state.value) * stiffness - state.velocity * damping) * dt;
    state.value += state.velocity * dt;
  }
  return state.value;
}
