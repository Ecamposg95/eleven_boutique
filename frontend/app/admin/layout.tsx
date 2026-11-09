import type { Metadata } from "next";
import type { ReactNode } from "react";
import "./admin.css";

export const metadata: Metadata = {
  title: { default: "Panel", template: "%s | Panel Eleven" },
  robots: { index: false, follow: false, nocache: true },
  openGraph: null,
  alternates: null,
};

export default function AdminLayout({ children }: { children: ReactNode }) {
  return <div className="a-root flex-1">{children}</div>;
}
