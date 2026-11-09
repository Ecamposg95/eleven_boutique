import Link from "next/link";
import type { AdminCollection } from "@/lib/admin/types";
import { CreateByName } from "./CreateByName";
import { Empty, StatusLabel, Thumb } from "./ui";

/** Lista compartida de colecciones y lookbooks. */
export function ContentList({
  items,
  basePath,
  endpoint,
  createLabel,
  createAction,
  emptyMessage,
}: {
  items: AdminCollection[];
  basePath: string;
  endpoint: string;
  createLabel: string;
  createAction: string;
  emptyMessage: string;
}) {
  return (
    <>
      {items.length === 0 ? (
        <Empty message={emptyMessage} />
      ) : (
        <table className="a-table">
          <thead>
            <tr>
              <th scope="col" className="w-24">
                Portada
              </th>
              <th scope="col">Título</th>
              <th scope="col" className="max-sm:hidden">
                Productos
              </th>
              <th scope="col" className="max-sm:hidden">
                Estado
              </th>
            </tr>
          </thead>
          <tbody>
            {items.map((item) => (
              <tr key={item.id}>
                <td>
                  <Thumb src={item.cover_url} size="4.5rem" ratio="4 / 3" sizes="120px" emptyLabel="Sin portada" />
                </td>
                <td>
                  <Link href={`${basePath}/${item.id}`} prefetch={false} className="a-piece hover:underline">
                    {item.title}
                  </Link>
                  {item.summary ? <span className="muted line-clamp-1 block">{item.summary}</span> : null}
                  <span className="block sm:hidden">
                    <StatusLabel status={item.status} />
                  </span>
                </td>
                <td className="max-sm:hidden">{item.product_ids?.length ?? 0}</td>
                <td className="max-sm:hidden">
                  <StatusLabel status={item.status} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      <div className="a-section">
        <CreateByName endpoint={endpoint} field="title" label={createLabel} action={createAction} basePath={basePath} />
      </div>
    </>
  );
}
