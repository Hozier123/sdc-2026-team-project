import test from "node:test";
import assert from "node:assert/strict";
import { introChapterAt, INTRO_CLOSE_AT, INTRO_WINDOWS } from "../src/lib/intro-depth";

test("intro chapters switch at exact thresholds in both scroll directions", () => {
  const stops = [0, 0.1799, 0.18, 0.3999, 0.4, 0.6199, 0.62, 0.8399, 0.84, 1];
  const expected = ["welcome", "welcome", "read", "read", "check", "check", "approve", "approve", "close", "close"];
  assert.deepEqual(stops.map(introChapterAt), expected);
  assert.deepEqual([...stops].reverse().map(introChapterAt), [...expected].reverse());
  assert.equal(introChapterAt(-1), "welcome");
  assert.equal(introChapterAt(NaN), "welcome");
  assert.equal(introChapterAt(2), "close");
});

test("each chapter has a reading hold and leaves before the next enters", () => {
  INTRO_WINDOWS.forEach((window, index) => {
    assert.ok(window.enter < window.full && window.full < window.exit && window.exit < window.gone);
    assert.ok(window.exit - window.full >= 0.079);
    assert.ok(window.gone <= (INTRO_WINDOWS[index + 1]?.enter ?? INTRO_CLOSE_AT));
  });
});
