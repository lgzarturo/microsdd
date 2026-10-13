# PASOS: trabajo verificable

- [ ] T01 (AC-01, AC-02): En `tests/test_sdd.py` (clase `MicroSDDTests`), añadir prueba que apruebe la spec, proteja y selle `tests/test_auth.py` escrito con LF, lo reescriba con `write_bytes` sustituyendo `\n` por `\r\n` y verifique que `validate` no tiene errores con «sellado»; luego cambiar el contenido real y verificar que sí aparece.
- [ ] T02 (AC-03): En `tests/test_sdd.py`, añadir prueba que apruebe la spec, convierta con `write_bytes` los tres `.md` de la spec a CRLF y verifique que `validate` no tiene errores con «alterada»; luego cambiar `diseño.md` y verificar que sí aparece.
- [ ] T03 (AC-04): En `tests/test_sdd.py`, añadir prueba de compatibilidad: archivo LF ⇒ `sdd.hash_file(p) == hashlib.sha256(p.read_bytes()).hexdigest()` (añadir `import hashlib`).
- [ ] T04 (AC-05): En `tests/test_sdd.py`, añadir prueba `skipUnless(shutil.which('git'))` que, con la raíz real del repo obtenida de `Path(__file__)`, compruebe que existe `.gitattributes` y que `git check-attr eol -- .microharness/python.sh` termina en `eol: lf`.
- [ ] T05 (AC-06): Ejecutar la suite y confirmar que fallan las pruebas de T01, T02 y T04 (TDD); T03 puede pasar ya, porque protege la compatibilidad.
- [ ] T06 (AC-05): Crear `.gitattributes` en la raíz con la línea `*.sh text eol=lf`.
- [ ] T07 (AC-01..AC-04): En `.microharness/sdd.py`, aplicar `.replace(b'\r\n', b'\n')` a los bytes leídos en `hash_file()` y en el bucle de `spec_fingerprint()`. No tocar `code_fingerprint()` ni otras funciones.
- [ ] T08 (AC-06): Ejecutar `python -m unittest discover -s tests -v` y `sh .microharness/python.sh .microharness/sdd.py check eol-hashes-estables`; confirmar suite verde y que el diff solo toca `.gitattributes`, `.microharness/sdd.py` y `tests/test_sdd.py`.
