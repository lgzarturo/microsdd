# PASOS: trabajo verificable

Orden TDD: pruebas RED primero, luego implementación mínima, luego README, luego verificación.

## Pruebas (RED) — `tests/test_installer.py`
- [ ] T01 (AC-01..AC-09): crear `tests/test_installer.py` con unittest; cargar `src/microsdd/installer.py` por ruta (patrón de `tests/test_sdd.py` líneas 8-11); utilidades: repo Git temporal (`git init`), snapshot (ruta -> bytes) y `home` temporal inyectado; `source` = raíz de este repo; `python` = `sys.executable`.
- [ ] T02 (AC-01): prueba de instalación limpia: propios byte a byte, `CLAUDE.md` con marcadores e `@CLAUDE.microsdd.md`, `docs/` (4), `spec/`, `.microharness/memory.json`, exit 0.
- [ ] T03 (AC-02): segunda ejecución -> snapshot idéntico y un solo `<!-- microsdd:begin -->`.
- [ ] T04 (AC-03): `CLAUDE.md` previo (LF y CRLF) conserva prefijo; con `AGENTS.md` sin `CLAUDE.md`, el creado contiene `@AGENTS.md`.
- [ ] T05 (AC-04): `settings.json` distinto intacto; `.claude/settings.microsdd.json` igual al payload; salida con aviso de fusión.
- [ ] T06 (AC-05): propio modificado sin `--force` -> exit 1 y snapshot igual; con `--force` -> sobrescrito y compartidos intactos.
- [ ] T07 (AC-06): `--dry-run` -> snapshot igual, exit 0, plan en salida.
- [ ] T08 (AC-07): destino home, bajo `~/.claude`, no Git y subdirectorio -> exit 1 y cero escrituras.
- [ ] T09 (AC-08): intérprete falso (script que sale con 9009 y otro que reporta 3.9) -> exit 1 y cero escrituras; prueba pura del filtro de PATH (excluye `bin`/`Scripts` de `sys.prefix` cuando difiere de `base_prefix`, conserva el resto).
- [ ] T10 (AC-09): banner con "MicroSDD for Claude Opus 5.5" y alerta no global; `main([])` -> exit 2 sin escribir.
- [ ] T11 (AC-10): `skipUnless(shutil.which("uv"))`: copiar el repo a dir temporal, `uv build --sdist`, luego wheel desde el sdist; comprobar `microsdd/payload/<ruta>` para cada entrada del manifiesto y METADATA sin `Requires-Dist`.
- [ ] T12 (AC-01..AC-10): ejecutar `python -m unittest discover -s tests -v` y confirmar que las nuevas pruebas fallan (RED) por ausencia del módulo.

## Implementación — `pyproject.toml`, `src/microsdd/`
- [ ] T13 (AC-10): crear `pyproject.toml` (hatchling con versión mínima, `dependencies = []`, script `microsdd`, `packages`, `force-include` por archivo del manifiesto, `include` del sdist).
- [ ] T14 (AC-01): crear `src/microsdd/__init__.py` mínimo.
- [ ] T15 (AC-08, AC-09): en `src/microsdd/installer.py`: manifiesto, banner, filtro puro de PATH, verificación de `python3` ejecutándolo con remediación por SO.
- [ ] T16 (AC-07): validación de destino (home, `~/.claude`, `git rev-parse --show-toplevel` con `resolve` + `normcase`); advertencia de árbol sucio.
- [ ] T17 (AC-02, AC-03, AC-04, AC-05, AC-06): planificación/clasificación completa antes de escribir; bloque de `CLAUDE.md` con marcadores, LF/CRLF y `@AGENTS.md`; alterno de settings; conflicto/`--force`; `--dry-run`.
- [ ] T18 (AC-01): escritura con `shutil.copyfile` (bit ejecutable de `sdd.py` en POSIX), `sdd.py init`, smoke del hook (`deny`), próximos pasos con `git add` explícito; `main()` con argparse y códigos 0/1/2.
- [ ] T19 (AC-01..AC-10): ejecutar la suite hasta verde (GREEN) sin tocar archivos fuera del alcance.

## Documentación — `README.md`
- [ ] T20 (AC-11): actualizar `README.md`: título "MicroSDD for Claude Opus 5.5", `> [!WARNING]` no global, requisitos con `uv`, comando `uvx` con flags, tabla de política de conflictos, `git add` explícito, fijar tag, eliminación manual, árbol de archivos con `pyproject.toml` y `src/microsdd/`.

## Enmienda (Windows `python3.exe`, smoke estricto, README)
- [ ] T23 (AC-08): RED: en `tests/test_installer.py`, prueba `skipUnless(sys.platform == 'win32')` con un PATH temporal cuyo único candidato es `python3.cmd` -> exit 1 y snapshot igual.
- [ ] T24 (AC-13): RED: en `tests/test_installer.py`, `source` temporal (copia del manifiesto) cuyo `.claude/hooks/pretool.py` imprime `deny` con "Guardia inválida" -> exit 1.
- [ ] T25 (AC-08): GREEN: en `src/microsdd/installer.py`, en Windows buscar solo `python3.exe` en el PATH filtrado; remediación que indique que `.cmd`/`.bat` no sirven para Git Bash; otros SO sin cambios.
- [ ] T26 (AC-13): GREEN: en `src/microsdd/installer.py`, el smoke exige `deny` y "solo lectura"; fallo de smoke o de `init` -> exit 1.
- [ ] T27 (AC-11): `README.md`: código 1 también si `sdd.py init` o el smoke fallan después de escribir; en Windows se exige `python3.exe` (los shims `.cmd` no cuentan).

## Verificación
- [ ] T21 (AC-12): `python -m unittest discover -s tests -v` en verde, incluido `tests/test_sdd.py`.
- [ ] T22 (AC-01..AC-13): `python .microharness/sdd.py check instalador-uvx` sin archivos fuera de `scope.allowed_paths`.
