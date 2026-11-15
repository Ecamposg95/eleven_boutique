import Link from "next/link";
import type { CatalogOption } from "@/lib/categories";

/** Fila de enlaces tipo etiqueta bajo el título; se acomoda en varias líneas sin desbordar. */
export function DepartmentChips({
  label,
  options,
}: {
  label: string;
  options: CatalogOption[];
}) {
  if (options.length === 0) return null;
  return (
    <nav aria-label={label} className="mt-8">
      <ul className="flex flex-wrap gap-2">
        {options.map((option) => (
          <li key={option.href}>
            <Link
              href={option.href}
              aria-current={option.current ? "page" : undefined}
              className={`label inline-flex min-h-11 items-center border px-5 transition-colors ${
                option.current
                  ? "border-ivory bg-ivory text-ink"
                  : "border-bronze/40 hover:border-ivory"
              }`}
            >
              {option.label}
            </Link>
          </li>
        ))}
      </ul>
    </nav>
  );
}
