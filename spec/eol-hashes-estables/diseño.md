# CÓMO: diseño mínimo

## Situación comprobada
- `hash_file(path)` = `sha256(path.read_bytes())`. Usos: `seal()` (registra en `sealed_tests`) y `validate()` (compara). No hay otros usos.
- `spec_fingerprint(path, spec)` = sha256 de `spec.json` canonicalizado sin `state` + por cada `.md` `nombre\x00` + bytes crudos. Usos: `approve()` (registra) y `validate()` (compara).
- `code_fingerprint()` hashea bytes crudos de los archivos del diff; se registra en `review()` y se compara en `approve('close')` dentro de la misma sesión y árbol, por lo que la conversión de checkout no le afecta en el flujo normal.
- Sin `.gitattributes`; `core.autocrlf=true` en esta máquina; `python.sh` es el único `*.sh` rastreado y está LF en el índice.

## Decisión y justificación
Decisión registrada por el programador (no se reabre):
1. `.gitattributes` nuevo en la raíz con una única línea: `*.sh text eol=lf`. Fuerza LF en el árbol de trabajo para `python.sh` sin tocar el resto de archivos.
2. En `sdd.py`, normalizar `\r\n` → `\n` sobre los bytes antes de hashear, en los dos puntos:
   - `hash_file`: `hashlib.sha256(path.read_bytes().replace(b'\r\n', b'\n')).hexdigest()`.
   - `spec_fingerprint`: `digest.update((path / name).read_bytes().replace(b'\r\n', b'\n'))`.
   Sin función auxiliar nueva: son dos expresiones de una línea (YAGNI). `code_fingerprint()` no cambia.

Compatibilidad: para contenido sin `\r\n`, `replace` es la identidad, así que los hashes y huellas ya registrados sobre LF siguen coincidiendo y no hace falta migración ni nuevo sello.

README: no se propone cambio; la línea de `.gitattributes` se explica sola y el README queda fuera de alcance.

## Alternativas descartadas
- Solo `.gitattributes` con `* text=auto eol=lf`: cambia el comportamiento de todo el repo, exige `--renormalize` y no protege copias sin Git (zip, editores que guardan CRLF).
- Solo normalizar en `sdd.py`: no arregla `python.sh` en `sh` de Linux.
- Leer en modo texto (`read_text` / newline universal): también convertiría `\r` aislado y depende de decodificar; cambia hashes de archivos no UTF-8.
- Recalcular sellos existentes: innecesario por la compatibilidad anterior.

## Invariantes y riesgos
- Invariante: para archivos sin `\r\n`, `hash_file` y `spec_fingerprint` devuelven exactamente lo mismo que antes.
- Invariante: cualquier cambio de contenido distinto de `\r\n`↔`\n` sigue alterando el hash.
- Riesgo aceptado: un cambio que solo añade o quita `\r` antes de `\n` en una prueba sellada deja de detectarse; no altera la semántica de código Python ni de Markdown.
- Riesgo aceptado: un archivo sellado binario con la secuencia `\r\n` quedaría normalizado; las pruebas selladas son texto.
- Riesgo: `.gitattributes` no reescribe checkouts existentes; un `python.sh` ya extraído con CRLF requiere volver a extraerlo. Hoy está LF en este árbol.
- Efecto secundario: `git check-attr` lee el `.gitattributes` del árbol de trabajo, por lo que la prueba AC-05 pasa antes del commit.
- Prueba AC-05: debe resolver la raíz real del repo desde `Path(__file__)`, no `sdd.ROOT`, que el `setUp` de `MicroSDDTests` redirige a un temporal; conviene ubicarla fuera de esa clase o usar la ruta del archivo de pruebas.
