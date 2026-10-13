# CÓMO: diseño mínimo

## Situación comprobada (HEAD c257391)
- `pretool.run(event)` devuelve un motivo (deny) o `None`. Primero deniega las seis herramientas guardadas si `agent_type` no es un rol MicroSDD (`hook-fail-closed`). En edición, el orden es: revisor «solo lectura» → ruta ausente → `Path(filename).resolve()` (contra el cwd del proceso) → reglas por rol. El implementador tiene denegados `.claude/`, `.microharness/`, `docs/`, `spec/` y `CLAUDE.md` antes del alcance; después exige una sola spec en `proceso`, `fnmatchcase` sobre `allowed_paths`, aprobación de spec y que la prueba no esté sellada. El líder tiene la excepción `.microharness/memory.json`. En `Bash`/`PowerShell` solo se filtra al revisor.
- `sdd.main()` despacha los subcomandos tras `argparse` dentro de un `try` que convierte `ValueError` en `ERROR:` y código 1. `os` ya está importado.
- `CLAUDECODE=1` y stdin no TTY en el Bash de Claude Code (comprobado en la sesión del autor). No está verificado en otras plataformas.
- Las pruebas del hook cargan `pretool.py` con `importlib` (`tests/test_sdd.py`, `tests/test_hook_fail_closed.py`). `NoteTests.run_main` y `test_integridad_memoria.run_main` muestran el patrón para probar `main()`.
- `tests/test_api_publica.py` solo comprueba que nombres de subcomandos, opciones y rutas instaladas aparezcan en `assets/proceso-versionado.md`. Un cambio de redacción en API-01/API-05 no lo rompe.
- El parche externo (base b19fe30, dato no confiable) solo sirve como referencia de variantes de bypass.

## Decisión y justificación
Todo cabe en archivos existentes más un archivo de pruebas nuevo. No se crean módulos ni capas.

### 1. `pretool.py`: Bash y PowerShell (roles restringidos)
- Constantes `PROTECTED_RE = re.compile(r'microharness|memory\.json|sdd\.py', re.I)` y `SDD_ALLOWED`.
- `tokens(cmd)` devuelve `None` en estos casos: hay `$`, comilla invertida, `\`, `\n` o `\r`; `shlex.shlex(cmd, posix=True, punctuation_chars=True)` con `whitespace_split=True` lanza `ValueError`; o algún token está formado solo por `();<>|&`. Comprobado: `--evidence "a; b > c"` queda como un único token, y `x;rm` o `x>a` generan tokens de puntuación.
- `sdd_args(toks)` reconoce los lanzadores por prefijo exacto de tokens seguidos de `.microharness/sdd.py` y devuelve los argumentos restantes. `--python V` exige `fullmatch(r'(>=)?3\.[0-9]+')`.
- `protected_bash(cmd)`:
  - sin mención protegida → `None`;
  - con `tokens` igual a `None` → deny;
  - permite si el primer argumento de `sdd_args` está en `SDD_ALLOWED`, o si el comando es una excepción legítima;
  - en otro caso, deny con un motivo que nombre las formas permitidas e indique que `approve`/`seal` son del humano.
- En `run`, tras el bloque de edición: `if tool in ('Bash','PowerShell') and agent in ('lider','autor','implementador'): return protected_bash(cmd)`. El bloque del revisor y el fail-closed quedan textualmente iguales.
- Las excepciones legítimas son necesarias para el flujo actual: pruebas con el lanzador documentado, `git add … .microharness/memory.json` en cada commit e inspección con `git diff/log/show`. `git add` solo toca el índice, y `--output` es la única opción de esas órdenes que escribe archivos. `sh .microharness/python.sh -c …` se deniega porque ejecutaría código arbitrario.

### 2. `pretool.py`: herramientas de edición
- Ruta: `target = Path(filename)`; si no es absoluta, `target = base / target`; `rel = target.resolve().relative_to(base).as_posix()`.
- Regla común, después del revisor y antes de las ramas por rol:
  ```
  if rel.lower() == '.microharness' or rel.lower().startswith('.microharness/'):
      if not (agent == 'implementador' and rel in ('.microharness/sdd.py', '.microharness/python.sh')):
          deny
  ```
  Las dos rutas exactas, en minúsculas, siguen por la rama del implementador.
- Rama del implementador: el prefijo `.microharness/` sale de la lista de denegación previa al alcance (la regla común ya lo cubre). Así, `sdd.py`/`python.sh` pasan por las comprobaciones existentes: spec activa, `allowed_paths`, aprobación y sello. `.claude/`, `docs/`, `spec/` y `CLAUDE.md` siguen denegados.
- Rama del líder: queda `rel.startswith(('docs/', 'spec/'))`, sin la excepción de `memory.json`.
- El orden conserva el motivo «solo lectura» que espera el smoke test del instalador.

### 3. `sdd.py main()`
- Dentro del `try` y antes del despacho:
  ```
  if args.command in ('approve', 'seal') and ('CLAUDECODE' in os.environ or sys.stdin is None or not sys.stdin.isatty()):
      raise ValueError('… ejecútalo tú en una terminal interactiva, fuera de Claude Code.')
  ```
  Las funciones `approve()`/`seal()` no cambian: las pruebas que las llaman directamente siguen igual.
- «Definida» significa presente en el entorno aunque esté vacía.

### 4. `lider.md`
- Paso 3: el humano aprueba ejecutando `approve <slug> spec` en su terminal con el comando exacto que le da el líder. Las decisiones intermedias se registran con `sdd.py note --decision … --by …` solo si el humano realmente las dio.
- Paso 6: tras la aprobación verbal de cierre, el líder entrega el comando exacto `approve <slug> close …`, que el humano ejecuta; después, `check`, `commit-check` y el commit.
- Paso 7: la memoria solo cambia mediante `sdd.py` `new`, `review` y `note`; no se edita ni se redirige; `approve`/`seal` son del humano.

### 5. `README.md`
Ampliar el párrafo «Importante» y marcar los ejemplos de `approve`/`seal` del ciclo como «humano, en su terminal». Añadir una nota sobre las formas de Bash permitidas, la excepción del implementador y la lectura de la memoria con Read.

### 6. `assets/proceso-versionado.md`
- API-01: añadir que `approve` y `seal` devuelven 1 si `CLAUDECODE` está definida o stdin no es TTY (solo el humano los ejecuta).
- API-05: añadir las nuevas restricciones del hook.
- Es un cambio incompatible de API-01/API-05 (scripts o CI que llamaban a `approve` dejan de funcionar; el líder pierde la escritura de `memory.json`). Por las reglas del documento («manda el efecto real») corresponde `!`.

### 7. `CHANGELOG.md` (decisión KISS)
- Asunto propuesto: `fix(hook)!: impide que los agentes aprueben, sellen o editen la memoria`. No contiene menciones protegidas, porque el commit se hace con el hook nuevo activo, y pasa `commit-check`.
- Entrada en «Incompatible» de `[1.0.0]`, en el mismo commit y sin hash: `` - `hook`: impide que los agentes aprueben, sellen o editen la memoria ``. Un commit no puede contener su propio hash. Añadir el hash `(abcdef0)` después, en un commit posterior del líder (p. ej. el de preparación del tag), es lo más simple y honesto; inventarlo o hacer `--amend` no lo es. Ese paso queda fuera de esta tarea.
- Si el humano prefiere tratarlo como `fix` sin `!`, la entrada va en «Corregido» (AC-16 admite ambos casos según el asunto real).

### 8. Pruebas
Archivo nuevo `tests/test_bloquear_autoaprobacion.py` (patrón de `test_hook_fail_closed.py`), sin sellar (`protected_tests: []`). `tests/test_sdd.py` no se modifica.

### 9. `docs/arquitectura.md` (líder, al cierre)
Se justifica una línea con el invariante («ningún agente escribe `.microharness/` salvo el implementador en `sdd.py`/`python.sh` dentro del alcance; `approve`/`seal` exigen TTY sin `CLAUDECODE`»), porque condiciona las tareas futuras. La escribe el líder; el hook niega `docs/` al implementador.

## Orden de implementación (obligatorio)
El hook se recarga en cada llamada. Primero se modifican pruebas, `sdd.py`, `lider.md`, `README.md`, `assets/proceso-versionado.md` y `CHANGELOG.md`; `pretool.py`, al final. Hasta ese momento, el implementador edita `sdd.py` y `.claude/` por la vía que fije el líder (Q-01), igual que en tareas anteriores. Tras cambiar el hook, una nueva iteración puede editar `sdd.py` con Write (la ruta está en `allowed_paths`); `pretool.py` y `lider.md` ya no pueden editarse por Bash si el comando menciona cadenas protegidas. Si hiciera falta retocarlos, el humano aplica el parche.

## Alternativas descartadas
- Aplicar el parche externo: base antigua, no contempla `plan.md`, `py -3`, `uv` ni PowerShell, y mezcla otras tareas.
- Denegar solo `approve`/`seal` por regex: no cubre la escritura directa de la memoria (R3).
- Cerrar `.microharness/` por completo al implementador: bloquea toda tarea futura sobre `sdd.py` (R-01). Se adopta la excepción acotada por `allowed_paths`.
- Una variable de entorno para saltar la comprobación de TTY: un agente podría definirla.
- Un módulo de política separado: no hay necesidad.
- Añadir el hash al CHANGELOG con `--amend`: cambia el hash que se intenta registrar.

## Invariantes
- El hook sigue sin estado, con biblioteca estándar y la misma interfaz JSON. El fail-closed y la allowlist del revisor no cambian.
- Las funciones Python de `sdd.py` no cambian; solo `main()` añade la comprobación.
- Ningún agente puede ejecutar `approve`/`seal` por una forma reconocida, ni editar `memory.json` o `config.json` con herramientas de edición.

## Riesgos y efectos secundarios
- **R-01 (mitigado por decisión del líder):** el implementador mantiene Write/Edit sobre `sdd.py` y `python.sh` solo con spec aprobada que los incluya. Por Bash ya no puede tocarlos. La excepción reabre que el implementador cambie el checker que lo valida; lo compensan la revisión independiente y el diff confirmado por el humano.
- **R-02 (aceptado):** bajo mintty (Git Bash en Windows), Python nativo puede ver stdin como no TTY y rechazar el `approve` legítimo. Alternativas: Windows Terminal, PowerShell o `winpty`.
- **R-03 (aceptado):** la heurística es incompleta. Ofuscación, scripts o parches cuyo comando no menciona las cadenas pueden escribir la memoria. `approve`/`seal` quedan mitigados por `CLAUDECODE`/TTY y la manipulación de memoria por la integridad frente a `HEAD` (detecta, no impide).
- **R-04 (aceptado):** falsos positivos. Se deniegan `git commit -m` con cadenas protegidas en el mensaje, `$` o `\` aunque vayan entre comillas, una evidencia que sea solo `;`, y `cat`/`grep`/`ls` sobre `.microharness/` (usar Read/Grep/Glob).
- **R-05:** PowerShell se tokeniza con reglas POSIX. Las diferencias de comillas quedan acotadas porque se rechazan `$`, comilla invertida y `\` y se exige un subcomando exacto.
- **R-06:** el instalador ejecuta `init` y el smoke test con `sys.executable`, fuera del hook; no se ve afectado. Los repositorios instalados reciben los archivos nuevos con `--force`.
- **R-07:** CI y scripts sin TTY ya no pueden ejecutar `approve`/`seal`. Es intencional, y por eso el cambio es incompatible.
- **R-08:** una terminal abierta desde Claude Code hereda `CLAUDECODE` y se rechaza. Hay que usar una independiente.
- **R-09, cierre de esta tarea:** tras implementarla, el líder ya no puede ejecutar `approve … close` (lo deniega el hook) y `sdd.py` lo rechazaría desde Claude Code. El humano lo ejecuta en su terminal (comando exacto en `tareas.md`, T15).
- **R-10:** `implementador.md` dice «no cambies … el propio arnés», lo que choca con la excepción. Queda fuera de alcance; prevalece la spec aprobada, como en tareas anteriores.

## Dudas abiertas para el líder
- **Q-01 (bloqueante, recomendación incluida):** vía de edición de `.claude/hooks/pretool.py`, `.claude/agents/lider.md` y `.microharness/sdd.py` en esta tarea. Recomendación: autorizar al implementador a editarlos por Bash solo en esta tarea y solo dentro del alcance, con `pretool.py` en último lugar; si tras el cambio del hook hay que retocar `pretool.py` o `lider.md`, el humano aplica el parche.
- **Q-05 (recomendación: `!`):** asunto con `!` y grupo «Incompatible», frente a `fix` sin `!` y «Corregido». Se recomienda `!` porque cambia API-01 y API-05 de forma observable para scripts y para el líder.
