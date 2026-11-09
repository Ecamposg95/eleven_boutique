/**
 * Ritmo de la rejilla de producto (docs/design-system.md).
 * Escritorio: 12 columnas, cada sexta pieza ocupa el doble y desplaza a las de abajo.
 * Móvil: 2 columnas, una a ancho completo cada 5.
 */
export type RhythmSlot = { wideDesktop: boolean; wideMobile: boolean };

/** Piezas que deben seguir a la doble para que no queden huecos a sus lados. */
const FOLLOWERS_NEEDED = 3;

export function rhythmSlot(index: number, total: number): RhythmSlot {
  return {
    wideDesktop: (index + 1) % 6 === 0 && total - 1 - index >= FOLLOWERS_NEEDED,
    wideMobile: (index + 1) % 5 === 0,
  };
}
