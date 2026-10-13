# CÓMO: diseño mínimo

## Situación comprobada
- `.microharness/sdd.py`, `validate()`, rama `else` tras comprobar la memoria: el bucle `for file, expected in task_memory.get('sealed_tests', {}).items():` se ejecuta para cualquier estado.
- El sello de una tarea cerrada sigue comparándose contra el árbol actual, así que toda modificación legítima posterior de un archivo compartido (p. ej. `tests/test_sdd.py`) rompe el `check` de la tarea cerrada. Reproducido: `check deteccion-python-multiplataforma --no-scope` → `ERROR: Test sellado modificado: tests/test_sdd.py`, código 1.
- La puerta de cierre (`approve(..., 'close')`) solo opera con `state == 'proceso'` y llama a `validate(slug, run=True)`; el sello se verifica justo antes de pasar a `terminado`.

## Decisión y justificación
Envolver el bucle existente con una única condición sobre el estado:

```python
if s.get('state') != 'terminado':
    for file, expected in task_memory.get('sealed_tests', {}).items():
        ...  # cuerpo actual sin cambios
```

- Condición «distinto de `terminado`» y no «igual a `proceso`»: una tarea escalada a `pendiente` por agotar `max_iterations` conserva su baseline sellado; al reanudarse (nueva aprobación de spec) debe seguir protegida. Si se usara `== 'proceso'`, en `pendiente` se podrían alterar las pruebas selladas sin que `check` lo advirtiera y el cambio pasaría desapercibido hasta la reanudación. Con `!= 'terminado'`, solo el estado final, al que se llega tras pasar la puerta de cierre con el sello verificado, deja de comparar.
- `terminado` es irreversible en el flujo (`approve spec` rechaza tareas terminadas), así que no hay riesgo de reabrir una tarea con un sello que ya no se compara.
- Los sellos no se tocan: quedan en `memory.json` como registro histórico del baseline aprobado.
- README sección 6: la frase actual «`check` detecta cambios» quedaría imprecisa. Se añade una frase (AC-06) para que la documentación refleje la conducta real. Coste: una línea; beneficio: evitar que alguien interprete como fallo que una tarea cerrada no avise.

## Alternativas descartadas
- `state == 'proceso'`: deja sin protección a tareas escaladas a `pendiente` (ver arriba).
- Resellar o borrar el sello de la tarea cerrada al modificar el archivo: altera la memoria histórica y lo prohíbe el programador.
- Sellar por prueba/función en vez de por archivo: más complejo, no solicitado (YAGNI).
- Ignorar sellos solo con `--no-scope`: mezcla dos conceptos (alcance de diff y sello) y no resuelve el `check` con alcance.

## Invariantes y riesgos
- Invariante: en `pendiente` y `proceso` la conducta de `sealed_tests` es idéntica a la actual (mismo mensaje, mismo caso de archivo ausente, mismo `ValueError` de ruta).
- Invariante: aprobaciones, huella de spec, alcance y ejecución de `validate` no cambian; `memory.json` no se escribe desde `validate`.
- Riesgo: tras el cierre, una modificación deliberada de pruebas selladas ya no se detecta por `check` de esa tarea. Mitigación: era el comportamiento deseado por el programador; el baseline sigue en memoria y Git, y las tareas posteriores que toquen el archivo pasan por su propia spec, revisión y aprobación.
- Riesgo: `state` ausente o inválido → la condición evalúa verdadera y se compara el sello (falla cerrado); además ya se reporta «Estado fuera de la máquina de tres estados».
- Efecto secundario esperado: `check deteccion-python-multiplataforma` vuelve a pasar sin tocar su sello.
