import type { Metadata, Viewport } from "next";
import { Cormorant_Garamond, Inter } from "next/font/google";
import type { ReactNode } from "react";
import { Footer } from "@/components/Footer";
import { Header } from "@/components/Header";
import { PublicChrome } from "@/components/PublicChrome";
import { getSettings, soft } from "@/lib/api";
import { safeImageSrc } from "@/lib/images";
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
  weight: ["400", "500"],
  variable: "--font-inter",
  display: "swap",
});

export const metadata: Metadata = {
  metadataBase: new URL(SITE_URL),
  title: { default: SITE_NAME, template: `%s | ${SITE_NAME}` },
  description: DEFAULT_DESCRIPTION,
  openGraph: { siteName: SITE_NAME, locale: "es_MX", type: "website" },
};

export const viewport: Viewport = { themeColor: "#1B1915", colorScheme: "dark" };

export default async function RootLayout({ children }: { children: ReactNode }) {
  // Sin ajustes la página sigue en pie: encabezado sólido y sin franja demo.
  const settings = await soft(getSettings());
  const demo = settings?.demo_mode ?? false;

  return (
    <html lang="es-MX" data-demo={demo} className={`${cormorant.variable} ${inter.variable}`}>
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
              <Header heroPhoto={Boolean(safeImageSrc(settings?.hero.image_url))} />
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
