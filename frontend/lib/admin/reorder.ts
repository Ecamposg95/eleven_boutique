/** Devuelve una copia con el elemento movido. Índices fuera de rango no cambian nada. */
export function moveItem<T>(list: readonly T[], from: number, to: number): T[] {
  const copy = [...list];
  if (from < 0 || from >= copy.length || to < 0 || to >= copy.length || from === to) return copy;
  const [item] = copy.splice(from, 1);
  copy.splice(to, 0, item as T);
  return copy;
}

/** Principal efectiva: la elegida si sigue en la lista; si no, la primera. */
export function resolvePrimary<T extends { id: string; is_primary: boolean }>(list: readonly T[]): string | null {
  return (list.find((item) => item.is_primary) ?? list[0])?.id ?? null;
}

/** Cuerpo de PATCH /products/{id}/media. */
export function mediaOrderPayload<T extends { id: string; is_primary: boolean }>(list: readonly T[]) {
  return { order: list.map((item) => item.id), primary_id: resolvePrimary(list) };
}

export function setPrimary<T extends { id: string; is_primary: boolean }>(list: readonly T[], id: string): T[] {
  return list.map((item) => ({ ...item, is_primary: item.id === id }));
}

export function withPositions<T extends { position: number }>(list: readonly T[]): T[] {
  return list.map((item, position) => ({ ...item, position }));
}
