import type { Metadata } from "next";
import Link from "next/link";
import { BrandMark } from "@/components/BrandMark";
import { PageHeader } from "@/components/PageHeader";
import { ProductGrid } from "@/components/ProductGrid";
import { search } from "@/lib/api";
import { pageMeta } from "@/lib/seo";
import { brandHref, firstParam } from "@/lib/url";

type Props = { searchParams: Promise<Record<string, string | string[] | undefined>> };

const readQuery = (raw: string | string[] | undefined) => firstParam(raw)?.trim().slice(0, 100) ?? "";

export async function generateMetadata({ searchParams }: Props): Promise<Metadata> {
  const q = readQuery((await searchParams).q);
  return pageMeta({
    title: q ? `Búsqueda: ${q}` : "Buscar",
    description: "Búsqueda de marcas y piezas en el catálogo de Eleven Boutique.",
    path: "/buscar",
    noindex: true,
  });
}

export default async function SearchPage({ searchParams }: Props) {
  const q = readQuery((await searchParams).q);
  const results = q ? await search(q) : null;
  const empty = results && results.brands.length === 0 && results.products.length === 0;

  return (
    <>
      <PageHeader title="Buscar">
        <form action="/buscar" method="get" role="search" className="mt-10 flex max-w-2xl items-end gap-4">
          <div className="flex-1">
            <label htmlFor="q" className="block text-15">
              Marca, pieza o categoría
            </label>
            <input id="q" name="q" type="search" defaultValue={q} maxLength={100} className="field mt-1" />
          </div>
          <button type="submit" className="btn shrink-0">
            Buscar
          </button>
        </form>
      </PageHeader>

      <div className="page pb-24">
        {!results ? null : empty ? (
          <p className="serif measure text-30">
            Sin resultados para «{q}». Revise la ortografía o explore{" "}
            <Link href="/marcas" className="link">
              todas las marcas
            </Link>
            .
          </p>
        ) : (
          <div className="space-y-16">
            {results.brands.length > 0 ? (
              <section aria-labelledby="r-marcas">
                <h2 id="r-marcas" className="display mb-6 text-44">
                  Marcas
                </h2>
                <ul className="grid gap-x-6 gap-y-3 sm:grid-cols-2 lg:grid-cols-3">
                  {results.brands.map((brand) => (
                    <li key={brand.slug}>
                      <Link
                        href={brandHref(brand.slug)}
                        prefetch={false}
                        className="inline-block decoration-bronze decoration-1 underline-offset-[6px] hover:underline"
                      >
                        <BrandMark name={brand.name} logoUrl={brand.logo_url} textClass="text-30" />
                      </Link>
                    </li>
                  ))}
                </ul>
              </section>
            ) : null}
            {results.products.length > 0 ? (
              <section aria-labelledby="r-piezas">
                <h2 id="r-piezas" className="display mb-8 text-44">
                  Piezas
                </h2>
                <ProductGrid products={results.products} />
              </section>
            ) : null}
          </div>
        )}
      </div>
    </>
  );
}
