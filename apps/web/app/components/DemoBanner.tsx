import { env } from "~/env";

export function DemoBanner() {
  if (!env.demoMode) return null;
  return (
    <div
      role="note"
      className="bg-ink px-4 py-2 text-center text-xs tracking-wide text-ivory"
    >
      Demostración · Productos, precios y disponibilidad son ficticios
    </div>
  );
}
