import type { MetadataRoute } from "next";
import { getBrands, getCollections, getLookbooks, getProducts, soft } from "@/lib/api";
import { SITE_URL } from "@/lib/seo";
import type { ProductCard } from "@/lib/types";
import { brandHref, productHref } from "@/lib/url";

const STATIC_PATHS = ["/", "/marcas", "/colecciones", "/novedades", "/lookbooks", "/la-boutique", "/contacto"];
const MAX_PRODUCT_PAGES = 100;

async function allProducts(): Promise<ProductCard[]> {
  const products: ProductCard[] = [];
  for (let page = 1; page <= MAX_PRODUCT_PAGES; page++) {
    const batch = await getProducts({ page, page_size: 60 });
    products.push(...batch.items);
    if (batch.items.length === 0 || products.length >= batch.total) break;
  }
  return products;
}

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const [brands, products, collections, lookbooks] = await Promise.all([
    soft(getBrands()),
    soft(allProducts()),
    soft(getCollections()),
    soft(getLookbooks()),
  ]);
  const paths = [
    ...STATIC_PATHS,
    ...(brands ?? []).map((brand) => brandHref(brand.slug)),
    ...(products ?? []).map(productHref),
    ...(collections ?? []).map((item) => `/colecciones/${encodeURIComponent(item.slug)}`),
    ...(lookbooks ?? []).map((item) => `/lookbooks/${encodeURIComponent(item.slug)}`),
  ];
  return paths.map((path) => ({ url: `${SITE_URL}${path}` }));
}
