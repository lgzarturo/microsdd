# QUÉ: requisitos

## Objetivo
Proveer un script de mantenimiento, `scripts/limpiar_arnes.py`, que al preparar un release del arnés MicroSDD archive en `historial/<versión>/` los datos que el propio arnés generó durante su desarrollo (`.microharness/memory.json`, `docs/` y las tareas de `spec/`) y deje esos tres destinos en el estado inicial que produce `python .microharness/sdd.py init`. Así, quien instale una versión del arnés no hereda historial ajeno a su proyecto.

## Decisiones humanas que acota esta spec
Registradas en `.microharness/memory.json` (`project.decisions`, 2026-10-13T00:10:36Z):
- D1: el historial se archiva en `historial/<versión>/` en la raíz del repositorio.
- D2: el estado inicial es exactamente el que genera `sdd.py init`; la herramienta no fija plantillas propias.
- D3: si hay alguna tarea que no está en `terminado`, se aborta sin cambios y se listan las tareas abiertas.
- D4: script de mantenimiento en `scripts/`, solo biblioteca estándar, no distribuido por el instalador; no modifica `.microharness/sdd.py` ni `src/microsdd/`.

El comportamiento detallado que sigue (CLI, precondiciones, orden, códigos de salida) es una **propuesta del líder pendiente de aprobación humana**.

## Precondiciones
- Python >= 3.10 disponible como `python` (en la máquina del mantenedor `python3` es el stub de Microsoft Store).
- Git disponible en el PATH.
- La herramienta se ejecuta sobre un repositorio del arnés cuya raíz contiene `.microharness/sdd.py` con el subcomando `init`.
- Para ejecutarla de verdad (no en pruebas), todas las tareas deben estar cerradas y el árbol de trabajo limpio; esto lo comprueba la propia herramienta.

## Glosario
- **Raíz**: directorio padre de `scripts/` (inyectable en pruebas).
- **Tareas**: unión de las claves de `memory.json.tasks` y de los subdirectorios de `spec/`.
- **Tarea terminada**: existe `spec/<slug>/spec.json`, es JSON válido y su campo `state` vale `terminado`. Cualquier otra situación (estado `pendiente` o `proceso`, spec.json ausente o ilegible, entrada de memoria sin directorio) cuenta como abierta.
- **Sin cambios**: el contenido de todos los archivos del árbol de trabajo (excluido `.git/`), el índice y `HEAD` quedan idénticos a antes de la ejecución.

## Requisitos EARS
- REQ-01: WHEN se ejecuta `python scripts/limpiar_arnes.py <versión>` y se cumplen todas las precondiciones, THE herramienta SHALL copiar byte a byte `.microharness/memory.json` a `historial/<versión>/memory.json`, cada documento de `docs/` a `historial/<versión>/docs/` y cada entrada de `spec/` salvo `.gitkeep` a `historial/<versión>/spec/`.
- REQ-02: WHEN la copia al historial se ha verificado byte a byte, THE herramienta SHALL eliminar los originales archivados, ejecutar `<sys.executable> <raíz>/.microharness/sdd.py init`, asegurar que existe `spec/.gitkeep` y terminar con código 0.
- REQ-03: WHEN la limpieza termina con éxito, THE herramienta SHALL imprimir los próximos pasos: un `git add --` con la lista explícita de rutas afectadas (nunca `git add .`) y el mensaje sugerido `chore(release): archiva historial <versión>`; THE herramienta SHALL NOT crear commits, tags ni hacer push.
- REQ-04: THE herramienta SHALL NOT modificar ningún archivo fuera de `historial/<versión>/`, `docs/`, `spec/` y `.microharness/memory.json`.
- REQ-05: WHEN se pasa `--dry-run` y se cumplen las precondiciones, THE herramienta SHALL imprimir el plan (rutas a archivar y a eliminar) y terminar con código 0 sin escribir nada.
- REQ-06: IF existe al menos una tarea abierta, THEN THE herramienta SHALL terminar con código 1, listar los slugs abiertos con su motivo en español y no hacer cambios.
- REQ-07: IF `git status --porcelain` no está vacío (cambios rastreados o archivos no rastreados no ignorados), o la raíz no es un repositorio git, o `git rev-parse --show-toplevel` no resuelve exactamente a la raíz (raíz dentro de otro repositorio), o `git` no puede ejecutarse (`OSError`), THEN THE herramienta SHALL terminar con código 1 y un mensaje en español, sin traza y sin cambios.
- REQ-07b: IF existe algún archivo ignorado por git bajo `docs/`, `spec/` o en `.microharness/memory.json` (`git status --porcelain --ignored -- docs spec .microharness/memory.json` no vacío), THEN THE herramienta SHALL terminar con código 1, listar esas rutas y no hacer cambios, porque git no podría recuperarlas ni se versionarían en el historial.
- REQ-07c: IF alguna ruta del plan es un enlace simbólico (`.microharness/memory.json`, `docs/`, `spec/`, cualquier entrada bajo ellos, `historial`), THEN THE herramienta SHALL terminar con código 1 y no hacer cambios.
- REQ-08: IF `historial/<versión>/` ya existe, o `historial` existe y no es un directorio, THEN THE herramienta SHALL terminar con código 1 sin cambios.
- REQ-09: IF la versión no cumple la expresión SemVer estricta (núcleo `MAYOR.MENOR.PARCHE` sin ceros a la izquierda y prerelease opcional `-[0-9A-Za-z-]+(.[0-9A-Za-z-]+)*`, sin metadatos de build), THEN THE herramienta SHALL terminar con código 1 sin cambios (el código 2 queda reservado al uso inválido de argparse, REQ-13).
- REQ-10: IF `docs/` contiene alguna entrada distinta de los cuatro documentos del arnés (`AGENT.md`, `arquitectura.md`, `convensiones.md`, `specificaciones.md`), THEN THE herramienta SHALL terminar con código 1, listar las entradas desconocidas y no hacer cambios.
- REQ-11: IF falta `<raíz>/.microharness/sdd.py`, o `.microharness/memory.json` no existe, no es JSON válido o su campo `tasks` no es un objeto, THEN THE herramienta SHALL terminar con código 1 sin cambios.
- REQ-12: IF ocurre un fallo después de empezar a escribir (copia, verificación, borrado o `init`), THEN THE herramienta SHALL terminar con código 1 e imprimir la remediación con git (restaurar `docs`, `spec` y `.microharness/memory.json` desde `HEAD` y eliminar `historial/<versión>/`).
- REQ-13: WHEN los argumentos de línea de comandos son inválidos (falta la versión, opción desconocida), THE herramienta SHALL terminar con código 2 (argparse) sin cambios.

## Criterios de aceptación
Todas las pruebas se ejecutan en repositorios git temporales con una copia del `.microharness/sdd.py` real y datos ficticios; ninguna ejecuta la herramienta sobre el repositorio real.

- AC-01: Entrada: repo temporal limpio con `memory.json` ficticio, los 4 docs con contenido propio, `spec/.gitkeep` y dos tareas `terminado` (con un archivo de nombre no ASCII, p. ej. `diseño.md`). Acción: `main(['1.2.0'], root=tmp)`. Salida: código 0; cada archivo de `historial/1.2.0/` (memory.json, docs/*, spec/<slug>/*) es byte a byte igual al original previo; `historial/1.2.0/spec/.gitkeep` no existe.
- AC-02: En el mismo escenario de AC-01, tras la ejecución: los 4 docs y `.microharness/memory.json` son byte a byte iguales a los que produce `sdd.py init` en un directorio vacío con la misma copia de `sdd.py`; `docs/` contiene solo esos 4 archivos; `spec/` contiene solo `.gitkeep`.
- AC-03: En el mismo escenario de AC-01: todo archivo fuera de `historial/1.2.0/`, `docs/`, `spec/` y `.microharness/memory.json` queda idéntico (snapshot); `HEAD` no cambia y el índice no tiene cambios preparados; la salida estándar contiene `git add --` con las rutas `historial/1.2.0`, `docs`, `spec` y `.microharness/memory.json`, no contiene `git add .` y contiene `chore(release): archiva historial 1.2.0`.
- AC-04: Entrada: el escenario de AC-01. Acción: `main(['1.2.0', '--dry-run'], root=tmp)`. Salida: código 0; snapshot del árbol, `HEAD` e índice sin cambios; `historial/` no existe; la salida menciona `historial/1.2.0`.
- AC-05: Entrada: repo limpio con una tarea en `pendiente`, otra en `proceso`, una clave en `memory.json.tasks` sin directorio en `spec/` y un directorio de `spec/` sin `spec.json` (casos probados por separado o combinados). Acción: `main(['1.2.0'], root=tmp)`. Salida: código 1; el mensaje lista cada slug abierto; sin cambios.
- AC-06: Entrada: escenario de AC-01 con (a) un archivo rastreado modificado sin commit, (b) un archivo no rastreado no ignorado, (c) un directorio temporal que no es repositorio git y (d) el escenario de AC-01 construido en un subdirectorio de otro repositorio git temporal (sin `git init` propio). Acción: `main(['1.2.0'], root=tmp)` (en (d), `root` es el subdirectorio). Salida: código 1 y sin cambios en cada caso.
- AC-07: Entrada: escenario de AC-01 con (a)-(c) `historial/1.2.0/` ya versionado (con un archivo) y (d) `historial` como archivo versionado. Acción: `main(['1.2.0'], root=tmp)`. Salida: código 1; sin cambios en cada caso.
- AC-08: Entrada: escenario de AC-01. Acción: `main([v], root=tmp)` con `v` en `../x`, `1.0`, `01.2.0`, `1.2.0/../x`, `1.2.0+build`, `1.2.0\n`. Salida: código 1 exactamente y sin cambios. Con `1.2.0-rc.1` el flujo feliz termina con código 0 y crea `historial/1.2.0-rc.1/`.
- AC-09: Entrada: escenario de AC-01 con un quinto archivo versionado `docs/extra.md`. Acción: `main(['1.2.0'], root=tmp)`. Salida: código 1; el mensaje menciona `extra.md`; sin cambios.
- AC-10: Entrada: escenario de AC-01 con (a) `.microharness/memory.json` eliminado y commit, (b) `memory.json` con JSON inválido versionado, (c) sin `.microharness/sdd.py` y (d) `memory.json` con `"tasks": []` versionado. Acción: `main(['1.2.0'], root=tmp)`. Salida: código 1 y sin cambios en cada caso.
- AC-11: Entrada: argumentos `[]` y `['1.2.0', '--desconocida']`. Acción: `main(argv, root=tmp)`. Salida: código 2 (`SystemExit(2)` de argparse) y sin cambios.
- AC-12: Entrada: escenario de AC-01 donde la copia de `.microharness/sdd.py` se sustituye **antes del commit inicial** por un script que, con `init`, termina con código 1 (el árbol queda limpio). Acción: `main(['1.2.0'], root=tmp)`. Salida: código 1; existe `historial/1.2.0/`; la salida de error contiene una remediación con `git restore` y la ruta `historial/1.2.0`.
- AC-13: `python -m unittest discover -s tests -v` termina en verde, incluidas las pruebas existentes de `tests/test_sdd.py` sin modificarlas; ni el script ni las pruebas invocan `python3` (usan `sys.executable`).
- AC-14: Entrada: escenario de AC-01 con un `.gitignore` versionado que ignora `.coverage` y un archivo `spec/<slug>/.coverage` creado tras el commit (el árbol aparece limpio en `git status --porcelain`). Acción: `main(['1.2.0'], root=tmp)`. Salida: código 1; el mensaje menciona la ruta ignorada; sin cambios.
- AC-15: Entrada: escenario de AC-01 con un enlace simbólico `spec/<slug>/enlace` versionado que apunta a un archivo fuera de `spec/`. Acción: `main(['1.2.0'], root=tmp)`. Salida: código 1; sin cambios. La prueba se omite (`skipTest`) si la plataforma no permite crear enlaces simbólicos (p. ej. Windows sin modo desarrollador).

## Fuera de alcance
- Crear tags, commits, push o publicar el paquete.
- Modificar `README.md` (el uso se documenta en el docstring y en `--help`; el README lo actualizará otra tarea), `.microharness/sdd.py`, `ensure_init`, `.claude/`, `src/microsdd/` o `pyproject.toml`.
- Enriquecer las plantillas de docs o de memoria.
- Integrar la herramienta en el paquete o en el manifiesto del instalador `uvx`.
- Limpiar o reescribir el historial de git.
- Rollback automático propio ante fallos parciales (la recuperación se hace con git sobre un árbol que estaba limpio y sin archivos ignorados en las rutas archivadas, REQ-07 y REQ-07b).
- Verificar la aprobación humana de cierre registrada en memoria: el criterio de tarea terminada es solo `state == "terminado"` (D3).
