# especificaciones

| Regla | Capa | Función |
| --- | --- | --- |
| Recibo de check --run antes de review APROBADO | verificacion | record_verification / review |
| Pases reales (unittest sin solo skipped) | estatico | tests_ran / unittest_counts |
| Encogimiento del núcleo > 100 líneas netas | estatico | core_shrink_errors |
| Tope RDD por diff de alcance | estatico | rdd_diff_line_errors |
| Versión mezclada con cambio de función | estatico | version_mix_errors |
| docs/ sin placeholder | estatico | docs_placeholder_errors |
