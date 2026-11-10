import type { Metadata } from "next";
import { notFound, permanentRedirect } from "next/navigation";
import { BrandMark } from "@/components/BrandMark";
import { CatalogBar } from "@/components/CatalogBar";
import { CatalogImage } from "@/components/CatalogImage";
import { EmptyState } from "@/components/EmptyState";
import { Pagination } from "@/components/Pagination";
import { ProductGrid } from "@/components/ProductGrid";
import { TextBody } from "@/components/TextBody";
import { getBrand, getBrandCategories, getProducts, soft } from "@/lib/api";
import { filterOptions, sortOptions } from "@/lib/categories";
import { safeImageSrc } from "@/lib/images";
import { pageMeta } from "@/lib/seo";
import {
  brandHref,
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

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const slug = decodeSlug((await params).slug);
  const brand = await soft(getBrand(slug));
  if (!brand) return { title: "Marcas" };
  return pageMeta({
    title: brand.name,
    description:
      brand.description ??
      `Piezas de ${brand.name} en el catálogo de Eleven Boutique.`,
    path: brandHref(brand.slug),
    image: brand.editorial_image_url,
  });
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
    getProducts({
      brand: brand.slug,
      category,
      sort,
      page,
      page_size: PAGE_SIZE,
    }),
    getBrandCategories(brand.slug),
  ]);
  const editorial = safeImageSrc(brand.editorial_image_url);

  return (
    <>
      <header className="page grid gap-8 pb-10 pt-12 md:grid-cols-12 md:gap-x-6 md:pb-16 md:pt-24">
        <div className={editorial ? "md:col-span-5" : "md:col-span-8"}>
          {brand.logo_url ? (
            <h1>
              <BrandMark
                name={brand.name}
                logoUrl={brand.logo_url}
                textClass="text-68"
                logoClass="h-20 w-72"
              />
            </h1>
          ) : (
            <h1 className="display text-104">{brand.name}</h1>
          )}
          {brand.description ? (
            <TextBody text={brand.description} className="serif mt-6 text-22" />
          ) : null}
        </div>
        {editorial ? (
          <div className="mono relative aspect-[8/5] bg-charcoal md:col-span-7">
            <CatalogImage
              src={editorial}
              alt=""
              sizes="(min-width: 768px) 58vw, 100vw"
              preload
              className="object-cover"
            />
          </div>
        ) : null}
      </header>

      <div className="page pb-32">
        {products.items.length > 0 ? (
          <ProductGrid products={products.items} />
        ) : products.total > 0 ? (
          <EmptyState
            message="Esta página no tiene piezas."
            href={withParams(path, { category, sort })}
            action="Volver a la primera página"
          />
        ) : category ? (
          <EmptyState
            message="No hay piezas de esta marca en la categoría elegida."
            href={path}
            action="Ver todas las piezas"
          />
        ) : (
          <EmptyState
            message="Aún no hay piezas publicadas de esta marca."
            href="/marcas"
            action="Explorar marcas"
          />
        )}

        <Pagination
          path={path}
          params={{ category, sort }}
          page={page}
          pageSize={products.page_size}
          total={products.total}
        />
      </div>
      <CatalogBar
        filters={
          categories.length > 1
            ? filterOptions(path, categories, category, sort)
            : []
        }
        sorts={products.total > 1 ? sortOptions(path, { category }, sort) : []}
      />
    </>
  );
}
