import { useState } from "react";
import { Search } from "lucide-react";
import { catalogNotice, type CatalogProduct, type CatalogProductsResponse } from "../lib/catalog";
import { useResource } from "../lib/hooks";
import type { Service } from "../lib/types";
import { Empty, ErrorNotice, Loading, Modal } from "./ui";

export function CatalogChoices({ result, query, onSelect }: {
  result: CatalogProductsResponse;
  query: string;
  onSelect: (product: CatalogProduct) => void;
}) {
  const normalized = query.trim().toLocaleLowerCase();
  const products = result.items.filter((product) =>
    [product.display_name, product.sku_id, product.pack_size, product.grade, product.base_unit]
      .some((part) => part?.toLocaleLowerCase().includes(normalized)),
  );
  return (
    <>
      <p className="manual-catalog-count" role={result.truncated ? "alert" : "status"}>
        {catalogNotice(result)}
        {result.truncated && " Selection is unavailable until the full tenant directory loads."}
      </p>
      {!products.length ? (
        <Empty title={result.items.length ? "No matching products" : "No active products"}
          description={result.items.length ? "Try the product name, SKU, pack size or unit." : "Ask the customer or close this draft with a reason."} />
      ) : (
        <div className="manual-catalog-list" role="list" aria-label="Tenant products">
          {products.map((product) => (
            <div role="listitem" key={product.sku_id}>
            <button type="button"
              className="manual-catalog-item" disabled={result.truncated}
              aria-label={`Choose ${product.display_name}, ${product.pack_size ?? "no pack size"}, ${product.base_unit}`}
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

export function ManualCatalogPicker({ service, onSelect, onClose }: {
  service: Service;
  onSelect: (product: CatalogProduct) => void;
  onClose: () => void;
}) {
  const resource = useResource(() => service.catalogProducts(), [service]);
  const [query, setQuery] = useState("");
  return (
    <Modal title="Choose a product" onClose={onClose} wide className="manual-catalog-modal">
      <p className="modal-copy">
        Choose from this tenant’s complete live directory. Confirm quantity before saving;
        customer price, stock and approval checks appear only after the save response.
      </p>
      <label className="manual-catalog-search">
        Search products
        <span><Search size={17} aria-hidden="true" />
          <input type="search" value={query} onChange={(event) => setQuery(event.target.value)}
            placeholder="Name, SKU, pack size or unit" />
        </span>
      </label>
      {resource.error ? <ErrorNotice error={resource.error} retry={resource.refresh} />
        : resource.value === undefined ? <Loading label="Loading live directory…" />
        : <CatalogChoices result={resource.value} query={query} onSelect={onSelect} />}
      <div className="modal-actions">
        <button type="button" className="button secondary" onClick={onClose}>Cancel</button>
      </div>
    </Modal>
  );
}
