# CÓMO: plan

## Enfoque mínimo

Enhebrar el rol (`agent`) desde `run()` hasta `deny_or_allow_gated`. Permitir el atajo `@note` solo si `agent == 'lider'` y `agent_may_approve(cwd)`. En cualquier otro caso, denegar con mensaje específico (no el genérico de TTY humano, para que quede claro el motivo de rol).

```python
def deny_or_allow_gated(cmd: str, cwd: str | None, agent: str = '') -> str | None:
    if agent_may_approve(cwd) and gated_with_note_evidence(cmd) and agent == 'lider':
        return None
    if agent_may_approve(cwd) and gated_with_note_evidence(cmd) and agent != 'lider':
        return msg_gated_lider_only()  # mensaje claro
    return msg_approve()
```

Propagar `agent` en `check_shell` → `guard_segment` → `deny_or_allow_gated`. `run()` ya pasa `check_shell(..., cwd)`; añadir el agente.

Fail closed de rol ausente: ya cubierto al inicio de `run()` (Bash denegado si agente no reconocido). Añadir test explícito.

## Archivos

| Archivo | Cambio |
|---|---|
| `.claude/hooks/pretool.py` | Rol en `deny_or_allow_gated`; mensaje; firma de `check_shell`/`guard_segment` |
| `tests/test_agent_may_approve.py` | Tests AC-01…AC-05 |
| `README.md` | Dejar explícito «solo líder» (ya lo dice; reforzar si hace falta) |
| `CHANGELOG.md` | Entrada `[1.3.2]` |
| `assets/proceso-versionado.md` | API-01/API-05 + estado `1.3.2` |
| `assets/arnes-completo.md` | Párrafo agent_may_approve: solo líder en el hook |
| `.claude/agents/lider.md` | Solo si el texto implica ambigüedad (probable no) |
| `.microharness/sdd.py` | Solo `__version__ = '1.3.2'` |
| `pyproject.toml` | `version = "1.3.2"` |

## Alternativas descartadas

- Validar rol en `sdd.py` vía env: Claude Code no exporta `agent_type` al proceso hijo de forma fiable documentada; YAGNI.
- Denegar siempre a autor/implementador en `PROTECTED_RE` sin mirar `@note`: ya se deniega sin `@note`; el bug es el bypass con `@note`.

## Riesgos

- Romper tests que asumen allow sin `agent_type` en el evento: los existentes usan `'agent_type': 'lider'`.
- Mensaje demasiado genérico: exigir que nombre «líder».

## Pruebas

```bash
sh .microharness/python.sh -m unittest tests.test_agent_may_approve -v
```
