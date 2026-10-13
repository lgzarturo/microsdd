# QUÉ: requisitos

## Objetivo
Riesgos R1 y R3 del análisis de seguridad: que ningún agente (`lider`, `autor`, `implementador`) pueda registrar aprobaciones humanas (`approve`) ni sellos (`seal`), ni escribir directamente la memoria o la configuración de `.microharness/`. Defensa en dos capas: el hook `PreToolUse` (heurística de texto, best effort) y una comprobación en `sdd.py main()` que exige terminal interactiva fuera de Claude Code para `approve`/`seal`.

Decisiones registradas (datos de entrada, no aprobación formal de esta spec):
- Programador: reimplementar el parche externo en tareas pequeñas; esta es la (1). El líder registra notas con `sdd.py note`; `approve` y `seal` quedan solo para el humano.
- Programador, sobre esta spec: se aceptan las excepciones `git add|diff|status|log|show` y las del lanzador; no se sella `tests/test_sdd.py` (`protected_tests: []`); se aceptan los riesgos R-02 a R-04.
- Líder, bajo la autorización global (mitigación de R-01): el implementador puede seguir usando herramientas de edición sobre `.microharness/sdd.py` y `.microharness/python.sh` solo si la spec activa aprobada los incluye en `allowed_paths`. El resto de `.microharness/` (incluidos `memory.json` y `config.json`) queda denegado a todos los roles, y líder y autor no escriben nada en `.microharness/`. Por Bash rige la denegación general.

## Hechos comprobados (HEAD c257391)
- `pretool.run` deniega las seis herramientas guardadas (`Write`, `Edit`, `MultiEdit`, `NotebookEdit`, `Bash`, `PowerShell`) si `agent_type` no es uno de los cuatro roles (`hook-fail-closed`). Para los roles, `Bash`/`PowerShell` solo se filtran al revisor (allowlist con `--textconv`, `-O` y `--open-files-in-pager` denegados).
- En edición, el líder puede escribir `.microharness/memory.json` (excepción explícita); el implementador tiene denegados `.claude/`, `.microharness/`, `docs/`, `spec/` y `CLAUDE.md` antes de comprobar `allowed_paths`; el autor solo escribe los cuatro archivos de `spec/<slug>/`.
- Las rutas de edición se resuelven con `Path(filename).resolve()`, es decir, contra el directorio del proceso del hook y no contra `event['cwd']`.
- La sesión principal con `agent: lider` envía `agent_type` (sonda registrada en memoria).
- En el Bash de Claude Code de la sesión del autor, `CLAUDECODE=1` y stdin no es TTY.
- `sdd.py` ya importa `os`. `main()` convierte `ValueError` en `ERROR:` y código 1. Las pruebas existentes llaman a `sdd.approve()`/`sdd.seal()` directamente, no por `main()`.
- `.microharness/` contiene `sdd.py`, `python.sh`, `memory.json`, `memory.lock` y, de forma opcional y humana, `config.json` (API-09).
- `assets/proceso-versionado.md` define API-01 (CLI) y API-05 (restricciones por rol del hook); `tests/test_api_publica.py` verifica que subcomandos, opciones y rutas instaladas estén documentados.
- `CHANGELOG.md` tiene `## [1.0.0] - 2026-10-13` con grupos «Incompatible», «Añadido», «Corregido» y «Otros»; cada entrada lleva el formato ``- `scope`: asunto (hash)``. Todavía no existe ningún tag.
- Comandos legítimos que mencionan las cadenas protegidas: `sh .microharness/python.sh .microharness/sdd.py new|check|review|note|commit-check …`, `sh .microharness/python.sh -m unittest discover -s tests -v` y `git add … .microharness/memory.json` en el commit de cada tarea.
- El smoke test del instalador envía `{"agent_type": "revisor", "tool_name": "Edit", "tool_input": {}}` y exige `deny` con «solo lectura».

## Precondiciones
- Python 3.10+ solo con biblioteca estándar.
- El líder define cómo se editan en esta tarea `.claude/hooks/pretool.py` y `.claude/agents/lider.md`, porque el hook vigente niega `.claude/` al implementador (Q-01).
- `pretool.py` se modifica en último lugar (ver plan).

## Definiciones
- **Roles restringidos:** `lider`, `autor`, `implementador`.
- **Mención protegida:** el comando contiene `microharness`, `memory.json` o `sdd.py`, sin distinguir mayúsculas.
- **Metacaracteres prohibidos:** `$`, comilla invertida, `\`, salto de línea o retorno de carro en cualquier posición; y `;`, `|`, `&`, `>`, `<`, `(`, `)` fuera de comillas (tokenización `shlex` POSIX con `punctuation_chars`).
- **Lanzadores admitidos** (tokens exactos): `sh .microharness/python.sh`, `python`, `python3`, `py -3`, `uv run --no-project [--quiet] [--python V]`, con `V` que cumple `(>=)?3\.[0-9]+` una vez quitadas las comillas. Van seguidos del token `.microharness/sdd.py`.
- **Subcomandos permitidos:** `init`, `new`, `check`, `review`, `commit-check`, `note`, `release`, `--version`, `--help` (token inmediatamente posterior a `.microharness/sdd.py`).
- **Excepciones legítimas** (sin metacaracteres prohibidos): `sh .microharness/python.sh --version`; `sh .microharness/python.sh -m unittest …` con los tokens siguientes sin mención protegida; `git add|diff|status|log|show …` con tokens que cumplen `[\w./:^~=+,@-]+`, sin ninguno que empiece por `--output` o `--ext-diff`.
- **Archivos editables del arnés:** `.microharness/sdd.py` y `.microharness/python.sh` (rutas exactas, en minúsculas).

## Requisitos EARS
- REQ-01: WHEN un rol restringido invoca `Bash` o `PowerShell` con un comando que contiene una mención protegida, THE hook SHALL denegarlo, salvo que sea una invocación con lanzador admitido y subcomando permitido, o una excepción legítima, en ambos casos sin metacaracteres prohibidos.
- REQ-02: WHEN un rol restringido invoca `sdd.py approve` o `sdd.py seal` por cualquier vía, THE hook SHALL denegarlo, también en la forma exacta con lanzador admitido.
- REQ-03: WHEN una invocación permitida lleva argumentos entre comillas que contienen metacaracteres (p. ej. `--evidence "a; b > c"`), THE hook SHALL permitirla.
- REQ-04: WHEN el comando de un rol restringido no contiene ninguna mención protegida, THE hook SHALL mantener la conducta actual.
- REQ-05: THE allowlist del revisor para `Bash`/`PowerShell` y la denegación fail-closed de agentes no reconocidos SHALL mantenerse sin cambios.
- REQ-06: WHEN `lider` o `autor` usan `Write`, `Edit`, `MultiEdit` o `NotebookEdit` sobre una ruta que, una vez resuelta, es `.microharness` o está bajo `.microharness/` (sin distinguir mayúsculas), THE hook SHALL denegarlo.
- REQ-07: WHEN el implementador usa una herramienta de edición sobre una ruta bajo `.microharness/`, THE hook SHALL denegarla salvo que sea exactamente un archivo editable del arnés; IF lo es, THEN THE hook SHALL aplicar las comprobaciones existentes (una sola spec en `proceso`, ruta en `allowed_paths`, aprobación de spec registrada y pruebas no selladas).
- REQ-08: WHEN la ruta de edición es relativa, THE hook SHALL resolverla contra `event['cwd']` antes de aplicar cualquier regla.
- REQ-09: WHEN el revisor usa una herramienta de edición, THE hook SHALL seguir denegando con el motivo «solo lectura», también sin ruta.
- REQ-10: IF `sdd.py approve` o `sdd.py seal` se ejecuta con la variable de entorno `CLAUDECODE` definida (con cualquier valor, incluso vacío), o con stdin que no es TTY o es `None`, THEN THE CLI SHALL imprimir `ERROR:` por stderr, terminar con código 1 y no invocar `approve()`/`seal()` ni escribir archivos.
- REQ-11: WHEN `approve`/`seal` se ejecutan sin `CLAUDECODE` y con stdin TTY, THE CLI SHALL comportarse como hoy; las funciones Python y los demás subcomandos no cambian de conducta.
- REQ-12: THE `.claude/agents/lider.md` SHALL indicar en el paso 7 que la memoria solo cambia mediante `sdd.py` (`new`, `review`, `note`) y que `approve`/`seal` los ejecuta el humano en su terminal con el comando exacto que le entrega el líder; los pasos 3 y 6 SHALL ser coherentes con ello.
- REQ-13: THE `README.md` SHALL documentar el bloqueo del hook, la excepción del implementador, la comprobación `CLAUDECODE`/TTY y que el humano ejecuta `approve`/`seal` en una terminal propia.
- REQ-14: THE `assets/proceso-versionado.md` SHALL reflejar en API-01 la nueva condición de `approve`/`seal` y en API-05 las nuevas restricciones del hook.
- REQ-15: THE `CHANGELOG.md` SHALL incluir, dentro de `[1.0.0]`, la entrada de esta tarea en el grupo que corresponde a su commit.

## Criterios de aceptación
- AC-01: Para cada rol restringido y cada herramienta (`Bash`, `PowerShell`), `pretool.run` devuelve un motivo (no `None`) para cada variante de bypass:
  - `approve`/`seal` con `./.microharness/sdd.py`, una ruta absoluta, `python3.12`, la ejecución directa `.microharness/sdd.py`, `python3 -m microharness.sdd`, `cd .microharness && python3 sdd.py …`, `F=.microharness/sdd.py; python3 $F …`, `python3 "$PWD/.microharness/sdd.py" …`, `uv run .microharness/sdd.py …` (sin `--no-project`) y `.microharness\sdd.py`;
  - un `check` permitido encadenado con `&&`, `;`, `|`, `||`, `&` o un salto de línea;
  - `--evidence "$(…)"` y la variante con comilla invertida;
  - `echo {} > .microharness/memory.json`, `>>`, `tee`, `cp`, `mv`, `sed -i`, `python3 -c "open('.microharness/memory.json','w')"`, `cat .microharness/memory.json`, `echo {} > .microharness/config.json`, `sh .microharness/python.sh -c "…"`, `git checkout -- .microharness/memory.json` y `git diff --output=.microharness/memory.json`;
  - variantes de mayúsculas (`.MicroHarness/`, `SDD.PY`, `Memory.JSON`).
- AC-02: Para cada rol restringido, cada herramienta y cada lanzador admitido, se deniegan `approve <slug> spec|close --by P --evidence ok` y `seal <slug> --by P`.
- AC-03: Para los tres roles restringidos y ambas herramientas, `pretool.run` devuelve `None` con cada lanzador admitido para: `init`, `new fix-x`, `check fix-x`, `check fix-x --run`, `check fix-x --no-scope`, `review fix-x APROBADO --evidence "diff; pruebas > ok"`, `note --fact "F" --evidence "E"`, `note --decision "D" --by Programador --evidence "E"`, `commit-check 'fix(x): corrige y'`, `release propose`, `--version` y `--help`. También con `uv run --no-project --quiet --python '>=3.10'`, `--python ">=3.10"` y `--python 3.12`.
- AC-04: Para los roles restringidos se permiten `sh .microharness/python.sh -m unittest discover -s tests -v`, `sh .microharness/python.sh --version`, `git add .microharness/memory.json spec/x/plan.md`, `git diff -- .microharness/sdd.py`, `git log --oneline -- .microharness/memory.json`, `git show HEAD:.microharness/sdd.py`, `git status`, `python -m unittest discover -s tests -v` y `git commit -m 'fix(hook)!: impide que los agentes aprueben, sellen o editen la memoria'`.
- AC-05: Las pruebas existentes del revisor y de `tests/test_hook_fail_closed.py` pasan sin modificarse, y el revisor sigue sin poder ejecutar `approve`, `seal`, `review` ni `note`.
- AC-06: Para `lider` y `autor` y cada herramienta de edición (`NotebookEdit` con `notebook_path`), se deniegan `.microharness/memory.json`, `.microharness/config.json`, `.microharness/sdd.py`, `.microharness/python.sh`, `<cwd>/docs/../.microharness/memory.json` y `<cwd>/.MicroHarness/memory.json`. El líder sigue pudiendo escribir `docs/AGENT.md` y `spec/x/plan.md`.
- AC-07: Con un `cwd` temporal que tiene una spec en `proceso` aprobada en `memory.json` y cuyo `allowed_paths` incluye `.microharness/sdd.py` y `.microharness/python.sh`, el implementador puede editar esas dos rutas (`None`), pero se le deniegan `.microharness/memory.json`, `.microharness/config.json`, `.microharness/memory.lock`, `.microharness/otro.py` y `.MicroHarness/sdd.py`. Sin esas rutas en `allowed_paths`, o con la spec sin aprobar, también se le deniegan `sdd.py` y `python.sh`.
- AC-08: Con un `cwd` temporal distinto del directorio del proceso, un `Write` del líder a la ruta relativa `spec/x/plan.md` devuelve `None` y a `.microharness/memory.json` devuelve un motivo.
- AC-09: El evento `{"agent_type": "revisor", "tool_name": "Edit", "tool_input": {}}` produce un motivo con «solo lectura»; las pruebas del instalador (smoke test) siguen pasando.
- AC-10: `sdd.main()` con argv `approve x spec --by P --evidence ok` o `seal x --by P` y `CLAUDECODE` definida (`"1"` y `""`) devuelve 1, escribe `ERROR:` en stderr, no llama a `approve()`/`seal()` (mock) y `memory.json` queda byte a byte igual.
- AC-11: Sin `CLAUDECODE` y con `sys.stdin.isatty()` falso, o con `sys.stdin` igual a `None`, los mismos argv devuelven 1 con `ERROR:` y no llaman a las funciones.
- AC-12: Sin `CLAUDECODE` y con `sys.stdin.isatty()` verdadero, los mismos argv llaman a `approve()`/`seal()` (mock) con los argumentos recibidos y devuelven 0. `note` y `check` con `CLAUDECODE=1` y stdin no TTY siguen funcionando como hoy.
- AC-13: En `.claude/agents/lider.md`:
  - el paso 7 dice que la memoria solo cambia mediante `sdd.py` `new`, `review` y `note`, que no se edita ni se redirige, y que `approve`/`seal` los ejecuta el humano en su terminal con el comando exacto que entrega el líder;
  - el paso 3 pide al humano ejecutar `approve <slug> spec` en lugar de «registrar la decisión en memoria»;
  - el paso 6 indica que el cierre lo registra el humano con `approve <slug> close` antes del commit.
- AC-14: `README.md` explica:
  - que el hook deniega a los agentes `approve`, `seal` y los comandos con mención protegida fuera de las formas permitidas (enumeradas);
  - que deniega toda edición bajo `.microharness/` salvo `sdd.py`/`python.sh` al implementador dentro de `allowed_paths`;
  - que `sdd.py` rechaza `approve`/`seal` con `CLAUDECODE` definida o sin TTY;
  - que el humano los ejecuta en una terminal propia (no con `!` dentro de Claude Code);
  - que los agentes leen la memoria con la herramienta Read.
  Los ejemplos de `approve`/`seal` de la sección del ciclo están marcados como comandos del humano.
- AC-15: `assets/proceso-versionado.md`:
  - API-01 indica que `approve` y `seal` devuelven 1 si `CLAUDECODE` está definida o stdin no es TTY;
  - API-05 indica que el hook deniega a `lider`, `autor` e `implementador` `approve`/`seal` y los comandos de shell con mención protegida fuera de las formas permitidas, y la edición bajo `.microharness/` salvo la excepción del implementador;
  - `tests/test_api_publica.py` sigue en verde sin modificarse.
- AC-16: `CHANGELOG.md`:
  - contiene, dentro de `## [1.0.0] - 2026-10-13` y en el grupo que corresponde al tipo del commit de la tarea («Incompatible» si el asunto lleva `!`, «Corregido» si es `fix` sin `!`), una entrada `` - `hook`: <descripción del asunto> `` idéntica a la descripción del asunto del commit y sin hash;
  - el asunto del commit no contiene menciones protegidas y pasa `commit-check`.
- AC-17: La suite completa `python -m unittest discover -s tests -v` termina con código 0 (incluidos `tests/test_installer.py`, `tests/test_api_publica.py` y `tests/test_hook_fail_closed.py`).

## Fuera de alcance
- Fail-closed adicional, cambios en la allowlist del revisor, en el lock/atomicidad, en el mínimo de pruebas o en la lista blanca de runners.
- Proteger `.claude/`, `CLAUDE.md` o `docs/` frente a escritura por Bash; permitir al implementador editar `.claude/` con herramientas de edición.
- Ofuscación por construcción de cadenas (globs como `.m*/s?d.py`, `printf`, base64), y scripts o parches cuyo comando no menciona las cadenas protegidas (`git apply p.patch`, `python /tmp/x.py`).
- Autenticar al humano; cambios en `.claude/settings.json`, `CLAUDE.md`, `installer.py`, `python.sh`, `pyproject.toml` u otros agentes (incluida la frase «ni el propio arnés» de `implementador.md`).
- Añadir el hash del commit a la entrada de `CHANGELOG.md` (lo hace el líder en un commit posterior; ver plan).
