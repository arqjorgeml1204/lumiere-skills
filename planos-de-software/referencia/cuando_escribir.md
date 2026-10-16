# ¿Qué planos necesita tu cambio? (método fijo)

Califica cada criterio con la evidencia de **tu pedido y tu repo** (el mapa de `mapa_repo.py` y lo que leíste). Muestra siempre la tabla completa.

| # | Criterio | Respuesta | Puntos |
|---|---|---|---|
| 1 | Tamaño del cambio | 1 a 3 archivos de un solo módulo | 0 |
|   |  | Varios módulos o capas (rutas + servicio + datos) | 1 |
|   |  | Módulo, servicio o integración nueva, o cambia la arquitectura | 2 |
| 2 | Reversibilidad | Se revierte con otro despliegue y no deja rastro | 0 |
|   |  | Cambia el modelo de datos de forma reversible (columna o tabla nueva) | 1 |
|   |  | Difícil o imposible de revertir: borra o transforma datos, contrato de API pública, proveedor externo con contrato o datos de clientes | 2 |
| 3 | Cuántas personas dependen | Solo tú | 0 |
|   |  | Tu equipo o un área (soporte, ventas, operación) | 1 |
|   |  | Clientes finales, otros equipos o integradores externos | 2 |
| 4 | Dinero, datos personales o seguridad | No los toca | 0 |
|   |  | Sí: cobros, reembolsos, datos personales, permisos, autenticación | 2 |
| 5 | Duración estimada | Menos de 2 días | 0 |
|   |  | De 2 días a 2 semanas | 1 |
|   |  | Más de 2 semanas | 2 |

## Resultado

| Total | Qué escribir |
|---|---|
| 0–2 | **Ninguno.** Basta una nota corta de cambio (abajo) en el issue o en la descripción del PR. |
| 3–4 | **Solo PRD**, corto. Si el «qué» ya está claro y la duda es técnica (refactor, migración, cambiar de librería), **solo design doc**. |
| 5 o más | **PRD + design doc.** Si el cambio es puramente técnico y no cambia lo que ve el usuario, **design doc solo**. |

**Más un RFC** (con cualquier total ≥ 3) si se cumplen las dos:
1. Hay una decisión con al menos dos opciones razonables en la que gente sensata no está de acuerdo (proveedor, política, arquitectura).
2. Esa decisión afecta a alguien más que al autor (otro equipo, el dueño del negocio, soporte, finanzas).

El RFC lleva **una sola decisión**, con fecha límite de comentarios y quién decide. Si hay dos decisiones discutibles, son dos RFC.

**Comunicado y preguntas frecuentes (opcional):** si el cambio lo verá un cliente y todavía no está claro que convenza, escribe primero `comunicado.md`. Si no puedes escribir un comunicado de una página que entusiasme, el problema no está en el diseño.

## Si el resultado es «ninguno»: nota corta de cambio

```markdown
**Qué cambia:** una frase.
**Por qué:** una frase con el problema.
**Archivos:** `ruta/real.js`, `otra/ruta.py`
**Cómo se prueba:** comando o pasos.
**Cómo se revierte:** revertir el commit / apagar la bandera.
```

## Ejemplos rápidos
- Cambiar el texto de un correo de confirmación: 0 + 0 + 1 + 0 + 0 = 1 → ninguno.
- Agregar un filtro por fecha a una lista interna: 1 + 0 + 1 + 0 + 1 = 3 → solo PRD corto.
- Migrar de SQLite a PostgreSQL sin cambiar lo que ve el usuario: 2 + 2 + 1 + 0 + 2 = 7, puramente técnico → design doc solo (y RFC si el equipo duda entre dos motores).
- Cobrar en línea un anticipo de la reservación: 2 + 2 + 2 + 2 + 1 = 9 → PRD + design doc, y RFC para elegir proveedor de pagos.
