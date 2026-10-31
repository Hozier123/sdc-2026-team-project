import { useState } from "react";
import { Search } from "lucide-react";
import { catalogNotice, matchingCatalogProducts, type CatalogProduct, type CatalogProductsResponse } from "../lib/catalog";
import { useResource } from "../lib/hooks";
import type { Service } from "../lib/types";
import { Empty, ErrorNotice, Loading, Modal } from "./ui";

export function CatalogChoices({ result, query, onSelect, items = result.items, notice, onBrowseAll }: {
  result: CatalogProductsResponse;
  query: string;
  onSelect: (product: CatalogProduct) => void;
  items?: CatalogProduct[];
  notice?: string;
  onBrowseAll?: () => void;
}) {
  const normalized = query.trim().toLocaleLowerCase();
  const products = items.filter((product) =>
    [product.display_name, product.sku_id, product.pack_size, product.grade, product.base_unit]
      .some((part) => part?.toLocaleLowerCase().includes(normalized)),
  );
  return (
    <>
      <p className="manual-catalog-count" role={result.truncated ? "alert" : "status"}>
        {notice ?? catalogNotice(result)}
        {result.truncated && " Selection is unavailable until the full tenant directory loads."}
      </p>
      {!products.length ? (
        <Empty title={result.items.length ? "No matching products" : "No active products"}
          description={result.items.length
            ? onBrowseAll ? "The message did not match a directory name. Browse all products or clarify the item with the customer."
              : "Try the product name, SKU, pack size or unit."
            : "Ask the customer or close this draft with a reason."}>
          {onBrowseAll && result.items.length > 0 && (
            <button type="button" className="button secondary" onClick={onBrowseAll}>Browse all products</button>
          )}
        </Empty>
      ) : (
        <div className="manual-catalog-list" role="list" aria-label="Tenant products">
          {products.map((product) => (
            <div role="listitem" key={product.sku_id}>
            <button type="button"
              className="manual-catalog-item" disabled={result.truncated}
              aria-label={`Choose ${product.display_name}, ${product.pack_size ?? "no pack size"}${product.grade ? `, grade ${product.grade}` : ""}, ${product.base_unit}`}
              onClick={() => onSelect(product)}>
              <span className="manual-catalog-name">{product.display_name}</span>
              <span className="manual-catalog-spec">
                {product.pack_size ?? "No pack size"}{product.grade ? ` · Grade ${product.grade}` : ""} · {product.base_unit}
              </span>
              <code>{product.sku_id}</code>
            </button>
            </div>
          ))}
        </div>
      )}
    </>
  );
}

export function ManualCatalogPicker({ service, onSelect, onClose, sourceSpan = "", candidateSkuIds = [], initialView = "all" }: {
  service: Service;
  onSelect: (product: CatalogProduct) => void;
  onClose: () => void;
  sourceSpan?: string;
  candidateSkuIds?: string[];
  initialView?: "matched" | "all";
}) {
  const resource = useResource(() => service.catalogProducts(), [service]);
  const [query, setQuery] = useState("");
  const [view, setView] = useState<"matched" | "all">(initialView);
  const matches = resource.value
    ? matchingCatalogProducts(resource.value.items, sourceSpan, candidateSkuIds)
    : { items: [], phrase: null };
  return (
    <Modal title={view === "matched" ? "Choose a matching product" : "Choose a product"} onClose={onClose} wide className="manual-catalog-modal">
      <p className="modal-copy">
        Confirm the exact grade, pack and unit with the customer. Enter the quantity after choosing;
        price and stock checks appear after saving.
      </p>
      {(sourceSpan || candidateSkuIds.length > 0) && (
        <div className="manual-catalog-views" aria-label="Product list">
          <button type="button" className={view === "matched" ? "active" : ""}
            aria-pressed={view === "matched"} onClick={() => { setView("matched"); setQuery(""); }}>
            Matching options
          </button>
          <button type="button" className={view === "all" ? "active" : ""}
            aria-pressed={view === "all"} onClick={() => { setView("all"); setQuery(""); }}>
            All products
          </button>
        </div>
      )}
      {view === "matched" && resource.value && matches.items.length > 0 && (
        <p className="manual-catalog-context" role="status">
          {`${matches.phrase ? `Found “${matches.phrase}” in the message. ` : "These options came from the draft. "}Select only after confirming the variant with the customer.`}
        </p>
      )}
      {(view === "all" || !resource.value || matches.items.length > 0) && (
        <label className="manual-catalog-search">
          Search products
          <span><Search size={17} aria-hidden="true" />
            <input type="search" value={query} onChange={(event) => setQuery(event.target.value)}
              placeholder="Name, SKU, size, unit" />
          </span>
        </label>
      )}
      {resource.error ? <ErrorNotice error={resource.error} retry={resource.refresh} />
        : resource.value === undefined ? <Loading label="Loading live directory…" />
        : <CatalogChoices result={resource.value} items={view === "matched" ? matches.items : undefined}
            notice={view === "matched" ? `${matches.items.length} matching options · ${catalogNotice(resource.value)}` : undefined}
            query={query} onSelect={onSelect}
            onBrowseAll={view === "matched" && !matches.items.length ? () => { setView("all"); setQuery(""); } : undefined} />}
      <div className="modal-actions">
        <button type="button" className="button secondary" onClick={onClose}>Cancel</button>
      </div>
    </Modal>
  );
}
