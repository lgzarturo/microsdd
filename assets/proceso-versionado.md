# Proceso de versionado de MicroSDD

## Propósito y alcance

Este documento regula cómo se versiona el arnés MicroSDD: qué constituye su API pública, cómo se calcula cada incremento de versión, qué reglas rigen mientras la versión mayor sea 0, qué criterios deben cumplirse para declarar 1.0.0, cómo se nombran los tags y prereleases, cómo se ejecuta un release dentro del flujo MicroSDD y qué archivos forman una instalación.

Se basa en Semantic Versioning 2.0.0 (https://semver.org/lang/es/) y en Conventional Commits 1.0.0 (https://www.conventionalcommits.org/es/v1.0.0/), en la medida en que `commit-check` los valida.

`assets/` es material de consulta del repositorio del arnés y no forma parte de la instalación. Todo lo marcado como futuro o como propuesta en este documento no existe aún en el repositorio.

## Estado actual

- El repositorio no tiene ningún tag (`git tag` no devuelve resultados) hasta que se cree `v1.0.0`, tras ejecutar `scripts/limpiar_arnes.py 1.0.0`.
- Existe `CHANGELOG.md`, con la sección `[1.0.0]`; no existe `VERSION`. `.microharness/sdd.py` define la constante `__version__` (`1.0.0`), expuesta con `--version` y replicada en `version` de `pyproject.toml`.
- No hubo release 0.y.z: el programador fijó la versión 1.0.0 (2026-10-13).

## API pública

- **API-01** · CLI de `.microharness/sdd.py`: subcomandos `init`, `new`, `check` (`--run`, `--no-scope`), `approve` (`spec`/`close`, `--by`, `--evidence`), `review` (`APROBADO`/`RECHAZADO`, `--evidence`), `seal` (`--by`), `note` (`--fact`, `--decision`, `--by`, `--evidence`), `commit-check` y `release` (acción `propose`), más la opción global `--version`; código de salida 0 en éxito y 1 en error de ejecución, incluidos el tiempo de espera del lock y los fallos de integridad (los errores de uso de argumentos devuelven 2, comportamiento estándar de `argparse`). El lanzador `.microharness/python.sh` ejecuta sus argumentos con el primer Python ≥ 3.10 válido (respeta `MICROSDD_PYTHON`) y devuelve 2 si no encuentra un intérprete válido.
- **API-02** · Esquema de `spec.json` (`schema_version` 1): campos y valores que acepta `validate` (`id`, `state`, `model`, `effort`, `max_iterations`, `method`, `scope`, `requirements`, `testing`), incluido `testing.min_tests` (entero ≥ 1, opcional, 1 por defecto); salvo en `terminado`, `testing.commands` (y `mutation.command` si `mutation.enabled` es verdadero) deben empezar por un runner de la lista blanca de `sdd.py`, ampliable con `project.allowed_test_commands`.
- **API-03** · Esquema de `.microharness/memory.json` (`schema_version` 1): `project` (incluido el opcional `project.allowed_test_commands`) y `tasks`, con aprobaciones, sellos, revisión, iteraciones y eventos de cada tarea. `check` compara la memoria con `HEAD:.microharness/memory.json`: los eventos confirmados son inmutables y los campos vigilados solo cambian con un evento nuevo que lo justifique. El archivo de lock `.microharness/memory.lock` no se versiona y su contenido no es API.
- **API-04** · Estructura de tarea `spec/<slug>/`: cuatro archivos (`requerimientos.md`, `plan.md`, `tareas.md`, `spec.json`), formato de slug y los tres estados (`pendiente`, `proceso`, `terminado`).
- **API-05** · Contratos de agentes en `.claude/agents/`: nombres, responsabilidades, frontmatter (`model`, `effort` y, cuando se declara, `tools`) y restricciones por rol que aplica `.claude/hooks/pretool.py`, que además deniega `Write`, `Edit`, `MultiEdit`, `NotebookEdit`, `Bash` y `PowerShell` a cualquier agente distinto de `autor`, `implementador`, `revisor` o `lider` (fail-closed).
- **API-06** · `.claude/settings.json` (agente predeterminado, modelo, esfuerzo y registro del hook) y la skill `/sdd`.
- **API-07** · Formato de mensaje aceptado por `commit-check`.
- **API-08** · Conjunto de rutas instaladas (sección «Instalación»).
- **API-09** · `.microharness/config.json`: archivo humano opcional con las claves `model` y `effort` (valores por defecto de `sdd.py`; otras claves son error). No lo crea el instalador.

No forman parte de la API pública: los textos de los mensajes de salida y de error (sí sus códigos de salida), las funciones internas de `sdd.py`, `tests/`, `README.md`, `assets/`, `CHANGELOG.md` y las specs y la memoria del propio arnés.

Justificación: de estos elementos dependen un repositorio instalado, sus specs y memoria existentes y los hábitos del programador; cambiarlos de forma incompatible rompe instalaciones o tareas en curso.

## Reglas de incremento

| Señal en el commit | Efecto en la API pública | Incremento (desde 1.0.0) |
|---|---|---|
| `!` en el asunto o pie `BREAKING CHANGE` | incompatible | MAJOR |
| `feat` | funcionalidad compatible | MINOR |
| `fix`, `perf` | corrección compatible | PATCH |
| `docs`, `test`, `refactor`, `chore` | sin cambio de API | ninguno propio |

- El tipo es una señal; manda el efecto real sobre API-01 a API-09. Un `docs` o `refactor` que cambie un contrato de agente de forma incompatible debe llevar `!`.
- El release toma el mayor incremento entre los commits desde el último tag. MAJOR pone MINOR y PATCH a 0; MINOR pone PATCH a 0. Si solo hay commits sin incremento propio, no se publica versión.
- Lo incompatible se marca con `!` en el asunto (por ejemplo, `feat!: ...`), porque `commit-check` solo valida un mensaje de una línea: un mensaje con cuerpo o con pie `BREAKING CHANGE:` es rechazado. El pie puede añadirse en el cuerpo del commit, pero `commit-check` se aplica solo a la primera línea.

## Fase 0.y.z

Mientras la versión mayor sea 0, la API pública puede cambiar. En esta fase, un cambio incompatible incrementa MINOR, y `feat`, `fix` y `perf` incrementan PATCH.

«MicroSDD 0.1» equivale a la línea `0.1.0`, aún no publicada. Por decisión del programador, el primer tag es `v1.0.0`.

## Criterios para declarar 1.0.0

- **C-01** API pública documentada y vigente (este documento coincide con el repositorio). Verificación: revisión independiente de la tarea de release 1.0.0.
- **C-02** Herramienta de release implementada. Verificación: su tarea en `memory.json` está `terminado` y `check --run` pasa.
- **C-03** Al menos un release 0.y.z completo con este proceso. Verificación: `git tag -l "v0.*"` no vacío y release visible en GitHub.
- **C-04** Evaluación del MVP de la sección 8 de `README.md` con tres tareas reales. Verificación: resultados registrados en `memory.json` como observaciones del proyecto.
- **C-05** Defectos de instalación conocidos (hook con `python3` en Windows; `core.quotePath` en la comprobación de alcance) corregidos o declarados como limitación en `README.md`. Verificación: tarea terminada o texto en `README.md`.
- **C-06** `CHANGELOG.md` con entrada para 1.0.0. Verificación: lectura del archivo en el commit del release.
- **C-07** Suite completa en verde. Verificación: `python -m unittest discover -s tests` con código 0 en el commit candidato.
- **C-08** Decisión humana explícita de declarar 1.0.0. Verificación: aprobación `spec` registrada en la tarea `release-v1-0-0`.

## Tags y prereleases

- Cada versión se marca con un tag anotado `vX.Y.Z` sobre el commit de release en `main`: `git tag -a vX.Y.Z -m "MicroSDD X.Y.Z"`.
- Las prereleases solo usan la forma `vX.Y.Z-rc.N` (N ≥ 1), sin metadatos de compilación.
- Expresión de referencia: `^v(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)(-rc\.[1-9][0-9]*)?$`.
- Un tag publicado no se mueve ni se borra; un error se corrige con una nueva versión PATCH.
- Un tag local aún no publicado puede borrarse solo con autorización humana.
- El tag se publica de forma individual con `git push origin vX.Y.Z`; nunca con `git push --tags` ni con `--force`.

## Release dentro del flujo MicroSDD

1. Precondiciones: `main` actualizado, árbol de trabajo limpio, ninguna tarea en `proceso` y suite en verde.
2. El líder crea la tarea con `python .microharness/sdd.py new release-vX-Y-Z` (el slug no admite puntos).
3. El autor especifica: commits desde el último tag (o desde el inicio si no hay ninguno), su clasificación según «Reglas de incremento», la versión propuesta, las entradas de `CHANGELOG.md` y el alcance (`CHANGELOG.md` y la fuente de versión).
4. El humano aprueba la spec y la versión; el líder registra `approve release-vX-Y-Z spec`.
5. El implementador aplica los cambios del alcance.
6. El revisor dictamina y se ejecuta `check release-vX-Y-Z --run`; el líder registra `review`.
7. El humano aprueba el cierre, el commit y la creación del tag; el líder registra `approve release-vX-Y-Z close`.
8. El líder valida el mensaje con `commit-check 'chore(release): vX.Y.Z'` y hace el commit atómico con stage explícito (nunca `git add .`).
9. El líder crea el tag anotado con `git tag -a vX.Y.Z` sobre ese commit y lo muestra con `git show vX.Y.Z`.
10. Solo con autorización explícita e independiente del humano: `git push origin main` y `git push origin vX.Y.Z`.
11. Solo con autorización explícita: release de GitHub desde el tag existente, con las notas de la sección correspondiente de `CHANGELOG.md` y marcado como prerelease si es `-rc.N`; lo crea el humano en la interfaz web o el líder con la CLI `gh`, si está disponible y autorizada.
12. El líder registra en `memory.json` una observación con el tag y el enlace del release.

Mientras no exista la herramienta de release, los pasos 3 y 5 se hacen a mano; cuando exista, la tarea de release la usará sin saltarse aprobaciones.

## Instalación

El instalador (`src/microsdd/installer.py`) copia solo las rutas de su `MANIFEST`: el `CLAUDE.md` del arnés se instala como `CLAUDE.microsdd.md` y al `CLAUDE.md` destino se le anexa un bloque de registro que lo importa (o se crea con ese bloque). Si `.claude/settings.json` ya existe y difiere, se escribe `.claude/settings.microsdd.json` para fusionarlo a mano. Después ejecuta `sdd.py init`, que genera `docs/`, `spec/` y `.microharness/memory.json` sin sobrescribir lo existente. Los documentos usan los nombres `docs/convenciones.md` y `docs/especificaciones.md`; si existen los nombres antiguos `docs/convensiones.md` o `docs/specificaciones.md`, `init` avisa y no mueve archivos.

### Incluido

Copiados desde `MANIFEST`:

- `.claude/agents/autor.md`
- `.claude/agents/implementador.md`
- `.claude/agents/lider.md`
- `.claude/agents/revisor.md`
- `.claude/hooks/pretool.py`
- `.claude/skills/sdd/SKILL.md`
- `.claude/settings.json` (o el alterno indicado arriba)
- `.microharness/sdd.py`
- `.microharness/python.sh`
- `CLAUDE.microsdd.md` (copia de `CLAUDE.md` del arnés)
- `CLAUDE.md` (bloque de registro anexado o archivo nuevo)

Generados por `sdd.py init`:

- `docs/AGENT.md`
- `docs/arquitectura.md`
- `docs/convenciones.md`
- `docs/especificaciones.md`
- `.microharness/memory.json`
- `spec/`

### Excluido

Todo lo versionado que no figura en «Incluido», en particular: `assets/`, `scripts/`, `historial/` (si existe), `src/`, `tests/`, `pyproject.toml`, `README.md`, `LICENSE`, `.gitignore`, `.gitattributes`, `CHANGELOG.md` y las specs y la memoria del propio arnés. Tampoco se crea `.microharness/config.json` (API-09), ni se copia `.claude/settings.local.json`, que no se versiona.

Nota: sin `--force`, si una ruta del `MANIFEST` ya existe con contenido distinto (salvo `.claude/settings.json`, que usa el alterno), el instalador informa el conflicto y no escribe nada; revisa antes `CLAUDE.md` y `.claude/settings.json` del repositorio destino.

## Herramienta de release

Existen `sdd.py --version`, que imprime `MicroSDD <__version__>`, y `sdd.py release propose`, que solo lee Git y propone la siguiente versión sin modificar archivos, tags, ramas ni memoria. `release prepare` (actualizar `CHANGELOG.md` y la fuente de versión) y `release tag` (crear el tag) están pendientes de su propia tarea. La herramienta cumple, y la parte pendiente deberá cumplir, estos requisitos:

- **R-01** Usar solo la biblioteca estándar de Python y exponerse como subcomando `release` de `.microharness/sdd.py`, con las acciones `propose`, `prepare` y `tag`.
- **R-02** Rechazar la ejecución, con código 1, si no se cumplen las precondiciones de su fase:
  - `release propose`: rama `main`, ninguna tarea en `proceso` y árbol limpio salvo `spec/**` y `.microharness/memory.json` (se ejecuta mientras el autor especifica la tarea de release).
  - `release prepare X.Y.Z[-rc.N]` (pendiente): rama `main`, árbol limpio salvo `spec/<slug>/**` y `.microharness/memory.json`, la tarea `<slug>` de release en `proceso` y ninguna otra tarea en `proceso`, y tag inexistente.
  - `release tag X.Y.Z[-rc.N]` (pendiente): rama `main`, árbol totalmente limpio, la tarea `<slug>` en `terminado` con aprobación `close`, ninguna tarea en `proceso` y tag inexistente.
  - El slug es `release-v` seguido de la versión con `.` sustituido por `-` (por ejemplo, `release-v0-2-0-rc-1`).
- **R-03** Proponer el incremento según «Reglas de incremento» y «Fase 0.y.z», leyendo los asuntos de commit desde el último tag; la versión final la confirma el humano.
- **R-04** Actualizar `CHANGELOG.md` (una sección `## [X.Y.Z] - AAAA-MM-DD` por versión, con entradas agrupadas en «Incompatible», «Añadido», «Corregido» y «Otros») y la fuente única de versión, que deberá coincidir con el tag.
- **R-05** Crear el tag anotado solo tras la aprobación `close` registrada y validar el formato de la sección «Tags y prereleases».
- **R-06** No ejecutar `push` ni crear releases en GitHub; como máximo, imprimir los comandos para que el humano los autorice.
- **R-07** Devolver código de salida 0 en éxito y 1 en error, coherente con API-01, con pruebas unitarias en `tests/`.

Fuente única de versión en el árbol: la constante `__version__` de `.microharness/sdd.py`, expuesta con `--version`, para que una instalación conozca su versión sin acceso a los tags.
