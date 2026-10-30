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
