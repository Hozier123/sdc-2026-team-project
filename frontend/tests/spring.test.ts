import { test } from "node:test";
import assert from "node:assert/strict";
import { advanceSpring } from "../src/lib/spring";

test("spring settles at the same target across 60Hz and 120Hz displays", () => {
  for (const fps of [60, 120]) {
    const state = { value: 0, velocity: 0 };
    for (let i = 0; i < fps * 3; i++) advanceSpring(state, 100, 1 / fps);
    assert.ok(Math.abs(state.value - 100) < 0.01);
    assert.ok(Math.abs(state.velocity) < 0.01);
  }
});

test("spring remains finite after a suspended tab and reverses toward a new target", () => {
  const state = { value: 0, velocity: 0 };
  advanceSpring(state, 100, 20);
  assert.ok(Number.isFinite(state.value) && Number.isFinite(state.velocity));
  assert.ok(state.value < 100);
  for (let i = 0; i < 240; i++) advanceSpring(state, -40, 1 / 120);
  assert.ok(Math.abs(state.value + 40) < 0.01);
});
