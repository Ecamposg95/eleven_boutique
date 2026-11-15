import type { Paginated, ProductCard, ProductSort } from "@/lib/types";
import { withParams } from "@/lib/url";
import { EmptyState } from "./EmptyState";
import { Pagination } from "./Pagination";
import { ProductGrid } from "./ProductGrid";

/** Cuadrícula, paginación y estados vacíos compartidos por los listados de /tienda. */
export function CatalogListing({
  products,
  path,
  brand,
  sort,
  page,
  emptyMessage,
}: {
  products: Paginated<ProductCard>;
  path: string;
  brand?: string;
  sort?: ProductSort;
  page: number;
  emptyMessage: string;
}) {
  return (
    <div className="page pb-32">
      {products.items.length > 0 ? (
        <ProductGrid products={products.items} />
      ) : products.total > 0 ? (
        <EmptyState
          message="Esta página no tiene piezas."
          href={withParams(path, { brand, sort })}
          action="Volver a la primera página"
        />
      ) : (
        <EmptyState
          message={emptyMessage}
          href={brand ? path : "/tienda/marcas"}
          action={brand ? "Quitar el filtro de marca" : "Explorar marcas"}
        />
      )}
      <Pagination
        path={path}
        params={{ brand, sort }}
        page={page}
        pageSize={products.page_size}
        total={products.total}
      />
    </div>
  );
}
