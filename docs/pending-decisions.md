# Decisiones y dependencias pendientes

Registro vivo. Cada pendiente tiene responsable y la entrega que bloquea. Mientras siga abierto
se avanza con fixtures, adaptadores o placeholders **identificados**; ningún supuesto se publica
como dato real.

Responsable por defecto: **Emmanuel Campos (EC)**, producto Atlas Tech, hasta que asigne a otra
persona de Eleven.

Estados: `abierto` · `en curso` · `resuelto` (con fecha y referencia).

## Resueltas

| # | Decisión | Resolución | Fecha | Ref. |
|---|---|---|---|---|
| R-01 | ¿Existe ADF reutilizable? | No; se define en el proyecto | 2026-10-06 | ADR-0001 |
| R-02 | Render y SEO de la web pública | Vite + React Router con prerender | 2026-10-06 | ADR-0002 |
| R-03 | Alcance técnico de E1 | Web + API de catálogo mínima (FastAPI + Postgres) | 2026-10-06 | ADR-0001 |
| R-04 | Hosting del preview | Railway: web estática, API y Postgres | 2026-10-06 | ADR-0001 |
| R-05 | Entorno local | Docker Compose | 2026-10-06 | ADR-0001 |
| R-06 | Número de WhatsApp para el botón de contacto | +525639748035, desde configuración | 2026-10-06 | — |

## Abiertas

| # | Pendiente | Responsable | Bloquea | Mientras tanto |
|---|---|---|---|---|
| P-01 | Dominio definitivo y acceso DNS | EC | Producción | Dominio de Railway en el preview |
| P-02 | Direcciones y horarios por punto de venta | EC / Eleven | Sección Tiendas | Sección omitida |
| P-03 | Número final de tiendas y puestos | EC / Eleven | Modelo Location real | `Location` sin número fijo en código |
| P-04 | Política de envíos, cambios y apartados | Eleven | Texto público, agente (E4) | Placeholder «pendiente de aprobación» |
| P-05 | Aviso de privacidad (LFPDPPP) y uso de cookies/analítica | Eleven / legal | Leads (E2+), WhatsApp (E4), analítica real | Placeholder; sin capturar datos personales en E1 |
| P-06 | Precios aprobados y su fuente | Eleven | Publicar precios | «Consultar precio» |
| P-07 | Catálogo maestro: número de productos y variantes, taxonomía | Eleven / EC | E2, primer lote real (EB-14) | Fixtures demo |
| P-08 | Conciliación de los Excel (`catalogo_2026-09-21_corregido.xlsx`, `Eleven_Catalogo_Propuesto_desde_Hoja1.xlsx`) | EC | EB-09 | Solo análisis de estructura |
| P-09 | Responsable de aprobar catálogo y fotos | Eleven | E2, E3 | — |
| P-10 | Plataforma web existente, si la hay (migración, redirecciones) | EC | Producción | Se asume que no hay |
| P-11 | Propietario de cuentas: dominio, hosting, Meta Business Portfolio, WABA | EC / Eleven | E4, producción | — |
| P-12 | Estado del número de WhatsApp (app, coexistencia, migración a API) | EC | E4 | Solo enlace `wa.me` |
| P-13 | Proveedor de WhatsApp (Cloud API directa o BSP; aclarar la recomendación «zernio») | EC | E4 | Adaptador independiente del proveedor |
| P-14 | Proveedor y presupuesto de IA (atributos y embeddings) | EC | E3 | — |
| P-15 | Acceso a repositorio, OpenAPI y entorno de pruebas de Atlas ONE | Atlas Tech | E5 (EB-15) | `MockAtlasAdapter` identificado |
| P-16 | Origen y autoridad del stock; semántica de cantidades netas | Atlas Tech / Eleven | E5, E6 | Disponibilidad `unknown` |
| P-17 | Pasarela de pago | EC / Eleven | E6 | Checkout demo, `PAYMENTS_ENABLED=false` |
| P-18 | Fotografía editorial autorizada para el hero | Eleven | Landing final | Foto de la muestra o placeholder identificado |
| P-19 | Herramienta de analítica | EC | Medición real | Capa de eventos propia sin proveedor |
| P-20 | Redes sociales confirmadas para el pie | Eleven | Pie de página | Omitidas |
| P-21 | Proyecto y presupuesto de Railway | EC | Despliegue del preview (EB-07) | Solo local |
| P-22 | Licencia y uso del logo `eleven_boutique_logo_vector.svg` (versiones claro/oscuro) | Eleven | EB-03 | Logo original sin modificar |

## Supuestos activos

Se usan para avanzar, son reversibles y no se publican como hechos.

| # | Supuesto | Dónde aplica |
|---|---|---|
| S-01 | Fuentes con licencia abierta alojadas en el sitio (serif editorial para títulos, Inter para texto) | EB-03 |
| S-02 | 24–40 productos demo con nombres genéricos, sin marcas de terceros | EB-05 |
| S-03 | Demo sin precio («Consultar precio») salvo que el preview necesite precios ficticios para totales del carrito; en ese caso, rotulados como demo | EB-05, EB-06 |
| S-04 | Un solo tenant real (Eleven) más un tenant demo | EB-02 |
