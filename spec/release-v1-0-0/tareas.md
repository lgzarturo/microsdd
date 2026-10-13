# PASOS: trabajo verificable

- [ ] T01 (AC-01, AC-03): en `tests/test_sdd.py`, en `test_version_flag_prints_microsdd_version`, cambiar `MicroSDD 0.1.0` → `MicroSDD 1.0.0` y la regex `0\.1\.0` → `1\.0\.0`, y añadir la comparación por regex de `version = "..."` de `pyproject.toml` con `__version__`. Ejecutar la prueba y comprobar que falla (rojo) antes de T02. Nada más en el archivo.
- [ ] T02 (AC-01, AC-02): en `.microharness/sdd.py`, sustituir por Bash la línea 28 `__version__ = '0.1.0'` por `__version__ = '1.0.0'`; nada más en el archivo.
- [ ] T03 (AC-03, AC-10): en `pyproject.toml`, `version = "0.1.0"` → `version = "1.0.0"`; nada más.
- [ ] T04 (AC-01, AC-03): `python -m unittest tests.test_sdd.VersionTests -v` en verde; `sh .microharness/python.sh .microharness/sdd.py --version` → `MicroSDD 1.0.0`; cambiar temporalmente la versión de `pyproject.toml` y comprobar que la prueba falla; restaurar.
- [ ] T05 (AC-04, AC-05, AC-06): crear `CHANGELOG.md` con la estructura de `plan.md` a partir de `git log --no-merges --reverse --format='%h %s' 5bd110e` y de la clasificación de `release propose` (2/18/9/11); incluir la nota de merges omitidos; sin `[Unreleased]` ni marcadores.
- [ ] T06 (AC-05, AC-06): verificar: conjunto de hashes igual al de `git log --no-merges --format=%h 5bd110e` (40, sin repetidos), ningún hash de `git log --merges`, grupo y orden correctos, descripción literal de cada asunto.
- [ ] T07 (AC-07, AC-08): editar `assets/proceso-versionado.md` solo en los cinco puntos de `plan.md` (Estado actual, primer tag, API-02 `mutation.command`, «(cuando exista)», «tampoco existe `CHANGELOG.md`»); revisar con `git diff assets/proceso-versionado.md`; `python -m unittest tests.test_api_publica -v` en verde.
- [ ] T08 (AC-02): `git grep -n "0\.1\.0" -- ':!tests' ':!spec' ':!historial' ':!.microharness/memory.json' ':!CHANGELOG.md'` sin declaraciones de versión restantes.
- [ ] T09 (AC-10): `uv build --wheel --out-dir <scratchpad>`; comprobar `microsdd-1.0.0-py3-none-any.whl` y `Version: 1.0.0` en `METADATA`; registrar la salida como evidencia sin dejar artefactos en el repositorio.
- [ ] T10 (AC-09, AC-11): `python -m unittest discover -s tests -v` (código 0, ≥175 pruebas), `sdd.py check release-v1-0-0 --run`, `git status` (solo rutas del alcance) y `git tag` (vacío).
