# MicroSDD for Claude Opus 5.5

> [!WARNING]
> MicroSDD es un **micro arnés por proyecto**: se instala en la raíz de cada repositorio Git, es agnóstico al stack y trabaja sobre el código base de ese repositorio. **No es un arnés global** ni una configuración de `~/.claude`; el instalador rechaza el directorio home y cualquier ruta bajo `~/.claude`.

> **Propósito:** código mínimo, correcto, verificable y trazable. Claude Code orquesta nativamente. No hay SDK, servidor, base de datos ni dependencia de Python aparte de la biblioteca estándar.

## 1. Requisitos mínimos

| Requisito | Versión | Para qué |
|---|---|---|
| **Python** (obligatorio) | 3.10+ | Ejecuta `.microharness/sdd.py`, que valida y da seguimiento a la máquina de estados (`pendiente` → `proceso` → `terminado`), las aprobaciones, huellas SHA-256 y la puerta de pruebas; también ejecuta el hook `.claude/hooks/pretool.py` que limita herramientas por agente. |
| **uv** (recomendado; obligatorio para el hook) | cualquiera reciente, como ejecutable real en `PATH` (`uv.exe` en Windows) | El hook se declara en forma exec: `uv run --no-project --quiet --python ">=3.10" .claude/hooks/pretool.py`, sin shell ni `python3`. |
| `sh` POSIX | macOS/Linux nativo; Git Bash en Windows | Lanzador `.microharness/python.sh` para el CLI. |
| Git | cualquiera reciente | `check` usa el diff para validar el alcance y la huella de revisión; el instalador exige la raíz del repositorio. |
| `uvx` (incluido en uv) | — | Ejecuta el instalador `microsdd` sin instalarlo de forma permanente. |
| Claude Code | ≥ 2.1.295 | Necesario para `"onFailure": "block"` del hook, además de `agent` predeterminado, frontmatter `effort` y `PreToolUse`. |

**Sin Python ≥3.10 el arnés no puede controlar el flujo:** no hay validación de transiciones de estado, ni registro de aprobaciones, ni puerta de pruebas. Solo se usa la biblioteca estándar, no hay que instalar paquetes.

### Instalación por sistema operativo

Opción recomendada: instalar uv con su instalador oficial (https://docs.astral.sh/uv/); uv obtiene un Python ≥3.10 si no hay uno (la primera ejecución puede descargarlo).

- **macOS / Linux:** `curl -LsSf https://astral.sh/uv/install.sh | sh`. Alternativa: Python ≥3.10 del sistema o del gestor de paquetes.
- **Windows (PowerShell):** `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"`. Instala también Git for Windows para disponer de `sh` (Git Bash).

**Stub de Microsoft Store (Windows):** `python3`/`python` pueden resolver a un alias de la Store que no ejecuta Python (sale con código 49). El lanzador lo descarta al sondear la versión. Para quitarlo: Configuración → Aplicaciones → Configuración avanzada de aplicaciones → Alias de ejecución de aplicaciones, y desactivar `python.exe` y `python3.exe`.

**Windows sin Git Bash:** el hook funciona igual (uv en forma exec, sin shell), pero `sh .microharness/python.sh` no está disponible; invoca el CLI con un Python ≥3.10 explícito, p. ej. `uv run --no-project --python ">=3.10" .microharness/sdd.py --help` o `py -3.12 .microharness/sdd.py --help` (usa una versión ≥3.10 instalada; `py -3` elige la más reciente y no garantiza ≥3.10).

**Argumentos con comillas desde procesos nativos de Windows:** al invocar `sh .microharness/python.sh` desde un proceso nativo (no desde Git Bash), MSYS puede alterar argumentos sin espacios que contienen comillas (p. ej. `print("x")` llega como `print(\x")`). Desde Git Bash no ocurre; el hook no se ve afectado porque usa uv en forma exec.

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

El hook usa `"onFailure": "block"`: si uv no está en `PATH` o el hook falla, Claude Code bloquea toda llamada `Write|Edit|MultiEdit|NotebookEdit|Bash`, también en la sesión principal. Para salir, instala uv o edita `.claude/settings.json` **fuera de Claude Code** (editor o terminal) y reinicia la sesión.

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

- Una sesión iniciada sin `--agent` y sin `agent: lider` efectivo (por ejemplo, por un override de usuario o un `settings.json` fusionado solo con el hook) queda sin escritura ni shell.
- Los subagentes ajenos a MicroSDD, como `Explore` o `general-purpose`, pierden esas seis herramientas dentro de un proyecto MicroSDD; `Explore` queda limitado a lectura.

Cómo proceder: lanza la sesión con `claude --agent lider`; delega el trabajo en los cuatro agentes (autor, implementador, revisor, lider); o, si necesitas trabajar sin MicroSDD, desactiva el hook editando `.claude/settings.json` **fuera de Claude Code** y reinicia la sesión.

## 2. Instalación por proyecto con `uvx`

Desde la raíz de un repositorio Git existente (se recomienda una rama nueva con working tree limpio; si hay cambios sin confirmar solo se muestra una advertencia):

El instalador copia solo los archivos del arnés listados abajo: `assets/` (material de consulta, ver el [proceso de versionado](https://github.com/lgzarturo/microsdd/blob/main/assets/proceso-versionado.md)), `scripts/` (mantenimiento) e `historial/` (historial del propio arnés) no forman parte de la instalación.

```bash
uvx --from git+https://github.com/lgzarturo/microsdd microsdd install --dry-run   # ver el plan
uvx --from git+https://github.com/lgzarturo/microsdd microsdd install             # instalar
```

Se recomienda **fijar un tag o commit revisado** para no instalar cambios no revisados de la rama principal: `uvx --from git+https://github.com/lgzarturo/microsdd@<tag> microsdd install`.

Para probar el instalador desde una copia local usa `uvx --no-cache --from <ruta o git+url> microsdd install`, para no reutilizar un wheel en caché.

| Flag | Efecto |
|---|---|
| `--target RUTA` | Raíz del repositorio destino (por defecto, el directorio actual). Debe ser exactamente `git rev-parse --show-toplevel`. |
| `--dry-run` | Imprime el plan clasificado y termina sin escribir nada. |
| `--force` | Sobrescribe solo los archivos propios del arnés que difieren (útil para actualizar de versión). |

El instalador verifica antes de escribir: que el destino no sea el home ni esté bajo `~/.claude`, que sea la raíz de un repositorio Git y que `uv` esté en el `PATH` como ejecutable real y `uv --version` **se ejecute** con éxito, porque el hook se lanza con `uv run` en forma exec. En Windows se exige `uv.exe`: los shims `uv.cmd`/`.bat` no cuentan. No se exige `python3`; si falta `uv`, muestra cómo instalarlo según el sistema operativo. Planifica todo antes de escribir, es idempotente (una segunda ejecución no cambia nada) y termina con código 0 (éxito o nada que hacer), 1 (precondición o conflicto) o 2 (uso incorrecto). El código 1 también se devuelve si `sdd.py init` o el smoke test del hook fallan **después de escribir** los archivos; en ese caso revisa el mensaje y vuelve a ejecutar el instalador.

Política de conflictos:

| Archivo en el destino | Si no existe | Si existe idéntico | Si existe y difiere |
|---|---|---|---|
| Propios: `.claude/agents/{lider,autor,implementador,revisor}.md`, `.claude/hooks/pretool.py`, `.claude/skills/sdd/SKILL.md`, `.microharness/sdd.py`, `CLAUDE.microsdd.md` | crear | sin cambios | conflicto: código 1 sin escribir nada; `--force` lo actualiza |
| `CLAUDE.md` (compartido) | crear con el bloque de registro (antepone `@AGENTS.md` si existe `AGENTS.md`) | sin cambios si ya tiene `<!-- microsdd:begin -->` | anexar el bloque una sola vez, respetando LF/CRLF; nunca se sobrescribe |
| `.claude/settings.json` (compartido) | crear | sin cambios | se conserva intacto y se escribe `.claude/settings.microsdd.json` (alterno); `agent: lider` y el hook no están activos hasta fusionarlo manualmente |

Al terminar, el instalador ejecuta `.microharness/sdd.py init` con el mismo Python que ejecuta el instalador (crea `docs/`, `spec/` y `.microharness/memory.json` sin sobrescribir), comprueba, también con ese Python, que el hook deniega `Edit` al revisor por la regla de «solo lectura» (un `deny` por otro motivo, como «Guardia inválida», cuenta como fallo) e imprime la lista exacta de archivos para versionar. Usa siempre un `git add` explícito, nunca `git add .`:

```bash
git add CLAUDE.md CLAUDE.microsdd.md .claude/agents/lider.md .claude/agents/autor.md \
  .claude/agents/implementador.md .claude/agents/revisor.md .claude/hooks/pretool.py \
  .claude/skills/sdd/SKILL.md .claude/settings.json .microharness/sdd.py .microharness/python.sh .microharness/memory.json \
  docs/AGENT.md docs/arquitectura.md docs/convenciones.md docs/especificaciones.md
claude --agent lider --model claude-opus-5-5 --effort medium
```

**Migración de `diseño.md` a `plan.md`** (repositorios ya instalados): el documento de diseño de cada tarea se llama ahora `plan.md` y su nombre forma parte de la huella de aprobación. Actualiza el arnés con `--force`, renombra cada `spec/<slug>/diseño.md` a `spec/<slug>/plan.md` (`git mv`) y ejecuta `python <copia de MicroSDD>/scripts/migrar_plan_md.py <raíz>`: recalcula solo las huellas que coinciden con el esquema antiguo, registra un evento `migración_plan_md` por tarea y aborta sin escribir si alguna especificación fue alterada. Como alternativa, reaprueba con `approve <slug> spec` las tareas no terminadas (las terminadas no admiten reaprobación).

**Migración de nombres de `docs/`** (repositorios ya instalados): `docs/convensiones.md` y `docs/specificaciones.md` se llaman ahora `docs/convenciones.md` y `docs/especificaciones.md`. Actualiza el arnés con `--force` y renombra ambos documentos: `git mv docs/convensiones.md docs/convenciones.md` y `git mv docs/specificaciones.md docs/especificaciones.md`. Hasta entonces, `sdd.py init` (y el instalador) imprime un `AVISO:` y no crea el nombre nuevo, para no duplicar documentos; nunca mueve ni borra archivos.

**Eliminación manual** (no hay desinstalador): borra los archivos propios de la tabla, `.microharness/`, `CLAUDE.microsdd.md` y, si aplica, `.claude/settings.microsdd.json`; quita de `CLAUDE.md` el bloque entre `<!-- microsdd:begin -->` y `<!-- microsdd:end -->`; revisa `.claude/settings.json` si fusionaste `agent: lider` y el hook; conserva o elimina `docs/` y `spec/` según te sirvan.

Para desarrollar este repositorio:

```bash
python -m unittest discover -s tests -v   # en Windows; python3 en macOS/Linux
```

`.claude/settings.json` ya fija `agent: lider`, el modelo y el esfuerzo; el flag es redundante y sirve para comprobar que la sesión corre efectivamente con ese rol. Revisa el encabezado `@lider` en Claude Code. Escribe en la sesión: `Quiero corregir X, con el cambio mínimo y criterios verificables` o invoca `/sdd ...`. **No invoques `autor` o `implementador` como conversación principal:** el líder conserva el contexto de decisiones y aprobaciones.

> No está publicado en PyPI ni es un sistema de agentes remoto. No se ha ejecutado Claude Code en este entorno; las comprobaciones realizadas son las pruebas locales del script y del instalador.

## 3. Archivos y responsabilidades

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
  installer.py               # Instalador `microsdd install` (stdlib; manifiesto único)
tests/test_installer.py      # Pruebas del instalador
```

Los nombres de archivo del arnés y de `spec/<slug>/` son solo ASCII: `check` rechaza cualquier entrada de `spec/<slug>/` con un nombre no ASCII.

En el repositorio destino solo se instalan los archivos del arnés (más `CLAUDE.microsdd.md` y el bloque en `CLAUDE.md`); `pyproject.toml`, `src/` y `tests/` pertenecen a este repositorio.

Los cuatro documentos generales nacen con **pendientes explícitos**, no con datos inventados. El líder los completa al inspeccionar el proyecto y solo los actualiza ante nuevos hechos. La memoria JSON registra aprobaciones declaradas, sellos de tests y revisiones; las especificaciones son contratos separados y versionados. No se usa memoria privada del subagente (`memory:`).

## 4. Flujo y máquina de estados

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

## 5. Ciclo operativo por tarea

Comandos ilustrativos; ejecutarlos desde la raíz del repositorio. Sustituye el slug y ajusta specs:

```bash
# El líder prepara contexto y encarga a autor especificar
sh .microharness/python.sh .microharness/sdd.py new corregir-sesion

# Autor edita los cuatro documentos con EARS, AC, alcance y pruebas
sh .microharness/python.sh .microharness/sdd.py check corregir-sesion

# SOLO DESPUÉS de que el humano diga explícitamente que aprueba la spec
sh .microharness/python.sh .microharness/sdd.py approve corregir-sesion spec \
  --by 'Programador' --evidence 'Confirmación explícita: aprobar especificación'

# El implementador escribe y ejecuta pruebas y código.
# Opcional: tras revisión humana de pruebas base, fija su SHA-256.
sh .microharness/python.sh .microharness/sdd.py seal corregir-sesion --by 'Programador'

# El revisor comprueba límites, integridad, comandos y criterios
sh .microharness/python.sh .microharness/sdd.py check corregir-sesion --run
sh .microharness/python.sh .microharness/sdd.py review corregir-sesion APROBADO \
  --evidence 'AC-01 satisfecha, tests ejecutados, diff revisado'

# SOLO después de aprobación humana de cierre
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

## 6. `spec.json`: contrato mínimo

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
4. La línea 14 de `.claude/agents/autor.md`, que nombra el modelo y el esfuerzo de la plantilla.

Las tareas en `pendiente` o `proceso` fallarán `check` hasta actualizar su `spec.model`; ese cambio altera la huella de la especificación y exige reaprobarla.

### EARS, SDD, RDD, ODD

- **EARS:** en `requerimientos.md`, declarar comportamiento del tipo `WHEN <evento>, THE <sistema> SHALL <respuesta>` y AC con datos de entrada y salida verificables. No sustituye discusiones de dominio difíciles.
- **SDD:** obligatorio: ningún código sin spec, revisión humana y cambios acotados.
- **TDD** es estrategia de pruebas: `tdd` o `after`. No asumas TDD como dogma cuando la prueba anticipada no aporte.
- **RDD:** sigla no definida inequívocamente por el documento fuente: `optional: ["RDD"]` solo con definición operativa explícita en `notes`.
- **ODD:** interpretado como *Organic Driven Development* según el contexto del proyecto; es una clasificación opcional de granularidad/crecimiento incremental, no otro ciclo obligatorio. Si se activa, `notes` debe explicar cómo cambia las decisiones.

### Mutation testing y hashing de pruebas

- **Mutation testing:** activar en un módulo de lógica crítica y con herramienta disponible, nunca como requisito indiscriminado. Revisar mutantes supervivientes relevantes y equivalentes; no convertir la cifra de mutation score en objetivo absoluto. `check --run` ejecuta también `mutation.command` si `enabled=true`.
- **SHA-256:** `seal` guarda hash por archivo en memoria. `check` detecta cambios. El sello se compara mientras la tarea no esté `terminado`; tras el cierre queda como registro histórico. Protege principalmente de deriva accidental de pruebas de aceptación. No aporta inmutabilidad real frente a quien pueda modificar tests, memoria y Git. Para reforzarlo: guardar hash y test en commit previo, CI con verificación, revisión/branch protection.

## 7. Qué se obliga y qué NO

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

## 8. Evaluación del MVP

Prueba primero con 3 tareas reales de distinto perfil: **corrección localizada**, **funcionalidad de una sola regla**, y **refactor pequeño sin cambio de comportamiento**. Registra por tarea: cambios de líneas, archivos afectados, porcentaje de AC cumplidos, defectos encontrados por revisor y humano, ciclos de rechazo, tiempo/costo y eventual regresión. Compara con las mismas tareas realizadas con Claude Code sin arnés. El arnés se justifica solo si mejora calidad y control con sobrecarga aceptable.

Para comparar esfuerzo `medium` frente a `high`, ver el protocolo (no ejecutado) en [`assets/eval-esfuerzo.md`](assets/eval-esfuerzo.md).

No agregues más agentes, estado ni pasos hasta observar fallas repetibles.

## 9. Fuentes

- Guía proporcionada `prompting-opus-5-5-2026-10-11.md` (prompting, esfuerzo, progreso, guardas, exploración).
- https://platform.claude.com/docs/es/build-with-claude/prompt-engineering/prompting-claude-opus-5-5
- https://code.claude.com/docs/en/sub-agents
- https://code.claude.com/docs/en/settings
- https://code.claude.com/docs/en/memory
- https://code.claude.com/docs/en/hooks

**Limitaciones conocidas:** sin autenticación de aprobaciones, sin sandbox obligatorio, sin validación semántica automática de AC, sin control de costos/tokens por agente, sin comparador histórico de benchmarks. Son límites intencionales del MVP, no características implementadas.

**Integridad de `memory.json`:** la comprobación detecta, no impide. Su base es el último commit (`HEAD`): quien confirma `memory.json` fija la nueva base, de modo que una manipulación confirmada (o un `HEAD` reescrito) se acepta, y un agente puede añadir al final el evento que justifica un cambio fabricado. La protección efectiva depende de que el humano revise el diff de `.microharness/memory.json` antes de cada commit. Ante un error `Integridad de memoria`, recupera la memoria versionada con `git restore --source=HEAD -- .microharness/memory.json` o, si el cambio es legítimo (p. ej. una corrección manual), confírmalo tras revisar el diff. Un error en cualquier tarea bloquea `check` y `approve` de todas. Cualquier fallo de `git show` (incluido uno forzado por el entorno, p. ej. `GIT_DIR`) deja la comprobación en «no aplica»; solo una memoria presente en `HEAD` pero ilegible (no UTF-8, no JSON o `tasks` no objeto) es error.

## 10. Licencia

MicroSDD se distribuye bajo la licencia MIT. Copyright (c) 2026 Arturo López. Consulte el texto completo en [LICENSE](LICENSE).

Los archivos que `microsdd install` copia en otro repositorio siguen cubiertos por la licencia MIT. Si los redistribuye, debe conservar el aviso de copyright y el aviso de permiso, que el instalador no añade por usted.
