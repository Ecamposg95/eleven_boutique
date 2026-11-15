# Tienda nueva: portada que se vuelve tienda y área `/tienda`

Fecha: 2026-11-14 · Estado: aprobado por el dueño el 2026-11-14

## Intención y por qué

Eleven Boutique quiere que eleven.boutique se sienta como una **landing muy premium** y, al mismo
tiempo, funcione como un **catálogo completo y elegante**. La mayoría de las visitas llegan desde
Instagram al celular, así que todo se piensa primero para teléfono. La venta se cierra por
WhatsApp: el sitio solo muestra el producto, **nunca precios**, y los botones de WhatsApp e
Instagram tienen mucho peso.

Al dueño **le gusta el estilo actual** (blanco y negro editorial, encabezado acrílico, foto a
pantalla completa con el nombre gigante ELEVEN) y quiere **más elementos y más fotografía**, no un
rediseño.

De tres estructuras posibles, el dueño eligió la **B: una portada que empieza premium y, al bajar,
ya se convierte en tienda**, más un área de catálogo completo en la ruta `eleven.boutique/tienda`.

## Objetivos

1. Portada más rica y con más fotografía, en el estilo actual, con esta historia de arriba a abajo:
   actitud → universo → lo nuevo → el detalle → las casas → el lugar y el trato → escríbenos.
2. Tres elementos nuevos que eligió el dueño:
   - **Departamentos con piezas** (pestañas por departamento con sus piezas en la misma portada).
   - **Recién llegado** (carrusel con las últimas piezas).
   - **Bloque de atención** (cierre en negro con WhatsApp e Instagram grandes).
3. Lugares para la fotografía que el dueño ya produjo (ver «Fotografía»): portada de cada
   departamento, franja de detalle panorámica y foto de la boutique.
4. Área **`/tienda`** con el catálogo completo: departamentos, subcategorías, filtro por marca y
   orden.
5. **Instagram** presente en el sitio: `https://www.instagram.com/eleven.fashionboutique/`.
6. Muy responsiva; teléfono primero.

## No objetivos

- Precios, carrito, pago o existencias exactas.
- Franja con publicaciones de Instagram incrustadas (el dueño no la eligió): Instagram es un enlace
  al perfil.
- Botones flotantes de WhatsApp/Instagram en todo el sitio (no elegidos).
- Muro de logos nuevo, franja de confianza, sección de visita/mapa (no elegidos).
- Conexión con Atlas ONE (proyecto aparte, en curso en su propio repo; ver
  `docs/atlas-one-task-pack.md`). Este diseño no debe depender de ella.

## Anti-objetivos (aunque funcione, sería un fracaso)

- Que se pierda el carácter premium/editorial actual o parezca una tienda genérica o un mercado.
- Que el teléfono se sienta lento o pesado (portada con muchas fotos: cada aparato debe bajar solo
  lo que ve, imágenes diferidas fuera de pantalla).
- Que enlaces ya compartidos (por WhatsApp o Instagram) dejen de funcionar.
- Que la portada se vea vacía o rota mientras no haya piezas publicadas (hoy hay 0 en producción).

## Estado actual (para quien construye)

- Next.js (App Router) + FastAPI + Postgres en Railway. Diseño en `docs/design-system.md`.
- Portada `frontend/app/page.tsx`, en este orden: foto a pantalla completa con fotos que se turnan
  (`HeroSlides` + `HeroPicture`, con versión de teléfono y computadora por foto, ya en producción),
  carrusel «Comprar por categoría» (`CategoryRail`), franja negra de historias (`Strip`),
  colecciones, texto de presentación, «Novedades» (cuadrícula de 4), casas destacadas
  (`HouseShowroom`), muro de marcas (`BrandWall`) y cierre «La boutique» (`Closing`).
- Cada sección se oculta sola si no tiene datos.
- Rutas públicas actuales: `/novedades`, `/categorias/[slug]` (con barra «Filtros · Ordenar»,
  `CatalogBar`), `/marcas`, `/marcas/[slug]`, `/marcas/[slug]/[producto]`, `/piezas/[slug]` (pieza
  sin marca), `/colecciones`, `/lookbooks`, `/la-boutique`, `/contacto`, `/buscar`, `/seleccion`.
- Las categorías son un árbol de dos niveles (`categories.parent_id`): 8 principales (Ropa,
  Calzado, Bolsos, Accesorios, Joyería, Relojería, Equipaje, Otros) con subcategorías.
- WhatsApp: `consult_url` por pieza y «Mi selección» (`POST /selection/consult`). Hay línea general
  y línea Boutique para casas premium. El número nunca se expone por separado.
- Fotos: biblioteca en el panel (`media_assets`); el sitio aplica blanco y negro (`.mono`).

## Portada: estructura

Orden decidido por el dueño a partir de la propuesta (los puntos marcados *[mi decisión]* los puede
cambiar quien construye si encuentra algo mejor, sin alterar la intención):

1. **Foto a pantalla completa** (ya existe, con versión de teléfono y computadora). Se le agrega un
   acceso visible a la tienda en la tarjeta del titular: «Entrar a la tienda», que lleva a
   `/tienda`. *[mi decisión: reemplaza a «Explorar marcas» como acción principal; «Explorar marcas»
   pasa a segundo enlace]*
2. **Departamentos con piezas** (nuevo; sustituye a `CategoryRail`).
3. **Recién llegado** (nuevo; sustituye a la cuadrícula «Novedades»).
4. **Franja de detalle** (nueva, foto panorámica).
5. Franja negra de historias, colecciones y texto de presentación (se quedan).
6. Casas destacadas y muro de marcas (se quedan).
7. «La boutique» (se queda; hoy solo aparece si hay texto de la boutique).
8. **Bloque de atención** (nuevo), al final.

### 2 · Departamentos con piezas

- Pestañas con los departamentos principales que tienen piezas, en el orden de `display_order`.
- Cada pestaña muestra: la **foto de portada del departamento** (nueva, 4:5) como primera ficha
  grande, seguida de hasta 8 piezas recientes de ese departamento *[mi decisión]* y un enlace «Ver
  todo [departamento] →» a `/tienda/[departamento]`.
- En teléfono, pestañas y piezas se deslizan de lado.
- Accesible: patrón de pestañas con teclado (flechas) y lector de pantalla.
- **Sin piezas publicadas**: la sección se muestra igual con las fotos de portada de los
  departamentos que tengan foto, como fichas que llevan a `/tienda/[departamento]`. Si no hay ni
  piezas ni fotos, se oculta.

### 3 · Recién llegado

- Carrusel con hasta 12 piezas *[mi decisión]*, de la más reciente a la más antigua, misma ficha
  que hoy (`ProductCard`, 4:5 con segunda foto al pasar el cursor).
- En teléfono se desliza con el dedo; en computadora, flechas como en `CategoryRail`.
- «Ver todas →» lleva a `/tienda?orden=recientes` *[mi decisión: `/novedades` redirige ahí]*.
- Sin piezas, se oculta.

### 4 · Franja de detalle

- Una foto panorámica a todo lo ancho (21:9 en computadora; recorte central 4:5 en teléfono, o una
  versión de teléfono si se carga).
- Sin texto encima, o una sola línea editable opcional *[mi decisión: campo opcional en el panel]*.
- Sin foto, se oculta.

### 8 · Bloque de atención

- Fondo negro; detrás, la foto de la boutique (16:9 en computadora, 4:5 en teléfono) en blanco y
  negro, con la mitad izquierda tranquila para el texto.
- Texto: «Escríbenos. Te asesoramos.» *[mi decisión: titular y subtítulo editables en el panel,
  con ese texto por defecto]*.
- Botones: **WhatsApp** (principal, grande) e **Instagram** (secundario, igual de visible).
  - WhatsApp abre un mensaje general, no el de una pieza: «Hola, me gustaría recibir atención
    personalizada de Eleven Boutique.» *[mi decisión]*, a la línea general.
  - Si existe línea Boutique distinta de la general, un segundo enlace «Línea Boutique (casas
    premium)» *[mi decisión]*.
  - El número no se expone en el HTML más allá del enlace `wa.me` (igual que hoy en las piezas);
    la API devuelve el enlace armado.
- Sin WhatsApp configurado, solo Instagram; sin ninguno, se oculta.

## Área `/tienda`

- `/tienda`: todo el catálogo. Arriba, chips de departamentos; abajo, la cuadrícula con la barra
  «Filtros · Ordenar». Hoy esa barra filtra por subcategoría y ordena; **se le agrega filtro por
  marca** (solo marcas con piezas dentro del filtro actual), combinable con departamento y
  subcategoría *[mi decisión: entra en esta entrega, porque el dueño pidió que se sepa qué marcas se
  venden]*. Paginada como hoy.
- `/tienda/[departamento]` y `/tienda/[departamento]/[subcategoría]`: el mismo listado filtrado.
  Encabezado con la foto de portada del departamento si existe.
- Las fichas de pieza y de marca pasan bajo la tienda *[mi decisión]*:
  `/tienda/marcas/[marca]`, `/tienda/marcas/[marca]/[pieza]`, `/tienda/piezas/[pieza]`.
- **Redirecciones permanentes (301)** desde todas las rutas viejas: `/categorias/*`, `/novedades`,
  `/marcas/*`, `/piezas/*`. También hay que actualizar el enlace que viaja en los mensajes de
  WhatsApp (`backend/app/services/whatsapp.py`, `Piece.link`), el sitemap, los datos estructurados
  y las URLs canónicas.
- Menú lateral: «Tienda» como primera entrada, con Novedades, Categorías y Casas dentro, o a su
  lado *[se deja a quien construye, sin perder lo que hay hoy]*.
- El encabezado agrega un acceso «Tienda» visible *[mi decisión]*.

## Instagram

- Configurable en el panel (campo `instagram_url` en ajustes del sitio), con valor inicial
  `https://www.instagram.com/eleven.fashionboutique/`.
- Aparece en: el bloque de atención, el pie del sitio y el menú lateral *[mi decisión]*.
- Enlace externo, `rel="noopener"`; ícono más la palabra «Instagram» (no solo ícono).

## Fotografía

Medidas y propósito (la guía completa la vio el dueño; el panel debe mostrar estas medidas como
ayuda):

| Lugar | Formato | Medida ideal | Dónde se carga |
|---|---|---|---|
| Portada (ya existe) | 16:9 + versión 9:16 | 2880×1620 / 1080×1920 | Ajustes del sitio |
| Portada de departamento (nuevo) | 4:5 | 1600×2000 | Panel → Categorías, solo las principales. **Una foto por departamento** *[mi decisión]* |
| Franja de detalle (nuevo) | 21:9 (+ 4:5 opcional para teléfono) | 2880×1234 | Ajustes del sitio |
| Boutique / atención (nuevo) | 16:9 + 4:5 | 2880×1620 / 1600×2000 | Ajustes del sitio |
| Producto (ya existe) | 4:5 | 2000×2500 | Ficha de producto |

Fotos ya subidas a la biblioteca de producción para asignar al terminar:

| Foto | Destino |
|---|---|
| 07 gabardina de piel | Ropa *[mi decisión; 05 suéter y 10 pantalón quedan en la biblioteca]* |
| 12 botín vino | Calzado |
| 13 bolso vino | Bolsos |
| 15 cinturón | Accesorios |
| 14 piel con costura, 1913×822 | Franja de detalle |
| 16 boutique, persona doblando un suéter | Bloque de atención |

**Quién asigna:** Claude, en la sesión de construcción, después de que el dueño publique el código y
el despliegue termine. Lo hace como con la portada: por `railway ssh --service api`, buscando los
`media_assets` de producción por nombre de archivo (`ChatGPT Image Nov 14_ 2026_ 06_5x_xx PM.png`) y
comprobando en el sitio en vivo. El plan incluye esa tarea de datos al final. No va en una
migración, porque los IDs de producción no viven en el repo.

Joyería, Relojería y Equipaje todavía no tienen foto: sin foto, su ficha usa la pieza más reciente,
como hoy.

Las fotos son generadas con IA: se usan como **ambiente**, nunca como fichas de producto (el
catálogo debe ser fiel a lo que hay en venta).

## Restricciones

- Mantener el sistema de diseño actual (`docs/design-system.md`), tipografías, blanco y negro y
  ritmo editorial.
- Teléfono primero; sin desplazamiento horizontal de la página; objetivos táctiles ≥ 44 px.
- Rendimiento: solo la primera foto de portada se precarga; el resto, diferido. Cada aparato baja
  solo su versión.
- Cambios de base de datos con Alembic (el backend ya lo usa), aditivos.
- El panel sigue siendo la forma de cargar todo; nada de contenido escrito en el código salvo
  valores por defecto.
- Deploy: push a `main` despliega a Railway. Quien construye no puede hacer push: lo hace el dueño.

## Lo que se deja a quien construye

- Componentes, nombres, estructura de rutas internas de Next y forma exacta de los endpoints.
- Animaciones y microinteracciones dentro del estilo actual (`Reveal`, fundidos).
- Cómo reorganizar el menú lateral, siempre que «Tienda» sea lo primero.
- Pruebas: seguir la práctica del repo (pytest en backend; vitest para lógica del frontend) y
  revisar en navegador en teléfono y computadora.
