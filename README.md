# MicroSDD 0.1 · Miniarnés para Claude Opus 5.5

> **Propósito:** código mínimo, correcto, verificable y trazable. Claude Code orquesta nativamente. No hay SDK, servidor, base de datos ni dependencia de Python aparte de la biblioteca estándar.

## 1. Requisitos mínimos

| Requisito | Versión | Para qué |
|---|---|---|
| **Python** (obligatorio) | 3.10+ | Ejecuta `.microharness/sdd.py`, que valida y da seguimiento a la máquina de estados (`pendiente` → `proceso` → `terminado`), las aprobaciones, huellas SHA-256 y la puerta de pruebas; también ejecuta el hook `.claude/hooks/pretool.py` que limita herramientas por agente. |
| **uv** (recomendado; obligatorio para el hook) | cualquiera reciente, como ejecutable real en `PATH` (`uv.exe` en Windows) | El hook se declara en forma exec: `uv run --no-project --quiet --python ">=3.10" .claude/hooks/pretool.py`, sin shell ni `python3`. |
| `sh` POSIX | macOS/Linux nativo; Git Bash en Windows | Lanzador `.microharness/python.sh` para el CLI. |
| Git | cualquiera reciente | `check` usa el diff para validar el alcance y la huella de revisión. |
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

### Bloqueo si falta uv

El hook usa `"onFailure": "block"`: si uv no está en `PATH` o el hook falla, Claude Code bloquea toda llamada `Write|Edit|MultiEdit|NotebookEdit|Bash`, también en la sesión principal. Para salir, instala uv o edita `.claude/settings.json` **fuera de Claude Code** (editor o terminal) y reinicia la sesión.

Comprobación rápida:

```bash
uv --version                                            # el hook requiere uv
sh .microharness/python.sh --version                    # debe mostrar 3.10 o superior
sh .microharness/python.sh .microharness/sdd.py --help  # debe listar los comandos del arnés
```

## 2. Instalación en un repositorio de prueba

Copia **el contenido** de esta carpeta a la raíz de un repositorio Git existente (no copies una carpeta `microsdd-opus55/` dentro del proyecto). Revisa conflictos con `.claude/settings.json`, `CLAUDE.md` y otras reglas. Se recomienda un repositorio de prueba o una rama nueva con working tree limpio. Verifica antes los [requisitos mínimos](#1-requisitos-mínimos); Python ≥3.10 es indispensable, y el hook requiere uv en `PATH`.

```bash
sh .microharness/python.sh .microharness/sdd.py init
sh .microharness/python.sh -m unittest discover -s tests -v
claude --agent lider --model claude-opus-5-5 --effort medium
```

`.claude/settings.json` ya fija `agent: lider`, el modelo y el esfuerzo; el flag es redundante y sirve para comprobar que la sesión corre efectivamente con ese rol. Revisa el encabezado `@lider` en Claude Code. Escribe en la sesión: `Quiero corregir X, con el cambio mínimo y criterios verificables` o invoca `/sdd ...`. **No invoques `autor` o `implementador` como conversación principal:** el líder conserva el contexto de decisiones y aprobaciones.

> No es un paquete listo para publicar ni un sistema de agentes remoto. No se ha ejecutado Claude Code en este entorno; las comprobaciones realizadas son las pruebas locales del script.

## 3. Archivos y responsabilidades

```text
CLAUDE.md                    # Entrada corta al contexto común
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
  convensiones.md            # Estilo, herramientas y reglas de ingeniería
  specificaciones.md         # Índice y contrato del flujo
spec/<slug>/                 # Exactamente cuatro archivos por tarea
  requerimientos.md          # QUÉ: EARS, AC y precondiciones
  diseño.md                  # CÓMO: decisión técnica mínima
  tareas.md                  # PASOS: checklist con AC
  spec.json                  # Máquina de estado y política de ejecución
.microharness/
  memory.json                # Estado operativo, decisiones, aprobaciones, hashes
  sdd.py                     # Puertas estructurales y ejecución de pruebas
.claude/hooks/pretool.py     # Límites de Write/Edit/Bash según agente
tests/test_sdd.py            # Pruebas unitarias del controlador
```

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

# Validación sintáctica del mensaje
sh .microharness/python.sh .microharness/sdd.py commit-check 'fix(auth): corrige expiración de sesión'

# Líder: stage EXPLÍCITO y commit atómico; jamás `git add .` o push sin permiso
# git add src/auth/... tests/... spec/corregir-sesion/... .microharness/memory.json
# git commit -m 'fix(auth): corrige expiración de sesión'
```

El comando `seal` requiere que `testing.protected_tests` contenga rutas de tests ya existentes. No es obligatorio si la tarea no necesita congelar un baseline. Con TDD, redacta los tests, confirma RED, solicita revisión humana y *después* sella los tests antes de implementar. Rebaseline requiere una nueva decisión humana; el sellado en este MVP sobrescribe hashes y **no sustituye** protección del repositorio. Commitear el baseline antes de implementación aporta trazabilidad.

Para rechazar:

```bash
sh .microharness/python.sh .microharness/sdd.py review corregir-sesion RECHAZADO \
  --evidence 'AC-02 falla con entrada límite; repetir corrección mínima'
```

El implementador trabaja de nuevo desde el motivo concreto del revisor. Si cambia `requerimientos.md`, `diseño.md`, `tareas.md` o metadata de `spec.json` ya aprobada, el fingerprint invalida la aprobación anterior. Si cambia código después del dictamen `APROBADO`, la huella del diff también exige nueva revisión antes del cierre. Para reaprobar, el humano revisa nuevamente y se ejecuta `approve ... spec`. No deben usarse cambios silenciosos del contrato.

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
    "mutation": {
      "enabled": false,
      "command": [],
      "reason": "No hay lógica crítica compleja que justifique costo adicional"
    }
  }
}
```

`commands` y `mutation.command` son **arreglos de argumentos**, no cadenas shell; el verificador los ejecuta con `shell=False`. No puede determinar que un comando sea confiable: el líder debe verificarlo antes de ejecutar. `max_iterations` limita revisiones declaradas, no las llamadas internas al modelo, y `effort` es una preferencia consignada en la especificación; el runtime real lo configuran settings/frontmatter, no el JSON automáticamente.

### EARS, SDD, RDD, ODD

- **EARS:** en `requerimientos.md`, declarar comportamiento del tipo `WHEN <evento>, THE <sistema> SHALL <respuesta>` y AC con datos de entrada y salida verificables. No sustituye discusiones de dominio difíciles.
- **SDD:** obligatorio: ningún código sin spec, revisión humana y cambios acotados.
- **TDD** es estrategia de pruebas: `tdd` o `after`. No asumas TDD como dogma cuando la prueba anticipada no aporte.
- **RDD:** sigla no definida inequívocamente por el documento fuente: `optional: ["RDD"]` solo con definición operativa explícita en `notes`.
- **ODD:** interpretado como *Organic Driven Development* según el contexto del proyecto; es una clasificación opcional de granularidad/crecimiento incremental, no otro ciclo obligatorio. Si se activa, `notes` debe explicar cómo cambia las decisiones.

### Mutation testing y hashing de pruebas

- **Mutation testing:** activar en un módulo de lógica crítica y con herramienta disponible, nunca como requisito indiscriminado. Revisar mutantes supervivientes relevantes y equivalentes; no convertir la cifra de mutation score en objetivo absoluto. `check --run` ejecuta también `mutation.command` si `enabled=true`.
- **SHA-256:** `seal` guarda hash por archivo en memoria. `check` detecta cambios. Protege principalmente de deriva accidental de pruebas de aceptación. No aporta inmutabilidad real frente a quien pueda modificar tests, memoria y Git. Para reforzarlo: guardar hash y test en commit previo, CI con verificación, revisión/branch protection.

## 7. Qué se obliga y qué NO

| Control | Capa | Alcance real |
|---|---|---|
| Agente líder predeterminado | Claude Code `agent` | Efectivo salvo override explícito de sesión/usuario |
| Acceso por rol | Frontmatter + hook | Bloquea herramientas de edición habituales según agente; `Bash` y herramientas externas no son sandbox universal |
| AC, contrato y tres estados | `sdd.py check` | Validación estructural y estados; no demuestra que el requisito esté bien interpretado |
| Huella de especificación | SHA-256 en `memory.json` | Invalida cambios posteriores a aprobación; no evita manipulación deliberada de la memoria |
| Scope de cambios | Git diff en `check` | Evita cerrar con modificaciones fuera de patrones; empieza con working tree limpio |
| Huella de revisión | Hash de archivos cambiados en el diff | Detecta nuevos cambios de código después de `APROBADO`; no protege de Git/memoria manipulados |
| Tests y mutación | `check --run` | Código de salida de comandos configurados; un comando deficiente no prueba corrección |
| Reviews y aprobación | Líder + JSON | Contrato procedimental; no autentica al humano |
| Conventional Commits | `commit-check` | Comprueba patrón básico; el carácter atómico depende del `git add` y revisión humana |

El hook necesita confianza del workspace y uv para estar activo; si falla al arrancar (p. ej., falta uv), `"onFailure": "block"` bloquea la herramienta (ver [Bloqueo si falta uv](#bloqueo-si-falta-uv)). Si no se ejecuta, permanecen los controles de revisión y checker pero se pierde el bloqueo previo a herramientas. No usar `bypassPermissions` para simular una seguridad inexistente.

## 8. Evaluación del MVP

Prueba primero con 3 tareas reales de distinto perfil: **corrección localizada**, **funcionalidad de una sola regla**, y **refactor pequeño sin cambio de comportamiento**. Registra por tarea: cambios de líneas, archivos afectados, porcentaje de AC cumplidos, defectos encontrados por revisor y humano, ciclos de rechazo, tiempo/costo y eventual regresión. Compara con las mismas tareas realizadas con Claude Code sin arnés. El arnés se justifica solo si mejora calidad y control con sobrecarga aceptable.

No agregues más agentes, estado ni pasos hasta observar fallas repetibles.

## 9. Fuentes

- Guía proporcionada `prompting-opus-5-5-2026-10-11.md` (prompting, esfuerzo, progreso, guardas, exploración).
- https://platform.claude.com/docs/es/build-with-claude/prompt-engineering/prompting-claude-opus-5-5
- https://code.claude.com/docs/en/sub-agents
- https://code.claude.com/docs/en/settings
- https://code.claude.com/docs/en/memory
- https://code.claude.com/docs/en/hooks

**Limitaciones conocidas:** sin autenticación de aprobaciones, sin sandbox obligatorio, sin validación semántica automática de AC, sin control de costos/tokens por agente, sin comparador histórico de benchmarks. Son límites intencionales del MVP, no características implementadas.
