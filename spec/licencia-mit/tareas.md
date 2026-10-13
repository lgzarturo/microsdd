# PASOS: trabajo verificable

Orden TDD: primero las pruebas (RED), después `LICENSE` y `pyproject.toml` (GREEN), luego el README y al final la verificación.

## Pruebas (RED): `tests/test_installer.py`
- [ ] T01 (AC-01): añadir la constante con el texto MIT canónico de `diseño.md` y la prueba `test_license_file_is_canonical_mit` (`# AC-01`). Lee `SOURCE / 'LICENSE'` como UTF-8, normaliza CRLF a LF, quita el salto final y compara igualdad exacta.
- [ ] T02 (AC-02, AC-03): en `test_wheel_from_sdist_contains_payload_without_dependencies`, añadir `'LICENSE'` a los archivos copiados al proyecto temporal y luego comprobar:
  - con `import tarfile`, que el sdist contiene `<raíz>/LICENSE`;
  - en `METADATA`, las líneas `License-Expression: MIT` y `License-File: LICENSE`;
  - que existe `*.dist-info/licenses/LICENSE` y es igual byte a byte al `LICENSE` del sdist.

  Las aserciones actuales se conservan.
- [ ] T03 (AC-01..AC-03): ejecutar `python -m unittest discover -s tests -v` y confirmar el RED esperado: AC-01 falla porque no existe `LICENSE` y la prueba de wheel falla en la copia o en las aserciones de licencia.

## Implementación (GREEN): `LICENSE`, `pyproject.toml`
- [ ] T04 (AC-01): crear `LICENSE` en la raíz con el texto exacto de `diseño.md` (UTF-8 sin BOM, LF, salto final).
- [ ] T05 (AC-04): verificar en el changelog de hatchling o con una construcción real la versión mínima con soporte PEP 639 (se espera 1.27.0) y registrar la evidencia en el informe.
- [ ] T06 (AC-02, AC-03, AC-04): en `pyproject.toml`:
  - subir `hatchling>=1.24` a la mínima verificada;
  - añadir `license = "MIT"` y `license-files = ["LICENSE"]` en `[project]`;
  - añadir `"LICENSE"` al `include` del sdist.

  No tocar nada más.
- [ ] T07 (AC-01..AC-03, AC-06): ejecutar la suite hasta verde. La prueba de wheel debe aparecer ejecutada, no `skipped`.

## Documentación: `README.md`
- [ ] T08 (AC-05): añadir al final `## 10. Licencia` con: licencia MIT, `Copyright (c) 2026 Arturo López`, enlace `[LICENSE](LICENSE)` y nota de que los archivos que el instalador copia en otro repositorio están bajo MIT, que exige conservar el aviso de copyright y de permiso al redistribuirlos. No afirmar que el instalador copia `LICENSE`. Comprobar con `git diff README.md` que solo se añaden líneas al final.

## Verificación
- [ ] T09 (AC-06): `python -m unittest discover -s tests -v` en verde, incluido `tests/test_sdd.py`.
- [ ] T10 (AC-07): `python .microharness/sdd.py check licencia-mit` sin archivos fuera de `scope.allowed_paths`.
