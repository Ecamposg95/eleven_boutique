"use client";

import { useRouter } from "next/navigation";
import { type FormEvent, useState } from "react";
import { api, errorText } from "@/lib/admin/client";
import { TextField } from "./ui";

/** Alta mínima: pide el nombre, crea en borrador y abre la edición. El servidor genera el slug. */
export function CreateByName({
  endpoint,
  field,
  label,
  action,
  basePath,
}: {
  endpoint: string;
  field: "name" | "title";
  label: string;
  action: string;
  basePath: string;
}) {
  const router = useRouter();
  const [value, setValue] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    const clean = value.trim();
    if (!clean) {
      setError("Escriba un nombre.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const created = await api<{ id: string }>(endpoint, { json: { [field]: clean, status: "draft" } });
      router.push(`${basePath}/${created.id}`);
    } catch (cause) {
      setError(errorText(cause));
      setBusy(false);
    }
  };

  return (
    <form onSubmit={submit} noValidate className="flex flex-wrap items-start gap-2">
      <TextField label={label} value={value} onChange={setValue} error={error} className="min-w-60 flex-1 sm:max-w-sm" />
      <button type="submit" className="a-btn sm:mt-[1.625rem]" disabled={busy}>
        {action}
      </button>
    </form>
  );
}
