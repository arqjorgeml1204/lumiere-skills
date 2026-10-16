# Las 5 optimizaciones: método fijo y supuestos

El script simula cada optimización **sola**, función por función, y luego las 3 que más ahorran **juntas** (sección 4 del informe). Todo supuesto se puede cambiar con `--supuestos supuestos.json`, por ejemplo `{"recorte_prompt": 0.15, "ttl_cache_s": 3600}`.

| | Optimización | Qué cambia en la simulación | Medido con tus datos | Supuesto (valor por defecto) | Riesgo para la calidad |
|---|---|---|---|---|---|
| a | Caché de prompts | La parte fija se cobra como lectura de caché si la llamada anterior de esa función fue hace ≤ 5 min; si no, como escritura (más cara). No aplica si la parte fija es menor que el mínimo del modelo | Aciertos con las fechas de tus llamadas; parte fija con `--fijos` | Sin fechas: llamadas repartidas en 12 h (`horas_activas_dia`); un token en caché tarda 10 % (`factor_latencia_cache`) | Ninguno; el prefijo debe ser idéntico |
| b | Modelo más barato para tareas simples | Se recalcula con el `modelo_economico` del proveedor (en `precios.json`) con los mismos tokens | Funciones simples con `--simples` | Sin `--simples`: salida promedio ≤ 100 tokens; el modelo pequeño tarda 50 % (`factor_latencia_modelo_economico`) | Medio-alto: probar con 20 casos reales |
| c | Recortar el prompt fijo | Se quita `recorte_prompt` de la parte fija en cada llamada | Parte fija | 25 % (`recorte_prompt`): ajústalo tras leer el prompt | Medio: empezar por duplicados |
| d | Streaming | Costo igual, tiempo total igual; la espera percibida pasa a ser el tiempo al primer token | `ttft_ms` si lo registras | Si no: fijo por llamada + tiempo de procesar la entrada, del ajuste de latencia por modelo | Ninguno; requiere cambiar la pantalla |
| e | Caché de respuestas | Una pregunta idéntica en la misma función dentro de 24 h cuesta $0 y tarda 50 ms | Repeticiones con `hash_entrada` o el texto de la pregunta | Sin hash: 5 % (`repeticion_respuestas`); ventana 24 h (`ventana_respuestas_h`) | Medio: caducidad obligatoria |

## Cómo se calcula el costo
`costo = (entrada × precio_entrada + caché_lectura × precio_lectura + caché_escritura × precio_escritura + salida × precio_salida) ÷ 1,000,000`

Si la entrada total de una llamada pasa el `umbral` del modelo (p. ej. 100K en Claude Haiku 5.5, 200K en Gemini 2.5 Pro, 272K en GPT-5.5), toda la llamada usa los precios de `sobre_umbral`. Si el precio tiene fecha de cambio (`vigente_hasta`), después de esa fecha usa `siguiente`. Mes = 30 días (`dias_mes`).

## Cómo se calcula la latencia
Con 10 filas o más se ajusta `latencia ≈ fijo + b × tokens de entrada + c × tokens de salida` (mínimos cuadrados), uno por modelo si tiene 30 filas o más. Eso dice de dónde sale tu espera: casi siempre de la **salida**. Por eso pedir respuestas más cortas y usar streaming suele acelerar más que la caché. El informe muestra la R² de cada ajuste.

## Lo que no se simula (y cuándo mencionarlo)
- **Procesamiento por lotes (Batch API):** 50 % menos en Claude (otros proveedores ofrecen descuentos parecidos: verifícalo en su página de precios) para tareas que pueden esperar horas (reportes nocturnos, clasificar un histórico). Menciónalo si una función no necesita respuesta inmediata.
- **Respuestas más cortas** (`max_tokens`, instrucción de largo): baja costo y latencia a la vez; en el ajuste de latencia se ve cuánto pesa cada token de salida.
- **Almacenamiento de la caché explícita de Gemini** (cobro por hora) y caché de 1 hora de Claude (escritura a 2×): ajusta `ttl_cache_s` si la usas y revisa el precio a mano.
