import type { AiMode } from "./types";

export const EXTRACTION: Record<AiMode, { label: string; description: string }> = {
  LLM: { label: "LLM", description: "This order used the language model." },
  FALLBACK: { label: "FALLBACK · non-AI", description: "This order used backend fallback matching without the language model." },
  MIXED: { label: "MIXED", description: "This order combined extraction sources; it is not a pure LLM result." },
  ALIAS_ONLY: { label: "ALIAS_ONLY · non-AI", description: "This order used saved aliases without the language model." },
};

export function snapshotMode(snapshot: unknown): AiMode | null {
  const mode = snapshot && typeof snapshot === "object" && "ai_mode" in snapshot ? snapshot.ai_mode : null;
  return typeof mode === "string" && Object.hasOwn(EXTRACTION, mode) ? mode as AiMode : null;
}
