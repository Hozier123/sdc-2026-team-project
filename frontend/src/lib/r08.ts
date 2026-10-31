import type { Issue } from "./types";
import { money } from "./types";

export interface R08IdentityCandidate {
  sku_id: string;
  family_id: string;
  display_name: string;
  pack_size: string;
  grade: string | null;
  base_unit: string;
  tier_unit_price: string | null;
  available_qty: number;
}

export interface R08Diagnostics {
  problem_kind: string;
  explanation: string;
  identity_candidates: R08IdentityCandidate[];
  identity_candidates_complete: boolean;
  priced_candidate_list_withheld: boolean;
  selectable: boolean;
}

export const MISSING_TIER_PRICE = "MISSING_TIER_PRICE";
export const MISSING_TIER_PRICE_TITLE = "Tier price is not configured";
// Safe fallback when the diagnostic is present but its explanation is absent
// or malformed; never falls back to the generic NO_CANDIDATE copy.
export const MISSING_TIER_PRICE_FALLBACK_BODY =
  "A compatible product was identified but its customer tier price is not configured. Confirm the product from the directory; an authorized operator must configure the tier price before this order can be saved.";
export const MISSING_TIER_PRICE_SAVE_ERROR = {
  title: MISSING_TIER_PRICE_TITLE,
  body: "The selected product has no customer tier price, so this order was not saved. The draft version is unchanged and your edits are kept. An authorized operator must configure the tier price before it can be saved; you can also re-open the product directory now and choose a product that already has a price.",
};

const isRecord = (value: unknown): value is Record<string, unknown> =>
  typeof value === "object" && value !== null && !Array.isArray(value);

const identityCandidate = (value: unknown): R08IdentityCandidate | null => {
  if (!isRecord(value)) return null;
  if (typeof value.sku_id !== "string" || !value.sku_id) return null;
  if (typeof value.display_name !== "string" || !value.display_name) return null;
  return {
    sku_id: value.sku_id,
    family_id: typeof value.family_id === "string" ? value.family_id : "",
    display_name: value.display_name,
    pack_size: typeof value.pack_size === "string" ? value.pack_size : "",
    grade: typeof value.grade === "string" ? value.grade : null,
    base_unit: typeof value.base_unit === "string" ? value.base_unit : "",
    tier_unit_price:
      typeof value.tier_unit_price === "string" ? value.tier_unit_price : null,
    available_qty:
      typeof value.available_qty === "number" ? value.available_qty : 0,
  };
};

export function r08Diagnostics(
  issue: Pick<Issue, "data_used">,
): R08Diagnostics | undefined {
  const raw = issue.data_used?.r08;
  if (!isRecord(raw)) return undefined;
  if (typeof raw.problem_kind !== "string" || !raw.problem_kind) return undefined;
  const identity_candidates = Array.isArray(raw.identity_candidates)
    ? raw.identity_candidates
        .map(identityCandidate)
        .filter((c): c is R08IdentityCandidate => c !== null)
    : [];
  return {
    problem_kind: raw.problem_kind,
    // Total accessor: a malformed explanation degrades to "" so the copy
    // layer can apply its own fallback instead of dropping the diagnostic.
    explanation: typeof raw.explanation === "string" ? raw.explanation : "",
    identity_candidates,
    identity_candidates_complete: raw.identity_candidates_complete === true,
    priced_candidate_list_withheld: raw.priced_candidate_list_withheld === true,
    // Fail closed: an unrecognised payload is never selectable.
    selectable: raw.selectable === true,
  };
}

export const tierPriceLabel = (price: string | null | undefined): string =>
  price == null ? "Not configured" : money(price);
