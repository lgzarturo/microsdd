# Windows, PowerShell y worktrees (1.1.3)

## Decisión de lanzador

**Entrada preferida (igual en bash y PowerShell):** `python .microharness/sdd.py …` (o `python.exe` / `py -3` en Windows).

Lanzadores del arnés (misma semántica: primer Python ≥3.10 vía `MICROSDD_PYTHON` → `uv` → `python`/`python3` → `py -3`):

| Plataforma | Comando |
|---|---|
| Unix / macOS | `sh .microharness/python.sh .microharness/sdd.py …` |
| PowerShell 7 | `.\.microharness\python.ps1 .microharness\sdd.py …` |
| cmd.exe | `.microharness\python.cmd .microharness\sdd.py …` |

El console script `microsdd` (instalador: `install`/`on`/`off`/`status`/`worktree`) es el paquete publicado; el CLI del arnés por proyecto sigue siendo `.microharness/sdd.py`. No se duplican `approve`/`seal` en el instalador para no acoplar el paquete al `ROOT` local ni saltarse las guardas de `sdd.py`.

En Windows el líder y los mensajes del hook **nunca** deben sugerir `sh` ni `cp`. Equivalentes: `python` / `python.ps1` y `Copy-Item -Recurse`.

## Worktrees: decisión

Opciones evaluadas:

1. **`microsdd worktree sync <ruta>`** (humano, TTY, fuera de Claude Code): copia plantillas del arnés (`sdd.py`, lanzadores) y `docs/` al worktree; `memory.json` es **local al worktree** (no se sobrescribe si ya existe; no se enlaza al principal).
2. Leer `.microharness`/`docs` desde el checkout principal (`git rev-parse --git-common-dir`): riesgo de que un agente en el worktree mute `memory.json`/aprobaciones del principal.
3. Versionar `.microharness/` completo: `memory.json` es estado mutable y provoca conflictos de merge; no aísla aprobaciones.

**Elegido: (1).** Un worktree no altera aprobaciones ni `memory.json` del checkout principal sin pasar por el humano (puerta TTY + `approve`/`seal` en el árbol donde corre `sdd.py`). Si hace falta copiar memoria del principal, el humano usa `--with-memory` de forma explícita (sigue siendo copia, no symlink).

```powershell
# Desde el checkout principal, en tu terminal (fuera de Claude Code):
microsdd worktree sync .claude\worktrees\mi-rama
# Opcional y explícito:
microsdd worktree sync .claude\worktrees\mi-rama --with-memory
```

```bash
microsdd worktree sync .claude/worktrees/mi-rama
```
