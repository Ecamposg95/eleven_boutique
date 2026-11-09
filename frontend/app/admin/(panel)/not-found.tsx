import Link from "next/link";

export default function NotFound() {
  return (
    <>
      <h1 className="a-h1">Este registro no existe</h1>
      <p className="measure mt-2">Puede que la dirección esté mal escrita o que el registro se haya quitado.</p>
      <p className="mt-4">
        <Link href="/admin" prefetch={false} className="a-btn">
          Ir al inicio
        </Link>
      </p>
    </>
  );
}
