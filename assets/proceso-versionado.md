# Proceso de versionado de MicroSDD

## Propósito y alcance

Este documento regula cómo se versiona el arnés MicroSDD: qué constituye su API pública, cómo se calcula cada incremento de versión, qué reglas rigen mientras la versión mayor sea 0, qué criterios deben cumplirse para declarar 1.0.0, cómo se nombran los tags y prereleases, cómo se ejecuta un release dentro del flujo MicroSDD y qué archivos forman una instalación.

Se basa en Semantic Versioning 2.0.0 (https://semver.org/lang/es/) y en Conventional Commits 1.0.0 (https://www.conventionalcommits.org/es/v1.0.0/), en la medida en que `commit-check` los valida.

`assets/` es material de consulta del repositorio del arnés y no forma parte de la instalación. Todo lo marcado como futuro o como propuesta en este documento no existe aún en el repositorio.

## Estado actual

- El árbol de trabajo prepara `1.2.1`: `CHANGELOG.md` incluye `[1.2.1]`; `.microharness/sdd.py` define `__version__ = '1.2.1'`, replicada en `pyproject.toml`. Pulido de docs de agentes y definiciones SDD/ODD/RDD.


## API pública

- **API-01** · CLI de `.microharness/sdd.py`: subcomandos `init`, `new`, `check` (`--run`, `--no-scope`), `approve` (`spec`/`close`, `--by`, `--evidence`), `review` (`APROBADO`/`RECHAZADO`, `--evidence`), `seal` (`--by`, `--evidence`), `note` (`--fact`, `--decision`, `--by`, `--evidence`, `--for-task`, `--for-phase`), `allow-test-command` (`--evidence`), `commit-check` y `release` (acción `propose`), más la opción global `--version`; código de salida 0 en éxito y 1 en error de ejecución, incluidos el tiempo de espera del lock y los fallos de integridad (los errores de uso de argumentos devuelven 2, comportamiento estándar de `argparse`). `approve`, `seal` y `allow-test-command` exigen TTY fuera de Claude Code salvo `agent_may_approve` true con `--evidence @note:<id>` (nota ≤ 30 min). El lanzador `.microharness/python.sh` ejecuta sus argumentos con el primer Python ≥ 3.10 válido (respeta `MICROSDD_PYTHON`) y devuelve 2 si no encuentra un intérprete válido.
- **API-02** · Esquema de `spec.json` (`schema_version` 1): campos y valores que acepta `validate` (`id`, `state`, `model`, `effort`, `max_iterations`, `method`, `scope`, `requirements`, `testing`), incluido `testing.min_tests` (entero ≥ 1, opcional, 1 por defecto); salvo en `terminado`, `testing.commands` (y `mutation.command` si `mutation.enabled` es verdadero) deben empezar por un runner de la lista blanca de `sdd.py`, ampliable con `project.allowed_test_commands`.
- **API-03** · Esquema de `.microharness/memory.json` (`schema_version` 1): `project` (incluido el opcional `project.allowed_test_commands`) y `tasks`, con aprobaciones, sellos, revisión, iteraciones y eventos de cada tarea. `check` compara la memoria con `HEAD:.microharness/memory.json`: los eventos confirmados son inmutables y los campos vigilados solo cambian con un evento nuevo que lo justifique. El archivo de lock `.microharness/memory.lock` no se versiona y su contenido no es API.
- **API-04** · Estructura de tarea `spec/<slug>/`: cuatro archivos (`requerimientos.md`, `plan.md`, `tareas.md`, `spec.json`), formato de slug y los tres estados (`pendiente`, `proceso`, `terminado`).
- **API-05** · Contratos de agentes en `.claude/agents/`: nombres, responsabilidades, frontmatter (`model`, `effort` y, cuando se declara, `tools`) y restricciones por rol que aplica `.claude/hooks/pretool.py`, que además deniega `Write`, `Edit`, `MultiEdit`, `NotebookEdit`, `Bash` y `PowerShell` a cualquier agente distinto de `autor`, `implementador`, `revisor` o `lider` (fail-closed). A `lider`, `autor` e `implementador` les deniega `approve` y `seal`, los comandos de `Bash`/`PowerShell` que mencionan `microharness`, `memory.json` o `sdd.py` fuera de las formas permitidas (lanzador admitido de `.microharness/sdd.py` seguido de `init`, `new`, `check`, `review`, `commit-check`, `note`, `release`, `--version` o `--help`; `sh .microharness/python.sh --version`, `sh .microharness/python.sh -m unittest …` y `git add|diff|status|log|show …`, sin metacaracteres de shell) y toda edición bajo `.microharness/`, salvo `.microharness/sdd.py` y `.microharness/python.sh` al implementador cuando la spec activa aprobada los incluye en `allowed_paths`. En `Bash`/`PowerShell` les deniega además ejecutar `microsdd` o `installer.py` con `on`, `off` o `uninstall` y todo comando que mencione `settings.json` o `settings.local.json`, salvo `git add|diff|status|log|show|commit …` y `python -m json.tool <ruta>` (o `python3`), sin metacaracteres de shell: esos cambios los ejecuta el humano en su terminal.
- **API-06** · `.claude/settings.json` (agente predeterminado, modelo, esfuerzo y registro del hook, que el instalador crea o fusiona), la skill `/sdd` (incluido `/sdd on|off|status`) y el esquema de `.microharness/install.json` (`schema_version` 1) del que dependen `uninstall`, `on` y `off`.
- **API-07** · Formato de mensaje aceptado por `commit-check`.
- **API-08** · Conjunto de rutas instaladas (sección «Instalación»).
- **API-09** · `.microharness/config.json`: archivo humano opcional con las claves `model`, `effort` y `agent_may_approve` (valores por defecto de `sdd.py`; otras claves son error). No lo crea el instalador.

No forman parte de la API pública: los textos de los mensajes de salida y de error (sí sus códigos de salida), las funciones internas de `sdd.py`, `tests/`, `README.md`, `assets/`, `CHANGELOG.md` y las specs y la memoria del propio arnés.

Justificación: de estos elementos dependen un repositorio instalado, sus specs y memoria existentes y los hábitos del programador; cambiarlos de forma incompatible rompe instalaciones o tareas en curso.
