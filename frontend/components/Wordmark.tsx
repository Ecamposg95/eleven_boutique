/**
 * Wordmark tipográfico provisional. No existe activo original del logotipo:
 * al recibirlo del propietario, se reemplaza solo este archivo.
 */
export function Wordmark({ className = "text-30" }: { className?: string }) {
  return <span className={`display leading-none ${className}`}>Eleven</span>;
}
