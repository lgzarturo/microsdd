# Aprobación firmada (futuro)

## Estado

**No implementado** en 1.1.2. MicroSDD registra declaraciones de aprobación en `.microharness/memory.json`; no autentica identidad ni firma criptográficamente.

## Mecanismo actual (1.1.2) contra aprobaciones falsas vía script

1. **Puerta humana en la función:** `require_human_terminal` al inicio de `approve` y `seal` (también en `main` como defensa en profundidad). Con `CLAUDECODE` o stdin no-TTY, la llamada directa (import del módulo) lanza `ValueError` y no escribe.
2. **Integridad antes de mutar:** `approve`, `seal`, `note` y `review` llaman a `memory_integrity` al inicio; si ya hay errores frente a `HEAD`, no escriben. Un script que corrompió la memoria no puede sellar/aprobar encima sin que `check`/`op` lo detecte.
3. **Hook best-effort:** deniega Write/Edit bajo `.microharness/`, menciones sensibles en Bash y ejecutables bajo `docs/`/`spec/`.

## Trabajo futuro (fuera del repo)

Aprobación firmada (p. ej. clave hardware, firma detached, o verificación en CI/hooks de Git) **fuera del árbol del proyecto**, de modo que un agente con Write no pueda fabricar ni la clave ni el veredicto. Hasta entonces, la evidencia válida sigue siendo la acción expresa del humano en su terminal.
