import Link from "next/link";

export function EmptyState({ message, href, action }: { message: string; href?: string; action?: string }) {
  return (
    <div className="pb-24">
      <p className="serif measure text-30">{message}</p>
      {href && action ? (
        <p className="mt-6">
          <Link href={href} className="link text-15">
            {action}
          </Link>
        </p>
      ) : null}
    </div>
  );
}
