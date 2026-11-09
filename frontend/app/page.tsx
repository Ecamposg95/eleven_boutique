import type { Metadata } from "next";
import Link from "next/link";
import { BrandWall } from "@/components/BrandWall";
import { CatalogImage } from "@/components/CatalogImage";
import { HeroPicture } from "@/components/HeroPicture";
import { HouseShowroom } from "@/components/HouseShowroom";
import { ProductCard } from "@/components/ProductCard";
import { Reveal } from "@/components/Reveal";
import { firstParagraph } from "@/components/TextBody";
import { Wordmark } from "@/components/Wordmark";
import { getBrands, getNovedades, getSettings, soft } from "@/lib/api";
import { safeImageSrc } from "@/lib/images";
import { splitShowroom } from "@/lib/showroom";
import { DEFAULT_DESCRIPTION, SITE_NAME } from "@/lib/seo";
import type { BrandSummary, PublicSettings } from "@/lib/types";

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
      <Wordmark className="h-40 md:h-64" />
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
  const [brands, featuredBrands, novedades] = await Promise.all([
    soft(getBrands()),
    soft(getBrands({ featured: true })),
    soft(getNovedades({ page_size: 4 })),
  ]);

  const heroImage = safeImageSrc(settings.hero.image_url);
  const allBrands = brands ?? [];
  // La portada es un showroom: las casas destacadas (en el orden del panel) mandan.
  const { stars, rest } = splitShowroom(allBrands, featuredBrands ?? []);
  const showroom = stars.length > 0;
  const boutique = settings.boutique.body?.trim();

  return (
    <>
      {showroom ? (
        <HouseShowroom houses={stars} title={settings.hero.headline ?? settings.site_name} />
      ) : heroImage ? (
        <PhotoHero settings={settings} image={heroImage} />
      ) : allBrands.length > 0 ? (
        <WallHero settings={settings} brands={allBrands} />
      ) : (
        <PlainHero settings={settings} />
      )}

      {showroom && rest.length > 0 ? (
        <section aria-labelledby="casas-t" className="section page">
          <Reveal>
            <h2 id="casas-t" className="serif muted mb-6 text-22">
              También en la boutique
            </h2>
            <BrandWall brands={rest} className="text-30 md:text-44" />
            <p className="mt-8">
              <Link href="/marcas" className="link text-15">
                Ver las {allBrands.length} casas
              </Link>
            </p>
          </Reveal>
        </section>
      ) : !showroom && heroImage && allBrands.length > 0 ? (
        <section aria-labelledby="casas-t" className="section page">
          <h2 id="casas-t" className="display mb-8 text-44">
            Marcas
          </h2>
          <BrandWall brands={allBrands} className="text-68" />
        </section>
      ) : null}

      {settings.intro?.trim() ? (
        <section aria-label="Presentación" className="section page">
          <Reveal>
            <p className="serif measure text-30 md:ml-[calc((100%+1.5rem)/12*2)]">{settings.intro}</p>
          </Reveal>
        </section>
      ) : null}

      {novedades?.items.length ? (
        <section aria-labelledby="novedades-t" className="section page">
          <SectionHead id="novedades-t" title="Novedades" href="/novedades" action="Ver todas las novedades" />
          <ul className="grid grid-cols-2 gap-x-4 gap-y-10 md:grid-cols-4 md:gap-x-6">
            {novedades.items.slice(0, 4).map((product) => (
              <li key={product.slug}>
                <ProductCard product={product} sizes="(min-width: 1600px) 360px, (min-width: 768px) 25vw, 50vw" />
              </li>
            ))}
          </ul>
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
