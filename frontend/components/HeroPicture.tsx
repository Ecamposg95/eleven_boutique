import { getImageProps } from "next/image";
import { bypassOptimizer, parseImageHosts } from "@/lib/images";

const HOSTS = parseImageHosts(process.env.NEXT_PUBLIC_IMAGE_HOSTS);
const SMALL = "(max-width: 767px)";
const LARGE = "(min-width: 768px)";

/**
 * Portada con dirección de arte: el teléfono descarga solo su imagen. <source> elige una y las
 * precargas van limitadas por media; una precarga sin media bajaría también la de escritorio.
 */
export function HeroPicture({ desktop, mobile }: { desktop: string; mobile: string }) {
  const common = { alt: "", fill: true, sizes: "100vw" } as const;
  const large = getImageProps({ ...common, src: desktop, unoptimized: bypassOptimizer(desktop, HOSTS) }).props;
  const small = getImageProps({ ...common, src: mobile, unoptimized: bypassOptimizer(mobile, HOSTS) }).props;
  return (
    <>
      <link rel="preload" as="image" media={SMALL} href={small.src} imageSrcSet={small.srcSet} imageSizes="100vw" fetchPriority="high" />
      <link rel="preload" as="image" media={LARGE} href={large.src} imageSrcSet={large.srcSet} imageSizes="100vw" fetchPriority="high" />
      <picture>
        <source media={SMALL} srcSet={small.srcSet ?? small.src} sizes="100vw" />
        <source media={LARGE} srcSet={large.srcSet ?? large.src} sizes="100vw" />
        {/* eslint-disable-next-line jsx-a11y/alt-text -- props de getImageProps, con alt vacío: decorativa. */}
        <img {...large} srcSet={undefined} sizes={undefined} loading="eager" fetchPriority="high" className="object-cover" />
      </picture>
    </>
  );
}
