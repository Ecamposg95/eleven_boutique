import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { CatalogBar } from "@/components/CatalogBar";
import { EmptyState } from "@/components/EmptyState";
import { PageHeader } from "@/components/PageHeader";
import { Pagination } from "@/components/Pagination";
import { ProductGrid } from "@/components/ProductGrid";
import { getCategories, getProducts } from "@/lib/api";
import {
  categoryHref,
  childCategories,
  filterOptions,
  sortOptions,
} from "@/lib/categories";
import { pageMeta } from "@/lib/seo";
import {
  decodeSlug,
  firstParam,
  PAGE_SIZE,
  parsePage,
  parseSort,
  withParams,
} from "@/lib/url";

type Props = {
  params: Promise<{ slug: string }>;
  searchParams: Promise<Record<string, string | string[] | undefined>>;
};

async function findCategory(slug: string) {
  const categories = await getCategories();
  const category = categories.find(
    (item) => item.slug === slug && !item.parent_slug,
  );
  return category
    ? { category, children: childCategories(categories, category.slug) }
    : null;
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const found = await findCategory(decodeSlug((await params).slug)).catch(
    () => null,
  );
  if (!found) return { title: "Categorías" };
  return pageMeta({
    title: found.category.name,
    description: `${found.category.name} de las casas de lujo en el catálogo de Eleven Boutique.`,
    path: categoryHref(found.category.slug),
  });
}

export default async function CategoryPage({ params, searchParams }: Props) {
  const slug = decodeSlug((await params).slug);
  const query = await searchParams;
  const found = await findCategory(slug);
  if (!found) notFound();
  const { category, children } = found;

  const path = categoryHref(category.slug);
  const requested = firstParam(query.category)?.slice(0, 100) || undefined;
  const sub = children.some((child) => child.slug === requested)
    ? requested
    : undefined;
  const sort = parseSort(query.sort);
  const page = parsePage(query.page);
  const products = await getProducts({
    category: sub ?? category.slug,
    sort,
    page,
    page_size: PAGE_SIZE,
  });

  return (
    <>
      <PageHeader kicker="Categoría" title={category.name} />
      <div className="page pb-32">
        {products.items.length > 0 ? (
          <ProductGrid products={products.items} />
        ) : products.total > 0 ? (
          <EmptyState
            message="Esta página no tiene piezas."
            href={withParams(path, { category: sub, sort })}
            action="Volver a la primera página"
          />
        ) : sub ? (
          <EmptyState
            message="No hay piezas en esta selección."
            href={path}
            action={`Ver toda la categoría`}
          />
        ) : (
          <EmptyState
            message="Aún no hay piezas publicadas en esta categoría."
            href="/marcas"
            action="Explorar marcas"
          />
        )}
        <Pagination
          path={path}
          params={{ category: sub, sort }}
          page={page}
          pageSize={products.page_size}
          total={products.total}
        />
      </div>
      <CatalogBar
        filters={
          children.length > 0 ? filterOptions(path, children, sub, sort) : []
        }
        sorts={
          products.total > 1 ? sortOptions(path, { category: sub }, sort) : []
        }
      />
    </>
  );
}
