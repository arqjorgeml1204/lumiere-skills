# Plantilla del PRD (documento de requisitos del producto)

Responde **qué** se construye, **para quién** y **cómo se sabrá que funcionó**. No dice cómo se programa: eso va en el design doc. Inspirada en el PR/FAQ de Amazon (empezar por el cliente y su problema) y en los PRD de la industria.

Cópiala a `prd.md`, sustituye cada `[completar: …]` y borra los comentarios `<!-- -->`. Los títulos `##` no se cambian: el revisor los busca tal cual. Extensión: 250 a 2,000 palabras.

````markdown
# PRD: [completar: nombre corto del cambio]

**Autor:** [completar] · **Fecha:** [completar: AAAA-MM-DD] · **Estado:** borrador
**Documentos relacionados:** design-doc.md, rfc.md <!-- borra los que no existan -->

## Problema
<!-- El dolor del cliente, con un caso real y un número si lo hay. Cómo se resuelve hoy y qué cuesta. Nada de soluciones todavía. -->
[completar]

## Para quién
<!-- Quién lo usa y a quién afecta (clientes, personal, soporte). Uno o dos perfiles concretos. -->
- [completar]

## Metas
<!-- Resultados, no tareas. 2 a 4. -->
- [completar]

## No-metas
<!-- Lo que a propósito NO se hará en esta versión. Evita que el proyecto crezca solo. Mínimo 2. -->
- [completar]

## Métricas de éxito
<!-- Cada fila: meta con número y plazo con número o fecha. Si hoy no se mide, línea base «sin dato» y di desde cuándo se medirá. -->
| Métrica | Línea base (hoy) | Meta | Plazo | Cómo se mide |
|---|---|---|---|---|
| [completar] | [completar] | [completar] | [completar] | [completar] |

## Requisitos
<!-- P0 = sin esto no se lanza · P1 = importante, puede ir una semana después · P2 = deseable. Cada P0 debe poder probarse. -->
| ID | Requisito | Prioridad |
|---|---|---|
| R1 | [completar] | P0 |

## Supuestos
<!-- Lo que das por cierto sin confirmarlo. Si no hay, escribe «Ninguno». -->
- S1: [completar]

## Preguntas abiertas
<!-- Cada pregunta con dueño: quien la va a responder. -->
- [completar] — dueño: [completar]
````
