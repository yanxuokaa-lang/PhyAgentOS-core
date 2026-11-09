# typesafe-translate

Escribe algo normal y obtén las variables que necesita TypeSafe — y, por defecto, la respuesta ya ejecutada.

TypeSafe no genera texto, así que un LLM local (tu flota Ollama: `qwen3.8:27b` @ corsair)
**compila** tu frase en un request TypeSafe válido `{state, questions{...}}`, se valida,
y se llama a la API de TypeSafe (Jev / System One).

## Uso

```bash
export TYPESAFE_API_KEY=...

# contenido embebido en la propia frase
typesafe-translate "dime si este ticket es urgente (de baja a crítica) y su tono (calmado/frustrado/enfadado): 'me cobraron dos veces!!'"

# contenido por stdin; la frase describe solo los juicios
echo "<email o ticket>" | typesafe-translate "clasifica si es queja/pregunta/mejora y si requiere respuesta urgente"

# solo genera el esquema (no ejecuta), para revisarlo o reusarlo
typesafe-translate "..." --json
```

Salida de ejemplo:
```
modelo: jev-1.13.0   tokens_in: 409
  • urgencia   [score]  1.99/3 → Alta: bloqueo grave o pérdida activa de dinero/datos.  (conf 0.99)
  • tono       [choice] enfadado  (conf 0.52)  [enfadado=0.68 frustrado=0.32 calmado=0.00]
```

## Cómo elige el tipo

El compilador aplica las reglas de TypeSafe: escala ordenada → **score** (niveles concretos
e independientes), categorías sin orden → **choice**, condición sí/no → **noul**. Una pregunta
por juicio; no inventa juicios que no pediste.

## Fallback automático de la flota

Si el host primario no responde, el CLI **no falla**: recorre una cadena de hosts hasta que
uno compila el request. Antes de cada intento hace un chequeo rápido de vida (`/api/tags`, 4 s)
para no bloquearse en un host caído. Si el host caído es despertable, pide a **ollawake**
(`/ensure/<host>`) que lo levante y reintenta una vez; si no, pasa al siguiente.

Cadena por defecto (ver con `typesafe-translate x --chain`):

1. `corsair` · `qwen3.8:27b`  (primario, despertable)
2. `corsair` · `qwen3.6:35b-a3b`  (mismo host, modelo alterno)
3. `mac-studio` · `ornith-1.5:35b`
4. `alien18` · `qwen3:14b`

También se reintenta el siguiente host si uno devuelve JSON irreparable. Se cae con error
claro solo si **ningún** host responde.

## Flags / entorno

| Flag | Env | Default |
|---|---|---|
| `--llm-url` | — | forzar un host (desactiva el fallback) |
| `--llm-model` | — | modelo para `--llm-url` |
| — | `TS_TRANSLATE_LLM_CHAIN` | JSON `[{label,url,model,wake?}]` para sustituir la cadena entera |
| — | `TS_TRANSLATE_OLLAWAKE` | `http://100.70.244.85:11436` |
| `--ts-model` | `TS_TRANSLATE_TS_MODEL` | `jev-latest` |
| `-c/--content` | — | contenido a evaluar (si no, stdin o el propio texto) |
| `--json` | — | solo imprime el request (no ejecuta) |
| `--chain` | — | imprime la cadena de fallback efectiva y sale |
| `--show` | — | imprime también el request generado (a stderr) al ejecutar |

`--llm-url`/`--llm-model` fuerzan un único host (sin cadena). Para cambiar la cadena
completa usa `TS_TRANSLATE_LLM_CHAIN`.

## Notas de robustez

- `think:false` + strip `<think>` (modelos híbridos qwen3).
- `format:"json"` + **reparación de llaves/corchetes** desbalanceados (los LLMs a veces
  se dejan un `}`); ver `_balance_repair`.
- La key de TypeSafe solo se lee del entorno; nunca se escribe a disco.

## Tests

```bash
python3 test_translate.py     # offline: reparación JSON + validación (sin red)
```
