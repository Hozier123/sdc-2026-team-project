import test from "node:test";
import assert from "node:assert/strict";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { ErrorNotice } from "../src/components/ui";
import { ApiError } from "../src/lib/types";

test("canonical authentication errors give recovery guidance without a blind write retry", () => {
  for (const [code, title, recovery] of [
    ["INVALID_TOKEN", "Your session has expired", "reconnect your session"],
    [
      "FORBIDDEN_ACTION",
      "You don’t have access to this action",
      "check your role and permissions",
    ],
  ]) {
    const markup = renderToStaticMarkup(
      createElement(ErrorNotice, {
        error: new ApiError(code, "Synthetic failure", {}, "fixture-request"),
        retry: () => {},
      }),
    );
    assert.ok(markup.includes(title), code);
    assert.ok(markup.includes(recovery), code);
    assert.ok(markup.includes("fixture-request"));
    assert.equal(markup.includes("Refresh and try again"), false, code);
  }
});
