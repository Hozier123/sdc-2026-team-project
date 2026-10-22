import { test } from "node:test";
import assert from "node:assert/strict";
import { watchPageVisibility } from "../src/lib/page-visibility";

test("visibility signal starts with current state, resumes and cleans up", () => {
  class Page extends EventTarget { hidden = true; }
  const page = new Page();
  const states: boolean[] = [];
  const stop = watchPageVisibility(page, visible => states.push(visible));
  page.hidden = false;
  page.dispatchEvent(new Event("visibilitychange"));
  page.hidden = true;
  page.dispatchEvent(new Event("visibilitychange"));
  stop();
  page.hidden = false;
  page.dispatchEvent(new Event("visibilitychange"));
  assert.deepEqual(states, [false, true, false]);
});
