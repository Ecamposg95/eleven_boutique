import type { Metadata } from "next";
import Link from "next/link";
import { BrandMark } from "@/components/BrandMark";
import { BrandWall } from "@/components/BrandWall";
import { CatalogImage } from "@/components/CatalogImage";
import { HeroPicture } from "@/components/HeroPicture";
import { ProductGrid } from "@/components/ProductGrid";
import { Reveal } from "@/components/Reveal";
import { firstParagraph } from "@/components/TextBody";
import { Wordmark } from "@/components/Wordmark";
import { getBrands, getCollections, getLookbooks, getNovedades, getProducts, getSettings, soft } from "@/lib/api";
import { safeImageSrc } from "@/lib/images";
import { DEFAULT_DESCRIPTION, SITE_NAME } from "@/lib/seo";
import type { BrandSummary, PublicSettings } from "@/lib/types";
import { brandHref } from "@/lib/url";

export const metadata: Metadata = {
  title: { absolute: SITE_NAME },
  description: DEFAULT_DESCRIPTION,
  alternates: { canonical: "/" },
  openGraph: { title: SITE_NAME, description: DEFAULT_DESCRIPTION, url: "/" },
};

function HeroText({ settings, light, quiet }: { settings: PublicSettings; light?: boolean; quiet?: boolean }) {
  return (
    <div className="max-w-2xl">
      <h1 className={quiet ? "serif text-30" : "display text-44 md:text-68"}>
        {settings.hero.headline ?? settings.site_name}
      </h1>
      {settings.hero.subhead ? (
        <p className={`serif measure mt-2 text-22 ${light ? "" : "muted"}`}>{settings.hero.subhead}</p>
      ) : null}
    </div>
  );
}

function PhotoHero({ settings, image }: { settings: PublicSettings; image: string }) {
  const mobileImage = safeImageSrc(settings.hero.mobile_image_url);
  return (
    <section className="relative -mt-[var(--header-h)] flex h-[calc(100svh-var(--banner-h))] min-h-[32rem] items-end bg-charcoal">
      {mobileImage ? (
        <HeroPicture desktop={image} mobile={mobileImage} />
      ) : (
        <CatalogImage src={image} alt="" sizes="100vw" preload className="object-cover" />
      )}
      <div aria-hidden="true" className="scrim-top absolute inset-x-0 top-0 h-[calc(var(--header-h)+3.5rem)]" />
      <div className="relative w-full pt-28">
        <div aria-hidden="true" className="scrim-bottom absolute inset-0" />
        <div className="page relative flex flex-col gap-8 pb-10 md:flex-row md:items-end md:justify-between md:pb-14">
          <HeroText settings={settings} light />
          <Link href="/marcas" className="btn btn-on-photo shrink-0 self-start md:self-auto">
            Explorar marcas
          </Link>
        </div>
      </div>
    </section>
  );
}

function WallHero({ settings, brands }: { settings: PublicSettings; brands: BrandSummary[] }) {
  return (
    <section className="flex h-[calc(100svh-var(--chrome-h))] min-h-[34rem] flex-col">
      <BrandWall
        brands={brands}
        className="wall-cover wall-in page min-h-0 flex-1 pt-6 text-104 md:pt-8"
      />
      <div className="page flex shrink-0 flex-col gap-5 pb-8 pt-4 md:flex-row md:items-end md:justify-between md:pb-10">
        <HeroText settings={settings} quiet />
        <Link href="/marcas" className="btn shrink-0 self-start md:self-auto">
          Explorar marcas
        </Link>
      </div>
    </section>
  );
}

function PlainHero({ settings }: { settings: PublicSettings }) {
  return (
    <section className="page flex min-h-[calc(100svh-var(--chrome-h))] flex-col justify-between gap-12 py-10">
      <Wordmark className="text-104" />
      <HeroText settings={settings} />
    </section>
  );
}

function SectionHead({ id, title, href, action }: { id: string; title: string; href?: string; action?: string }) {
  return (
    <div className="mb-10 flex flex-wrap items-baseline justify-between gap-x-8 gap-y-2 md:mb-14">
      <h2 id={id} className="display text-44">
        {title}
      </h2>
      {href && action ? (
        <Link href={href} className="link inline-flex min-h-6 items-center text-15">
          {action}
        </Link>
      ) : null}
    </div>
  );
}

export default async function HomePage() {
  // Sin ajustes no hay portada posible: lo recoge app/error.tsx.
  const settings = await getSettings();
  // Cada sección es opcional: si su dato falla, se oculta como si estuviera vacía.
  const [brands, featuredBrands, collections, curated, novedades, lookbooks] = await Promise.all([
    soft(getBrands()),
    soft(getBrands({ featured: true })),
    soft(getCollections()),
    soft(getProducts({ featured: true, page_size: 12 })),
    soft(getNovedades({ page_size: 4 })),
    soft(getLookbooks()),
  ]);

  const heroImage = safeImageSrc(settings.hero.image_url);
  const allBrands = brands ?? [];
  const mainCollection = collections?.[0];
  const lookbook = lookbooks?.[0];
  const boutique = settings.boutique.body?.trim();

  return (
    <>
      {heroImage ? (
        <PhotoHero settings={settings} image={heroImage} />
      ) : allBrands.length > 0 ? (
        <WallHero settings={settings} brands={allBrands} />
      ) : (
        <PlainHero settings={settings} />
      )}

      {settings.intro?.trim() ? (
        <section aria-label="Presentación" className="section page">
          <Reveal>
            <p className="serif measure text-30 md:ml-[calc((100%+1.5rem)/12*2)]">{settings.intro}</p>
          </Reveal>
        </section>
      ) : null}

      {heroImage && allBrands.length > 0 ? (
        <section aria-labelledby="casas-t" className="section page">
          <h2 id="casas-t" className="display mb-8 text-44">
            Marcas
          </h2>
          <BrandWall brands={allBrands} className="text-68" />
        </section>
      ) : !heroImage && featuredBrands?.length ? (
        <section aria-labelledby="destacadas-t" className="section page">
          <Reveal>
            <h2 id="destacadas-t" className="display mb-10 text-44">
              Marcas destacadas
            </h2>
            <ul className="grid gap-x-6 gap-y-6 sm:grid-cols-2 lg:grid-cols-3">
              {featuredBrands.map((brand) => (
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
          </Reveal>
        </section>
      ) : null}

      {mainCollection ? (
        <section aria-labelledby="coleccion-t" className="section page">
          <Reveal className="grid gap-8 md:grid-cols-12 md:items-end md:gap-x-6">
            <Link
              href={`/colecciones/${encodeURIComponent(mainCollection.slug)}`}
              prefetch={false}
              aria-hidden="true"
              tabIndex={-1}
              className="relative block aspect-[8/5] bg-charcoal md:col-span-8"
            >
              <CatalogImage
                src={mainCollection.cover_url}
                alt=""
                sizes="(min-width: 768px) 66vw, 100vw"
                className="object-cover"
              />
            </Link>
            <div className="md:col-span-4">
              <h2 id="coleccion-t" className="display text-44">
                {mainCollection.title}
              </h2>
              {mainCollection.summary ? <p className="serif muted mt-3 text-22">{mainCollection.summary}</p> : null}
              <p className="mt-6">
                <Link href={`/colecciones/${encodeURIComponent(mainCollection.slug)}`} className="link text-15">
                  Ver colección
                </Link>
              </p>
            </div>
          </Reveal>
        </section>
      ) : null}

      {curated?.items.length ? (
        <section aria-labelledby="seleccion-t" className="section page">
          <SectionHead id="seleccion-t" title="Selección" />
          <ProductGrid products={curated.items} />
        </section>
      ) : null}

      {novedades?.items.length ? (
        <section aria-labelledby="novedades-t" className="section page">
          <SectionHead id="novedades-t" title="Novedades" href="/novedades" action="Ver todas las novedades" />
          <ProductGrid products={novedades.items} />
        </section>
      ) : null}

      {lookbook ? (
        <section aria-labelledby="lookbook-t" className="section">
          <Reveal>
            <Link
              href={`/lookbooks/${encodeURIComponent(lookbook.slug)}`}
              prefetch={false}
              aria-hidden="true"
              tabIndex={-1}
              className="relative block aspect-[4/3] bg-charcoal md:aspect-[5/2]"
            >
              <CatalogImage src={lookbook.cover_url} alt="" sizes="100vw" className="object-cover" />
            </Link>
            <div className="page mt-6">
              <h2 id="lookbook-t" className="display text-44">
                {lookbook.title}
              </h2>
              {lookbook.summary ? <p className="serif muted measure mt-3 text-22">{lookbook.summary}</p> : null}
              <p className="mt-6">
                <Link href={`/lookbooks/${encodeURIComponent(lookbook.slug)}`} className="link text-15">
                  Ver lookbook
                </Link>
              </p>
            </div>
          </Reveal>
        </section>
      ) : null}

      {boutique ? (
        <section aria-labelledby="boutique-t" className="section bg-charcoal">
          <Reveal className="page">
            <h2 id="boutique-t" className="display text-44">
              La boutique
            </h2>
            <p className="serif measure mt-5 text-22">{firstParagraph(boutique)}</p>
            <p className="mt-6">
              <Link href="/la-boutique" className="link text-15">
                Conocer la boutique
              </Link>
            </p>
          </Reveal>
        </section>
      ) : null}
    </>
  );
}
