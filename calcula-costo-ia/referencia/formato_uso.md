# Formato del registro de uso

`costo_ia.py medir` lee **CSV** (separado por `,` `;` tabulador o `|`), **JSONL** (un objeto JSON por línea) o **JSON** (una lista de objetos). Los objetos anidados se aplanan: `usage.input_tokens` se reconoce igual que `input_tokens`. Mayúsculas, acentos y guiones bajos no importan.

## Columnas

| Campo | Obligatorio | Nombres que reconoce (algunos) | Nota |
|---|---|---|---|
| modelo | sí | `modelo`, `model`, `model_name`, `model_id` | Acepta IDs con fecha, `models/…`, `anthropic.…-v1:0` y `…@fecha` |
| tokens_entrada | sí (o salida) | `tokens_entrada`, `input_tokens`, `prompt_tokens`, `prompt_token_count` | Ver «¿La entrada incluye la caché?» |
| tokens_salida | sí (o entrada) | `tokens_salida`, `output_tokens`, `completion_tokens`, `candidates_token_count` | En Gemini suma también `thoughts_token_count` |
| tokens_cache_lectura | no | `tokens_cache_lectura`, `cache_read_input_tokens`, `cached_tokens`, `cached_content_token_count` | |
| tokens_cache_escritura | no | `tokens_cache_escritura`, `cache_creation_input_tokens` | |
| funcion | no (muy útil) | `funcion`, `feature`, `task`, `endpoint`, `route`, `tag` | Qué parte de tu app hizo la llamada |
| fecha | no (muy útil) | `fecha`, `timestamp`, `ts`, `created_at`, `date` | ISO 8601, `AAAA-MM-DD HH:MM:SS`, `DD/MM/AAAA HH:MM` o época en segundos/milisegundos. Con fechas se miden los días y los aciertos de caché |
| latencia_ms | no | `latencia_ms`, `latency_ms`, `duration_ms`; en segundos: `duration_s`, `latency_s` | Sin unidad (`latency`) y todos < 100: se toma en segundos y se avisa |
| ttft_ms | no | `ttft_ms`, `time_to_first_token_ms` | Tiempo al primer token; si falta, se estima |
| llamadas | no | `llamadas`, `calls`, `count`, `requests` | Una fila puede representar N llamadas iguales (útil para estimados) |
| hash_entrada | no | `hash_entrada`, `prompt_hash`, `input_hash` | Para medir preguntas repetidas sin guardar el texto |
| texto de la pregunta | no | `pregunta`, `user_message`, `query`, `mensaje` | El script solo guarda su hash; mejor registra el hash tú |

Números: acepta `1,234`, `1234` y coma decimal (`2,1`). Una fila con un valor que no es número, negativa, sin modelo, con columnas de más o de menos, con JSON roto o con un modelo que no está en `precios.json` **se ignora y se reporta con su número de línea**: el script nunca se cae por una fila.

## ¿La entrada incluye la caché?
- **Claude (Anthropic):** `input_tokens` **no** incluye la caché. Entrada total = `input_tokens + cache_read_input_tokens + cache_creation_input_tokens`.
- **OpenAI y Gemini:** `prompt_tokens` / `input_tokens` / `prompt_token_count` **sí** incluyen los tokens en caché. El script los resta solo (`--entrada-incluye-cache auto`).
- Si tu columna se llama exactamente `tokens_entrada`, el script entiende que ya **no** incluye la caché. Para forzarlo: `--entrada-incluye-cache si|no`.

## Ejemplo mínimo
Ver `ejemplo_uso.csv`. En JSONL, una línea típica:
```json
{"ts": "2026-10-14T09:00:01Z", "funcion": "resumir", "model": "claude-sonnet-5-5", "usage": {"input_tokens": 1200, "output_tokens": 450, "cache_read_input_tokens": 0, "cache_creation_input_tokens": 0}, "latency_ms": 8200, "prompt_hash": "1b55b58c78ee4614"}
```

## Sin registros: estimado.csv
Una fila por función, con lo que el usuario estima para **un día** (sin columna de fecha, el script supone 1 día):
```csv
funcion,modelo,llamadas,tokens_entrada,tokens_salida,latencia_ms
chat_soporte,claude-sonnet-5-5,800,2500,300,6000
etiquetar_ticket,claude-sonnet-5-5,1500,1200,10,900
```
Con estimados, el acierto de caché se calcula suponiendo las llamadas repartidas en 12 horas, y la latencia por partes no se puede medir (faltan filas). El informe lo dice.

## Empieza a registrar (ofrécelo, con permiso)
Agrega una función así justo después de cada llamada a la IA. Guarda solo números y un hash; nunca el texto del usuario ni llaves.

```python
import hashlib, json, time
from datetime import datetime, timezone

def registrar_uso(funcion, modelo, entrada_texto, inicio, e, s, cr=0, cw=0, ruta="logs/uso.jsonl"):
    with open(ruta, "a", encoding="utf-8") as f:
        f.write(json.dumps({
            "ts": datetime.now(timezone.utc).isoformat(), "funcion": funcion, "modelo": modelo,
            "tokens_entrada": e, "tokens_salida": s, "tokens_cache_lectura": cr, "tokens_cache_escritura": cw,
            "latencia_ms": round((time.time() - inicio) * 1000),
            "hash_entrada": hashlib.sha1(entrada_texto.strip().lower().encode()).hexdigest()[:16],
        }) + "\n")
```

De dónde salen los números en cada SDK (Python):
- **Anthropic** (`client.messages.create`): `e = r.usage.input_tokens`, `s = r.usage.output_tokens`, `cr = r.usage.cache_read_input_tokens or 0`, `cw = r.usage.cache_creation_input_tokens or 0`.
- **OpenAI Chat Completions**: `cr = r.usage.prompt_tokens_details.cached_tokens`, `e = r.usage.prompt_tokens - cr`, `s = r.usage.completion_tokens`.
- **OpenAI Responses**: `cr = r.usage.input_tokens_details.cached_tokens`, `e = r.usage.input_tokens - cr`, `s = r.usage.output_tokens`.
- **Gemini** (`google-genai`): `cr = r.usage_metadata.cached_content_token_count or 0`, `e = r.usage_metadata.prompt_token_count - cr`, `s = r.usage_metadata.candidates_token_count + (r.usage_metadata.thoughts_token_count or 0)`.

Como `registrar_uso` escribe `tokens_entrada` ya sin la caché, el script no vuelve a restarla.
