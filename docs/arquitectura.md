# arquitectura

Componentes y límites que el código impone. La prosa no sustituye a la función listada.

| Regla | Capa | Función |
| --- | --- | --- |
| Un solo dueño de memoria y estados | arquitectura | `.microharness/sdd.py` (`approve`, `review`, `seal`) |
| Hook fail-closed por `agent_type` | arquitectura | `pretool.run` |
| `sdd.py` / `pretool.py` no se encogen en silencio | estatico | `core_shrink_errors` |
| Alcance quirúrgico vía `git diff` | estatico | `validate` / `diff_files` |
| Recibo de verificación antes del dictamen | verificacion | `record_verification` |
| Telemetría opcional sin esquema nuevo aquí | estatico | `emit` + `metrics.py` |
