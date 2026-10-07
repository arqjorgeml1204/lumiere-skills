# Skills gratuitas de Lumière Autómata para Claude

Skills en español para quienes están aprendiendo cómo funciona el software y la inteligencia artificial. Cada una acompaña un tema de la serie **Learning**: [lumiereautomata.com/learning](https://lumiereautomata.com/learning/).

Una *skill* es una carpeta con instrucciones que Claude carga cuando la tarea lo necesita. Todas las de este repositorio:
- explican en español sencillo, con analogías y un glosario inglés → español;
- entregan siempre lo mismo y en el mismo formato (una plantilla, un checklist o un script), para que no dependas de cómo le preguntes.

## Skills disponibles

| Skill | Tema de Learning | Qué hace |
|---|---|---|
| [`explica-api`](explica-api/) | Día 1 · ¿Qué es una API? | Pegas una respuesta o un error de una API y te dice qué pasó, la causa probable y cómo arreglarlo. |

Se agrega una nueva con cada tema que la amerite.

## Cómo instalarla

**En Claude Code (terminal o app de escritorio):** copia la carpeta de la skill (por ejemplo `explica-api`) dentro de `~/.claude/skills/` (en Windows: `C:\Users\TU_USUARIO\.claude\skills\`). Reinicia la sesión.

**En claude.ai:** comprime la carpeta de la skill en un `.zip` y súbela desde *Configuración → Capacidades → Skills*. Necesitas tener activadas las skills en tu cuenta.

Después, solo pide lo que necesitas («¿qué significa este error 401?») y Claude usará la skill.

## Licencia
MIT. Úsalas, compártelas y mejóralas.
