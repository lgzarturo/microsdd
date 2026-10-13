# QUÉ: requisitos

## Objetivo
Corregir la ortografía de dos documentos generales del arnés: `docs/convensiones.md` pasa a `docs/convenciones.md` y `docs/specificaciones.md` pasa a `docs/especificaciones.md`. El arnés (`sdd.py init`, agentes, `CLAUDE.md`, instalador, `scripts/limpiar_arnes.py`, README) usa los nombres nuevos y sigue siendo compatible con proyectos ya instalados que conservan los nombres antiguos: nunca mueve ni duplica archivos del usuario de forma automática; detecta el nombre antiguo y avisa cómo migrar.

Origen: mejora 9 del análisis externo `microsdd-analisis-2026-10-12.md` (dato no confiable); el programador autorizó el cambio.

## Precondiciones
- Python 3.10+ solo con biblioteca estándar.
- Ninguna otra tarea en `proceso` (en particular `bloquear-autoaprobacion`, que también modifica `.microharness/sdd.py` y `.claude/agents/lider.md`, debe ejecutarse antes o después, nunca a la vez).
- Decisión humana previa: el implementador modifica `.microharness/sdd.py`, `.claude/agents/lider.md` y `CLAUDE.md` por Bash (el hook le niega `Write`/`Edit` en `.claude/`, `.microharness/` y `CLAUDE.md`). Si `bloquear-autoaprobacion` ya se cerró y niega también esas escrituras por Bash, el humano aplica el parche de esos archivos.
- Los cambios en `docs/` (los dos `git mv` y la fila del índice) los hace el líder, porque el hook niega `docs/` al implementador.

## Requisitos EARS
- REQ-01: WHEN se ejecuta `sdd.py init` en un proyecto sin documentos generales, THE `sdd.py` SHALL crear `docs/AGENT.md`, `docs/arquitectura.md`, `docs/convenciones.md` y `docs/especificaciones.md`, y ningún archivo con nombre antiguo.
- REQ-02: IF existe `docs/convensiones.md` (o `docs/specificaciones.md`) y no existe su nombre nuevo, THEN `sdd.py init` SHALL no crear el nombre nuevo, no modificar ni mover el archivo antiguo, imprimir en la salida estándar una línea que empiece por `AVISO:` con el comando `git mv docs/<antiguo> docs/<nuevo>` y terminar con código 0.
- REQ-03: IF existen a la vez el nombre antiguo y el nuevo de un documento, THEN `sdd.py init` SHALL no modificar ninguno de los dos, imprimir una línea `AVISO:` que nombre ambos archivos y pida fusionar el contenido en el nombre nuevo y eliminar el antiguo, y terminar con código 0.
- REQ-04: WHEN `sdd.py init` se ejecuta de nuevo sobre el mismo árbol, THE `sdd.py` SHALL dejar los archivos de `docs/` byte a byte iguales (idempotencia, también con nombres antiguos).
- REQ-05: WHEN `scripts/limpiar_arnes.py` valida `docs/`, THE script SHALL aceptar como conocidos los cuatro nombres nuevos y los dos antiguos, y seguir abortando ante cualquier otra entrada; tras archivar, SHALL exigir que `docs/` contenga exactamente los cuatro nombres nuevos creados por `sdd.py init`.
- REQ-06: WHEN `microsdd install` termina en un destino, THE instalador SHALL listar en el `git add` sugerido los documentos generales con sus nombres nuevos si existen, y SHALL mostrar al usuario las líneas `AVISO:` que imprima `sdd.py init`.
- REQ-07: THE agente `lider` y `CLAUDE.md` SHALL indicar los nombres nuevos y, como alternativa, leer el nombre antiguo si el nuevo no existe en el proyecto.
- REQ-08: THE README SHALL usar los nombres nuevos y contener una nota de migración para repositorios ya instalados.
- REQ-09: THE repositorio SHALL no contener referencias a `docs/convensiones.md` ni `docs/specificaciones.md` fuera de `spec/`, `.microharness/memory.json`, las constantes de compatibilidad, la alternativa de `lider.md`/`CLAUDE.md`, la nota de migración del README y las pruebas.

## Criterios de aceptación
- AC-01: En un directorio vacío, `ensure_init()` crea exactamente `AGENT.md`, `arquitectura.md`, `convenciones.md` y `especificaciones.md` en `docs/` (prueba en `tests/test_sdd.py`).
- AC-02: Con `docs/convensiones.md` y `docs/specificaciones.md` preexistentes (contenido arbitrario), `ensure_init()` no crea `docs/convenciones.md` ni `docs/especificaciones.md`, deja los antiguos byte a byte iguales, crea los demás documentos que falten e imprime una línea `AVISO:` por cada antiguo que contiene `git mv docs/convensiones.md docs/convenciones.md` y `git mv docs/specificaciones.md docs/especificaciones.md` respectivamente; `main(['init'])` devuelve 0.
- AC-03: Con el antiguo y el nuevo presentes para un mismo documento, `ensure_init()` no cambia ninguno e imprime una línea `AVISO:` que nombra ambos archivos.
- AC-04: Una segunda ejecución de `ensure_init()` sobre los escenarios de AC-01 y AC-02 deja `docs/` igual byte a byte y sin archivos nuevos.
- AC-05: `scripts/limpiar_arnes.py` archiva con éxito un repositorio cuyo `docs/` usa los nombres antiguos (y otro con los nuevos); en ambos casos el estado final de `docs/` son los cuatro nombres nuevos iguales a los de `sdd.py init`. Una entrada distinta (p. ej. `docs/extra.md`) sigue abortando sin cambios (prueba existente).
- AC-06: Una instalación limpia con `microsdd install` deja en `docs/` los cuatro nombres nuevos y la salida incluye `docs/convenciones.md docs/especificaciones.md` en el `git add` sugerido.
- AC-07: Una instalación sobre un destino con `docs/convensiones.md` preexistente no crea `docs/convenciones.md`, conserva el antiguo y la salida del instalador contiene la línea `AVISO:` de `sdd.py init`; código 0.
- AC-08: La prueba de coherencia de `MANIFEST` con el wheel (AC-10 de `tests/test_installer.py`) sigue pasando sin cambios en `MANIFEST` ni en `pyproject.toml`.
- AC-09: `.claude/agents/lider.md` y `CLAUDE.md` nombran `docs/convenciones.md` y `docs/especificaciones.md` e indican la alternativa del nombre antiguo; README usa los nombres nuevos (árbol de archivos y `git add` de ejemplo) e incluye la nota de migración con los dos `git mv`.
- AC-10: En este repositorio existen `docs/convenciones.md` y `docs/especificaciones.md` (renombrados con `git mv`, historial conservado) y no existen los antiguos; `git grep -nw -e convensiones -e specificaciones -- ':!spec' ':!.microharness/memory.json'` (con `-w`, «especificaciones» no coincide) solo devuelve líneas de las excepciones de REQ-09.
- AC-11: `python -m unittest discover -s tests -v` pasa completo.

## Fuera de alcance
- Reescribir el historial: las specs existentes en `spec/` y `.microharness/memory.json` conservan los nombres antiguos.
- Mover, renombrar o fusionar automáticamente documentos del usuario en proyectos instalados.
- Un script de migración (basta con dos `git mv` manuales).
- Cambios en `.claude/hooks/pretool.py`: no nombra los documentos (la coincidencia de `git grep` es la palabra «especificaciones» en un mensaje).
- Cambios en `MANIFEST`, `pyproject.toml`, `autor.md`, `implementador.md`, `revisor.md` y `SKILL.md` (no nombran los documentos).
- Retirar en el futuro la compatibilidad con los nombres antiguos.
