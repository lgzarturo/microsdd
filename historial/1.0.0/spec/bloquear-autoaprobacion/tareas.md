# PASOS: trabajo verificable

Antes de delegar: el líder resuelve Q-01 y Q-05. La aprobación de la spec la registra el humano en su terminal, no el líder:
`sh .microharness/python.sh .microharness/sdd.py approve bloquear-autoaprobacion spec --by 'Programador' --evidence '<texto de la aprobación>'`

Orden obligatorio: `pretool.py` se modifica al final (T12), porque el hook se recarga en cada llamada.

## RED (pruebas primero, archivo nuevo `tests/test_bloquear_autoaprobacion.py`, sin sellar)
- [ ] T01 (AC-01, AC-02): cargar `pretool.py` con `importlib`; recorrer `lider`/`autor`/`implementador` × `Bash`/`PowerShell` × la lista de bypass de AC-01, y `approve`/`seal` con los cinco lanzadores (AC-02). El resultado no debe ser `None` (un `subTest` por caso).
- [ ] T02 (AC-03, AC-04): comprobar que se permiten (`None`) los comandos de AC-03 con cada lanzador y los de AC-04, para los tres roles y ambas herramientas.
- [ ] T03 (AC-05): el revisor, con `approve`, `seal`, `review` y `note` por el lanzador `sh`, queda denegado. No se modifican `tests/test_sdd.py` ni `tests/test_hook_fail_closed.py`.
- [ ] T04 (AC-06, AC-08, AC-09): pruebas de edición con `cwd` en un `TemporaryDirectory`: rutas de AC-06 × `lider`/`autor` × las cuatro herramientas denegadas; rutas relativas `docs/AGENT.md` y `spec/x/plan.md` permitidas al líder; revisor + `Edit` + `tool_input: {}` con «solo lectura».
- [ ] T05 (AC-07): `cwd` temporal con `spec/t/spec.json` en `proceso` (`allowed_paths` con `.microharness/sdd.py` y `.microharness/python.sh`) y `memory.json` con `approvals.spec` registrada. El implementador puede editar esas dos rutas y se le deniegan las demás de AC-07. Variantes sin las rutas en `allowed_paths` y sin aprobación: denegadas.
- [ ] T06 (AC-10, AC-11, AC-12): `sdd.main()` con `mock.patch.object(sys, 'argv', …)`, `mock.patch.dict(os.environ, …)` (añadir o quitar `CLAUDECODE`), `sys.stdin` sustituido por un objeto con `isatty()` controlado o por `None`, y `approve`/`seal` mockeados. Comprobar el código de salida, `ERROR:`, las llamadas y que `memory.json` queda byte a byte igual en un `ROOT` temporal. Incluir `note` y `check` con `CLAUDECODE=1` y stdin no TTY.
- [ ] T07 (AC-01..AC-12): `python -m unittest discover -s tests -v`: las pruebas nuevas fallan (RED) y las existentes pasan. El líder informa del resultado al humano.

## GREEN (implementación mínima, en este orden)
- [ ] T08 (AC-10, AC-11, AC-12): `.microharness/sdd.py`: añadir la comprobación de `CLAUDECODE`/TTY en `main()`, solo para `approve`/`seal`. T06 pasa.
- [ ] T09 (AC-13): `.claude/agents/lider.md`, pasos 3, 6 y 7, según el plan.
- [ ] T10 (AC-14, AC-15): `README.md` y `assets/proceso-versionado.md` (API-01 y API-05) según el plan.
- [ ] T11 (AC-16): `CHANGELOG.md`: entrada sin hash en «Incompatible» (o en «Corregido» según Q-05) de `[1.0.0]`, idéntica a la descripción del asunto acordado.
- [ ] T12 (AC-01..AC-09): `.claude/hooks/pretool.py`: `PROTECTED_RE`, `SDD_ALLOWED`, `tokens`, `sdd_args` y `protected_bash`; resolución de la ruta contra `event['cwd']`; regla común de `.microharness/` con la excepción del implementador; quitar `.microharness/` de la lista previa del implementador y la excepción `memory.json` del líder. El fail-closed y el bloque del revisor no cambian. T01–T05 pasan.

## Verificación
- [ ] T13 (AC-05, AC-15, AC-17): `python -m unittest discover -s tests -v` termina con código 0 (incluidos `test_installer`, `test_api_publica` y `test_hook_fail_closed`). `git diff --stat` solo muestra archivos de `scope.allowed_paths`, y `git diff -- .claude/hooks/pretool.py` deja intactos el fail-closed y el bloque del revisor.
- [ ] T14 (AC-01..AC-17): el revisor ejecuta `sh .microharness/python.sh .microharness/sdd.py check bloquear-autoaprobacion --run` (sigue permitido) y emite su dictamen. El líder lo registra con `sdd.py review`.
- [ ] T15 (AC-13, AC-16): cierre. El líder añade la línea del invariante a `docs/arquitectura.md` y la fila de `docs/especificaciones.md`, pide la aprobación de cierre y entrega al humano este comando para su terminal (fuera de Claude Code, sin `!`):
  `sh .microharness/python.sh .microharness/sdd.py approve bloquear-autoaprobacion close --by 'Programador' --evidence '<texto de la aprobación de cierre>'`
  Después, el líder ejecuta `sdd.py check bloquear-autoaprobacion`, `sdd.py commit-check 'fix(hook)!: impide que los agentes aprueben, sellen o editen la memoria'` y el commit con `git add` explícito de los archivos de la tarea y `.microharness/memory.json`. El hash de la entrada de `CHANGELOG.md` se añade en un commit posterior, fuera de esta tarea.
