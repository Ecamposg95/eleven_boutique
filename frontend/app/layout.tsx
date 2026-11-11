import type { Metadata, Viewport } from "next";
import { Cormorant_Garamond, Inter, Montserrat } from "next/font/google";
import type { ReactNode } from "react";
import { Footer } from "@/components/Footer";
import { Header } from "@/components/Header";
import { PublicChrome } from "@/components/PublicChrome";
import { getBrands, getCategories, getSettings, soft } from "@/lib/api";
import { categoryHref, stockedCategories } from "@/lib/categories";
import { safeImageSrc } from "@/lib/images";
import { brandHref } from "@/lib/url";
import { DEFAULT_DESCRIPTION, SITE_NAME, SITE_URL } from "@/lib/seo";
import "./globals.css";

const cormorant = Cormorant_Garamond({
  subsets: ["latin"],
  weight: ["300", "400", "500"],
  style: ["normal", "italic"],
  variable: "--font-cormorant",
  display: "swap",
});
const inter = Inter({
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
  variable: "--font-inter",
  display: "swap",
});
// Solo para las dos líneas pequeñas del logotipo (components/Wordmark.tsx).
const montserrat = Montserrat({
  subsets: ["latin"],
  weight: ["400", "500", "700"],
  variable: "--font-montserrat",
  display: "swap",
});

export const metadata: Metadata = {
  metadataBase: new URL(SITE_URL),
  title: { default: SITE_NAME, template: `%s | ${SITE_NAME}` },
  description: DEFAULT_DESCRIPTION,
  openGraph: { siteName: SITE_NAME, locale: "es_MX", type: "website" },
};

export const viewport: Viewport = {
  themeColor: "#EFECE6",
  colorScheme: "light",
};

export default async function RootLayout({
  children,
}: {
  children: ReactNode;
}) {
  // Sin ajustes la página sigue en pie: encabezado sólido y sin franja demo.
  // El menú es opcional por partes: sin catálogo, el panel muestra solo los enlaces fijos.
  const [settings, categories, houses] = await Promise.all([
    soft(getSettings()),
    soft(getCategories()),
    soft(getBrands({ featured: true })),
  ]);
  const menuCategories = stockedCategories(categories ?? []).map(
    (category) => ({
      href: categoryHref(category.slug),
      label: category.name,
    }),
  );
  const menuHouses = (houses ?? [])
    .slice(0, 12)
    .map((brand) => ({ href: brandHref(brand.slug), label: brand.name }));
  const demo = settings?.demo_mode ?? false;

  return (
    <html
      lang="es-MX"
      data-demo={demo}
      className={`${cormorant.variable} ${inter.variable} ${montserrat.variable}`}
    >
      <body className="flex min-h-svh flex-col">
        <a
          href="#contenido"
          className="fixed left-4 top-2 z-50 -translate-y-24 bg-ivory px-4 py-3 text-15 text-ink focus:translate-y-0"
        >
          Saltar al contenido
        </a>
        <PublicChrome
          top={
            <div className="sticky top-0 z-40">
              {demo ? (
                <p className="flex h-[var(--banner-h)] items-center bg-charcoal px-[var(--gutter)] text-15">
                  Entorno de demostración: productos e imágenes de ejemplo.
                </p>
              ) : null}
              <Header
                overHero={Boolean(
                  safeImageSrc(settings?.hero.image_url) ||
                  settings?.hero.gallery?.some((url) => safeImageSrc(url)),
                )}
                categories={menuCategories}
                houses={menuHouses}
              />
            </div>
          }
          footer={<Footer />}
        >
          {children}
        </PublicChrome>
      </body>
    </html>
  );
}
