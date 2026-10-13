# PASOS: trabajo verificable

- [ ] T01 (AC-01; `tests/test_hook_fail_closed.py`): crear el archivo con una clase que cargue `.claude/hooks/pretool.py` con `importlib` (como `HookTests`) y pruebe, con `subTest` por herramienta y por valor de `agent_type` (ausente, `''`, `None`, `'general-purpose'`, `'Explore'`, `'Lider'`, `' lider'`), que `run()` devuelve una cadena con `claude --agent lider`. `Write`/`Edit`/`MultiEdit` con `file_path` dentro de un `cwd` temporal; `NotebookEdit` con `notebook_path`; `Bash`/`PowerShell` con `git status`.
- [ ] T02 (AC-02; mismo archivo): con `agent_type` ausente y `'general-purpose'`, `run()` devuelve `None` para `Read`, `Grep`, `Glob`, `WebFetch` y sin `tool_name`.
- [ ] T03 (AC-03; mismo archivo): con `Bash` + `git status`, `run()` devuelve `None` para `lider`, `autor` e `implementador`; el revisor con `Edit` sigue recibiendo «solo lectura».
- [ ] T04 (AC-04; mismo archivo): ejecutar `pretool.py` con `subprocess.run([sys.executable, <ruta>], input=...)`: evento sin `agent_type` + `Write` → código 0, JSON `deny` con `claude --agent lider`; `lider` + `Bash git status` → stdout vacío.
- [ ] T05 (RED): ejecutar `python -m unittest discover -s tests -v`; deben fallar solo los casos de T01 y el primero de T04, y pasar T02, T03 y el resto de la suite. Registrar la salida.
- [ ] T06 (AC-06; `README.md`): añadir la subsección «Sesiones y subagentes sin rol MicroSDD» junto a «Bloqueo si falta uv» y ajustar la fila «Acceso por rol» de la sección 7, según AC-06. Sin otros cambios.
- [ ] T07 (AC-01..AC-04; `.claude/hooks/pretool.py`, último cambio de código, por Bash): sustituir solo la salida temprana de `run()` por el bloque del plan. Validar la sintaxis del nuevo contenido con `py_compile` antes de reemplazar el archivo (R-03).
- [ ] T08 (GREEN, AC-05): ejecutar inmediatamente `python -m unittest discover -s tests -v`; todo debe pasar, incluidos `tests/test_installer.py` y `SettingsTests`.
- [ ] T09 (AC-07): `git diff --name-only` y `git status --short` solo muestran rutas de `allowed_paths`.
