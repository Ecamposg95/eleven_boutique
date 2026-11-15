import { bandPhoto } from "@/lib/home";
import type { DetailSettings } from "@/lib/types";
import { HeroPicture } from "./HeroPicture";

/** Franja de detalle: una foto a todo lo ancho (21:9 en computadora, 4:5 en teléfono) con pie opcional. */
export function DetailBand({ detail }: { detail: DetailSettings | undefined }) {
  const photo = bandPhoto(detail?.image_url, detail?.mobile_image_url);
  if (!photo) return null;
  const caption = detail?.caption?.trim();
  return (
    <section aria-label="Detalle">
      <div className="mono relative aspect-[4/5] overflow-hidden bg-charcoal md:aspect-[21/9]">
        <HeroPicture photo={photo} sizes="100vw" className="object-cover" preload={false} />
      </div>
      {caption ? <p className="label muted page py-4">{caption}</p> : null}
    </section>
  );
}
