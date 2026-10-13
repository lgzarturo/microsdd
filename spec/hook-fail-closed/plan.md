# CÓMO: diseño mínimo

## Situación comprobada

- `.claude/hooks/pretool.py`, `run()`: `agent = event.get('agent_type') or ''`; si `agent` no está en la tupla de roles, `return None` (línea 14). Después se filtran herramientas de edición (`Write`, `Edit`, `MultiEdit`, `NotebookEdit`) por rol y `Bash`/`PowerShell` solo para el revisor.
- El bloque `__main__` convierte un motivo no vacío en JSON `deny` y cualquier excepción en «Guardia inválida».
- Pruebas: `tests/test_sdd.py` (`HookTests` carga el hook con `importlib`; `SettingsTests` valida settings y ejecuta el hook con uv) y `tests/test_installer.py` (smoke con `sys.executable`, revisor + `Edit`). Ninguna prueba envía eventos sin rol.

## Decisión y justificación

Cambio mínimo en `run()`: sustituir la salida temprana por

```python
if agent not in ('autor', 'implementador', 'revisor', 'lider'):
    if tool in ('Write', 'Edit', 'MultiEdit', 'NotebookEdit', 'Bash', 'PowerShell'):
        return ('Agente no reconocido por MicroSDD: inicia la sesión con `claude --agent lider` '
                'o usa uno de los agentes autor, implementador, revisor o lider.')
    return None
```

- Mismo conjunto de herramientas que el matcher; filtrar dentro de `run()` mantiene `None` para otras herramientas (REQ-02) y no depende de que el matcher esté bien configurado.
- Comparación exacta (sensible a mayúsculas y espacios), como el resto de la guardia.
- Sin cambios en `__main__`: ya emite el JSON `deny` (REQ-04).
- Pruebas nuevas en un archivo propio `tests/test_hook_fail_closed.py`, que se carga igual que `HookTests` (`importlib` sobre `.claude/hooks/pretool.py`). Así se puede sellar sin sellar `tests/test_sdd.py` (decisión anterior del humano en `bloquear-autoaprobacion`: no sellar ese archivo).
- README: nueva subsección junto a «Bloqueo si falta uv» y ajuste de la fila «Acceso por rol» de la sección 7.

## Alternativas descartadas

- **Mantener permitir y solo documentar:** deja abierto R5 para sesiones sin `--agent` y subagentes ajenos.
- **Lista blanca de subagentes integrados (`Explore`, etc.):** esos subagentes no tienen límites de rol en el hook; permitirles Bash reabre el bypass. YAGNI.
- **Variable de entorno para desactivar la denegación:** sería un bypass por diseño; ya existe la vía humana de editar `settings.json` fuera de Claude Code.
- **Mover la tupla de herramientas a una constante compartida con `settings.json`:** el hook no lee settings; una constante local basta y `SettingsTests` ya fija el matcher.
- **Incluir el `agent_type` recibido en el mensaje:** útil para diagnóstico, pero añade texto no confiable al motivo; el README explica los casos. Queda como decisión abierta (D-01).

## Invariantes

- Los cuatro roles conservan exactamente su comportamiento (REQ-03).
- Herramientas fuera del conjunto: siempre `None` para agentes no reconocidos.
- El smoke del instalador (revisor + `Edit` → «solo lectura») no cambia.
- `settings.json` y su matcher no cambian.

## Riesgos y efectos secundarios

- **R-01, subagentes ajenos (impacto medio):** en un proyecto MicroSDD con el hook activo, `Explore`, `general-purpose`, `Plan` u otros subagentes no MicroSDD pierden Write/Edit/MultiEdit/NotebookEdit/Bash/PowerShell. `Explore` usa Bash para inspección (`ls`, `git log`), así que queda limitado a Read/Grep/Glob. Mitigación: README; el líder debe delegar en los cuatro agentes. Cambiar `lider.md` queda fuera de alcance.
- **R-02, sesiones sin agente:** `claude` sin `--agent` y sin `agent: lider` efectivo (p. ej. un override de usuario, o un `settings.json` fusionado solo con el hook) queda sin escritura ni Bash. Mitigación: mensaje explícito y README. Las instalaciones que conservaron `settings.json` y escribieron `settings.microsdd.json` no se ven afectadas hasta fusionarlo.
- **R-03, autobloqueo durante la implementación:** el hook se recarga en cada llamada; un error de sintaxis en `pretool.py` deja a todos los agentes sin herramientas vigiladas («Guardia inválida»). Mitigación: modificar `pretool.py` al final, con un solo comando Bash verificable (`python -c` con `py_compile` antes de sustituir, o escritura atómica), y ejecutar la suite inmediatamente.
- **R-04, supuesto sobre `agent_type`:** la sesión principal con `agent: lider` está verificada; el nombre exacto que envían los subagentes integrados no lo está. Si alguno enviara un rol homónimo (`lider`), recibiría los permisos del rol; no es nuevo respecto de hoy.
- **R-05, `bloquear-autoaprobacion`:** su `plan.md` («Situación comprobada») describe el `run()` actual; tras esta tarea habrá que revisar ese texto y su impacto antes de implementarla.
- **R-06, repositorios instalados:** reciben el cambio con `microsdd install --force`; el comportamiento nuevo afecta a sus sesiones según R-01/R-02.

## Decisiones abiertas (recomendación entre paréntesis; se adoptan salvo objeción)

- D-01: ¿Incluir el `agent_type` recibido en el mensaje? (No; KISS, el README cubre el diagnóstico.)
- D-02: ¿Pruebas en archivo nuevo `tests/test_hook_fail_closed.py` y sellarlo como `protected_tests`? (Sí.)
- D-03: ¿Añadir a `lider.md` una instrucción de no usar `Explore`/`general-purpose`? (No en esta tarea; fuera de alcance, solo README.)
