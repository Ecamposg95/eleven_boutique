import Link from "next/link";

/** Encabezado para páginas de servidor. Las de cliente usan PageHead de ./ui, con la misma forma. */
export function PageHeadStatic({ title, back }: { title: string; back?: { href: string; label: string } }) {
  return (
    <>
      {back ? (
        <p className="mb-1">
          <Link href={back.href} prefetch={false} className="link">
            {back.label}
          </Link>
        </p>
      ) : null}
      <div className="a-page-head">
        <h1 className="a-h1">{title}</h1>
      </div>
    </>
  );
}
