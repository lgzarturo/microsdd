# QUÉ: requisitos

## Objetivo
Que los sellos de pruebas y la huella de especificación aprobada de `.microharness/sdd.py` no cambien solo por convertir finales de línea LF↔CRLF (p. ej. checkout con `core.autocrlf=true`), y que `.microharness/python.sh` se extraiga siempre con LF para que `sh` de Linux lo ejecute.

## Hechos comprobados
- `hash_file()` (`sdd.py:100`) hace `sha256(path.read_bytes())`; lo usan `seal` (línea 325) y la verificación de `sealed_tests` en `validate` (línea 219, error «Test sellado modificado»).
- `spec_fingerprint()` (`sdd.py:104-112`) añade al digest los bytes crudos de `requerimientos.md`, `diseño.md` y `tareas.md`; `validate` lo compara con la huella aprobada (línea 227, error «Especificación alterada después de aprobación»). La parte de `spec.json` se hashea ya canonicalizada desde JSON y no depende de finales de línea.
- En esta máquina `core.autocrlf=true` y no existe `.gitattributes`. `git ls-files --eol` muestra `.microharness/sdd.py` como `i/lf w/crlf`: un checkout convierte LF→CRLF en el árbol de trabajo.
- `.microharness/python.sh` es el único `*.sh` rastreado; está `i/lf w/lf` en este checkout, pero sin atributo nada garantiza LF en otros checkouts Windows.
- Los hashes ya guardados en `.microharness/memory.json` se calcularon sobre contenido LF (dato aportado por el líder; no reverificado archivo a archivo).

## Precondiciones
- PRE-01: El programador autorizó expresamente que el implementador edite `.microharness/sdd.py` en esta tarea (solo `hash_file()` y `spec_fingerprint()`). Sigue requiriéndose la aprobación humana de esta especificación antes de implementar.
- PRE-02: `git` disponible en el PATH para la prueba de `.gitattributes`; si no, esa prueba se omite (`skipUnless`).

## Requisitos EARS
- REQ-01: WHEN una prueba sellada se reescribe con el mismo contenido pero con finales CRLF en lugar de LF, THE validador SHALL no reportar «Test sellado modificado» para ese archivo.
- REQ-02: IF el contenido de una prueba sellada cambia más allá de los finales de línea, THEN THE validador SHALL reportar «Test sellado modificado: <ruta>».
- REQ-03: WHEN los archivos `requerimientos.md`, `diseño.md` y `tareas.md` de una spec aprobada se convierten de LF a CRLF sin otro cambio, THE validador SHALL no reportar «Especificación alterada después de aprobación».
- REQ-04: IF el contenido de uno de esos archivos cambia más allá de los finales de línea tras la aprobación, THEN THE validador SHALL reportar «Especificación alterada después de aprobación».
- REQ-05: THE función `hash_file()` SHALL devolver, para un archivo sin `\r\n`, el mismo valor que `sha256` de sus bytes crudos (compatibilidad con hashes ya registrados).
- REQ-06: THE repositorio SHALL declarar en `.gitattributes` de la raíz que `*.sh` se trata como texto con `eol=lf`.

## Criterios de aceptación
- AC-01: En el fixture temporal de `tests/test_sdd.py`, tras aprobar la spec, sellar `tests/test_auth.py` escrito con LF y reescribirlo en binario con los mismos bytes sustituyendo `\n` por `\r\n`, `sdd.validate('fix-sesiones')` no contiene ningún error con «sellado».
- AC-02: En el mismo escenario, si después se cambia el contenido real del archivo (p. ej. `assert 2 == 2\r\n`), `sdd.validate('fix-sesiones')` contiene un error con «sellado».
- AC-03: En el fixture, tras `approve(..., 'spec', ...)`, reescribir en binario los tres `.md` de la spec convirtiendo `\n` en `\r\n` deja `sdd.validate('fix-sesiones')` sin errores con «alterada»; un cambio real posterior en `diseño.md` produce un error con «alterada».
- AC-04: Para un archivo con contenido LF (sin `\r\n`), `sdd.hash_file(p) == hashlib.sha256(p.read_bytes()).hexdigest()`.
- AC-05: Existe `.gitattributes` en la raíz del repositorio y `git check-attr eol -- .microharness/python.sh` (ejecutado en la raíz real del repo) termina con `eol: lf`; la prueba se omite si no hay `git`.
- AC-06: La suite completa (`python -m unittest discover -s tests -v`) pasa; las pruebas de AC-01 y AC-03 fallan antes de modificar `sdd.py` y la de AC-05 falla antes de crear `.gitattributes` (TDD).

## Fuera de alcance
- `code_fingerprint()` (huella del diff para la revisión; se calcula y comprueba en la misma sesión y árbol de trabajo).
- Normalizar `\r` aislado (finales tipo Mac clásico), BOM, espacios finales u otras diferencias de texto.
- Atributos de Git para otros tipos de archivo (`*.py`, `*.md`, `*.json`) y renormalizar el índice (`git add --renormalize`).
- Hook, `.claude/settings.json`, README, `docs/`, `.microharness/memory.json`, recalcular sellos o huellas existentes.
