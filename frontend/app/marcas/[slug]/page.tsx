import type { Metadata } from "next";
import Link from "next/link";
import { notFound, permanentRedirect } from "next/navigation";
import { BrandMark } from "@/components/BrandMark";
import { CatalogImage } from "@/components/CatalogImage";
import { EmptyState } from "@/components/EmptyState";
import { Pagination } from "@/components/Pagination";
import { ProductGrid } from "@/components/ProductGrid";
import { TextBody } from "@/components/TextBody";
import { getBrand, getBrandCategories, getProducts, soft } from "@/lib/api";
import { safeImageSrc } from "@/lib/images";
import { pageMeta } from "@/lib/seo";
import { brandHref, decodeSlug, firstParam, PAGE_SIZE, parsePage, parseSort, withParams } from "@/lib/url";

type Props = {
  params: Promise<{ slug: string }>;
  searchParams: Promise<Record<string, string | string[] | undefined>>;
};

const SORTS = [
  { value: undefined, label: "Selección" },
  { value: "recent", label: "Recientes" },
  { value: "name", label: "Nombre" },
] as const;

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const slug = decodeSlug((await params).slug);
  const brand = await soft(getBrand(slug));
  if (!brand) return { title: "Marcas" };
  return pageMeta({
    title: brand.name,
    description: brand.description ?? `Piezas de ${brand.name} en el catálogo de Eleven Boutique.`,
    path: brandHref(brand.slug),
    image: brand.editorial_image_url,
  });
}

function FilterLink({ href, current, children }: { href: string; current: boolean; children: string }) {
  return (
    <Link
      href={href}
      aria-current={current ? "true" : undefined}
      className="label inline-flex min-h-8 items-center decoration-bronze decoration-1 underline-offset-[6px] hover:underline aria-[current=true]:underline"
    >
      {children}
    </Link>
  );
}

export default async function BrandPage({ params, searchParams }: Props) {
  const slug = decodeSlug((await params).slug);
  const query = await searchParams;
  const brand = await getBrand(slug);
  if (!brand) notFound();

  const category = firstParam(query.category)?.slice(0, 100) || undefined;
  const sort = parseSort(query.sort);
  const page = parsePage(query.page);
  const path = brandHref(brand.slug);

  // Alias como /marcas/bape: la dirección canónica es la de la marca.
  if (brand.slug !== slug) {
    permanentRedirect(withParams(path, { category, sort, page }));
  }

  const [products, categories] = await Promise.all([
    getProducts({ brand: brand.slug, category, sort, page, page_size: PAGE_SIZE }),
    getBrandCategories(brand.slug),
  ]);
  const editorial = safeImageSrc(brand.editorial_image_url);

  return (
    <>
      <header className="page grid gap-8 pb-10 pt-12 md:grid-cols-12 md:gap-x-6 md:pb-16 md:pt-24">
        <div className={editorial ? "md:col-span-5" : "md:col-span-8"}>
          {brand.logo_url ? (
            <h1>
              <BrandMark name={brand.name} logoUrl={brand.logo_url} textClass="text-68" logoClass="h-20 w-72" />
            </h1>
          ) : (
            <h1 className="display text-104">{brand.name}</h1>
          )}
          {brand.description ? <TextBody text={brand.description} className="serif mt-6 text-22" /> : null}
        </div>
        {editorial ? (
          <div className="mono relative aspect-[8/5] bg-charcoal md:col-span-7">
            <CatalogImage src={editorial} alt="" sizes="(min-width: 768px) 58vw, 100vw" preload className="object-cover" />
          </div>
        ) : null}
      </header>

      <div className="page pb-24">
        {categories.length > 1 || products.total > 1 ? (
          <div className="mb-10 flex flex-col gap-4 border-y border-bronze/30 py-3 md:flex-row md:items-baseline md:justify-between md:gap-10">
            {categories.length > 1 ? (
              <nav aria-label="Filtrar por categoría">
                <ul className="flex flex-wrap gap-x-5 gap-y-1">
                  <li>
                    <FilterLink href={withParams(path, { sort })} current={!category}>
                      Todas
                    </FilterLink>
                  </li>
                  {categories.map((item) => (
                    <li key={item.slug}>
                      <FilterLink href={withParams(path, { category: item.slug, sort })} current={category === item.slug}>
                        {item.name}
                      </FilterLink>
                    </li>
                  ))}
                </ul>
              </nav>
            ) : (
              <span />
            )}
            {products.total > 1 ? (
              <nav aria-label="Ordenar piezas">
                <ul className="flex flex-wrap gap-x-5 gap-y-1">
                  {SORTS.map((item) => (
                    <li key={item.label}>
                      <FilterLink href={withParams(path, { category, sort: item.value })} current={sort === item.value}>
                        {item.label}
                      </FilterLink>
                    </li>
                  ))}
                </ul>
              </nav>
            ) : null}
          </div>
        ) : null}

        {products.items.length > 0 ? (
          <ProductGrid products={products.items} />
        ) : products.total > 0 ? (
          <EmptyState message="Esta página no tiene piezas." href={withParams(path, { category, sort })} action="Volver a la primera página" />
        ) : category ? (
          <EmptyState message="No hay piezas de esta marca en la categoría elegida." href={path} action="Ver todas las piezas" />
        ) : (
          <EmptyState message="Aún no hay piezas publicadas de esta marca." href="/marcas" action="Explorar marcas" />
        )}

        <Pagination path={path} params={{ category, sort }} page={page} pageSize={products.page_size} total={products.total} />
      </div>
    </>
  );
}
