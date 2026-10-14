# CÓMO: diseño mínimo

## Situación comprobada
Ver «Hechos comprobados» en `requerimientos.md`. Todo cabe en `installer.py` (CLI) y `pretool.py` (guardia); no se crean módulos ni capas.

## Decisión y justificación
1. Fragmento = payload (DRY): `agent`, `model`, `effortLevel` y la única entrada de `hooks.PreToolUse` se leen de `PAYLOAD/.claude/settings.json`; no se duplican constantes.
2. `plan()` etiqueta `.claude/settings.json` como `crear` (no existe; copia binaria, AC-01), `sin cambios` (la fusión no cambia nada) o `fusionar` (contenido calculado por `merge()`). `SETTINGS_ALT` y la etiqueta `alterno` desaparecen. JSON inválido se detecta en `plan()`, antes de escribir (REQ-05). `--force` no afecta a `settings.json`.
3. `merge(current, payload) -> (nuevo, registro)`: por cada clave raíz: ausente → añadir (`{"previous_absent": true}`); distinta → reemplazar (`{"previous": valor}`, D-02); igual → no registrar salvo `agent` (solo existe por MicroSDD). Entrada de hook: si no hay una igual (comparación de objetos) en `PreToolUse`, se añade al final; se registra su huella `sha256(json.dumps(entrada, sort_keys=True))`; si ya existe, se adopta igual. Crea `hooks`/`PreToolUse` si faltan.
4. `unmerge(current, registro)`: elimina o restaura cada clave registrada, quita las entradas con la huella registrada, borra `PreToolUse` y `hooks` si quedan vacíos.
5. Manifiesto `.microharness/install.json` (el hook ya protege `.microharness/` de agentes; `check` no lo cuenta fuera de alcance):
   `{"schema_version": 1, "settings": {"created": bool, "enabled": bool, "keys": {...}, "hook": "<sha256>"|null}, "claude_md": {"mode": "created"|"appended", "text": "<bytes escritos, utf-8>"}}`.
   Se escribe tras escribir los demás archivos; si no cambia, no se reescribe (AC-04). Va en el `git add` impreso; `INSTALL_RECORD` se añade al conjunto de `tests/test_api_publica.py`.
6. Respaldo: `backup(path)` copia a `settings.json.bak.<%Y%m%dT%H%M%S%fZ UTC>` justo antes de reescribir un `settings.json` existente. Escritura: `json.dumps(data, indent=2, ensure_ascii=False) + '\n'`.
7. Subcomandos en `main()`: `install` (igual), `uninstall [--target] [--force]`, `on|off|status [--target]`. `on`, `off` y `uninstall` llaman a `human_gate()` en `main()` (misma regla que `sdd.py`: `'CLAUDECODE' in os.environ or sys.stdin is None or not sys.stdin.isatty()` → `ERROR:` y 1). Las funciones `toggle(target, enable)` y `uninstall(source, target, force)` no la incluyen, para probarlas directamente; AC-09 prueba la puerta vía `main()`.
8. `off`: `unmerge`, respaldo, `enabled=false`, `keys={}`, `hook=null`; idempotente si ya está desactivado. `on`: `merge` y nuevo registro. Ambos exigen manifiesto. `status`: solo lectura; `activo` si `agent == "lider"` y la entrada del hook está presente, `inactivo` si ninguno, `parcial` en otro caso; además imprime `model` y `effortLevel`.
9. `uninstall`: precomprueba todo (manifiesto, JSON, propios iguales al payload salvo `--force`) antes de escribir; si está activo aplica `off` (con respaldo); si `settings.created` y el resultado es `{}`, borra `settings.json`; borra propios de `MANIFEST` (excepto `settings.json`), `CLAUDE.microsdd.md` y `.claude/settings.microsdd.json` si existe; `CLAUDE.md`: si `created` y el contenido es `text` → borrar; si termina en `text` → truncar; si no, quitar las líneas de `BEGIN` a `END` y avisar; por último borra el manifiesto.
10. `install` con `.claude/settings.microsdd.json` presente: `AVISO:` de que es obsoleto (no lo borra; lo hace `uninstall`).
11. `pretool.py`: nueva `guard_bash(cmd)` antes de `protected_bash` para `lider`, `autor` e `implementador`:
    - `TOGGLE_RE = r'(?:microsdd|installer\.py).*\b(?:on|off|uninstall)\b'` (re.I, re.S) y `SETTINGS_RE = r'settings(?:\.local)?\.json'` (re.I) sobre el comando completo.
    - Excepción solo si `tokens(cmd)` no es `None` y `toks[0] == 'git'` y `toks[1]` está en `add|diff|status|log|show|commit` (así `git -c …` y `sh -c "…"` se deniegan); o `toks` es exactamente `[python|python3, -m, json.tool, <ruta>]`.
    - Motivo: «on, off y uninstall de microsdd, y los cambios a .claude/settings.json, los ejecuta el humano en su terminal, fuera de Claude Code.»
    - Las ediciones nativas no cambian: AC-13 es regresión.
12. Documentación: `SKILL.md` añade un párrafo `on|off|status`; `CLAUDE.md` línea 3 → «(configurado en `.claude/settings.json` mientras el arnés está activo; compruébalo con `microsdd status`)»; `README.md` (tabla, «Bloqueo si falta uv», «Sesiones…», «Eliminación manual» → «Desinstalación», nuevo apartado on/off/status); `proceso-versionado.md` («Instalación», «Incluido», «Nota», API-05).

## Alternativas descartadas
- Mantener `settings.microsdd.json`: Claude Code no lo lee (causa del problema).
- `settings.local.json`: no se versiona; el equipo no hereda la guardia.
- Detectar propiedad por igualdad de valor sin manifiesto: borraría valores ajenos iguales; no permite restaurar previos.
- Conflicto ante valores distintos: deja el arnés inactivo, que es el problema original (D-02).
- Clase/módulo de settings o JSON Patch: YAGNI.

## Invariantes y riesgos
- Nunca se escribe nada si alguna precondición falla (JSON, manifiesto, conflictos, puerta humana).
- Lo ajeno queda igual en comparación de objetos tras `off`/`uninstall`.
- El payload `.claude/settings.json` no cambia.
- R-01: guardia de mejor esfuerzo (NO sandbox): `python -c`, aliases o scripts intermedios pueden esquivarla; la puerta `CLAUDECODE`/TTY solo protege `main()`.
- R-02: se pierde el formato original de `settings.json`; lo mitiga el respaldo.
- R-03: el árbol de trabajo actual puede tener `settings.json` sin hooks: `check` lo marcaría fuera de alcance y `SettingsTests` fallaría.
- R-04: `Bash` puede editar `.claude/hooks/pretool.py`; queda fuera de alcance.
- R-05: falsos positivos en comandos que mencionan `microsdd` y `on`; se resuelven con `git commit` o ejecutándolos el humano.
- R-06: los `.bak` se acumulan y pueden versionarse por error; el `git add` impreso los excluye.
- Efecto lateral: cambia el conjunto de rutas instaladas (API-08) y la API del hook (API-05): D-03.
- D-01 (bloqueante): quién edita `.claude/hooks/pretool.py`, `.claude/skills/sdd/SKILL.md` y `CLAUDE.md`. Orden: `pretool.py` al final.
