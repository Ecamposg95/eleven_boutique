import {
  isRouteErrorResponse,
  Links,
  Meta,
  Outlet,
  Scripts,
  ScrollRestoration,
} from "react-router";

import type { Route } from "./+types/root";
import "./app.css";
import { DemoBanner } from "./components/DemoBanner";
import { env } from "./env";

export function Layout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es-MX">
      <head>
        <meta charSet="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        {env.demoMode && <meta name="robots" content="noindex, nofollow" />}
        <Meta />
        <Links />
      </head>
      <body className="min-h-dvh antialiased">
        <DemoBanner />
        {children}
        <ScrollRestoration />
        <Scripts />
      </body>
    </html>
  );
}

export default function App() {
  return <Outlet />;
}

export function HydrateFallback() {
  return <p className="p-8 text-sm">Cargando…</p>;
}

export function ErrorBoundary({ error }: Route.ErrorBoundaryProps) {
  let title = "Algo salió mal";
  let details = "Ocurrió un error inesperado. Intenta de nuevo.";
  let stack: string | undefined;

  if (isRouteErrorResponse(error)) {
    title = error.status === 404 ? "Página no encontrada" : "Error";
    details =
      error.status === 404
        ? "La página que buscas no existe o ya no está disponible."
        : error.statusText || details;
  } else if (import.meta.env.DEV && error instanceof Error) {
    details = error.message;
    stack = error.stack;
  }

  return (
    <main className="mx-auto max-w-3xl p-8">
      <h1 className="text-2xl">{title}</h1>
      <p className="mt-2">{details}</p>
      {stack && (
        <pre className="mt-4 overflow-x-auto text-xs">
          <code>{stack}</code>
        </pre>
      )}
    </main>
  );
}
