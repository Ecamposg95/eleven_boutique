import Link from "next/link";

export default function Forbidden() {
  return (
    <>
      <h1 className="a-h1">Sin permiso para esta sección</h1>
      <p className="measure mt-2">
        Este usuario no puede abrir esta pantalla. Si la necesita, pida a un administrador que cambie su rol.
      </p>
      <p className="mt-4">
        <Link href="/admin" prefetch={false} className="a-btn">
          Ir al inicio
        </Link>
      </p>
    </>
  );
}
