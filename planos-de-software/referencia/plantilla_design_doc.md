# Plantilla del design doc (documento de diseño)

Responde **cómo** se construye en **tu** código, qué opciones había y por qué se eligió una. Inspirada en los design docs de la industria (contexto, metas, propuesta, alternativas consideradas, riesgos, plan de despliegue).

Cópiala a `design-doc.md`, sustituye cada `[completar: …]` y borra los comentarios `<!-- -->`. Los títulos `##` no se cambian. Extensión: 400 a 3,500 palabras.

Reglas que el revisor comprueba:
- Toda ruta de archivo va entre comillas invertidas y debe existir en el repo. Lo que todavía no existe lleva `(nuevo)` justo después; lo que vive fuera del repo, `(fuera del repo)`. Los otros planos de la misma carpeta (`prd.md`, `rfc.md`) se citan por su nombre.
- Cada decisión es un `###` dentro de «Alternativas consideradas», con tabla de al menos 2 opciones, la elegida, el trade-off y el costo de revertir (alto, medio o bajo).
- Cada requisito P0 del PRD aparece por su ID (R1, R2…) en «Plan de pruebas».

````markdown
# Design doc: [completar: nombre corto del cambio]

**Autor:** [completar] · **Fecha:** [completar: AAAA-MM-DD] · **Estado:** borrador
**PRD:** prd.md · **Revisores sugeridos:** [completar]

## Contexto
<!-- Qué existe hoy en el repo (con rutas), qué pide el PRD en una frase y qué queda fuera. -->
[completar]

## Propuesta
<!-- La solución en 1 a 3 párrafos y, si ayuda, el flujo paso a paso o un diagrama Mermaid. -->
[completar]

## Alternativas consideradas
<!-- Una sección ### por cada decisión importante. Una opción puede ser «no hacerlo / dejarlo como está». -->

### Decisión 1: [completar: qué se decide]
| Opción | Qué ganas | Qué sacrificas |
|---|---|---|
| A. [completar] | [completar] | [completar] |
| B. [completar] | [completar] | [completar] |

**Elegida:** [completar: opción y por qué, ligado a las metas del PRD]
**Trade-off:** [completar: ganamos X a cambio de Y]
**Costo de revertir:** [completar: alto | medio | bajo, y por qué]

## Impacto en el código
<!-- Archivo por archivo: qué cambia. Rutas reales del repo; lo nuevo con (nuevo). -->
| Archivo | Cambio |
|---|---|
| `[completar: ruta/real]` | [completar] |

## Datos
<!-- Tablas o colecciones nuevas o modificadas, migración, y qué pasa con los datos existentes. Si no cambia nada, dilo. -->
[completar]

## Riesgos y mitigación
| Riesgo | Probabilidad | Impacto | Mitigación |
|---|---|---|---|
| [completar] | [completar: baja/media/alta] | [completar] | [completar] |

## Plan de pruebas
<!-- Pruebas automáticas (archivo y caso) y manuales. Cada P0 del PRD con su ID. -->
- R1: [completar]

## Plan de despliegue y vuelta atrás
<!-- Pasos de despliegue (bandera, porcentaje, piloto) y cómo se revierte sin perder datos. -->
- Despliegue: [completar]
- Vuelta atrás: [completar]

## Preguntas abiertas
- [completar] — dueño: [completar]
````
