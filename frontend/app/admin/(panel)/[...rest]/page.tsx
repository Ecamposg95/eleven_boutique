import { notFound } from "next/navigation";
import { requireMe } from "@/lib/admin/server";

// Las rutas desconocidas del panel se quedan dentro del panel, y también exigen sesión.
export default async function UnknownAdminRoute() {
  await requireMe();
  notFound();
}
