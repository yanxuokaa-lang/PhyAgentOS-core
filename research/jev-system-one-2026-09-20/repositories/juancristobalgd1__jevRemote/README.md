# jevRemote

`jevRemote` es una prueba reproducible de automatización web basada en decisiones de texto con [Jev](https://typesafe.ai/) —el modelo `jev-latest` de TypeSafe AI— y Playwright.

## Qué se está probando

En cada iteración, el programa:

1. Abre `TARGET_URL` con Chromium.
2. Detecta enlaces, botones y controles con rol `button` que sean visibles y tengan una etiqueta textual.
3. Envía a TypeSafe el estado estructurado de la pantalla y una pregunta `choice` cuyas opciones son esas etiquetas.
4. Hace clic en la opción elegida y repite hasta `MAX_STEPS` o hasta que no queden elementos etiquetados.

La CLI imprime la etiqueta elegida, la confianza y la latencia medida desde justo antes de `fetch()` hasta recibir y analizar la respuesta HTTP. La medición no demuestra que todas las llamadas vayan a ~90 ms: depende de red, región, tamaño del estado, carga del servicio y otros factores.

Este proyecto verifica el contrato observable de decisión sobre texto. No intenta demostrar cómo está implementado internamente Jev ni atribuirle una arquitectura concreta.

## Qué reproduce fielmente y qué se sustituye

Se reproduce fielmente la parte verificable descrita en el hilo: una petición `POST` a `https://api.typesafe.ai/v1/systemone`, con `Authorization: Bearer ...`, el modelo `jev-latest`, una pregunta `choice`, un mapa `criteria` y el consumo de `choice`, `probabilities` y `confidence`.

La percepción visual local de macOS basada en CoreML/OCR se sustituye aquí por inspección del DOM con Playwright. No se toman capturas de pantalla ni se envían píxeles a TypeSafe: solo se envían el objetivo, el contexto estructurado y las etiquetas detectadas.

## Requisitos

- Node.js 20.6 o superior.
- Una API key de TypeSafe AI.
- Chromium de Playwright para la CLI.

## Uso de la CLI

```bash
npm install
npx playwright install chromium
cp .env.example .env
```

Edita `.env`:

```dotenv
TYPESAFE_API_KEY=ts_...
TARGET_URL=https://example.com
GOAL=Open the most useful information page
MAX_STEPS=3
HEADLESS=true
```

Ejecuta:

```bash
npm run start
```

También están disponibles:

```bash
npm run check  # comprobación TypeScript sin emitir archivos
npm test       # build + tests unitarios sin API key
npm run dev    # build + ejecución de la CLI
```

Ejemplo de salida:

```text
[step 1/3] click="More information..." confidence=84.0% latency=96.7ms
[done] Reached MAX_STEPS=3.
```

La CLI necesita que la URL de destino permita el comportamiento esperado después de cada clic. Para una prueba segura, usa una página de staging o de demostración; el programa puede interactuar con cualquier botón o enlace que Playwright encuentre visible.

## Demo web estática

La demo está en [`docs/index.html`](docs/index.html) y no necesita build ni dependencias externas. Permite pegar una API key, escribir un objetivo y simular la pantalla mediante una etiqueta por línea.

La API key solo vive en la memoria de esa pestaña durante la petición. No se guarda en `localStorage`, cookies, URLs ni en este repositorio; la petición la envía directamente al endpoint de TypeSafe porque la demo es estática. Si el endpoint no permite CORS para GitHub Pages, el navegador bloqueará la llamada y la interfaz lo indicará claramente. En ese caso, utiliza la CLI, que ejecuta la petición desde Node.

## Seguridad y límites

- `.env` está ignorado por Git; nunca subas una API key real.
- La demo es deliberadamente directa: no incluye un proxy que pudiera ocultar el destino o almacenar credenciales.
- El detector solo considera elementos visibles con texto, `aria-label`, `title`, `value` o `alt` de imagen.
- No hay garantía de que la decisión sea correcta ni de que el bucle alcance el objetivo; `MAX_STEPS` limita el riesgo de navegación accidental.
- La latencia impresa es la de la llamada HTTP completa observada por el proceso, no una promesa de rendimiento universal.

## Estructura

```text
src/typesafe.ts   contrato HTTP y validación de respuestas TypeSafe
src/perception.ts detección DOM de elementos clicables
src/runner.ts     loop detectar → decidir → hacer clic
src/cli.ts        configuración por entorno y lanzamiento de Chromium
test/             pruebas unitarias locales sin API key
docs/index.html   demo estática para GitHub Pages
```

Documentación oficial del endpoint: [docs.typesafe.ai/api](https://docs.typesafe.ai/api).

