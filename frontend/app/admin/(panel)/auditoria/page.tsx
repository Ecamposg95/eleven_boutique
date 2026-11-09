import type { Metadata } from "next";
import { PageHeadStatic } from "@/components/admin/static";
import { AuditPager } from "@/components/admin/AuditPager";
import { formatDateTime, plural } from "@/lib/admin/format";
import { auditLabel, auditValue } from "@/lib/admin/rules";
import { adminGet, requireMe } from "@/lib/admin/server";
import type { AuditEntry } from "@/lib/admin/types";
import { parsePage } from "@/lib/url";

export const metadata: Metadata = { title: "Auditoría" };

const PAGE_SIZE = 50;

export default async function AuditPage({ searchParams }: { searchParams: Promise<Record<string, string | string[] | undefined>> }) {
  await requireMe("admin");
  const page = parsePage((await searchParams).page);
  const data = await adminGet<{ items: AuditEntry[]; total: number }>("/audit", { page, page_size: PAGE_SIZE });
  return (
    <>
      <PageHeadStatic title="Auditoría" />
      <p className="muted mb-2">{plural(data.total, "registro", "registros")}</p>
      {data.items.length === 0 ? (
        <p className="serif text-22 py-8">Aún no hay cambios registrados. Cada cambio en el panel aparecerá aquí.</p>
      ) : (
        <table className="a-table">
          <caption className="sr-only">Registro de cambios</caption>
          <thead>
            <tr>
              <th scope="col">Fecha</th>
              <th scope="col" className="max-md:hidden">
                Usuario
              </th>
              <th scope="col">Operación</th>
              <th scope="col" className="max-lg:hidden">
                Cambios
              </th>
            </tr>
          </thead>
          <tbody>
            {data.items.map((entry) => {
              const changes = Object.entries(entry.changes ?? {});
              return (
                <tr key={entry.id}>
                  <td className="whitespace-nowrap max-sm:whitespace-normal">{formatDateTime(entry.created_at)}</td>
                  <td className="break-all max-md:hidden">{entry.user_email ?? "Sistema"}</td>
                  <td>
                    {auditLabel(entry.operation, entry.entity)}
                    <span className="muted block break-all">{entry.entity_id}</span>
                    <span className="muted block break-all md:hidden">{entry.user_email ?? "Sistema"}</span>
                  </td>
                  <td className="max-lg:hidden">
                    {changes.length ? (
                      <details>
                        <summary className="cursor-pointer">{plural(changes.length, "campo", "campos")}</summary>
                        <ul className="mt-1 max-w-xl space-y-1">
                          {changes.map(([field, value]) => (
                            <li key={field} className="break-words">
                              <span className="font-medium">{field}</span>:{" "}
                              {Array.isArray(value) && value.length === 2 ? `${auditValue(value[0])}, ahora ${auditValue(value[1])}` : auditValue(value)}
                            </li>
                          ))}
                        </ul>
                      </details>
                    ) : null}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      )}
      <AuditPager page={page} pageSize={PAGE_SIZE} total={data.total} />
    </>
  );
}
