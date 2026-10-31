# CÓMO: diseño mínimo

## Situación comprobada
Leído en el árbol actual (versión 1.5.3):
- `seal` en `.microharness/sdd.py` valida rutas, consume la nota en memoria y reemplaza `sealed_tests` completo con `{ruta: sha256}`. Solo escribe con `dump` al final, así que un error previo deja el archivo intacto, nota incluida.
- Consumidores que tratan `sealed_tests` como `{ruta: str}`: `validate` (`hash_file(target) != expected`), `write_witness` (`v[:16]`), `.claude/hooks/pretool.py` (claves) y pruebas de integridad (`test_integridad_memoria`).
- `INTEGRITY_FIELDS` vincula `sealed_tests` al evento `sellado_tests`; `approve spec` no toca los sellos.
- Vías de `maybe_require_human_terminal` para `seal`: `by == 'lider'` con lease íntegro (texto libre); `@note` con `agent_may_approve`; o TTY. El hook deja pasar cualquier `seal` del líder y deniega al resto de roles.
- `consume_note` valida existencia, uso, fase, tarea y edad, y solo muta la memoria en RAM.
- `main` captura `ValueError` pero no `SyntaxError`: hay que convertirlo.
- `sdd.py` tiene una sola copia en el repo. `pyproject.toml` lo empaqueta con `force-include` e `installer.py` lo copia del payload: `src/microsdd/` no requiere cambios.
- `assets/proceso-versionado.md` (API-01) enumera las fases de `note`; `test_api_publica` no fija las fases, pero el documento sí es contrato.

## Decisión y justificación
**Formato: mapa paralelo `tasks.<slug>.sealed_assertions = {ruta: int}`.** `sealed_tests` no cambia, de modo que ningún consumidor cambia y los sellos antiguos siguen siendo válidos sin conversión.

En `.microharness/sdd.py`:
1. `import ast`; añadir `'seal-reduce'` a `NOTE_PHASES`; añadir `(('sealed_assertions',), ('sellado_tests',))` a `INTEGRITY_FIELDS`.
2. `count_assertions(target: Path, relative: str) -> int`: `ast.parse(target.read_bytes())`; convierte `SyntaxError`, `ValueError`, `RecursionError` y `MemoryError` en `ValueError` con la ruta. Recorre con `ast.walk` y aplica la definición de `requerimientos.md`.
3. `assertion_reductions(previous, counts, sealed_paths)` o lógica equivalente en línea: valida `sealed_assertions` (objeto; enteros `>= 0`, excluye `bool`) y devuelve `[{file, previous, current}]`. Solo un helper si deja `seal` más legible.
4. En `seal`: primero calcular hashes y recuentos; después reducciones; después la nota; al final escribir.
   - Con reducciones sin nota: `ValueError` con el formato `Reducción de aserciones: <ruta>: anterior N, actual M; …` más la vía de autorización (`--for-phase seal-reduce`).
   - Con reducciones y nota: `consume_note(..., for_phase='seal-reduce', ...)` sin depender de `agent_may_approve` (en modo estricto la puerta TTY ya pasó). Si la nota falla, relanzar con el texto de reducción y el motivo.
   - Sin reducciones: flujo de nota actual con `for_phase='seal'`.
   - Guardar `sealed_assertions` y, solo si hay reducciones, `assertion_reductions` en el evento.

Las retiradas de `protected_tests` cuentan como reducción con `current: 0` porque si no bastaría con quitar la ruta y resellar.

No se añade `sealed_assertions` a la plantilla de `new`: la ausencia ya significa sello antiguo y `_field` lo trata como `None`.

## Alternativas descartadas
- **`sealed_tests[ruta] = {sha256, assertions}`:** obliga a tratar dos formas en `validate` y `write_witness`, cambia un formato que ya leen pruebas y herramientas, y toca más puntos que el mapa paralelo.
- **Comparar contra `HEAD` en vez de memoria:** falla sin Git y sin commit de la prueba; la memoria ya es la fuente de los sellos.
- **Opción nueva `seal --allow-reduction`:** el líder podría añadirla al comando bajo lease, sin cita humana; amplía API-01 más que una fase.
- **Reutilizar la fase `seal` como autorización:** un `@note` de resellado rutinario autorizaría una reducción que el humano no citó.
- **Comprobar recuentos en `validate`:** redundante; el hash ya detecta cualquier cambio.
- **Dependencias o análisis semántico:** contra D-05 y YAGNI.

## Invariantes
- `sealed_tests` sigue siendo `{ruta: sha256}`; las huellas no cambian.
- Cualquier rechazo deja `memory.json` idéntico byte a byte, nota sin consumir incluida.
- Los tres estados, los roles y las puertas de `maybe_require_human_terminal` no cambian. El orden de esa puerta sigue siendo el primero.
- Reaprobar la spec no reinicia `sealed_assertions`.
- Tareas cerradas: no se migran; `memory_integrity` sigue exigiendo `work == base`.

## Riesgos y efectos secundarios
- **Pruebas existentes con fases o eventos exactos:** ninguna fija `NOTE_PHASES` ni `INTEGRITY_FIELDS` por valor (buscado en `tests/`). Se añaden casos, no se cambian los existentes.
- **Archivo `.py` protegido que no parsea:** antes se sellaba y ahora falla (rompe el sellado de pruebas TDD escritas con errores de sintaxis, lo que es deseado). Pedido expresamente.
- **`SyntaxWarning` en `ast.parse`:** escapes inválidos en la prueba pueden imprimirse en stderr al sellar. No afecta al resultado; no se silencia (KISS).
- **Reducción no comparada en primer sello:** límite documentado.
- **Autoprotección:** el flujo TDD de esta tarea sella `tests/test_sdd.py` con el `seal` anterior (sin recuento), porque las pruebas se sellan antes de implementar. Es un sello antiguo válido por AC-04.
- **Reseal de la propia tarea:** si el implementador necesita corregir `tests/test_sdd.py` tras sellar, el líder debe resellar. Si la corrección reduce aserciones ya registradas, aplica DEC-01.
- **Compatibilidad API:** la fase `seal-reduce` es aditiva. No se cambia `__version__`: lo decide el proceso de versión.
- **`.claude/agents/lider.md` no se toca:** su punto 4 sigue siendo cierto para resellados sin reducción; el mensaje de error de `seal` indica la vía. Si el humano quiere que conste en las reglas del líder, sería una tarea aparte.
- **`docs/` y `assets/decisiones-diseno.md`:** D-09 sigue siendo cierta; no se reescriben.
