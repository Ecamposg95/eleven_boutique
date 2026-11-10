import type { Metadata } from "next";
import Link from "next/link";
import { BrandWall } from "@/components/BrandWall";
import { CatalogImage } from "@/components/CatalogImage";
import { HouseShowroom } from "@/components/HouseShowroom";
import { ProductCard } from "@/components/ProductCard";
import { Reveal } from "@/components/Reveal";
import { firstParagraph } from "@/components/TextBody";
import {
  getBrands,
  getCollections,
  getLookbooks,
  getNovedades,
  getSettings,
  soft,
} from "@/lib/api";
import {
  closingImage,
  giantWord,
  stripEntries,
  type StripEntry,
} from "@/lib/home";
import { safeImageSrc } from "@/lib/images";
import { splitShowroom } from "@/lib/showroom";
import { DEFAULT_DESCRIPTION, SITE_NAME } from "@/lib/seo";
import type { CollectionSummary, PublicSettings } from "@/lib/types";

export const metadata: Metadata = {
  title: { absolute: SITE_NAME },
  description: DEFAULT_DESCRIPTION,
  alternates: { canonical: "/" },
  openGraph: { title: SITE_NAME, description: DEFAULT_DESCRIPTION, url: "/" },
};

/**
 * Portada editorial: la palabra gigante, la fotografía montada encima y el titular a la derecha.
 * Sin fotografía queda solo la tipografía, que se sostiene sola.
 */
function Hero({
  settings,
  image,
}: {
  settings: PublicSettings;
  image: string | null;
}) {
  const word = giantWord(settings.site_name);
  return (
    <section
      aria-labelledby="hero-t"
      className="page overflow-hidden pb-14 pt-6 md:pb-20 md:pt-8"
    >
      <p
        aria-hidden="true"
        className="giant wall-in text-giant -ml-[0.04em] whitespace-nowrap"
      >
        {word}
      </p>

      <div className="mt-6 grid gap-8 md:mt-0 md:grid-cols-12 md:gap-6">
        <p className="label muted hidden md:col-span-3 md:block md:pt-10">
          Fashion
          <br />
          boutique
          <span aria-hidden="true" className="mt-4 block h-px w-8 bg-ivory" />
        </p>

        {image ? (
          <div className="mono relative aspect-[4/5] bg-charcoal md:col-span-5 md:-mt-[9vw]">
            <CatalogImage
              src={image}
              alt=""
              sizes="(min-width: 768px) 42vw, 100vw"
              preload
              className="object-cover"
            />
          </div>
        ) : null}

        <div
          className={`flex flex-col justify-end ${image ? "md:col-span-4" : "md:col-span-6 md:col-start-7"}`}
        >
          {/* Sin titular propio, el nombre ya está en la palabra gigante: el h1 queda solo para lectores. */}
          <h1 id="hero-t" className={settings.hero.headline ? "display text-68" : "sr-only"}>
            {settings.hero.headline ?? settings.site_name}
          </h1>
          {settings.hero.subhead ? (
            <p className="label muted mt-6 max-w-xs">{settings.hero.subhead}</p>
          ) : null}
          <span aria-hidden="true" className="mt-6 block h-px w-8 bg-ivory" />
          <Link href="/marcas" className="label cta mt-4 self-start">
            Explorar marcas
          </Link>
        </div>
      </div>
    </section>
  );
}

/** La franja negra de historias: miniatura, número, etiqueta, título y "Ver más". */
function Strip({ entries }: { entries: StripEntry[] }) {
  return (
    <section aria-label="Historias" className="inverse">
      <ul className="page grid md:grid-cols-3">
        {entries.map((entry, index) => {
          const image = safeImageSrc(entry.image);
          return (
            <li
              key={entry.href}
              className="border-bronze py-6 md:border-l md:px-6 md:py-8 md:first:border-l-0 md:first:pl-0"
            >
              <Link
                href={entry.href}
                prefetch={false}
                className="group grid grid-cols-[minmax(0,1fr)_minmax(0,1fr)] gap-5"
              >
                <span className="mono relative block aspect-[5/4] overflow-hidden bg-charcoal">
                  {image ? (
                    <CatalogImage
                      src={image}
                      alt=""
                      sizes="(min-width: 768px) 16vw, 45vw"
                      className="object-cover"
                    />
                  ) : (
                    <span
                      aria-hidden="true"
                      className="giant absolute inset-0 flex items-center justify-center text-68"
                    >
                      {entry.mark}
                    </span>
                  )}
                </span>
                <span className="flex flex-col">
                  <span className="label">
                    {String(index + 1).padStart(2, "0")}
                  </span>
                  <span className="label muted">{entry.kicker}</span>
                  <span className="serif mt-3 text-22 decoration-1 underline-offset-4 group-hover:underline">
                    {entry.title}
                  </span>
                  <span className="label cta mt-auto">Ver más</span>
                </span>
              </Link>
            </li>
          );
        })}
      </ul>
    </section>
  );
}

function SectionHead({
  id,
  title,
  href,
  action,
}: {
  id: string;
  title: string;
  href?: string;
  action?: string;
}) {
  return (
    <div className="mb-6 flex flex-wrap items-baseline justify-between gap-x-8 gap-y-2 md:mb-8">
      <h2 id={id} className="display text-44">
        {title}
      </h2>
      {href && action ? (
        <Link href={href} className="label cta">
          {action}
        </Link>
      ) : null}
    </div>
  );
}

function Collections({ collections }: { collections: CollectionSummary[] }) {
  return (
    <section aria-labelledby="colecciones-t" className="section page">
      <SectionHead
        id="colecciones-t"
        title="Colecciones"
        href="/colecciones"
        action="Ver todas"
      />
      <ul className={`grid gap-x-3 gap-y-10 ${collections.length === 2 ? "md:grid-cols-2" : "md:grid-cols-3"}`}>
        {collections.slice(0, 3).map((collection) => (
          <li key={collection.slug}>
            <Link
              href={`/colecciones/${encodeURIComponent(collection.slug)}`}
              prefetch={false}
              className="group block"
            >
              <span className="mono relative block aspect-[3/4] overflow-hidden bg-charcoal">
                <CatalogImage
                  src={collection.cover_url}
                  alt=""
                  sizes="(min-width: 768px) 33vw, 100vw"
                  className="object-cover transition-transform duration-700 group-hover:scale-[1.02]"
                />
              </span>
              <span className="mt-3 flex items-baseline justify-between gap-4">
                <span className="text-17 font-medium tracking-[-0.01em]">
                  {collection.title}
                </span>
                <span className="label cta shrink-0">Explorar</span>
              </span>
            </Link>
          </li>
        ))}
      </ul>
    </section>
  );
}

/** El cierre: retrato grande a la izquierda y la boutique en letra gruesa a la derecha. */
function Closing({ body, image }: { body: string; image: string | null }) {
  return (
    <section
      aria-labelledby="boutique-t"
      className="relative grid bg-charcoal md:min-h-[42rem] md:grid-cols-12"
    >
      {image ? (
        <div className="mono relative aspect-[4/5] md:col-span-7 md:aspect-auto">
          <CatalogImage
            src={image}
            alt=""
            sizes="(min-width: 768px) 58vw, 100vw"
            className="object-cover"
          />
        </div>
      ) : null}
      <Reveal
        className={`page flex flex-col justify-center py-14 md:py-20 ${image ? "md:col-span-5 md:pl-12" : "md:col-span-12"}`}
      >
        <h2 id="boutique-t" className="display text-68">
          La boutique.
        </h2>
        <p className="serif measure mt-6 text-22">{firstParagraph(body)}</p>
        <span aria-hidden="true" className="mt-8 block h-px w-8 bg-ivory" />
        <Link href="/la-boutique" className="label cta mt-4 self-start">
          Conocer la boutique
        </Link>
      </Reveal>
    </section>
  );
}

export default async function HomePage() {
  // Sin ajustes no hay portada posible: lo recoge app/error.tsx.
  const settings = await getSettings();
  // Cada sección es opcional: si su dato falla, se oculta como si estuviera vacía.
  const [brands, featuredBrands, novedades, collections, lookbooks] =
    await Promise.all([
      soft(getBrands()),
      soft(getBrands({ featured: true })),
      soft(getNovedades({ page_size: 4 })),
      soft(getCollections()),
      soft(getLookbooks()),
    ]);

  const heroImage = safeImageSrc(settings.hero.image_url);
  const allBrands = brands ?? [];
  const allCollections = collections ?? [];
  const allLookbooks = lookbooks ?? [];
  const newest = novedades?.items ?? [];
  const { stars, rest } = splitShowroom(allBrands, featuredBrands ?? []);
  const boutique = settings.boutique.body?.trim();
  const strip = stripEntries({
    lookbooks: allLookbooks,
    novedades: newest,
    brands: allBrands,
    boutique: Boolean(boutique),
  });

  return (
    <>
      <Hero settings={settings} image={heroImage} />

      {strip.length > 0 ? <Strip entries={strip} /> : null}

      {allCollections.length > 0 ? (
        <Collections collections={allCollections} />
      ) : null}

      {settings.intro?.trim() ? (
        <section aria-label="Presentación" className="section page pt-0">
          <Reveal>
            <p className="display measure text-44 md:ml-[calc((100%+1.5rem)/12*3)]">
              {settings.intro}
            </p>
          </Reveal>
        </section>
      ) : null}

      {newest.length > 0 ? (
        <section aria-labelledby="novedades-t" className="section page pt-0">
          <SectionHead
            id="novedades-t"
            title="Novedades"
            href="/novedades"
            action="Ver todas"
          />
          <ul className="grid grid-cols-2 gap-x-3 gap-y-10 md:grid-cols-4">
            {newest.slice(0, 4).map((product) => (
              <li key={product.slug}>
                <ProductCard
                  product={product}
                  sizes="(min-width: 1600px) 360px, (min-width: 768px) 25vw, 50vw"
                />
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      {stars.length > 0 ? <HouseShowroom houses={stars} /> : null}

      {allBrands.length > 0 ? (
        <section aria-labelledby="casas-t" className="section page">
          <Reveal>
            <SectionHead
              id="casas-t"
              title={stars.length > 0 ? "También en la boutique" : "Las casas"}
              href="/marcas"
              action={`Ver las ${allBrands.length}`}
            />
            <BrandWall
              brands={stars.length > 0 ? rest : allBrands}
              className="text-30 md:text-44"
            />
          </Reveal>
        </section>
      ) : null}

      {boutique ? (
        <Closing
          body={boutique}
          image={safeImageSrc(
            closingImage(allLookbooks, allCollections, heroImage),
          )}
        />
      ) : null}
    </>
  );
}
