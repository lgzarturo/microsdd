# CÓMO: diseño mínimo

## Situación comprobada
- `validate(slug, run, scope)` ya carga la memoria de trabajo (`task_files`) y acumula errores en una lista; `check`, `approve spec` y `approve close` la usan. Las comprobaciones de memoria actuales solo miran el slug comprobado.
- Existe el helper `git(*args)` (con `core.quotePath=false`, `cwd=ROOT`, UTF-8) que lanza `ValueError` si `git` devuelve código distinto de 0; si el ejecutable no existe, `subprocess.run` lanza `OSError` (`FileNotFoundError`).
- Las operaciones legítimas sobrescriben `approvals.spec`, `sealed_tests`, `review`, `review_fingerprint`, `iterations` y `approvals.close` (por reset), pero siempre añaden un evento identificable; `events` es append-only en la práctica.
- Una tarea con `approvals.close` no nulo solo puede estar en `terminado` (se escriben juntos en `approve close`) y `approve spec` rechaza tareas `terminado`: su entrada de memoria no tiene operación legítima que la cambie.
- La limpieza de release borra los `spec/<slug>/` archivados y deja `tasks: {}`; el commit de limpieza lo hace el humano.
- Las pruebas de `tests/test_sdd.py` reasignan `sdd.ROOT` y `sdd.MEMORY` a un directorio temporal y tienen un helper `git_repo()`; la mayoría no crea repo o no confirma `memory.json`, por lo que la nueva comprobación no les aplica.

## Decisión y justificación
**D-01. Comparación con `HEAD` dentro de `validate` (opción elegida).** Nueva función `memory_integrity(memory: dict) -> list[str]` en `sdd.py`, llamada desde `validate` justo después de cargar la memoria (independiente de `scope`, antes del bloque `run`). Pasos:
1. `rel = MEMORY.relative_to(ROOT).as_posix()`; `raw = git('show', f'HEAD:{rel}')`. Si lanza `ValueError` u `OSError` → `[]` (no aplica: sin repo, sin commits o sin memoria en `HEAD`). Una sola invocación (AC-11).
2. `json.loads(raw)`; si falla o `tasks` no es `dict` → un error `HEAD ilegible` (falla cerrado; se corrige confirmando una memoria válida).
3. Para cada `slug, base` de la base (orden de inserción):
   - Falta en trabajo: error solo si `(ROOT/'spec'/slug).is_dir()`.
   - Cerrada en base (`approvals.close` no nulo): error si la entrada de trabajo `!=` base; error si `spec/<slug>/spec.json` existe y su `state != 'terminado'` (lectura con `load`; si es ilegible, error de integridad en lugar de excepción).
   - Abierta en base: `events` de base debe ser prefijo exacto (`work_events[:n] == base_events`, con comprobación de tipo lista); tipos de eventos nuevos = `{e.get('event') for e in work_events[n:] if isinstance(e, dict)}`; para cada campo de una tabla constante `INTEGRITY_FIELDS` (ruta → tipos justificantes), si el valor difiere y no hay intersección con los tipos nuevos, error con el nombre del campo.
4. Mensajes `Integridad de memoria: <slug>: <detalle>`.

Valores ausentes se leen como `None` (`.get`), de modo que borrar una clave cuenta como cambio. La comparación es sobre JSON parseado, así que formato, indentación y CRLF no influyen. Las tareas nuevas y `project` no se recorren (REQ-09).

Por qué esta opción: usa solo Git ya presente y el helper existente, una lectura y comparaciones de diccionarios; no cambia el formato de la memoria ni el flujo humano; al vivir en `validate`, bloquea también `approve` y `check --run` sin código adicional. La base `HEAD` coincide con el punto en que el humano revisa el diff de `memory.json` antes de confirmar.

**D-02. Trailer `Approved-by:` — descartado (YAGNI).** Exigir un commit del humano con trailer no añade garantía frente a un agente que ya puede ejecutar `git commit` por Bash: escribir el trailer es tan fácil como editar la memoria. Solo aportaría con firma de commits (GPG/SSH) y política de verificación, que es la «criptografía exagerada» que el propio análisis desaconseja, exige configuración por desarrollador y cambia el flujo de commits. La comparación con `HEAD` cubre el caso objetivo (manipulación silenciosa no confirmada) y deja la confirmación como punto de control humano. Si el proyecto adopta firmas en el futuro, sería otra tarea.

**D-03. Limpieza de release sin subcomando nuevo.** En vez de un subcomando o una excepción explícita, una tarea puede desaparecer de la memoria solo si también desapareció su `spec/<slug>/`, que es exactamente lo que hace `limpiar_arnes.py`. No hay que tocar el script ni el flujo. Alternativa descartada: «comparar solo tareas presentes en trabajo» (más simple, pero no detecta el borrado de la entrada de otra tarea con su spec aún presente).

**D-04. Migraciones.** Las huellas reescritas por `migrar_plan_md.py` ya están confirmadas: forman parte de la base. Una migración futura que modifique tareas cerradas fallará `check` hasta confirmarla; es el comportamiento deseado (el humano revisa el diff y confirma).

### Alternativas descartadas
- **Hash de `memory.json` en un evento o en un archivo aparte:** el agente que edita la memoria puede recalcular el hash; no aporta sobre `HEAD`.
- **Prohibir cualquier cambio en campos vigilados:** rompe reaprobaciones, revisiones y sellos legítimos.
- **Exigir coherencia evento↔campo (misma `at`, `by`, huella):** más código y acoplamiento con el formato de cada operación; un atacante que fabrica el evento puede fabricar también la coherencia. YAGNI.
- **Comparar contra `origin/main` o el índice:** dependencias de red/configuración o base manipulable (`git add`); `HEAD` es suficiente.
- **Proteger `project.*`:** fuera de lo pedido; se deja como decisión abierta.

## Invariantes y riesgos
- Invariantes: sin repo/commits/memoria en `HEAD` el comportamiento de `validate` no cambia; las operaciones legítimas de `sdd.py` nunca producen errores de integridad (AC-05); la comprobación no escribe nada ni toma el lock.
- **Límite honesto:** detecta, no impide. Quien controla Git puede confirmar la manipulación (`git commit`) o reescribir `HEAD`, y la nueva base la acepta; un agente puede fabricar el evento justificante junto con el cambio; un agente puede hacer fallar `git show` (p. ej. variables `GIT_DIR`) y la comprobación queda en «no aplica». La protección efectiva depende de que el humano revise el diff de `memory.json` en cada commit y de `bloquear-autoaprobacion`.
- **Efecto global:** un error de integridad en cualquier tarea bloquea `check` y `approve` de todas. Es intencional; el mensaje indica slug y campo, y README explica la recuperación.
- **Falsos positivos:** ediciones manuales legítimas de la memoria (p. ej. corregir una evidencia) exigen confirmarlas antes de seguir; `note` no se ve afectado (`project` no se compara).
- **Rendimiento:** una invocación de `git` y un `json.loads` (memoria actual ~78 KB, 24 tareas) por `validate`; despreciable frente a `diff_files`.
- **Pruebas existentes:** las que crean repo con `git_repo()` no confirman `memory.json` (no aplica). Riesgo bajo de regresión; AC-13 lo verifica.
- **Conflicto con `bloquear-autoaprobacion`:** ambas tocan `sdd.py` (zonas distintas: `main()` frente a `validate`). Pruebas nuevas en archivo propio para no colisionar en `tests/test_sdd.py`.
- **Proceso:** el implementador edita `sdd.py` por Bash (el hook le niega `.microharness/` en herramientas de edición); `check` lo detecta igualmente por diff y alcance.

## Decisiones abiertas (recomendación; se adoptan salvo objeción)
- Q-01: ¿Proteger también `project.decisions`/`observations` (append-only) y `project.allowed_test_commands` (amplía la lista blanca)? Recomendación: no en esta tarea; candidata a tarea propia si se confirma el riesgo.
- Q-02: ¿Memoria base ilegible falla cerrado (REQ-02) o «no aplica»? Recomendación: falla cerrado.
- Q-03: Orden respecto a `bloquear-autoaprobacion`. Recomendación: implementar primero `bloquear-autoaprobacion` (prevención) y después esta (detección), o la que el humano apruebe antes.
