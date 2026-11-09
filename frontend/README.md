# Eleven Boutique: sitio público

Next.js (App Router) sobre la API de `backend/`. Sin precios, carrito ni pago.

```sh
cd frontend
npm install
cp .env.example .env.local
npm run dev            # http://localhost:3000, con la API en :8000
```

Verificación:

```sh
npm run lint
npm run typecheck      # next typegen + tsc --noEmit
npm test
npm run build          # no necesita la API
npm start
```


## Variables

| Variable | Default | Nota |
|---|---|---|
| `API_URL` | `http://localhost:8000/api/v1` | El servidor la lee al ejecutar; el rewrite `/api/v1/*` la fija al compilar |
| `NEXT_PUBLIC_SITE_URL` | `http://localhost:3000` | Canonical, Open Graph y sitemap. Se fija al compilar |
| `NEXT_PUBLIC_IMAGE_HOSTS` | vacío | Hostnames HTTPS que pasan por el optimizador, separados por coma. Se fija al compilar |

## Pendiente

`components/Wordmark.tsx` es un wordmark de texto provisional: se reemplaza ese archivo al recibir el activo del propietario.
