export type Named = { name: string; aliases?: string[] };
export type LetterGroup<T> = { letter: string; anchor: string; items: T[] };

export const OTHER_GROUP = "#";

/** Minúsculas y sin acentos: "Canadá" -> "canada". */
export function normalize(text: string): string {
  return text
    .normalize("NFD")
    .replace(/\p{Diacritic}/gu, "")
    .toLowerCase()
    .trim();
}

/** Además ignora espacios y puntuación: "Arc'teryx" y "arcteryx" coinciden. */
function compact(text: string): string {
  return normalize(text).replace(/[^\p{L}\p{N}]/gu, "");
}

/** Letra A-Z bajo la que se archiva un nombre; todo lo demás va a "#". */
export function groupLetter(name: string): string {
  const first = normalize(name).charAt(0).toUpperCase();
  return first >= "A" && first <= "Z" ? first : OTHER_GROUP;
}

/** Agrupa por letra con orden alfabético en español; "#" queda al final. */
export function groupByLetter<T extends Named>(items: readonly T[]): LetterGroup<T>[] {
  const groups = new Map<string, T[]>();
  for (const item of items) {
    const letter = groupLetter(item.name);
    const bucket = groups.get(letter);
    if (bucket) bucket.push(item);
    else groups.set(letter, [item]);
  }
  return [...groups.entries()]
    .sort(([a], [b]) => {
      if (a === OTHER_GROUP) return 1;
      if (b === OTHER_GROUP) return -1;
      return a.localeCompare(b, "es");
    })
    .map(([letter, bucket]) => ({
      letter,
      anchor: letter === OTHER_GROUP ? "letra-otros" : `letra-${letter.toLowerCase()}`,
      items: [...bucket].sort((a, b) => a.name.localeCompare(b.name, "es", { sensitivity: "base" })),
    }));
}

/** Filtro por nombre y alias, sin distinguir mayúsculas ni acentos. */
export function filterByName<T extends Named>(items: readonly T[], query: string): T[] {
  const needle = compact(query);
  if (!needle) return [...items];
  return items.filter((item) =>
    [item.name, ...(item.aliases ?? [])].some((text) => compact(text).includes(needle)),
  );
}
