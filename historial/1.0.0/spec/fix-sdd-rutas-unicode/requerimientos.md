# QUÉ: requisitos

## Objetivo
Corregir `diff_files()` en `.microharness/sdd.py` para que devuelva las rutas de archivos modificados y sin seguimiento como cadenas Unicode exactas (incluidos nombres no ASCII y con espacios), de modo que el chequeo de alcance de `validate()` y el sello `code_fingerprint()` funcionen con archivos como `spec/<slug>/diseño.md`.

## Precondiciones
- Git disponible en el `PATH` (comprobado: git 2.55.0.windows.5).
- Python >= 3.10 (comprobado: Python 3.12.3).
- Excepción autorizada por el programador 2026-10-12: solo para esta tarea, el implementador puede editar `.microharness/sdd.py`, aunque la regla del hook normalmente lo prohíbe. La excepción no se extiende a otras tareas ni a otros archivos de `.microharness/`.

## Hechos comprobados (defecto)
- `diff_files()` ejecuta `git diff --name-only HEAD` y `git ls-files --others --exclude-standard` con `text=True` y separa por líneas.
- Con `core.quotePath` por defecto, git entrega las rutas no ASCII entrecomilladas y en octal (`"spec/instalador-uvx/dise\303\261o.md"`); al no empezar por `spec/`, `validate()` las reporta como "Archivo modificado fuera de scope". Como `sdd.py new` siempre crea `diseño.md`, toda tarea sin commitear falla el chequeo de alcance (reproducido con `check instalador-uvx`).
- Aun con `core.quotePath=false`, `text=True` decodifica con la codificación del locale (cp1252 en Windows) y produce mojibake (`dise\xc3\xb1o.md`); `Path(...).is_file()` es False y `code_fingerprint()` sellaría `<deleted>` en lugar del contenido.

## Requisitos EARS
- REQ-01: WHEN existan en el repositorio archivos rastreados modificados o archivos sin seguimiento no ignorados, THE `diff_files()` SHALL devolver cada ruta exactamente como cadena Unicode relativa a la raíz, sin comillas ni escapes, independientemente de `core.quotePath` y de la codificación del locale.
- REQ-02: WHEN una ruta contenga espacios o caracteres no ASCII, THE `diff_files()` SHALL devolverla íntegra, de forma que `ROOT / ruta` apunte al archivo existente.
- REQ-03: WHILE una tarea esté sin commitear, THE `validate(slug)` con alcance SHALL omitir `spec/<slug>/diseño.md` del reporte "Archivo modificado fuera de scope".
- REQ-04: WHEN cambie el contenido de un archivo permitido por el alcance cuyo nombre no sea ASCII, THE `code_fingerprint()` SHALL producir un sello distinto.
- REQ-05: IF un comando git devuelve código distinto de cero, THEN THE `diff_files()` SHALL ignorar su salida, como hace hoy.

## Criterios de aceptación
- AC-01: en un repositorio Git temporal con un commit inicial, un archivo sin seguimiento `spec/x/diseño.md` y un archivo rastreado con nombre no ASCII modificado tras el commit, `diff_files()` devuelve exactamente esas rutas como `str` Unicode correctas (sin comillas ni secuencias octales) y `(ROOT / ruta).is_file()` es True para cada una.
- AC-02: en un repositorio Git temporal con commit inicial y la tarea `spec/<slug>/` sin commitear, `validate(slug)` con alcance no contiene ningún error "Archivo modificado fuera de scope" que mencione `spec/<slug>/diseño.md`.
- AC-03: con un archivo permitido por el alcance cuyo nombre no es ASCII y está modificado o sin seguimiento, `code_fingerprint(patrones)` cambia al modificar su contenido (demuestra que se lee el archivo y no `<deleted>`).
- AC-04: un archivo sin seguimiento cuya ruta contiene espacios (por ejemplo `src/con espacio.py`) aparece en `diff_files()` con la ruta exacta y existe en disco.
- AC-05: todas las pruebas existentes de `tests/test_sdd.py` siguen en verde con `python -m unittest discover -s tests -v`.

## Fuera de alcance
- El hook `pretool.py` y su comportamiento en Windows.
- Otros comandos o funciones de `sdd.py` (detección de repositorio, `validate`, `code_fingerprint`, `normalized_rel`, `path_allowed`, etc.).
- Cambiar la configuración git del repositorio o global (`core.quotePath`).
- Normalización Unicode NFC/NFD (por ejemplo, macOS).
- La tarea `instalador-uvx` (permanece en pendiente) y el README.
- Documentación general (`docs/**`), `CLAUDE.md`, configuración del arnés.
