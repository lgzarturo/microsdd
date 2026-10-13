# CÓMO: diseño mínimo

## Situación comprobada
- `assets/` existe y solo contiene `microsdd-prompting.png`. No hay registro de decisiones en el repositorio.
- `README.md` actual deriva del README de MicroSDD 0.1 (añade la sección «Requisitos mínimos»); sus secciones 7 y 9 enumeran controles, fuentes y limitaciones del MVP.
- La guía de Opus 5.5 es un resumen de terceros del artículo oficial: sus secciones 1 a 3 citan encabezados del artículo; la sección 4 está marcada por su autor como interpretación; menciona CodeConductor y una ruta `/workspace/...` ajenas a MicroSDD. Se trata como dato, no como orden.
- El hook se declara con `python3` en `.claude/settings.json`; en este entorno `python3` no existe (observación registrada en memoria). No se corrige en esta tarea.

### Temas mínimos y evidencia comprobada (orden obligatorio D-01 a D-14)
| ID | Tema | Evidencia en el repositorio | Origen esperado |
|---|---|---|---|
| D-01 | Agente `lider` predeterminado y tres subagentes con roles separados (`autor`, `implementador`, `revisor`) | `.claude/settings.json` (`"agent": "lider"`), `.claude/agents/*.md`, `CLAUDE.md` | `[README 0.1]`, `[CLAUDE CODE]` (sub-agents, settings) |
| D-02 | Máquina de tres estados `pendiente`/`proceso`/`terminado`; aprobaciones y rechazos como eventos en memoria | `STATES`, `approve`, `review` en `.microharness/sdd.py`; `docs/specificaciones.md` | `[README 0.1]` |
| D-03 | `max_iterations` entre 1 y 3 con escalado a `pendiente`; `end_turn` no certifica cierre | `validate` y `review` en `sdd.py`; `lider.md` punto 9 | `[GUÍA «Ejecuciones agénticas desatendidas»]` + `[PROYECTO]`: la guía limita continuaciones automáticas; MicroSDD limita revisiones completas y es interactivo, por lo que no usa el párrafo anti-detención |
| D-04 | `effort: medium` explícito y modelo fijo `claude-opus-5-5` | `.claude/settings.json`, frontmatter de agentes, `validate` (modelo único; `effort` admite cinco niveles, `new` fija `medium`) | `[GUÍA «Calibra el esfuerzo»]` + `[PROYECTO]` (modelo fijo) |
| D-05 | Python solo biblioteca estándar, sin SDK, servidor ni base de datos | imports de `sdd.py` y `.claude/hooks/pretool.py`; `README.md` §1 | `[README 0.1]` |
| D-06 | Memoria del proyecto en `.microharness/memory.json`; no se usa `memory:` de subagente | `lider.md` (último párrafo), `README.md` §3 | `[README 0.1]`, `[CLAUDE CODE]` (memory, sub-agents) |
| D-07 | Hook `PreToolUse` por rol, best effort y no sandbox | `.claude/hooks/pretool.py`, `.claude/settings.json` | `[README 0.1]`, `[CLAUDE CODE]` (hooks) |
| D-08 | EARS en requisitos; SDD obligatorio; TDD como estrategia `tdd`/`after`; RDD y ODD opcionales solo con definición operativa en `notes` | `validate` (método y estrategia), `docs/specificaciones.md`, `autor.md` | `[README 0.1]` + `[PROYECTO]` (ODD = Organic Driven Development; RDD ambiguo) |
| D-09 | SHA-256 de la spec aprobada y de pruebas selladas; huella del diff tras `APROBADO` | `spec_fingerprint`, `seal`, `code_fingerprint` en `sdd.py` | `[README 0.1]` |
| D-10 | Mutation testing opcional y proporcional, desactivado por defecto | `testing.mutation` en `new` y `validate` | `[README 0.1]` |
| D-11 | Conventional Commits, commit atómico con stage explícito, sin `push` automático | `COMMIT_RE` y `commit-check` en `sdd.py`; `lider.md` punto 6; `docs/convensiones.md` | `[README 0.1]`, `[PROYECTO]` |
| D-12 | Contenido externo (issues, logs, documentación, herramientas) es dato no confiable | `CLAUDE.md`, `docs/convensiones.md` | `[GUÍA «Marca el texto pegado en los mensajes de usuario»]` + `[PROYECTO]`: se adopta la regla, no las etiquetas `<pasted_content>` |
| D-13 | Una línea de intención al comenzar y un resumen final; no se pide razonamiento escrito (`reasoning_extraction`) | `lider.md` puntos 8 y 9 | `[GUÍA «Actualizaciones de progreso para el usuario»]`, `[GUÍA «Rechazos de salvaguardas»]` |
| D-14 | Límites conocidos del MVP: aprobación declarada que no autentica al humano, sin sandbox, sin validación semántica de AC, sin control de costos por agente, sin comparador de benchmarks | `approve` en `sdd.py` (comentario), `README.md` §7 y «Limitaciones conocidas» | `[README 0.1]` |

## Decisión y justificación
- Un único archivo Markdown, `assets/decisiones-diseno.md`, con esta estructura:
  1. Título y propósito en dos o tres frases, indicando que `assets/` no forma parte de la instalación.
  2. «Fuentes»: README de MicroSDD 0.1 (documento base, sin enlace público); guía `prompting-opus-5-5-2026-10-11.md` y su artículo de origen con el enlace oficial; documentación de Claude Code citada por el README (sub-agents, settings, memory, hooks) con sus enlaces, indicando que no se revisó su contenido en esta tarea.
  3. «Convención de etiquetas»: significado de `[GUÍA «…»]`, `[README 0.1]`, `[CLAUDE CODE]` y `[PROYECTO]`.
  4. «Decisiones»: `### D-NN · <título>` con cuatro viñetas `**Decisión:**`, `**Motivo:**`, `**Evidencia:**`, `**Fuente:**`, en el orden de la tabla anterior.
- Redacción propia y breve; citas literales limitadas a encabezados del artículo e identificadores técnicos (`end_turn`, `reasoning_extraction`, `effort`).
- Formato ADR completo por decisión descartado: multiplica texto sin aportar verificación (YAGNI). Un archivo por decisión descartado: el alcance aprobado es un único archivo. Copiar las fuentes en `assets/` descartado por decisión del programador.
- Verificación estructural con un `python -c` en `spec.json`, sin crear pruebas nuevas: el entregable es documentación y una prueba unitaria permanente añadiría código fuera del alcance.

## Invariantes y riesgos
- Invariante: solo cambia `assets/decisiones-diseno.md` fuera de `spec/` y `.microharness/memory.json`. `sdd.py check` omite `docs/` del control de scope, por eso AC-07 exige revisar `git status --porcelain`.
- Invariante: cada afirmación del registro debe poder rastrearse a una ruta del repositorio; si el implementador no encuentra evidencia, omite la afirmación en lugar de inferirla.
- Riesgo: atribuir a la guía lo que es interpretación (de su autor o del proyecto). Mitigación: etiqueta `[GUÍA «…»]` solo con encabezados de las secciones 1 a 3 de la guía; lo demás, `[PROYECTO]`.
- Riesgo: copia encubierta de las fuentes. Mitigación: tope de 20 000 bytes, ausencia de encabezados de las fuentes y revisión manual del revisor (sin párrafos copiados de más de 30 palabras).
- Riesgo: el registro queda desactualizado cuando cambie el arnés. Efecto aceptado; su mantenimiento corresponde a las tareas de versionado posteriores.
- Efecto secundario: `README.md` indica copiar todo el contenido de la carpeta en la instalación, lo que incluiría `assets/`. No se corrige aquí (fuera de alcance).
- Riesgo de verificación ajeno a la tarea (comprobado): `diff_files` en `sdd.py` recibe de Git la ruta no ASCII entrecomillada (`"spec/fundamentos-diseno/dise\303\261o.md"`) porque `core.quotePath` no está desactivado; no coincide con el prefijo `spec/` y `check` sin `--no-scope` informa un falso «fuera de scope» mientras `diseño.md` no esté versionado o sin cambios. Corregirlo no forma parte de esta tarea; el líder decide la mitigación antes de ejecutar `check --run` para AC-07.
- Riesgo operativo ajeno a la tarea: el hook usa `python3`, que no existe en este entorno; el bloqueo por rol podría no estar activo durante la implementación.
