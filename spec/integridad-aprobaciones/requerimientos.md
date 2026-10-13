# QUÉ: requisitos

## Objetivo
Detectar en `sdd.py check` (y en todo lo que llama a `validate`) la manipulación silenciosa del historial de aprobaciones de `.microharness/memory.json`: que, respecto a la memoria versionada en el último commit (`HEAD`), se borren o alteren entradas ya confirmadas, se cambie una aprobación, un sello o una revisión sin el evento que la operación legítima de `sdd.py` deja siempre, o se reabra o elimine una tarea cerrada. Es detección relativa al último commit, no prevención: quien controla Git puede reescribir `HEAD` o confirmar la manipulación.

Origen: mejora 4 y riesgo R3 de un análisis externo (dato no confiable; los hechos se comprobaron en el código).

## Hechos comprobados (código en `HEAD` 64e4733)
- `memory.json` guarda por tarea `approvals.spec`, `approvals.close`, `sealed_tests`, `review`, `review_fingerprint`, `iterations` y `events`. No existe la clave `reviews`: la revisión vigente está en `review`/`review_fingerprint` y el historial en eventos `revisión`.
- `approve spec` **sobrescribe** `approvals.spec` (con `fingerprint`), pone `approvals.close`, `review` y `review_fingerprint` a `null`, `iterations` a 0 y añade el evento `aprobación_spec`. Rechaza tareas `terminado`.
- `approve close` escribe `approvals.close`, añade `aprobación_close` y pasa la tarea a `terminado`. Solo desde `proceso`.
- `review` incrementa `iterations`, sobrescribe `review` y `review_fingerprint` y añade `revisión` (y `escalado` si agota intentos).
- `seal` **sobrescribe** `sealed_tests` completo y añade `sellado_tests`.
- `events` solo crece por las operaciones de `sdd.py`; ninguna operación borra ni modifica eventos existentes.
- `validate` no compara la memoria con Git; `.microharness/` está exento del control de alcance, por lo que hoy una edición directa de `memory.json` no la detecta nada.
- `approve spec` (con `validate(scope=False)`) y `approve close` (con `validate(run=True)`) usan `validate`; `review` y `seal` no.
- `scripts/limpiar_arnes.py` exige todas las tareas `terminado` y árbol limpio, archiva memoria y `spec/<slug>/` en `historial/<versión>/`, borra los `spec/<slug>/` y reinicia la memoria con `tasks: {}`; el humano confirma después.
- `scripts/migrar_plan_md.py` reescribió huellas de tareas ya confirmadas; ese cambio está en el historial confirmado.
- Con la memoria y el `HEAD` actuales, las 21 tareas con `approvals.close` en `HEAD` tienen `spec.json` en `terminado` y entrada idéntica en la memoria de trabajo (simulación de solo lectura del autor).

## Precondiciones
- Python 3.10+ solo con biblioteca estándar; `git` disponible para las pruebas (se omiten con `skipUnless` si falta).
- `ROOT` es la raíz del repositorio Git (invariante ya documentado en `docs/arquitectura.md`).
- La tarea `bloquear-autoaprobacion` (pendiente) también modifica `.microharness/sdd.py`: el líder decide el orden; la segunda en implementarse rebasa sobre la primera.

## Definiciones
- **Memoria base:** contenido de `HEAD:.microharness/memory.json` (ruta relativa de `MEMORY` respecto de `ROOT`).
- **Tarea cerrada en base:** tarea de la memoria base con `approvals.close` distinto de `null`.
- **Eventos nuevos:** los elementos de `events` de la memoria de trabajo posteriores a los N primeros, siendo N la longitud de `events` en la base.
- **Error de integridad:** mensaje que empieza por `Integridad de memoria: <slug>:` y nombra el campo afectado.

## Requisitos EARS
- REQ-01: IF no hay repositorio Git, no hay commits o `HEAD` no contiene `.microharness/memory.json`, THEN `validate` SHALL omitir la comprobación de integridad sin añadir errores.
- REQ-02: IF la memoria base no es JSON válido o su `tasks` no es un objeto, THEN `validate` SHALL añadir un error de integridad `memoria versionada en HEAD ilegible` (falla cerrado).
- REQ-03: WHEN `validate` se ejecuta con memoria base, THE sistema SHALL comparar todas las tareas de la base, no solo el slug comprobado, y lo hará con el control de alcance activado o desactivado (`--no-scope`).
- REQ-04: WHEN una tarea abierta en base existe en la memoria de trabajo, THE sistema SHALL exigir que los `events` de la base sean prefijo exacto de los de trabajo; IF se borró, alteró o reordenó alguno, THEN SHALL añadir un error de integridad sobre `events`.
- REQ-05: WHEN en una tarea abierta en base cambia uno de los campos vigilados respecto a la base, THE sistema SHALL exigir entre los eventos nuevos uno de los tipos que lo justifican; IF falta, THEN SHALL añadir un error de integridad que nombra el campo. Tabla: `approvals.spec` ← `aprobación_spec`; `approvals.close` ← `aprobación_close` o `aprobación_spec`; `sealed_tests` ← `sellado_tests`; `review`, `review_fingerprint`, `iterations` ← `revisión` o `aprobación_spec`.
- REQ-06: IF una tarea cerrada en base tiene en la memoria de trabajo una entrada distinta (incluido añadir eventos), THEN THE sistema SHALL añadir un error de integridad `tarea cerrada modificada`.
- REQ-07: IF una tarea cerrada en base tiene `spec/<slug>/spec.json` en la memoria de trabajo con `state` distinto de `terminado`, THEN THE sistema SHALL añadir un error de integridad `tarea cerrada reabierta`.
- REQ-08: IF una tarea de la base falta en la memoria de trabajo y su directorio `spec/<slug>/` existe, THEN THE sistema SHALL añadir un error de integridad `tarea eliminada de la memoria`; WHILE `spec/<slug>/` tampoco existe (limpieza de release), THE sistema SHALL no añadir error.
- REQ-09: WHEN una tarea existe en la memoria de trabajo pero no en la base, o cambian datos fuera de `tasks` (p. ej. `project`), THE sistema SHALL no compararlos.
- REQ-10: IF hay errores de integridad, THEN `approve spec` y `approve close` SHALL fallar sin escribir memoria ni `spec.json`, y `check --run` SHALL no ejecutar los comandos de prueba.
- REQ-11: WHEN se ejecuta `validate`, THE sistema SHALL leer la memoria base con una sola invocación de `git`.

## Criterios de aceptación
- AC-01: En un directorio temporal sin `git init`, en un repo sin commits y en un repo cuyo `HEAD` no incluye `memory.json`, `validate('fix-sesiones')` no devuelve ningún error que empiece por `Integridad de memoria`. (REQ-01)
- AC-02: Con `memory.json` confirmado como texto no JSON, o con `tasks` como lista, `validate` devuelve un error que contiene `Integridad de memoria` y `HEAD ilegible`. (REQ-02)
- AC-03: Con la memoria confirmada, borrar el evento `creada` de una tarea abierta, modificar su `at` o insertar un evento antes del último confirmado produce un error de integridad que contiene el slug y `events`; añadir al final un evento cualquiera no produce error de integridad sobre `events`. (REQ-04)
- AC-04: Para cada campo vigilado de REQ-05 (`approvals.spec`, `approvals.close`, `sealed_tests`, `review`, `review_fingerprint`, `iterations`), cambiarlo directamente en la memoria de trabajo sin añadir eventos produce un error de integridad que contiene el slug y el nombre del campo; añadir además un evento de un tipo justificante de la tabla elimina ese error; añadir un evento de tipo no justificante (p. ej. `sellado_tests` para `review`) no lo elimina. (REQ-05)
- AC-05: Partiendo de memoria confirmada, ejecutar las operaciones reales `approve spec`, reaprobación `approve spec` tras cambiar la spec, `seal`, `review RECHAZADO`, `review APROBADO` y `approve close` (sin confirmar entre ellas) deja `validate` sin errores de integridad tras cada paso. (REQ-05, sin falsos positivos)
- AC-06: Con una tarea cerrada confirmada: añadir un evento, cambiar `approvals.close.evidence` o poner `approvals.close` a `null` produce `tarea cerrada modificada`; cambiar su `spec.json` a `proceso` produce `tarea cerrada reabierta`; sin cambios no hay error. (REQ-06, REQ-07)
- AC-07: Eliminar de la memoria de trabajo una tarea confirmada conservando `spec/<slug>/` produce `tarea eliminada de la memoria`; simular la limpieza de release (reiniciar `tasks` a `{}`, borrar `spec/<slug>/` de las tareas confirmadas y crear otra con `new`) no produce errores de integridad al validar la nueva. (REQ-08)
- AC-08: Una tarea creada después del último commit puede cambiar cualquier campo sin errores de integridad, y modificar `project.observations` no produce errores de integridad. (REQ-09)
- AC-09: Con un error de integridad en una tarea distinta del slug comprobado, `validate(slug)` y `validate(slug, scope=False)` lo reportan, y `main()` con `check <slug> --no-scope` sale con código 1 y escribe `ERROR: Integridad de memoria` en stderr. (REQ-03)
- AC-10: Con un error de integridad, `approve <slug> spec` lanza `ValueError` y `memory.json` y `spec.json` quedan byte a byte iguales; `validate(slug, run=True)` no ejecuta los comandos (no imprime `EJECUTANDO:`). (REQ-10)
- AC-11: Contando las llamadas a `git` con un doble de prueba, un `validate` con memoria base hace exactamente una invocación cuyo argumento contiene `HEAD:.microharness/memory.json`. (REQ-11)
- AC-12: `README.md` documenta en la tabla de controles y en limitaciones: qué compara la comprobación (base `HEAD`), qué no aplica, cómo recuperar (`git restore --source=HEAD -- .microharness/memory.json` o confirmar tras revisar el diff), que detecta y no impide, y que quien confirma fija la nueva base. Comprobación por lectura del revisor.
- AC-13: La suite completa `python -m unittest discover -s tests -v` pasa sin modificar pruebas existentes, y `check integridad-aprobaciones --no-scope` sobre este repositorio no reporta errores de integridad.

## Fuera de alcance
- Trailer `Approved-by:`, firmas GPG/SSH o cualquier verificación de autoría de commits (ver `plan.md`, decisión D-02).
- Impedir la edición de `memory.json` o la ejecución de `approve`/`seal` por agentes (tarea `bloquear-autoaprobacion`).
- Detectar eventos fabricados que se añaden al final junto con el cambio que justifican, o comprobar coherencia de contenido entre evento y campo (fechas, autor, huella).
- Proteger `project` (`observations`, `decisions`, `allowed_test_commands`) y tareas nuevas no confirmadas.
- Comparar contra commits anteriores a `HEAD`, contra la rama remota o contra el índice.
- Cambios en `scripts/limpiar_arnes.py`, `scripts/migrar_plan_md.py`, hook, agentes o instalador.
