import { RefreshCw } from "lucide-react";
import { catalogNotice, type CatalogProductsResponse } from "../lib/catalog";
import { useResource } from "../lib/hooks";
import type { Service } from "../lib/types";
import { Empty, ErrorNotice, Loading, PageHeading } from "./ui";

export function CatalogResult({ result, mode }: {
  result: CatalogProductsResponse;
  mode: "demo" | "live" | "fixture";
}) {
  return (
    <>
      <div className="catalog-summary">
        <p role={result.truncated ? "alert" : "status"}>
          {catalogNotice(result)}
        </p>
        <span>Limit {result.limit} · {mode === "live" ? "Live directory" : mode === "fixture" ? "Synthetic fixture" : "Local demo sample"}</span>
      </div>
      {!result.items.length ? (
        <Empty title="No active products" description="This workspace has no active products in its directory." />
      ) : (
        <>
        <div className="catalog-scroll">
          <table className="catalog-table" aria-label="Product directory">
            <thead><tr><th>Product</th><th>SKU</th><th>Pack size</th><th>Grade</th><th>Unit</th></tr></thead>
            <tbody>{result.items.map((product) => (
              <tr key={product.sku_id}>
                <td>{product.display_name}</td>
                <td><code>{product.sku_id}</code></td>
                <td>{product.pack_size ?? "—"}</td>
                <td>{product.grade ?? "—"}</td>
                <td>{product.base_unit}</td>
              </tr>
            ))}</tbody>
          </table>
        </div>
        <ul className="catalog-mobile-list" aria-label="Product directory">
          {result.items.map((product) => (
            <li className="catalog-mobile-item" key={product.sku_id}>
              <strong>{product.display_name}</strong>
              <code>{product.sku_id}</code>
              <dl>
                <div><dt>Pack size</dt><dd>{product.pack_size ?? "—"}</dd></div>
                <div><dt>Grade</dt><dd>{product.grade ?? "—"}</dd></div>
                <div><dt>Unit</dt><dd>{product.base_unit}</dd></div>
              </dl>
            </li>
          ))}
        </ul>
        </>
      )}
    </>
  );
}

export function CatalogPage({ service }: { service: Service }) {
  const resource = useResource(() => service.catalogProducts(), [service]);
  return (
    <div className="catalog-page">
      <PageHeading title="Product directory" />
      <p className="catalog-description">Read-only product names, specifications and units for this workspace. Prices and stock are checked when an order is saved.</p>
      <section className="panel">
        <div className="catalog-toolbar">
          <h2>Active products</h2>
          <button className="button secondary small" onClick={resource.refresh} disabled={resource.loading}>
            <RefreshCw size={14} /> Refresh directory
          </button>
        </div>
        {resource.error ? <ErrorNotice error={resource.error} retry={resource.refresh} />
          : resource.value === undefined ? <Loading label="Loading product directory…" />
          : <CatalogResult result={resource.value} mode={service.fixture ? "fixture" : service.mode} />}
      </section>
    </div>
  );
}
