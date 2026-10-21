# QUÉ: el hook reconoce rutas absolutas de Windows

## Objetivo

Corregir el fallo de `windows-latest` en CI
(`test_ac01b_seal_launcher_forms_allowed_for_lider`, 2 subtests):
el hook deniega `python3 D:\...\sdd.py seal ...` del líder con
«Comando no analizable» porque `split_segments`/`tokens` rechazan
cualquier backslash. Tras el fix, las rutas absolutas Windows
(`[A-Za-z]:\...`) se normalizan a `/` antes del parseo y la forma
lanzador reconocida pasa; la relativa con backslash
(`.microharness\sdd.py`) sigue denegada.

## Precondiciones

- Rama `main`, HEAD `a10bd06` (release `v1.5.1` publicado).
- Fallo preexistente: también falla en el run de `v1.5.0`
  (no lo causó el release 1.5.1).
- Sonda `/tmp/hook_winpath_probe.py` en rojo con el síntoma exacto.

## Requisitos EARS

- REQ-01: WHEN el líder ejecute `python3 D:\...\.microharness\sdd.py
  seal ...` (Bash o PowerShell), THE hook SHALL permitirlo
  (devuelve `None`).
- REQ-02: WHEN la ruta con backslash sea relativa
  (`.microharness\sdd.py`), THE hook SHALL seguir denegándola
  al líder.
- REQ-03: WHEN un no-líder use la ruta absoluta Windows con `seal`,
  THE hook SHALL seguir denegándolo.
- REQ-04: WHEN se ejecute la suite, THE tests de hook SHALL pasar
  en Linux y el subtest absoluto SHALL pasar en Windows.

## Criterios de aceptación

- AC-01: sonda `/tmp/hook_winpath_probe.py` en verde (6/6).
- AC-02: test de regresión nuevo en
  `tests/test_bloquear_autoaprobacion.py` con rutas `X:\...`
  literales (rojo antes, verde después; corre en Linux y Windows).
- AC-03: `check fix-hook-winpath --run` pasa y la suite completa
  está en verde en Linux.
- AC-04: sin cambios fuera de `.claude/hooks/pretool.py` y su test.

## Fuera de alcance

- Rutas UNC (`\\server\...`): siguen denegadas (YAGNI, sin test).
- Commitear, taguear o publicar release (no solicitado).
