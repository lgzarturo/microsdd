# AGENT

Tabla de reglas del arnés con la función que las hace fallar. Sin fila inventada: cada una nombra código existente.

| Regla | Capa | Función |
| --- | --- | --- |
| Recibo de `check --run` antes de `review APROBADO` | verificacion | `record_verification` / `review` |
| Pases reales (unittest no cuenta solo skipped) | estatico | `tests_ran` / `unittest_counts` |
| Encogimiento del núcleo > 100 líneas netas | estatico | `core_shrink_errors` |
| Tope RDD por líneas añadidas de alcance | estatico | `rdd_diff_line_errors` |
| `__version__` mezclado con cambio de función | estatico | `version_mix_errors` |
| `docs/` sin placeholder | estatico | `docs_placeholder_errors` |
| Router de corrección (solo lectura) | verificacion | `cmd_correct` / `cmd_corrections` |
| Roles y rutas de edición | arquitectura | `.claude/hooks/pretool.py` `run` |
| Sello monotónico de aserciones | estatico | `seal` / `count_assertions` |
