import {
  ApiError,
  toInput,
  type Draft,
  type DraftSummary,
  type LineInput,
  type WarehouseOrder,
} from "./types";

/** The overview recommends the first actionable order in this same queue. */
export function overviewQueue(drafts: DraftSummary[]) {
  const rank = (status: DraftSummary["status"]) =>
    status === "DISAMBIGUATION_REQUIRED" ? 0 :
    status === "READY_FOR_APPROVAL" ? 1 : 2;
  const received = (draft: DraftSummary) => {
    const value = Date.parse(draft.created_at || draft.updated_at);
    return Number.isFinite(value) ? value : Infinity;
  };
  return drafts
    .filter(draft => !["DO_GENERATED", "REJECTED"].includes(draft.status))
    .sort((a, b) => rank(a.status) - rank(b.status) || received(a) - received(b));
}

// A picking task combines only identical SKU, unit and handling instructions.
export function pickingItems(items: WarehouseOrder["items"]) {
  const groups = new Map<
    string,
    WarehouseOrder["items"][number] & { picking_id: string }
  >();
  for (const item of items) {
    const key = JSON.stringify([
      item.sku_id,
      item.unit,
      item.picking_note ?? "",
    ]);
    const existing = groups.get(key);
    if (existing) existing.quantity += item.quantity;
    else groups.set(key, { ...item, picking_id: key });
  }
  return [...groups.values()];
}

export function invalidQuantities(lines: LineInput[]) {
  return lines.filter(
    (line) =>
      line.confirmed_qty !== null &&
      (!Number.isSafeInteger(line.confirmed_qty) ||
        line.confirmed_qty < 1 ||
        line.confirmed_qty > 100000),
  );
}

export function assertQuantities(lines: LineInput[]) {
  if (invalidQuantities(lines).length)
    throw new ApiError(
      "REQUEST_VALIDATION_FAILED",
      "Enter a whole quantity from 1 to 100,000 for every product.",
    );
}

export function validRoute(route: string) {
  const parts = route.split("/");
  if (["order", "approval", "delivery"].includes(parts[0]))
    return parts.length === 2 && !!parts[1].trim() && !/[?#]/.test(parts[1]);
  if (parts[0] === "inbox")
    return (
      parts.length === 1 ||
      (parts.length === 2 &&
        ["all", "needs", "ready", "owner", "closed"].includes(parts[1]))
    );
  return (
    parts.length === 1 &&
    [
      "intro",
      "workspace",
      "new",
      "approvals",
      "delivery-orders",
      "activity",
      "warehouse",
      "privacy",
    ].includes(route)
  );
}

export function rebaseInputs(base: Draft, latest: Draft, edits: LineInput[]) {
  if (!latest.allowed_actions.includes("EDIT_DRAFT"))
    throw new Error(
      "This order is now locked. Your edits are still here; choose discard and reload to view its saved status.",
    );
  const baseInputs = base.lines.map(toInput);
  const changed = edits.filter((edit) => {
    const original = baseInputs.find((line) => line.line_id === edit.line_id);
    return (
      !original ||
      (Object.keys(edit) as (keyof LineInput)[]).some(
        (key) => !Object.is(edit[key], original[key]),
      )
    );
  });
  if (
    changed.some(
      (edit) => !latest.lines.some((line) => line.line_id === edit.line_id),
    )
  )
    throw new Error(
      "A product you edited was removed from the latest order. Your edits are still here; review them before choosing to discard and reload.",
    );
  return latest.lines.map((line) => {
    const result = toInput(line);
    const edit = changed.find((item) => item.line_id === line.line_id);
    const original = baseInputs.find((item) => item.line_id === line.line_id);
    if (edit && original) {
      for (const key of Object.keys(edit) as (keyof LineInput)[]) {
        if (!Object.is(edit[key], original[key]))
          Object.assign(result, { [key]: edit[key] });
      }
      if (edit.sku_id !== original.sku_id) {
        for (const key of [
          "sku_id",
          "family_id",
          "pack_size",
          "grade",
          "uom",
          "match_source",
        ] as const)
          Object.assign(result, { [key]: edit[key] });
      }
    }
    return result;
  });
}
