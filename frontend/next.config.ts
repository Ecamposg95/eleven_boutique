import type { NextConfig } from "next";
import { parseImageHosts } from "./lib/images";

const apiUrl = (process.env.API_URL ?? "http://localhost:8000/api/v1").replace(/\/+$/, "");

// La API sirve los archivos fuera de /api/v1: /media cuelga de la raíz del backend.
const backendOrigin = apiUrl.replace(/\/api\/v\d+$/, "");

const config: NextConfig = {
  // forbidden() para la pantalla de sin permiso del panel.
  experimental: { authInterrupts: true },
  images: {
    localPatterns: [
      { pathname: "/media/**", search: "" },
      { pathname: "/demo/**", search: "" },
    ],
    remotePatterns: parseImageHosts(process.env.NEXT_PUBLIC_IMAGE_HOSTS).map((hostname) => ({
      protocol: "https" as const,
      hostname,
    })),
  },
  async rewrites() {
    return [
      { source: "/api/v1/:path*", destination: `${apiUrl}/:path*` },
      { source: "/media/:path*", destination: `${backendOrigin}/media/:path*` },
    ];
  },
  async headers() {
    return [{ source: "/admin/:path*", headers: [{ key: "X-Robots-Tag", value: "noindex, nofollow" }] }];
  },
};

export default config;
