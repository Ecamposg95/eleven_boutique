import { type NextRequest, NextResponse } from "next/server";
import { loginHref } from "@/lib/admin/return-path";
import { SESSION_COOKIE } from "@/lib/admin/session";

/**
 * Solo /admin. Revisión optimista: sin cookie ni se renderiza. Quien decide es el servidor, con
 * /auth/me en lib/admin/server.ts. También anota la ruta para volver a ella tras el login.
 * El matcher deja fuera /api/v1: las subidas no pasan por aquí ni se almacenan en memoria.
 */
export function proxy(request: NextRequest) {
  const { pathname, search } = request.nextUrl;
  const path = `${pathname}${search}`;
  const isLogin = pathname === "/admin/login";
  if (!isLogin && !request.cookies.has(SESSION_COOKIE)) {
    const response = NextResponse.redirect(new URL(loginHref(path), request.url));
    response.headers.set("X-Robots-Tag", "noindex, nofollow");
    return response;
  }
  const headers = new Headers(request.headers);
  headers.set("x-admin-path", path);
  const response = NextResponse.next({ request: { headers } });
  response.headers.set("X-Robots-Tag", "noindex, nofollow");
  response.headers.set("Cache-Control", "private, no-store");
  return response;
}

export const config = { matcher: "/admin/:path*" };
