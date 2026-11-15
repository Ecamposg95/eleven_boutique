import { attentionLinks, bandPhoto } from "@/lib/home";
import type { PublicSettings } from "@/lib/types";
import { HeroPicture } from "./HeroPicture";
import { InstagramLink } from "./InstagramLink";

/**
 * Bloque de atención, al final de la portada: foto de fondo, degradado para que el texto se lea
 * y, en la mitad izquierda, titular y botones de WhatsApp e Instagram. Sin ninguno de los dos, no hay bloque.
 */
export function AttentionBlock({ settings }: { settings: PublicSettings }) {
  const attention = settings.attention;
  const links = attentionLinks(settings);
  if (!attention || (!links.whatsapp && !links.instagram)) return null;
  const photo = bandPhoto(attention.image_url, attention.mobile_image_url);
  const subhead = attention.subhead?.trim();

  return (
    <section
      aria-labelledby="atencion-t"
      className="inverse relative flex min-h-[32rem] items-end overflow-hidden md:aspect-[16/9] md:min-h-[30rem] md:items-center"
    >
      {photo ? (
        <>
          <div className="mono absolute inset-0 bg-charcoal">
            <HeroPicture photo={photo} sizes="100vw" className="object-cover" preload={false} />
          </div>
          <div
            aria-hidden="true"
            className="pointer-events-none absolute inset-0 bg-linear-to-t from-[#0a0a0a]/90 via-[#0a0a0a]/60 to-[#0a0a0a]/5 md:bg-linear-to-r md:from-[#0a0a0a]/90 md:via-[#0a0a0a]/65 md:to-[#0a0a0a]/5"
          />
        </>
      ) : null}
      <div className="page relative z-10 w-full py-14 md:py-20">
        <div className="max-w-xl">
          <h2 id="atencion-t" className="display text-44 md:text-68">
            {attention.headline}
          </h2>
          {subhead ? <p className="serif mt-5 text-22">{subhead}</p> : null}
          <div className="mt-8 flex flex-col gap-3 sm:flex-row">
            {links.whatsapp ? (
              <a href={links.whatsapp} target="_blank" rel="noopener noreferrer" className="btn">
                Escribir por WhatsApp
              </a>
            ) : null}
            {links.instagram ? (
              <InstagramLink
                href={links.instagram}
                className="min-h-12 justify-center border border-[#efece6] bg-[#0a0a0a]/50 px-7 py-2.5 text-[#efece6] transition-colors duration-200 hover:bg-[#efece6] hover:text-[#121212]"
              />
            ) : null}
          </div>
          {links.boutique ? (
            <a
              href={links.boutique}
              target="_blank"
              rel="noopener noreferrer"
              className="label cta mt-4"
            >
              Línea Boutique (casas premium)
            </a>
          ) : null}
        </div>
      </div>
    </section>
  );
}
