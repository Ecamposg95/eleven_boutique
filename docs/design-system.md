# Eleven Boutique — dirección de diseño

Paleta y familias tipográficas vienen fijadas por el brief; todo lo demás es decisión de este documento.

## Tokens

Tema oscuro por decisión del propietario: invierte el uso que sugiere el brief, con la misma paleta.

| Token | HEX | Uso |
|---|---|---|
| `--color-ink` | `#1B1915` | Fondo principal (derivado de charcoal) |
| `--color-charcoal` | `#292620` | Bloques secundarios y franja demo |
| `--color-ivory` | `#F7F3EC` | Texto e interfaz |
| `--color-sand` | `#E9DFD1` | Titulares secundarios |
| `--color-taupe` | `#C7B7A3` | Texto secundario (AA sobre ink y charcoal) |
| `--color-bronze` | `#9A846B` | Bordes, foco, subrayados. Solo texto ≥ 24 px: sobre charcoal da ~4:1, no pasa AA en pequeño |

Sin blanco puro. La fotografía va directamente sobre ink.

**Tipografía:** Cormorant Garamond (300, 400, 500, con itálica) para nombres, titulares y fichas. Inter (400, 500) para navegación, botones y formularios. Cargar con `next/font`.

**Escala:** 15 / 17 / 22 / 30 / 44 / 68 / 104 px, fluida con `clamp()` en los tres mayores. Cormorant se ve pequeña: nunca por debajo de 17 px. Líneas de menos de 72 caracteres.

## La idea: el muro de casas

El activo real que Eleven ya tiene es su lista de marcas. Sin fotografía con derechos, el elemento memorable es tipográfico: los nombres de las casas corren como un solo párrafo enorme en Cormorant, como los créditos de una revista de moda. Cada nombre es un enlace. Al pasar el cursor o enfocar uno, los demás bajan a 30 % de opacidad.

Todo el resto de la interfaz queda callado para que esto destaque.

```
 Eleven                     Marcas Colecciones Novedades …  Buscar
 ------------------------------------------------------------------
 Acne Studios, Alexander McQueen, Alexander Wang, AMI Paris,
 Amiri, Arc'teryx, Asaali, Asali Jean, Audemars Piguet,
 Balenciaga, Balmain, Bottega Veneta, Brioni, Brunello
 Cucinelli, Burberry, …                  (se desvanece al final)

 Texto editorial corto                              Explorar marcas
```

**Hero con fotografía:** si `hero.image_url` existe, va a pantalla completa con wordmark, texto y CTA, y el muro baja a la sección de marcas. **Sin fotografía:** el muro es la portada. Si no hay marcas publicadas, solo wordmark y texto.

## Composición

- Alineación a la izquierda. El CTA de portada puede ir abajo a la derecha.
- **Rejilla de producto con ritmo:** 12 columnas donde cada sexta pieza ocupa el doble y las piezas bajo ella se desplazan. Móvil: 2 columnas con una a ancho completo cada 5. Sin cajas, sombras ni bordes en tarjetas: imagen, marca en Inter 15 px, nombre en Cormorant 22 px.
- **Directorio:** nombres en Cormorant 44 px, agrupados por letra. La letra se cuelga en el margen izquierdo porque ahí sí codifica información; en móvil es una barra pegajosa de índice.
- **Ficha:** galería vertical grande a la izquierda (7 columnas). A la derecha, pegajosos: marca, nombre, "Consultar esta pieza". Nada más.
- Esquinas rectas en imagen. Botones con borde ivory de 1 px y radio 0: al hover se rellenan de ivory con texto ink.

## Movimiento

- Una sola orquestación: el muro aparece por opacidad al cargar, en 700 ms.
- Reveal de solo opacidad (400 ms, una vez) para bloques editoriales, sin desplazamiento vertical.
- Fundido cruzado a la segunda imagen en hover (300 ms).
- Todo se anula con `prefers-reduced-motion`.

## Evitar

Etiquetas en mayúsculas sostenidas, eyebrows sobre títulos, numeración decorativa, separadores con punto medio, "→" en enlaces, palabra suelta en itálica dentro de un titular, tarjetas redondeadas, sombras, degradados decorativos, fuentes monoespaciadas, botón flotante de WhatsApp.

## Texto

Español de México, oraciones normales, tuteo no: trato de usted en consultas ("¿Podrían brindarme…"), impersonal en la interfaz. Ejemplos:

- Búsqueda sin resultados: "Sin resultados para «x». Revise la ortografía o explore todas las marcas."
- Sin WhatsApp configurado: el botón no se renderiza. En modo demo aparece: "Consulta desactivada: falta configurar WHATSAPP_NUMBER."

## Contenido sin confirmar

- **Logotipo:** no hay activo original. Se usa un wordmark tipográfico "Eleven" aislado en `components/Wordmark.tsx`, para reemplazarlo sin tocar nada más. Se reporta como pendiente.
- **Modo demo:** con `demo_mode=true`, franja superior fija y discreta en charcoal: "Entorno de demostración: productos e imágenes de ejemplo."
- **Nunca inventar:** direcciones, horarios, teléfonos, datos legales, relación con marcas o logotipos de marcas. Si un dato falta, no se renderiza.
