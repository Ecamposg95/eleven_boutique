export const SOLD_OUT_LABEL = "Agotada · consulta disponibilidad";

/** Aviso editorial de pieza agotada: texto en cursiva, sin insignia ni caja. */
export function SoldOutLabel({ className = "" }: { className?: string }) {
  return <span className={`serif muted block text-15 italic ${className}`.trim()}>{SOLD_OUT_LABEL}</span>;
}
