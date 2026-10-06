// Configuración pública de build. No colocar secretos en variables VITE_*.
export const env = {
  apiBaseUrl: import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000",
  siteUrl: import.meta.env.VITE_SITE_URL ?? "http://localhost:5173",
  demoMode: (import.meta.env.VITE_DEMO_MODE ?? "true") !== "false",
};
