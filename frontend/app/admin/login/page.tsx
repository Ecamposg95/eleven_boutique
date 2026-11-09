import type { Metadata } from "next";
import { redirect } from "next/navigation";
import { LoginForm } from "@/components/admin/LoginForm";
import { safeReturnPath } from "@/lib/admin/return-path";
import { getMe } from "@/lib/admin/server";
import { firstParam } from "@/lib/url";

export const metadata: Metadata = { title: "Entrar" };

export default async function LoginPage({ searchParams }: { searchParams: Promise<Record<string, string | string[] | undefined>> }) {
  const params = await searchParams;
  const next = safeReturnPath(firstParam(params.next));
  // Una API caída no debe impedir ver el formulario.
  const me = await getMe().catch((error: unknown) => {
    if (error instanceof Error && error.message.startsWith("auth/me")) return null;
    if (error instanceof TypeError || (error instanceof DOMException && error.name === "TimeoutError")) return null;
    throw error;
  });
  if (me) redirect(next);
  return <LoginForm next={next} expired={firstParam(params.expirada) === "1"} />;
}
