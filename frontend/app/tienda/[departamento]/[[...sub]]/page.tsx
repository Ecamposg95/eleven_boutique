import type { Metadata } from "next";
import { notFound, permanentRedirect } from "next/navigation";
import { CatalogBar } from "@/components/CatalogBar";
import { CatalogImage } from "@/components/CatalogImage";
import { CatalogListing } from "@/components/CatalogListing";
import { DepartmentChips } from "@/components/DepartmentChips";
import { PageHeader } from "@/components/PageHeader";
import { getBrandFacets, getCategories, getProducts } from "@/lib/api";
import {
  brandOptions,
  childCategories,
  sortOptions,
  subcategoryOptions,
} from "@/lib/categories";
import { safeImageSrc } from "@/lib/images";
import { pageMeta } from "@/lib/seo";
import {
  decodeSlug,
  departmentHref,
  firstParam,
  PAGE_SIZE,
  parsePage,
  parseSort,
  withParams,
} from "@/lib/url";

type Props = {
  params: Promise<{ departamento: string; sub?: string[] }>;
  searchParams: Promise<Record<string, string | string[] | undefined>>;
};

/**
 * Departamento y subcategoría opcional de la ruta; `null` si no hay departamento (o sobran
 * segmentos). Una subcategoría desconocida de un departamento válido se devuelve en `staleSub`.
 */
async function resolve({ departamento, sub }: Awaited<Props["params"]>) {
  if (sub && sub.length > 1) return null;
  const categories = await getCategories();
  const department = categories.find(
    (item) => item.slug === decodeSlug(departamento) && !item.parent_slug,
  );
  if (!department) return null;
  const children = childCategories(categories, department.slug);
  const subSlug = sub?.[0] === undefined ? undefined : decodeSlug(sub[0]);
  const subcategory =
    subSlug === undefined
      ? undefined
      : children.find((child) => child.slug === subSlug);
  const staleSub = subSlug !== undefined && !subcategory;
  return { department, children, subcategory, staleSub };
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const found = await resolve(await params).catch(() => null);
  if (!found) return { title: "Tienda" };
  const { department, subcategory } = found;
  const name = subcategory?.name ?? department.name;
  return pageMeta({
    title: name,
    description: `${name} de las casas de lujo en el catálogo de Eleven Boutique.`,
    path: departmentHref(department.slug, subcategory?.slug),
    image: subcategory ? undefined : department.cover_url,
  });
}

export default async function DepartmentPage({ params, searchParams }: Props) {
  const found = await resolve(await params);
  if (!found) notFound();
  const { department, children, subcategory, staleSub } = found;
  if (staleSub) {
    // Enlaces antiguos a una subcategoría renombrada o borrada: se muestra el departamento.
    const old = await searchParams;
    permanentRedirect(
      withParams(departmentHref(department.slug), {
        brand: firstParam(old.brand)?.slice(0, 100),
        sort: parseSort(old.sort),
      }),
    );
  }
  // La subcategoría sale solo de la ruta; `?category=` (de redirecciones antiguas) se ignora.
  const query = await searchParams;
  const sort = parseSort(query.sort);
  const page = parsePage(query.page);
  const scope = subcategory ?? department;
  const path = departmentHref(department.slug, subcategory?.slug);

  // Facetas y piezas van en paralelo; solo una marca que no aplica obliga a pedir de nuevo.
  const requested = firstParam(query.brand)?.slice(0, 100);
  const productsFor = (brand: string | undefined) =>
    getProducts({
      category: scope.slug,
      brand,
      sort,
      page,
      page_size: PAGE_SIZE,
    });
  const [facets, requestedProducts] = await Promise.all([
    getBrandFacets(scope.slug).catch(() => []),
    productsFor(requested),
  ]);
  const brand = facets.some((facet) => facet.slug === requested)
    ? requested
    : undefined;
  const products =
    brand === requested ? requestedProducts : await productsFor(undefined);

  const cover = subcategory ? null : safeImageSrc(department.cover_url);
  const filters = subcategoryOptions(department, children, subcategory?.slug, {
    brand,
    sort,
  });
  const chips = <DepartmentChips label="Subcategorías" options={filters} />;

  return (
    <>
      {cover ? (
        <header className="page grid gap-8 pb-10 pt-12 md:grid-cols-12 md:gap-x-6 md:pb-16 md:pt-20">
          <div className="md:col-span-7">
            <p className="label muted mb-4">Departamento</p>
            <h1 className="display text-104">{department.name}</h1>
            <span aria-hidden="true" className="mt-6 block h-px w-8 bg-ivory" />
            {chips}
          </div>
          <div className="mono relative aspect-[4/5] bg-charcoal md:col-span-5">
            <CatalogImage
              src={cover}
              alt=""
              sizes="(min-width: 768px) 40vw, 100vw"
              preload
              className="object-cover"
            />
          </div>
        </header>
      ) : (
        <PageHeader
          kicker={subcategory ? department.name : "Departamento"}
          title={scope.name}
        >
          {chips}
        </PageHeader>
      )}
      <CatalogListing
        products={products}
        path={path}
        brand={brand}
        sort={sort}
        page={page}
        emptyMessage={
          subcategory
            ? "Aún no hay piezas publicadas en esta subcategoría."
            : "Aún no hay piezas publicadas en este departamento."
        }
      />
      <CatalogBar
        filters={children.length > 0 ? filters : []}
        brands={brandOptions(path, facets, brand, sort)}
        sorts={products.total > 1 ? sortOptions(path, { brand }, sort) : []}
      />
    </>
  );
}
