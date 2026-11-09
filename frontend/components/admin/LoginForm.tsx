"use client";

import { type FormEvent, useState } from "react";
import { Wordmark } from "@/components/Wordmark";
import { AdminApiError, api } from "@/lib/admin/client";
import { TextField } from "./ui";

export function LoginForm({ next, expired }: { next: string; expired: boolean }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [emailError, setEmailError] = useState<string | null>(null);
  const [passwordError, setPasswordError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    const missingEmail = email.trim() ? null : "Escriba el correo.";
    const missingPassword = password ? null : "Escriba la contraseña.";
    setEmailError(missingEmail);
    setPasswordError(missingPassword);
    setError(null);
    if (missingEmail || missingPassword) return;
    setBusy(true);
    try {
      await api("/auth/login", { json: { email: email.trim(), password }, noSessionRedirect: true });
      // Navegación completa para que todo el panel se renderice ya con la sesión.
      window.location.assign(next);
    } catch (cause) {
      setBusy(false);
      setPassword("");
      if (cause instanceof AdminApiError && cause.status === 429) {
        setError("Demasiados intentos fallidos. El acceso con este correo queda bloqueado 15 minutos.");
      } else if (cause instanceof AdminApiError && (cause.status === 401 || cause.status === 400 || cause.status === 422)) {
        setError("Correo o contraseña incorrectos.");
      } else {
        setError("No fue posible iniciar sesión. Intente de nuevo en unos minutos.");
      }
    }
  };

  return (
    <main id="contenido" tabIndex={-1} className="flex min-h-svh items-center justify-center p-4 outline-none">
      <div className="w-full max-w-sm">
        <Wordmark className="h-20" />
        <h1 className="a-h2 mt-1">Panel de administración</h1>
        {expired ? (
          <p role="status" className="a-notice mt-4">
            La sesión terminó. Vuelva a entrar para continuar.
          </p>
        ) : null}
        <form onSubmit={submit} noValidate className="mt-6 space-y-4">
          <TextField
            label="Correo"
            type="email"
            autoComplete="username"
            value={email}
            onChange={setEmail}
            error={emailError}
            required
            autoFocus
          />
          <TextField
            label="Contraseña"
            type="password"
            autoComplete="current-password"
            value={password}
            onChange={setPassword}
            error={passwordError}
            required
          />
          {error ? (
            <p role="alert" className="a-alert">
              {error}
            </p>
          ) : null}
          <button type="submit" disabled={busy} className="a-btn a-btn-primary w-full">
            {busy ? "Entrando" : "Entrar"}
          </button>
        </form>
      </div>
    </main>
  );
}
