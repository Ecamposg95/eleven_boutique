"use client";

import { useRouter } from "next/navigation";
import { type FormEvent, useState } from "react";
import { AdminApiError, api, errorText } from "@/lib/admin/client";
import type { AdminCategory } from "@/lib/admin/types";
import { Empty, Notice, TextField, useConfirm, useUnsavedWarning } from "./ui";

function Row({ category, all, onDirty }: { category: AdminCategory; all: AdminCategory[]; onDirty: (id: string, dirty: boolean) => void }) {
  const router = useRouter();
  const [name, setName] = useState(category.name);
  const [parent, setParent] = useState(category.parent_id ?? "");
  const [saved, setSaved] = useState({ name: category.name, parent: category.parent_id ?? "" });
  const [error, setError] = useState<string | null>(null);
  const [note, setNote] = useState<string | null>(null);
  const [confirm, dialog] = useConfirm();
  const dirty = name !== saved.name || parent !== saved.parent;

  const update = (nextName: string, nextParent: string) => {
    setName(nextName);
    setParent(nextParent);
    setNote(null);
    onDirty(category.id, nextName !== saved.name || nextParent !== saved.parent);
  };

  const save = async () => {
    if (!name.trim()) {
      setError("Escriba el nombre.");
      return;
    }
    try {
      await api(`/categories/${category.id}`, { method: "PATCH", json: { name: name.trim(), parent_id: parent || null } });
      setSaved({ name: name.trim(), parent });
      setError(null);
      setNote("Guardada");
      onDirty(category.id, false);
      router.refresh();
    } catch (cause) {
      setError(errorText(cause));
    }
  };

  const remove = async () => {
    const accepted = await confirm({ title: `¿Eliminar la categoría ${saved.name}?`, confirmLabel: "Eliminar categoría" });
    if (!accepted) return;
    try {
      await api(`/categories/${category.id}`, { method: "DELETE" });
      onDirty(category.id, false);
      router.refresh();
    } catch (cause) {
      setError(
        cause instanceof AdminApiError && cause.status === 409
          ? "No se puede eliminar: tiene productos o subcategorías. Muévalos a otra categoría primero."
          : errorText(cause),
      );
    }
  };

  const errorId = `cat-err-${category.id}`;
  return (
    <tr data-category={category.id}>
      <td>
        <label htmlFor={`cat-${category.id}`} className="sr-only">
          Nombre de {saved.name}
        </label>
        <input
          id={`cat-${category.id}`}
          className="a-input"
          value={name}
          aria-invalid={error ? true : undefined}
          aria-describedby={error ? errorId : undefined}
          onChange={(event) => update(event.target.value, parent)}
        />
        {error ? (
          <p id={errorId} role="alert" className="a-error">
            {error}
          </p>
        ) : null}
      </td>
      <td className="max-sm:hidden">
        <label htmlFor={`cat-p-${category.id}`} className="sr-only">
          Categoría superior de {saved.name}
        </label>
        <select id={`cat-p-${category.id}`} className="a-input" value={parent} onChange={(event) => update(name, event.target.value)}>
          <option value="">Ninguna</option>
          {all
            .filter((other) => other.id !== category.id)
            .map((other) => (
              <option key={other.id} value={other.id}>
                {other.name}
              </option>
            ))}
        </select>
      </td>
      <td className="max-md:hidden">{category.product_count}</td>
      <td>
        <div className="flex flex-wrap items-center justify-end gap-2">
          {note ? (
            <span role="status" className="muted">
              {note}
            </span>
          ) : null}
          <button type="button" className="a-btn a-btn-small" disabled={!dirty} aria-label={`Guardar ${saved.name}`} onClick={() => void save()}>
            Guardar
          </button>
          <button type="button" className="a-btn a-btn-quiet a-btn-small" aria-label={`Eliminar ${saved.name}`} onClick={() => void remove()}>
            Eliminar
          </button>
        </div>
        {dialog}
      </td>
    </tr>
  );
}

export function CategoryManager({ categories }: { categories: AdminCategory[] }) {
  const router = useRouter();
  const [name, setName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const [dirtyIds, setDirtyIds] = useState<Set<string>>(new Set());
  useUnsavedWarning(dirtyIds.size > 0);

  const onDirty = (id: string, dirty: boolean) =>
    setDirtyIds((current) => {
      if (current.has(id) === dirty) return current;
      const next = new Set(current);
      if (dirty) next.add(id);
      else next.delete(id);
      return next;
    });

  const add = async (event: FormEvent) => {
    event.preventDefault();
    const clean = name.trim();
    setFormError(null);
    if (!clean) {
      setError("Escriba un nombre.");
      return;
    }
    setError(null);
    try {
      await api("/categories", { json: { name: clean, parent_id: null } });
      setName("");
      router.refresh();
    } catch (cause) {
      setFormError(errorText(cause));
    }
  };

  return (
    <>
      {categories.length === 0 ? (
        <Empty message="Aún no hay categorías. Se crean aquí o al importar el catálogo." />
      ) : (
        <table className="a-table">
          <caption className="sr-only">Categorías</caption>
          <thead>
            <tr>
              <th scope="col">Nombre</th>
              <th scope="col" className="max-sm:hidden">
                Categoría superior
              </th>
              <th scope="col" className="max-md:hidden">
                Productos
              </th>
              <th scope="col">
                <span className="sr-only">Acciones</span>
              </th>
            </tr>
          </thead>
          <tbody>
            {categories.map((category) => (
              <Row key={category.id} category={category} all={categories} onDirty={onDirty} />
            ))}
          </tbody>
        </table>
      )}
      <form onSubmit={add} noValidate className="a-section flex flex-wrap items-start gap-2">
        <TextField label="Nueva categoría" value={name} onChange={setName} error={error} className="min-w-60 flex-1 sm:max-w-sm" />
        <button type="submit" className="a-btn sm:mt-[1.625rem]">
          Agregar categoría
        </button>
      </form>
      {formError ? (
        <div className="mt-2">
          <Notice kind="error">{formError}</Notice>
        </div>
      ) : null}
    </>
  );
}
