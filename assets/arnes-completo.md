# Arnés MicroSDD: referencia completa

Material de consulta. El [README](../README.md) resume instalación y uso; este archivo detalla lanzador, flujo, archivos, `spec.json` y límites del MVP.

Ver también: [proceso de versionado](proceso-versionado.md), [decisiones de diseño](decisiones-diseno.md), [eval de esfuerzo](eval-esfuerzo.md).

**CI:** `.github/workflows/tests.yml` ejecuta la suite en push a `main` y en pull requests (Python 3.12). En local: `python -m unittest discover -s tests` y, en el flujo de tarea, `sdd.py check --run`.

### Lanzador `.microharness/python.sh`

`sh .microharness/python.sh <args…>` ejecuta `<args…>` con el primer intérprete que supere el sondeo de versión ≥3.10, en este orden: `MICROSDD_PYTHON` → `uv` → `python3` → `python` → `py -3`. Usa `exec`, así que conserva stdin, stdout, stderr y el código de salida.

- `MICROSDD_PYTHON` (ruta a un ejecutable, sin argumentos) tiene prioridad. Si está definida y no es un Python ≥3.10 válido, el lanzador termina con código 2 sin probar otros candidatos.
- Si ningún candidato es válido, termina con código 2 e indica cómo instalar uv o Python ≥3.10.

En `check --run`, un comando de `testing.commands` (o `mutation.command`) cuyo primer elemento sea exactamente `python` o `python3` se ejecuta con el mismo intérprete que corre el checker (`sys.executable`).

**Lista blanca de runners.** Mientras la tarea no esté `terminado`, `check` (también sin `--run`, y por tanto `approve spec`) exige que cada comando de `testing.commands`, y `mutation.command` si `enabled=true`, empiece por uno de estos prefijos de argv (tokens exactos, sensibles a mayúsculas; el resto de argumentos es libre):

`python -m unittest`, `python3 -m unittest`, `python -m pytest`, `python3 -m pytest`, `pytest`, `npm test`, `pnpm test`, `yarn test`, `bun test`, `go test`, `cargo test`, `mvn test`, `./mvnw test`, `gradle test`, `./gradlew test`, `mutmut run`.

- Si el primer elemento es exactamente `sys.executable` se trata como `python`. Cualquier otra ruta (`/usr/bin/python3`, `/tmp/x/python3`) se compara literalmente y queda fuera salvo que se amplíe.
- Un comando fuera de la lista produce `Comando de pruebas fuera de la lista blanca: <comando>` (o `Comando de mutación ...`) y, con `--run`, no se ejecuta ningún comando.
- Ampliación por proyecto en `.microharness/memory.json`: `"project": {"allowed_test_commands": [["make", "test"], ["uv", "run", "pytest"]]}`. Cada entrada es un prefijo: lista no vacía de strings no vacíos. Cada entrada inválida (o el valor completo si no es lista) se reporta como `project.allowed_test_commands inválido: <entrada>`, bloquea `check` de las tareas no terminadas y las entradas válidas siguen aplicando.
- Las tareas `terminado` no se validan contra la lista ni la ampliación.
- No se incluyen `py -3` ni `uv run`: `python`/`python3` ya se resuelven al intérprete elegido por el lanzador (que contempla `py -3` y `uv`), y `uv run` es un ejecutor genérico (`uv run sh -c ...`) que anularía la lista. Variantes Windows (`mvnw.cmd`, `gradlew.bat`) también requieren ampliación.
- Límite: la lista acota el ejecutable, no lo que ejecuta. `npm|pnpm|yarn|bun test`, `./mvnw`, `./gradlew`, `pytest` (plugins, `conftest.py`), `python -m unittest` y cualquier runner ejecutan código o scripts del propio proyecto; quien pueda modificarlos cambia lo que se ejecuta.

`check --run` captura la salida de cada comando, la reproduce al terminar (no en tiempo real) y, mientras la tarea no esté `terminado`, exige que **cada** comando de `testing.commands` muestre un recuento de pruebas ejecutadas de al menos `testing.min_tests`. `min_tests` es opcional, vale 1 por defecto y debe ser un entero mayor o igual a 1. Un comando que sale con 0 sin un resumen reconocible (por ejemplo, `python -m unittest --help` o `python -c ...`) falla la puerta. Runners reconocidos:

- unittest: `Ran N tests in`.
- pytest: `N passed`.
- bun: `N pass` al inicio de línea.
- Maven: `Tests run: N` (se toma la última línea; en multimódulo refleja solo el último módulo).
- Go: cada línea `ok <paquete>` cuenta como 1, así que se cuentan paquetes, no pruebas.

Si un formato aparece varias veces se usa la última coincidencia; si coinciden varios formatos, el mayor. `mutation.command` se ejecuta pero no se cuenta, y las tareas `terminado` no se cuentan.

### Bloqueo si falta uv

El hook usa `"onFailure": "block"`: si uv no está en `PATH` o el hook falla, Claude Code bloquea toda llamada `Write|Edit|MultiEdit|NotebookEdit|Bash`, también en la sesión principal. Para salir, instala uv o edita `.claude/settings.json` **fuera de Claude Code** (editor o terminal) y reinicia la sesión; con uv disponible, `microsdd off` en tu terminal retira el hook de forma reversible (ver [Activar, desactivar y consultar](#activar-desactivar-y-consultar)).

Comprobación rápida:

```bash
uv --version                                            # el hook requiere uv
sh .microharness/python.sh --version                    # debe mostrar 3.10 o superior
sh .microharness/python.sh .microharness/sdd.py --help  # debe listar los comandos del arnés
```

### Sesiones y subagentes sin rol MicroSDD

El hook deniega por defecto (fail-closed) cuando el evento no trae un `agent_type` exactamente igual a `autor`, `implementador`, `revisor` o `lider`. En ese caso se deniegan `Write`, `Edit`, `MultiEdit`, `NotebookEdit`, `Bash` y `PowerShell` con el motivo:

> Agente no reconocido por MicroSDD: inicia la sesión con `claude --agent lider` o usa uno de los agentes autor, implementador, revisor o lider.

`Read`, `Grep`, `Glob` y las demás herramientas no cambian.

Impacto:

- Una sesión iniciada sin `--agent` y sin `agent: lider` efectivo (por ejemplo, por un override de usuario o si `microsdd status` informa `parcial`) queda sin escritura ni shell.
- Los subagentes ajenos a MicroSDD, como `Explore` o `general-purpose`, pierden esas seis herramientas dentro de un proyecto MicroSDD; `Explore` queda limitado a lectura.

Cómo proceder: lanza la sesión con `claude --agent lider`; delega el trabajo en los cuatro agentes (autor, implementador, revisor, lider); o, si necesitas trabajar sin MicroSDD, ejecuta `microsdd off` en tu terminal **fuera de Claude Code** (o edita allí `.claude/settings.json`) y reinicia la sesión; `microsdd on` lo reactiva.

## Archivos y responsabilidades

```text
CLAUDE.md                    # Entrada corta al contexto común (en el destino: CLAUDE.microsdd.md)
.claude/settings.json        # Líder predeterminado, Opus, esfuerzo y hook
.claude/agents/
  lider.md                   # Orquesta e interactúa con el humano
  autor.md                   # Define QUÉ / CÓMO / PASOS y spec.json
  implementador.md           # Pruebas y código mínimo
  revisor.md                 # Dictamen independiente, sin herramientas de edición
.claude/skills/sdd/SKILL.md  # Activación opcional /sdd
docs/
  AGENT.md                   # Qué aplicación es; estado observado
  arquitectura.md            # Módulos e invariantes comprobados
  convenciones.md            # Estilo, herramientas y reglas de ingeniería
  especificaciones.md        # Índice y contrato del flujo
spec/<slug>/                 # Exactamente cuatro archivos por tarea
  requerimientos.md          # QUÉ: EARS, AC y precondiciones
  plan.md                    # CÓMO: decisión técnica mínima
  tareas.md                  # PASOS: checklist con AC
  spec.json                  # Máquina de estado y política de ejecución
.microharness/
  memory.json                # Estado operativo, decisiones, aprobaciones, hashes
  config.json                # Opcional, humano: modelo y esfuerzo por defecto (no lo crea el instalador)
  sdd.py                     # Puertas estructurales y ejecución de pruebas
.claude/hooks/pretool.py     # Límites de Write/Edit/Bash según agente
tests/test_sdd.py            # Pruebas unitarias del controlador
pyproject.toml               # Paquete microsdd (solo para este repositorio; no se instala en el destino)
src/microsdd/
  __init__.py
  installer.py               # `microsdd install|uninstall|on|off|status` (stdlib; manifiesto único)
tests/test_installer.py      # Pruebas del instalador
```

Los nombres de archivo del arnés y de `spec/<slug>/` son solo ASCII: `check` rechaza cualquier entrada de `spec/<slug>/` con un nombre no ASCII.

En el repositorio destino solo se instalan los archivos del arnés (más `CLAUDE.microsdd.md` y el bloque en `CLAUDE.md`); `pyproject.toml`, `src/` y `tests/` pertenecen a este repositorio.

Los cuatro documentos generales nacen con **pendientes explícitos**, no con datos inventados. El líder los completa al inspeccionar el proyecto y solo los actualiza ante nuevos hechos. La memoria JSON registra aprobaciones declaradas, sellos de tests y revisiones; las especificaciones son contratos separados y versionados. No se usa memoria privada del subagente (`memory:`).

## Flujo y máquina de estados

```text
Programador -> LÍDER -> AUTOR -> spec/...
                              |
                    aprobación humana (spec)
                              |
               pendiente -> proceso
                              |
                         IMPLEMENTADOR
                         pruebas + código
                              |
                           REVISOR
                        check --run + AC
                         /          \
                  RECHAZADO        APROBADO
                     |                |
               corregir y          aprobación
               repetir (<=3)        humana cierre
                     |                |
            agotar -> pendiente  terminado -> commit
```

**Estados únicos:** `pendiente`, `proceso`, `terminado`. No se agrega `blocked`, `rejected`, `in_review` ni `approved`. Las aprobaciones/rechazos son **eventos** en memoria. Una tarea nunca se cierra por `end_turn`, solo tras ambas aprobaciones y la puerta de pruebas. Máximo de 3 revisiones por tarea (valor configurable entre 1 y 3). Al agotarlo, vuelve a `pendiente` para decisión humana.

**Importante:** ejecutar `approve` registra una *declaración* de aprobación. El script no autentica al usuario ni puede demostrar que la aprobación fue emitida por un humano. En esta versión la aprobación válida sigue siendo la respuesta expresa del programador. El líder no debe inventarla. Para políticas de seguridad fuertes se necesita control externo de identidad, reglas Git y CI.

**Bloqueo de autoaprobación:** `approve` y `seal` los ejecuta solo el humano, en una terminal propia: no con `!` dentro de Claude Code ni en una terminal abierta desde ella, que hereda `CLAUDECODE`. `sdd.py` los rechaza con `ERROR:` y código 1 si la variable de entorno `CLAUDECODE` está definida (aunque esté vacía) o si stdin no es una terminal interactiva (TTY); los demás subcomandos no cambian. Además, el hook deniega a `lider`, `autor` e `implementador`:

- `approve` y `seal` por cualquier vía, y todo comando de `Bash`/`PowerShell` que mencione `microharness`, `memory.json` o `sdd.py` (sin distinguir mayúsculas) fuera de estas formas permitidas: un lanzador admitido (`sh .microharness/python.sh`, `python`, `python3`, `py -3` o `uv run --no-project [--quiet] [--python V]`) seguido de `.microharness/sdd.py` y de `init`, `new`, `check`, `review`, `commit-check`, `note`, `release`, `--version` o `--help`; `sh .microharness/python.sh --version`; `sh .microharness/python.sh -m unittest …`; y `git add|diff|status|log|show …` con argumentos simples, sin `--output` ni `--ext-diff`. En ningún caso se admiten `$`, comilla invertida, `\`, saltos de línea ni `;`, `|`, `&`, `>`, `<`, `(`, `)` fuera de comillas. Un `git commit -m` cuyo mensaje mencione esas cadenas también se deniega.
- Toda edición (`Write`, `Edit`, `MultiEdit`, `NotebookEdit`) bajo `.microharness/`, salvo `.microharness/sdd.py` y `.microharness/python.sh` al implementador cuando la spec activa aprobada los incluye en `allowed_paths`.

Desde 1.1.2 la puerta TTY/`CLAUDECODE` vive dentro de `approve`/`seal` (no solo en `main`), los mutadores rechazan memoria ya corrupta frente a `HEAD`, el líder solo escribe `~/.claude/plans/*.md` en la raíz, y las cadenas Bash que mezclan lectura de settings/protegidos con otro comando se deniegan. Firmas criptográficas: ver [aprobacion-firmada-futuro.md](aprobacion-firmada-futuro.md).


**agent_may_approve (1.2.0):** clave booleana en `.microharness/config.json` (default **true** si falta). Con `true`, el líder registra la cita humana `note --fact … --evidence '<cita>' --for-task <slug> --for-phase spec|close|seal|allow-test` y consume con `approve`/`seal`/`allow-test-command … --evidence @note:<id>` sin TTY (nota sin usar, misma tarea/fase, edad ≤ 30 min / `NOTE_EVIDENCE_MAX_AGE_S = 1800`). El hook solo permite esos subcomandos si el comando incluye `--evidence @note:<id>`. Con `false`, modo estricto (TTY + hook deniega). MicroSDD no verifica que un humano escribió la frase.

Desde 1.1.3 hay lanzadores para Windows (`.microharness/python.ps1` para PowerShell y `.microharness/python.cmd` para cmd.exe), los mensajes de `approve`/`seal` sugieren el comando según el sistema operativo y `microsdd worktree sync` prepara worktrees sin compartir `memory.json`: ver [windows-worktrees.md](windows-worktrees.md).

Los agentes leen la memoria con la herramienta Read (o Grep/Glob), no con `cat`. El hook es una heurística de texto (best effort): no detecta ofuscación ni scripts cuyo comando no nombra esas rutas; lo complementan la comprobación `CLAUDECODE`/TTY y la integridad de la memoria frente a `HEAD`. Bajo mintty (Git Bash en Windows), Python nativo puede no ver stdin como TTY: usa Windows Terminal, PowerShell o `winpty`.

## Ciclo operativo por tarea

Comandos ilustrativos; ejecutarlos desde la raíz del repositorio. Sustituye el slug y ajusta specs:

```bash
# El líder prepara contexto y encarga a autor especificar
sh .microharness/python.sh .microharness/sdd.py new corregir-sesion

# Autor edita los cuatro documentos con EARS, AC, alcance y pruebas
sh .microharness/python.sh .microharness/sdd.py check corregir-sesion

# HUMANO, en su terminal (fuera de Claude Code): solo si aprueba explícitamente la spec
sh .microharness/python.sh .microharness/sdd.py approve corregir-sesion spec \
  --by 'Programador' --evidence 'Confirmación explícita: aprobar especificación'

# El implementador escribe y ejecuta pruebas y código.
# Opcional, HUMANO en su terminal: tras revisar las pruebas base, fija su SHA-256.
sh .microharness/python.sh .microharness/sdd.py seal corregir-sesion --by 'Programador' --evidence 'Tests revisados'

# El revisor comprueba límites, integridad, comandos y criterios
sh .microharness/python.sh .microharness/sdd.py check corregir-sesion --run
sh .microharness/python.sh .microharness/sdd.py review corregir-sesion APROBADO \
  --evidence 'AC-01 satisfecha, tests ejecutados, diff revisado'

# HUMANO, en su terminal (fuera de Claude Code): solo si aprueba explícitamente el cierre
sh .microharness/python.sh .microharness/sdd.py approve corregir-sesion close \
  --by 'Programador' --evidence 'Confirmación explícita: aprobar cierre'

# Líder: registrar hechos comprobados y decisiones sin editar memory.json a mano
sh .microharness/python.sh .microharness/sdd.py note \
  --fact 'Las pruebas usan unittest de la biblioteca estándar' --evidence 'tests/test_sdd.py'
sh .microharness/python.sh .microharness/sdd.py note \
  --decision 'Solo dependencias de la biblioteca estándar' --by 'Programador' --evidence 'Confirmación explícita en la sesión'

# Validación sintáctica del mensaje
sh .microharness/python.sh .microharness/sdd.py commit-check 'fix(auth): corrige expiración de sesión'

# Líder: stage EXPLÍCITO y commit atómico; jamás `git add .` o push sin permiso
# git add src/auth/... tests/... spec/corregir-sesion/... .microharness/memory.json
# git commit -m 'fix(auth): corrige expiración de sesión'
```

El comando `seal` requiere que `testing.protected_tests` contenga rutas de tests ya existentes. No es obligatorio si la tarea no necesita congelar un baseline. Con TDD, redacta los tests, confirma RED, solicita revisión humana y *después* sella los tests antes de implementar. Rebaseline requiere una nueva decisión humana; el sellado en este MVP sobrescribe hashes y **no sustituye** protección del repositorio. Commitear el baseline antes de implementación aporta trazabilidad.

El comando `note` añade una observación (`--fact`) a `project.observations` o una decisión (`--decision` con `--by`) a `project.decisions` de `memory.json`. Registrar una decisión es una declaración, no autenticación: `--by` es texto libre y no autentica a nadie.

Para rechazar:

```bash
sh .microharness/python.sh .microharness/sdd.py review corregir-sesion RECHAZADO \
  --evidence 'AC-02 falla con entrada límite; repetir corrección mínima'
```

El implementador trabaja de nuevo desde el motivo concreto del revisor. Si cambia `requerimientos.md`, `plan.md`, `tareas.md` o metadata de `spec.json` ya aprobada, el fingerprint invalida la aprobación anterior. Si cambia código después del dictamen `APROBADO`, la huella del diff también exige nueva revisión antes del cierre. Para reaprobar, el humano revisa nuevamente y se ejecuta `approve ... spec`. No deben usarse cambios silenciosos del contrato.

## `spec.json`: contrato mínimo

El comando `new` genera un ejemplo completo y editable con estos campos relevantes:

```json
{
  "id": "corregir-sesion",
  "state": "pendiente",
  "model": "claude-opus-5-5",
  "effort": "medium",
  "max_iterations": 3,
  "method": { "primary": "SDD", "optional": [], "notes": "" },
  "scope": {
    "allowed_paths": ["src/auth/**", "tests/auth/**"],
    "excluded": []
  },
  "requirements": {
    "acceptance_ids": ["AC-01", "AC-02"],
    "preconditions": ["Existe validador de sesiones"]
  },
  "testing": {
    "strategy": "tdd",
    "commands": [["python", "-m", "pytest", "tests/auth", "-q"]],
    "protected_tests": ["tests/auth/test_expiration.py"],
    "min_tests": 1,
    "mutation": {
      "enabled": false,
      "command": [],
      "reason": "No hay lógica crítica compleja que justifique costo adicional"
    }
  }
}
```

`commands` y `mutation.command` son **arreglos de argumentos**, no cadenas shell; el verificador los ejecuta con `shell=False`. No puede determinar que un comando sea confiable: el líder debe verificarlo antes de ejecutar. `max_iterations` limita revisiones declaradas, no las llamadas internas al modelo, y `effort` es una preferencia consignada en la especificación; el runtime real lo configuran settings/frontmatter, no el JSON automáticamente.

### Modelo y esfuerzo por defecto: `.microharness/config.json`

Archivo opcional de configuración humana del proyecto; el instalador no lo crea ni lo distribuye y `sdd.py` solo lo lee. Es un objeto JSON con dos claves opcionales y ninguna otra:

```json
{ "model": "claude-opus-5-5", "effort": "medium" }
```

- `model`: cadena no vacía. `effort`: uno de `low`, `medium`, `high`, `xhigh`, `max`.
- Si el archivo no existe, o falta una clave, se usan `claude-opus-5-5` y `medium`.
- `new` copia ambos valores en el `spec.json` generado.
- `check` exige que `spec.model` sea igual al modelo configurado, salvo en tareas `terminado` (no se invalidan al cambiar de modelo). `spec.effort` solo debe ser un nivel válido; puede diferir del configurado.
- Un archivo inválido (JSON mal formado, no objeto, claves desconocidas o valores inválidos) hace fallar `new`, `check` y `approve` con `ERROR:` y el motivo, sin escrituras.

Cambiar de modelo o esfuerzo es manual y debe hacerse en todas las fuentes, que `check` no sincroniza:

1. `.microharness/config.json` (`model`, `effort`).
2. `.claude/settings.json` (`model`, `effortLevel`).
3. El frontmatter `model`/`effort` de los cuatro agentes en `.claude/agents/*.md`.
4. El cuerpo de `.claude/agents/autor.md` (y el resto de agentes): modelo y esfuerzo desde `.microharness/config.json` o defaults del proyecto; el frontmatter puede fijar valores para Claude Code.

Las tareas en `pendiente` o `proceso` fallarán `check` hasta actualizar su `spec.model`; ese cambio altera la huella de la especificación y exige reaprobarla.

### EARS, SDD, RDD, ODD

- **EARS:** en `requerimientos.md`, declarar comportamiento del tipo `WHEN <evento>, THE <sistema> SHALL <respuesta>` y AC con datos de entrada y salida verificables. No sustituye discusiones de dominio difíciles.
- **SDD** (primario, siempre): el humano es arquitecto; la spec (reglas de negocio, arquitectura, bordes) es la única fuente de verdad; el agente implementa de forma autónoma tras la aprobación. Ningún código sin spec, revisión humana y cambios acotados.
- **TDD** es estrategia de pruebas: `tdd` o `after`. No asumas TDD como dogma cuando la prueba anticipada no aporte.
- **ODD** (Outcomes-Driven / over-the-shoulder, opcional): iteración rápida desde un pedido directo con resultado esperado; si el humano autoriza, construir de inmediato en un ciclo corto de pair-programming sin fases rígidas de propuesta/diseño. Siguen los cuatro archivos (`plan.md` más ligero) y las puertas approve/note vigentes.
- **RDD** (Receive-Driven, opcional): recepción/auditoría antes del merge con cuatro lentes — legibilidad, resiliencia, robustez, riesgo/seguridad —. Con el microsdd actual: `method.optional: ["RDD"]` y `method.notes` breve; el revisor aplica las lentes en `review`; el humano cierra con approve.
- Si `method.optional` no está vacío, `method.notes` debe ser no vacío (`sdd.py` lo exige): una línea de cómo aplica RDD/ODD en esa tarea.

### Mutation testing y hashing de pruebas

- **Mutation testing:** activar en un módulo de lógica crítica y con herramienta disponible, nunca como requisito indiscriminado. Revisar mutantes supervivientes relevantes y equivalentes; no convertir la cifra de mutation score en objetivo absoluto. `check --run` ejecuta también `mutation.command` si `enabled=true`.
- **SHA-256:** `seal` guarda hash por archivo en memoria. `check` detecta cambios. El sello se compara mientras la tarea no esté `terminado`; tras el cierre queda como registro histórico. Protege principalmente de deriva accidental de pruebas de aceptación. No aporta inmutabilidad real frente a quien pueda modificar tests, memoria y Git. Para reforzarlo: guardar hash y test en commit previo, CI con verificación, revisión/branch protection.

## Qué se obliga y qué NO

| Control | Capa | Alcance real |
|---|---|---|
| Agente líder predeterminado | Claude Code `agent` | Efectivo salvo override explícito de sesión/usuario |
| Acceso por rol | Frontmatter + hook | Bloquea herramientas de edición habituales según agente; deniega `Write`/`Edit`/`MultiEdit`/`NotebookEdit`/`Bash`/`PowerShell` a agentes no reconocidos (ver [Sesiones y subagentes sin rol MicroSDD](#sesiones-y-subagentes-sin-rol-microsdd)); `Bash`/`PowerShell` y herramientas externas no son sandbox universal |
| AC, contrato y tres estados | `sdd.py check` | Validación estructural y estados; no demuestra que el requisito esté bien interpretado |
| Huella de especificación | SHA-256 en `memory.json` | Invalida cambios posteriores a aprobación; no evita manipulación deliberada de la memoria |
| Scope de cambios | Git diff en `check` | Evita cerrar con modificaciones fuera de patrones; empieza con working tree limpio |
| Huella de revisión | Hash de archivos cambiados en el diff | Detecta nuevos cambios de código después de `APROBADO`; no protege de Git/memoria manipulados |
| Tests y mutación | `check --run` | Código de salida de comandos configurados y, en tareas no `terminado`, recuento mínimo de pruebas ejecutadas por comando (`testing.min_tests`, sin contar la mutación); un resumen falso o una prueba deficiente no prueba corrección |
| Lista blanca de runners | `sdd.py check` | En tareas no `terminado`, `testing.commands` y `mutation.command` activo deben empezar por un prefijo conocido o ampliado en `project.allowed_test_commands`; acota el ejecutable, no el código del proyecto que el runner ejecuta, y la ampliación vive en `memory.json` editable |
| Integridad de la memoria | `validate` (`check`, `approve`) frente a `HEAD:.microharness/memory.json` | Compara todas las tareas confirmadas en el último commit: `events` debe conservar como prefijo los eventos confirmados (solo se añade al final); un cambio en `approvals.spec` exige un evento nuevo `aprobación_spec`, en `approvals.close` `aprobación_close` o `aprobación_spec`, en `sealed_tests` `sellado_tests`, y en `review`, `review_fingerprint` o `iterations` `revisión` o `aprobación_spec`; una tarea cerrada en `HEAD` no puede cambiar ni reabrirse, y no puede desaparecer de la memoria mientras exista su `spec/<slug>/`. No aplica sin repositorio, sin commits o sin memoria en `HEAD`; una memoria de `HEAD` ilegible es error. No compara tareas aún no confirmadas ni `project`. Detecta, no impide (ver limitaciones) |
| Reviews y aprobación | Líder + JSON | Contrato procedimental; no autentica al humano |
| Conventional Commits | `commit-check` | Comprueba patrón básico; el carácter atómico depende del `git add` y revisión humana |

El hook necesita confianza del workspace y uv para estar activo; si falla al arrancar (p. ej., falta uv), `"onFailure": "block"` bloquea la herramienta (ver [Bloqueo si falta uv](#bloqueo-si-falta-uv)). Si no se ejecuta, permanecen los controles de revisión y checker pero se pierde el bloqueo previo a herramientas. No usar `bypassPermissions` para simular una seguridad inexistente.

## Evaluación del MVP

Prueba primero con 3 tareas reales de distinto perfil: **corrección localizada**, **funcionalidad de una sola regla**, y **refactor pequeño sin cambio de comportamiento**. Registra por tarea: cambios de líneas, archivos afectados, porcentaje de AC cumplidos, defectos encontrados por revisor y humano, ciclos de rechazo, tiempo/costo y eventual regresión. Compara con las mismas tareas realizadas con Claude Code sin arnés. El arnés se justifica solo si mejora calidad y control con sobrecarga aceptable.

Para comparar esfuerzo `medium` frente a `high`, ver el protocolo (no ejecutado) en [`assets/eval-esfuerzo.md`](eval-esfuerzo.md).

No agregues más agentes, estado ni pasos hasta observar fallas repetibles.

## Fuentes

- Guía proporcionada `prompting-opus-5-5-2026-10-11.md` (prompting, esfuerzo, progreso, guardas, exploración).
- https://platform.claude.com/docs/es/build-with-claude/prompt-engineering/prompting-claude-opus-5-5
- https://code.claude.com/docs/en/sub-agents
- https://code.claude.com/docs/en/settings
- https://code.claude.com/docs/en/memory
- https://code.claude.com/docs/en/hooks

**Limitaciones conocidas:** sin autenticación de aprobaciones, sin sandbox obligatorio, sin validación semántica automática de AC, sin control de costos/tokens por agente, sin comparador histórico de benchmarks. Son límites intencionales del MVP, no características implementadas.

**Integridad de `memory.json`:** la comprobación detecta, no impide. Su base es el último commit (`HEAD`): quien confirma `memory.json` fija la nueva base, de modo que una manipulación confirmada (o un `HEAD` reescrito) se acepta, y un agente puede añadir al final el evento que justifica un cambio fabricado. La protección efectiva depende de que el humano revise el diff de `.microharness/memory.json` antes de cada commit. Ante un error `Integridad de memoria`, recupera la memoria versionada con `git restore --source=HEAD -- .microharness/memory.json` o, si el cambio es legítimo (p. ej. una corrección manual), confírmalo tras revisar el diff. Un error en cualquier tarea bloquea `check` y `approve` de todas. Cualquier fallo de `git show` (incluido uno forzado por el entorno, p. ej. `GIT_DIR`) deja la comprobación en «no aplica»; solo una memoria presente en `HEAD` pero ilegible (no UTF-8, no JSON o `tasks` no objeto) es error.

