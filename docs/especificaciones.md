# especificaciones

Contrato de especificación y cierre. Los AC semánticos los juzga el revisor; los IDs y el recibo los exige el arnés.

| Regla | Capa | Función |
| --- | --- | --- |
| Cuatro archivos por `spec/<slug>/` | estatico | `validate` / `TASK_FILES` |
| Aprobación de spec con huella | verificacion | `approve` + `spec_fingerprint` |
| `check --run` escribe recibo | verificacion | `record_verification` |
| `review APROBADO` exige recibo vigente | verificacion | `review` |
| Cierre exige `APROBADO` + huella de código | verificacion | `approve` fase `close` |
| Tope RDD no negociable en `decision` | estatico | `rdd_diff_line_errors` |
| Nota `rewrite-core` para encoger el núcleo | humano | `note` + `core_shrink_errors` |
