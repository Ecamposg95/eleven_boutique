import type { Route } from "./+types/home";

export function meta(_: Route.MetaArgs) {
  return [
    { title: "Eleven Boutique" },
    {
      name: "description",
      content:
        "Explora nuestra selección y recibe atención para elegir talla, color y disponibilidad.",
    },
  ];
}

// Marcador de EB-02: verifica el arranque. La landing real se construye en EB-04.
export default function Home() {
  return (
    <main className="mx-auto flex min-h-[70dvh] max-w-3xl flex-col justify-center gap-4 px-4">
      <p className="text-xs tracking-[0.2em] text-champagne uppercase">
        En construcción
      </p>
      <h1 className="text-4xl">Eleven Boutique</h1>
      <p className="text-base">Encuentra tu próximo favorito.</p>
    </main>
  );
}
