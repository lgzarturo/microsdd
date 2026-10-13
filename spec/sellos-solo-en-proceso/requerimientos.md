# QUÉ: requisitos

## Objetivo
Que `validate()` compare `sealed_tests` solo mientras la tarea no esté `terminado`, para que el `check` de tareas cerradas no falle cuando una tarea posterior modifica, dentro de su alcance aprobado, un archivo de pruebas compartido que la tarea cerrada selló.

## Hechos comprobados
- `validate()` en `.microharness/sdd.py` recorre `task_memory['sealed_tests']` y reporta «Test sellado modificado: ...» sin consultar `spec.json.state`.
- `check deteccion-python-multiplataforma --no-scope` (tarea `terminado`) devuelve hoy `ERROR: Test sellado modificado: tests/test_sdd.py` y código 1, porque `eol-hashes-estables` añadió pruebas a ese archivo.
- `approve(..., 'close')` exige `state == 'proceso'` y ejecuta `validate(slug, run=True)` antes de pasar a `terminado`; el sello se verifica, por tanto, en la puerta de cierre.
- `review` puede devolver la tarea a `pendiente` al agotar `max_iterations` (escalado), conservando `sealed_tests` en memoria.

## Precondiciones
- PRE-01: la tarea edita `.microharness/sdd.py`, archivo del arnés. El programador debe autorizarlo explícitamente al aprobar esta spec; la edición se limita al bloque de `sealed_tests` dentro de `validate`.

## Requisitos EARS
- REQ-01: WHILE la tarea esté en estado `terminado`, THE `validate` SHALL NOT comparar `sealed_tests` con el contenido actual ni reportar «Test sellado modificado».
- REQ-02: WHILE la tarea esté en estado `proceso`, THE `validate` SHALL reportar «Test sellado modificado» IF el hash de un archivo sellado difiere o el archivo no existe.
- REQ-03: WHILE la tarea esté en estado `pendiente`, THE `validate` SHALL reportar «Test sellado modificado» IF el hash de un archivo sellado difiere o el archivo no existe.
- REQ-04: THE `validate` SHALL mantener sin cambios el resto de comprobaciones (aprobaciones, huella de spec, alcance, ejecución) y SHALL NOT modificar ni borrar `sealed_tests` en memoria.
- REQ-05: THE README (sección 6, «Mutation testing y hashing de pruebas») SHALL indicar que `check` compara los sellos hasta el cierre y que, en tareas `terminado`, el sello queda como registro histórico.

## Criterios de aceptación
- AC-01: dada una tarea que se aprueba, sella `tests/test_auth.py`, recibe revisión `APROBADO` y se cierra (`terminado`), WHEN después se modifica el archivo sellado, THEN `validate(slug)` no contiene ningún error con «sellado».
- AC-02: dada una tarea en `proceso` con sello y archivo modificado, `validate(slug)` contiene un error con «sellado» (prueba existente `test_sealed_tests_detect_changes` sigue pasando sin cambios).
- AC-03: dada una tarea sellada que pasa a `pendiente` tras `max_iterations` revisiones `RECHAZADO`, WHEN se modifica el archivo sellado, THEN `validate(slug)` contiene un error con «sellado».
- AC-04: en AC-01, `sealed_tests` de la tarea en memoria conserva exactamente el hash registrado por `seal` (no se borra ni se reescribe).
- AC-05: la suite completa `python -m unittest discover -s tests -v` pasa, y `check deteccion-python-multiplataforma --no-scope` deja de reportar «Test sellado modificado».
- AC-06: README sección 6 contiene una frase que indica que el sello se compara hasta el cierre y que en tareas `terminado` queda como registro histórico.

## Fuera de alcance
- Hook, `settings.json`, `docs/**`, `.microharness/memory.json` y `python.sh`.
- Resellar, borrar o editar sellos ya registrados en memoria (incluido el de `deteccion-python-multiplataforma`).
- Cambiar `seal`, `approve`, `review` o cualquier otra comprobación de `validate`.
- Sellos por tarea en archivos compartidos con otra granularidad (por prueba, por función).
- Sellar `protected_tests` en esta tarea.
