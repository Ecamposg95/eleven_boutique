import type { ReactNode } from "react";

export function PageHeader({ title, children }: { title: string; children?: ReactNode }) {
  return (
    <header className="page pb-10 pt-14 md:pb-16 md:pt-24">
      <h1 className="display text-68">{title}</h1>
      {children}
    </header>
  );
}
