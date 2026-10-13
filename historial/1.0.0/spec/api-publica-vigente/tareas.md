# PASOS: trabajo verificable

- [ ] T01 (AC-01, AC-02, AC-03, AC-04): crear `tests/test_api_publica.py` según `plan.md` (sección por encabezado; subcomandos, acciones de `release`, `--version` y opciones largas desde `sdd.py --help`; `MANIFEST` e `INIT_FILES` vía `importlib`; comprobación inversa de «Incluido»). Ejecutar `python -m unittest tests.test_api_publica -v` y registrar el fallo (RED) con los nombres que faltan (`note`, `--version`, `propose`, `--fact`, `.microharness/python.sh`, `CLAUDE.microsdd.md`, `README.md` no instalado…). Sellado humano posterior.
- [ ] T02 (AC-01, AC-02, AC-05, AC-07): editar en `assets/proceso-versionado.md` las viñetas API-01, API-02, API-03 y API-05 con el texto mínimo de `plan.md`.
- [ ] T03 (AC-06): añadir API-09 (`.microharness/config.json`) tras API-08 y cambiar «API-01 a API-08» por «API-01 a API-09» en «Reglas de incremento»; `grep -rn "API-08" assets/` para revisar otras citas dentro del alcance.
- [ ] T04 (AC-03, AC-04, AC-07, AC-08): reescribir en «Instalación» el párrafo inicial, «Incluido» y «Excluido» según `MANIFEST`, `INIT_FILES`, bloque de `CLAUDE.md`, `settings.microsdd.json` y compatibilidad de nombres de `docs/`; ajustar la nota de conflictos.
- [ ] T05 (AC-01 a AC-04): `python -m unittest tests.test_api_publica -v` en verde (GREEN).
- [ ] T06 (AC-09, AC-11): `git diff assets/proceso-versionado.md` solo en las tres zonas permitidas; `git status` sin cambios en `.microharness/sdd.py`, `src/**`, `.claude/**`, `pyproject.toml`, `README.md`.
- [ ] T07 (AC-01, AC-04): comprobación manual de mutación: quitar temporalmente `` `note` `` de API-01 y añadir `` - `README.md` `` a «Incluido»; la prueba debe fallar en cada caso; restaurar y confirmar verde. Registrar la salida como evidencia.
- [ ] T08 (AC-10): `python -m unittest discover -s tests -v` (código 0, `Ran` ≥ 172) y `sh .microharness/python.sh .microharness/sdd.py check api-publica-vigente --run`.
