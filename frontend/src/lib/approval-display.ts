const submittedAt = new Intl.DateTimeFormat("en-GB", {
  day: "2-digit",
  month: "short",
  year: "numeric",
  hour: "2-digit",
  minute: "2-digit",
  hourCycle: "h23",
  timeZone: "Asia/Kuala_Lumpur",
});

// requested_at is the approval submission time, not the order creation time.
export function approvalSubmissionLabel(value: string | null | undefined) {
  const date = new Date(value ?? "");
  return Number.isNaN(date.getTime())
    ? "Submission time unavailable"
    : `Submitted ${submittedAt.format(date).replace(", ", " at ")} MYT`;
}

function price(value: unknown): string | null {
  if (typeof value !== "string" && typeof value !== "number") return null;
  const text = String(value).trim();
  return /^\d+(?:\.\d{1,2})?$/.test(text) ? text : null;
}

export function approvalReasonPrices(detail: Record<string, unknown>) {
  // Live backend fields take precedence; frozen fixtures/demo use legacy names.
  return {
    tier: price(detail.tier_unit_price ?? detail.tier_price),
    applied: price(detail.effective_unit_price ?? detail.applied_price),
  };
}
