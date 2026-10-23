import test from "node:test";
import assert from "node:assert/strict";
import { introChapterAt } from "../src/lib/intro-depth";

test("intro chapters switch at exact thresholds in both scroll directions", () => {
  const stops = [0, 0.1799, 0.18, 0.3999, 0.4, 0.6199, 0.62, 0.8399, 0.84, 1];
  const expected = ["welcome", "welcome", "read", "read", "check", "check", "approve", "approve", "close", "close"];
  assert.deepEqual(stops.map(introChapterAt), expected);
  assert.deepEqual([...stops].reverse().map(introChapterAt), [...expected].reverse());
  assert.equal(introChapterAt(-1), "welcome");
  assert.equal(introChapterAt(NaN), "welcome");
  assert.equal(introChapterAt(2), "close");
});

test("stopping in former transition and empty ranges retains a whole chapter", () => {
  const stops = [0.1, 0.21, 0.36, 0.39, 0.43, 0.57, 0.61, 0.65, 0.79, 0.83, 0.87];
  assert.deepEqual(stops.map(introChapterAt), [
    "welcome", "read", "read", "read", "check", "check", "check", "approve", "approve", "approve", "close",
  ]);
});
