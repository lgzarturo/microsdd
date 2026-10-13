# QUÉ: requisitos

## Objetivo
Hacer que `diff_files()` de `.microharness/sdd.py` devuelva las rutas modificadas y no rastreadas tal como existen en disco, también cuando contienen caracteres no ASCII (p. ej. `spec/<slug>/diseño.md`), para que la comprobación de alcance, `path_allowed` y `code_fingerprint` no fallen en falso.

## Hechos comprobados (por el líder y el autor)
- `diff_files()` ejecuta `git diff --name-only HEAD` y `git ls-files --others --exclude-standard` con `text=True` y sin `-c core.quotePath=false`.
- Con `core.quotePath=true` (valor por defecto de git) la ruta sale entrecomillada y escapada: `"spec/deteccion-python-multiplataforma/dise\303\261o.md"`. Como no empieza por `spec/`, `validate(scope=True)` reporta «Archivo modificado fuera de scope» para toda spec nueva (todas contienen `diseño.md`).
- Con `-c core.quotePath=false` git emite bytes UTF-8, pero `text=True` decodifica con la codificación local (cp1252 en Windows) y produce mojibake (`diseÃ±o.md`).
- Consecuencia actual: `python .microharness/sdd.py check <slug>` sin `--no-scope` falla en este repositorio por este defecto.

## Precondiciones
- PRE-01: El programador eligió esta tarea, separada de `deteccion-python-multiplataforma`, para corregir el defecto. Implica editar `.microharness/sdd.py`, archivo del arnés; esa edición requiere aprobación humana explícita al aprobar esta especificación.
- PRE-02: `git` disponible en el PATH para ejecutar la prueba nueva; si no lo está, la prueba se omite (`skipUnless`).

## Requisitos EARS
- REQ-01: WHEN el árbol de trabajo contiene un archivo modificado o no rastreado cuya ruta tiene caracteres no ASCII, THE función `diff_files()` SHALL devolver esa ruta literal (texto Unicode idéntico a la ruta relativa en disco, separada por `/`), sin comillas ni escapes octales y sin mojibake, con independencia de `core.quotePath` y de la codificación local.
- REQ-02: WHEN `validate(slug)` comprueba alcance y el único archivo no ASCII cambiado está bajo `spec/`, THE validador SHALL no reportar «Archivo modificado fuera de scope» por ese archivo.
- REQ-03: IF un archivo con ruta no ASCII cambiado queda fuera de `allowed_paths` y de las rutas exentas, THEN THE validador SHALL reportar «Archivo modificado fuera de scope: <ruta literal>».

## Criterios de aceptación
- AC-01: En un repositorio git temporal con `core.quotePath=true` configurado en el repo y sin commits, con `spec/fix-sesiones/diseño.md` sin rastrear, `sdd.diff_files()` contiene exactamente la cadena `'spec/fix-sesiones/diseño.md'`.
- AC-02: En ese mismo repositorio, `sdd.validate('fix-sesiones')` no contiene ningún error de alcance que mencione `diseño.md`.
- AC-03: Si además existe sin rastrear `fuera/configuración.txt` (fuera de `allowed_paths` `src/**`, `tests/**`), `sdd.validate('fix-sesiones')` contiene `'Archivo modificado fuera de scope: fuera/configuración.txt'`.
- AC-04: La suite completa (`python -m unittest discover -s tests -v`) pasa, y la prueba nueva falla antes del cambio en `diff_files()` (TDD).

## Fuera de alcance
- Cualquier cambio en la detección de Python o en la tarea `deteccion-python-multiplataforma`.
- Regex del hook, README, `docs/`, memoria del arnés, configuración.
- Otras funciones de `sdd.py` (incluida la llamada `git rev-parse` de `diff_files()`, cuya salida no se usa).
- Soporte de nombres de archivo con bytes no UTF-8.
