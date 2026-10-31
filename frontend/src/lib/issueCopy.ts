import type { Issue } from "./types";

const ISSUE_COPY: Record<string, { title: string; body: string }> = {
  MULTIPLE_PACK_SIZES: {
    title: "Which pack size?",
    body: "Ask the customer for the pack size, then select the matching product.",
  },
  MULTIPLE_GRADES: {
    title: "Which grade?",
    body: "Ask the customer for the grade, then select the matching product.",
  },
  MISSING_UOM: {
    title: "Confirm the order unit",
    body: "The unit is missing. Confirm how the quantity should be supplied.",
  },
  LOW_CONFIDENCE_MATCH: {
    title: "Confirm the product",
    body: "No confident match. Confirm the product, quantity and unit with the customer.",
  },
  INSUFFICIENT_STOCK: {
    title: "There isn’t enough stock",
    body: "Confirm a smaller quantity with the customer, then update the product line. No role can approve insufficient stock.",
  },
  SAME_DAY_ORDER: {
    title: "An order already exists today",
    body: "Choose an add-on or close this duplicate before approval.",
  },
};
export function issueGuidance(issue: Issue, editable: boolean): string {
  const known = issueCopy(issue)?.body;
  if (known) return known;
  if (issue.condition_kind === "STOCK")
    return "Stock availability is checked automatically. Resolve any stock shortage in the product lines.";
  if (issue.condition_kind === "PRICE") {
    if (issue.ask === "OWNER")
      return "An owner must review this price request before approval.";
    return editable
      ? "In Customer conditions, confirm the tier price or record a requested discount, then save changes."
      : "This price request still needs a decision before approval.";
  }
  if (issue.condition_kind) {
    return editable
      ? "Review this customer condition, record the outcome, then save changes."
      : "This customer condition still needs a decision before approval.";
  }
  return "Review and resolve this item before approval.";
}

// Only use reasons already present in the runtime Issue shape. An unknown
// reason stays generic; NO_CANDIDATE does not prove a unit conflict.
const MATCH_REASON_COPY: Record<string, { title: string; body: string }> = {
  FAMILY_NOT_EVIDENCED: {
    title: "Product not recognized",
    body: "The product family could not be verified from this message. Confirm the product with the customer, choose it from the directory and check the quantity and unit before saving.",
  },
  INVALID_QUANTITY: {
    title: "Confirm the quantity",
    body: "The quantity is missing or could not be validated. Check the original message with the customer. If the product has no row, use Add a confirmed product and enter a whole quantity and unit explicitly.",
  },
  AMBIGUOUS_QUANTITY: {
    title: "Which quantity did the customer mean?",
    body: "The message contains conflicting quantity evidence. Confirm the order quantity separately from the pack size. If the product has no row, use Add a confirmed product and enter the confirmed quantity and unit.",
  },
  FIELD_NOT_EVIDENCED: {
    title: "Check the extracted details",
    body: "An extracted field could not be verified against the original message. Confirm the product, quantity, unit and pack size with the customer before saving.",
  },
  NO_CANDIDATE: {
    title: "No matching product option",
    body: "No product option was returned. Check the product name, pack size and order unit against the directory. The response does not identify a specific cause; confirm the details with the customer before saving.",
  },
};

export function issueCopy(issue: Issue): { title: string; body: string } | undefined {
  if (issue.code === "LOW_CONFIDENCE_MATCH" && issue.reason_code) {
    return Object.hasOwn(MATCH_REASON_COPY, issue.reason_code)
      ? MATCH_REASON_COPY[issue.reason_code] : ISSUE_COPY[issue.code];
  }
  return Object.hasOwn(ISSUE_COPY, issue.code) ? ISSUE_COPY[issue.code] : undefined;
}
