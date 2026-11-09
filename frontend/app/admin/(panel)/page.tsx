import type { Metadata } from "next";
import Link from "next/link";
import { PageHeadStatic } from "@/components/admin/static";
import { formatNumber, plural } from "@/lib/admin/format";
import { hasRole } from "@/lib/admin/rules";
import { adminGet, requireMe } from "@/lib/admin/server";
import type { Dashboard } from "@/lib/admin/types";

export const metadata: Metadata = { title: "Inicio" };

function Count({ label, value, href }: { label: string; value: number; href: string }) {
  return (
    <div className="flex items-baseline justify-between gap-4 border-b border-bronze/30 py-2">
      <dt>
        <Link href={href} prefetch={false} className="link">
          {label}
        </Link>
      </dt>
      <dd className="text-17">{formatNumber(value)}</dd>
    </div>
  );
}

export default async function DashboardPage() {
  const me = await requireMe();
  const data = await adminGet<Dashboard>("/dashboard");
  const canConfigure = hasRole(me.role, "admin");
  const missing = data.products.without_photo;

  return (
    <>
      <PageHeadStatic title="Inicio" />
      {!data.whatsapp_configured ? (
        <p role="alert" className="a-alert mb-5 max-w-3xl">
          WhatsApp no está configurado: el botón «Consultar esta pieza» no aparece en el sitio.{" "}
          {canConfigure ? (
            <Link href="/admin/configuracion" prefetch={false}>
              Configurar número
            </Link>
          ) : (
            "Pida a un administrador que agregue el número."
          )}
        </p>
      ) : null}

      <section aria-labelledby="sin-foto-t" className="a-panel max-w-3xl p-5">
        <h2 id="sin-foto-t" className="a-h2">
          Productos sin foto
        </h2>
        {missing > 0 ? (
          <>
            <p className="display mt-1 text-44">{formatNumber(missing)}</p>
            <p className="measure mt-1">
              Un producto sin foto no se puede publicar. Suba las fotos y el panel propone a qué producto corresponde
              cada una.
            </p>
            <div className="mt-4 flex flex-wrap gap-2">
              <Link href="/admin/multimedia" prefetch={false} className="a-btn a-btn-primary">
                Subir y asignar fotos
              </Link>
              <Link href="/admin/productos?sin_foto=1" prefetch={false} className="a-btn">
                Ver productos sin foto
              </Link>
            </div>
          </>
        ) : (
          <p className="measure mt-2">
            Todos los productos tienen foto.{" "}
            {data.products.draft > 0 ? `Quedan ${plural(data.products.draft, "borrador", "borradores")} por publicar.` : ""}
          </p>
        )}
      </section>

      <div className="mt-8 grid max-w-3xl gap-x-10 gap-y-8 sm:grid-cols-2">
        <section aria-labelledby="productos-t">
          <h2 id="productos-t" className="a-h2">
            Productos
          </h2>
          <dl className="mt-2">
            <Count label="Borradores" value={data.products.draft} href="/admin/productos?status=draft" />
            <Count label="Publicados" value={data.products.published} href="/admin/productos?status=published" />
            <Count label="Archivados" value={data.products.archived} href="/admin/productos?status=archived" />
          </dl>
        </section>
        <section aria-labelledby="marcas-t">
          <h2 id="marcas-t" className="a-h2">
            Marcas y consultas
          </h2>
          <dl className="mt-2">
            <Count label="Marcas en borrador" value={data.brands.draft} href="/admin/marcas" />
            <Count label="Marcas publicadas" value={data.brands.published} href="/admin/marcas" />
            <div className="flex items-baseline justify-between gap-4 border-b border-bronze/30 py-2">
              <dt>Consultas por WhatsApp, 30 días</dt>
              <dd className="text-17">{formatNumber(data.consult_clicks_30d)}</dd>
            </div>
          </dl>
        </section>
      </div>
    </>
  );
}
