/** B02 types are independent of the frozen Gate 0 candidate/price models. */
export interface CatalogProduct {
  sku_id: string;
  display_name: string;
  pack_size: string | null;
  grade: string | null;
  base_unit: string;
}

export interface CatalogProductsResponse {
  items: CatalogProduct[];
  limit: number;
  truncated: boolean;
}

export function catalogNotice(result: CatalogProductsResponse): string {
  return result.truncated
    ? `Showing the first ${result.items.length} products (limit ${result.limit}). This directory is incomplete.`
    : `${result.items.length} products. Complete directory.`;
}

/** Suggest catalogue variants from server candidates or words evidenced in the message. */
export function matchingCatalogProducts(
  products: CatalogProduct[],
  sourceSpan: string,
  candidateSkuIds: string[] = [],
): { items: CatalogProduct[]; phrase: string | null } {
  const candidateIds = new Set(candidateSkuIds);
  const candidates = products.filter((product) => candidateIds.has(product.sku_id));
  if (candidates.length) return { items: candidates, phrase: null };

  const text = sourceSpan.toLocaleLowerCase();
  const matches = products.map((product) => {
    const terms = product.display_name.match(/[\p{Script=Han}]{2,}|[\p{Script=Latin}]{3,}/gu) ?? [];
    const phrase = terms
      .filter((term) => {
        const lower = term.toLocaleLowerCase();
        if (!text.includes(lower)) return false;
        if (/\p{Script=Han}/u.test(term)) return true;
        for (let start = text.indexOf(lower); start >= 0; start = text.indexOf(lower, start + 1)) {
          const before = start > 0 ? text[start - 1] : "";
          const after = text[start + lower.length] ?? "";
          if (!/[\p{L}\p{N}]/u.test(before) && !/[\p{L}\p{N}]/u.test(after)) return true;
        }
        return false;
      })
      .sort((a, b) => b.length - a.length)[0];
    return { product, phrase, score: phrase?.length ?? 0 };
  });
  const best = Math.max(0, ...matches.map((match) => match.score));
  if (!best) return { items: [], phrase: null };
  const bestMatches = matches.filter((match) => match.score === best);
  return { items: bestMatches.map((match) => match.product), phrase: bestMatches[0].phrase ?? null };
}
