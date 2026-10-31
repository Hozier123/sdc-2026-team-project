import type { CatalogProduct } from "./catalog";
import type { Issue, LineInput, ManualLineInput, Resolution } from "./types";

// The catalog contains product identity only. Price, stock and approval state
// always come from the saved draft response, never from this selection.
export function selectCatalogProduct(input: LineInput, product: CatalogProduct): LineInput {
  return {
    ...input,
    sku_id: product.sku_id,
    confirmed_qty: product.sku_id === input.sku_id && product.base_unit === input.uom
      ? input.confirmed_qty ?? Number.NaN
      : Number.NaN,
    family_id: undefined,
    pack_size: product.pack_size,
    grade: product.grade,
    uom: product.base_unit,
    match_source: "MANUAL_SELECTED",
    unit_price_override: null,
    override_reason: null,
    save_to_alias_cache: false,
    alias_scope: "CUSTOMER",
  };
}

export function createManualLine(product: CatalogProduct, clientLineRef: string): ManualLineInput {
  return {
    client_line_ref: clientLineRef,
    sku_id: product.sku_id,
    confirmed_qty: Number.NaN, // An empty field requires explicit confirmation.
    uom: product.base_unit,
    pack_size: product.pack_size,
    grade: product.grade,
    match_source: "MANUAL_SELECTED",
  };
}

export function clearPriceResolutions(resolutions: Resolution[], conditions: Issue[]): Resolution[] {
  const priceIssues = new Set(
    conditions.filter((issue) => issue.condition_kind === "PRICE").map((issue) => issue.issue_id),
  );
  return resolutions.filter((resolution) => !priceIssues.has(resolution.issue_id));
}
