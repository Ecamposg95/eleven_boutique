import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { CatalogImage } from "@/components/CatalogImage";
import { PageHeader } from "@/components/PageHeader";
import { ProductGrid } from "@/components/ProductGrid";
import { Reveal } from "@/components/Reveal";
import { TextBody } from "@/components/TextBody";
import { getLookbook, soft } from "@/lib/api";
import { pageMeta } from "@/lib/seo";
import type { LookbookBlock } from "@/lib/types";
import { decodeSlug } from "@/lib/url";

type Props = { params: Promise<{ slug: string }> };

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const lookbook = await soft(getLookbook(decodeSlug((await params).slug)));
  if (!lookbook) return { title: "Lookbooks" };
  return pageMeta({
    title: lookbook.title,
    description: lookbook.summary ?? `${lookbook.title}, lookbook de Eleven Boutique.`,
    path: `/lookbooks/${encodeURIComponent(lookbook.slug)}`,
    image: lookbook.cover_url,
  });
}

function Block({ block }: { block: LookbookBlock }) {
  if (block.type === "text") {
    return (
      <Reveal className="page">
        <div className="md:ml-[calc((100%+1.5rem)/12*2)]">
          {block.heading ? <h2 className="display mb-4 text-44">{block.heading}</h2> : null}
          <TextBody text={block.body} />
        </div>
      </Reveal>
    );
  }
  if (block.layout === "full") {
    return (
      <Reveal>
        <div className="mono relative aspect-[4/3] bg-charcoal md:aspect-[8/5]">
          <CatalogImage src={block.url} alt={block.alt} sizes="100vw" className="object-cover object-[50%_25%]" />
        </div>
      </Reveal>
    );
  }
  return (
    <Reveal className="page">
      <div className="md:grid md:grid-cols-12 md:gap-x-6">
        <div
          className={`mono relative aspect-[8/5] bg-charcoal md:col-span-7 ${block.layout === "right" ? "md:col-start-6" : ""}`}
        >
          <CatalogImage src={block.url} alt={block.alt} sizes="(min-width: 768px) 58vw, 100vw" className="object-cover object-[50%_25%]" />
        </div>
      </div>
    </Reveal>
  );
}

export default async function LookbookPage({ params }: Props) {
  const lookbook = await getLookbook(decodeSlug((await params).slug));
  if (!lookbook) notFound();
  const blocks = [...lookbook.blocks].sort((a, b) => a.position - b.position);
  return (
    <>
      <PageHeader title={lookbook.title} kicker="Lookbook">
        {lookbook.summary ? <p className="serif measure mt-5 text-22">{lookbook.summary}</p> : null}
      </PageHeader>
      {blocks.length > 0 ? (
        <div className="space-y-16 md:space-y-24">
          {blocks.map((block) => (
            <Block key={`${block.type}-${block.position}`} block={block} />
          ))}
        </div>
      ) : null}
      {lookbook.products.length > 0 ? (
        <section aria-labelledby="piezas-t" className="section page">
          <h2 id="piezas-t" className="display mb-10 text-44">
            Piezas de este lookbook
          </h2>
          <ProductGrid products={lookbook.products} />
        </section>
      ) : (
        <div className="pb-24" />
      )}
    </>
  );
}
