import Link from "next/link";
import { withParams } from "@/lib/url";

type Props = {
  path: string;
  params?: Record<string, string | undefined>;
  page: number;
  pageSize: number;
  total: number;
};

/** Enlaces normales: funciona sin JavaScript. */
export function Pagination({ path, params = {}, page, pageSize, total }: Props) {
  const pages = Math.ceil(total / pageSize);
  if (pages <= 1) return null;
  const href = (n: number) => withParams(path, { ...params, page: n });
  const linkClass = "inline-flex min-h-11 min-w-11 items-center justify-center px-2 text-15";

  return (
    <nav aria-label="Paginación" className="mt-16 flex flex-wrap items-center gap-x-2 gap-y-1">
      {page > 1 ? (
        <Link href={href(Math.min(page - 1, pages))} className={`link ${linkClass}`}>
          Anterior
        </Link>
      ) : null}
      {Array.from({ length: pages }, (_, i) => i + 1).map((n) =>
        n === page ? (
          <span key={n} aria-current="page" className={`font-medium ${linkClass}`}>
            {n}
          </span>
        ) : (
          <Link key={n} href={href(n)} aria-label={`Página ${n}`} className={`muted ${linkClass} hover:underline`}>
            {n}
          </Link>
        ),
      )}
      {page < pages ? (
        <Link href={href(page + 1)} className={`link ${linkClass}`}>
          Siguiente
        </Link>
      ) : null}
    </nav>
  );
}
