# convenciones

Convenciones que fallan en máquina. Lo demás es juicio humano.

| Regla | Capa | Función |
| --- | --- | --- |
| Conventional Commit sintáctico | estatico | `commit_check` |
| Sin placeholder en `docs/` | estatico | `docs_placeholder_errors` |
| EARS + `AC-NN` en spec | estatico | `validate` |
| `testing.commands` en lista blanca | estatico | `allowed_test_commands` / `command_allowed` |
| Versión solo en diffs de release | estatico | `version_mix_errors` |
| Corrección: capa más baja primero | verificacion | `cmd_correct` |
