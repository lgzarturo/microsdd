# PASOS: trabajo verificable

Estrategia `tdd`. Pruebas en una clase nueva de `tests/test_sdd.py`, con la raíz temporal de `MicroSDDTests` o equivalente. Las pruebas nuevas fallan hasta implementar: confirma ese fallo con el comando de T07.

## RED: pruebas
- [ ] T01 (AC-01, AC-02): en `tests/test_sdd.py`, pruebas de recuento con el contenido literal de AC-01 (5), archivo vacío (0) y función auxiliar sin invocar (1).
- [ ] T02 (AC-03, AC-17): pruebas de archivo que no parsea vía `main()` (`def (:` y `b'\xff\xfe\n'`, stderr con `ERROR:`, retorno 1, memoria intacta) y de archivo `.txt` por hash, `sealed_assertions == {}`, resellable.
- [ ] T03 (AC-04, AC-09): pruebas de sello antiguo sin recuento y de resellado sin reducción (igual y mayor, y fallo posterior al bajar de la nueva base).
- [ ] T04 (AC-05, AC-06, AC-07, AC-08): pruebas de rechazo por TTY con texto (`main()`), lease sin TTY, dos archivos reducidos, ruta retirada con recuento 2 y con recuento 0. Todas comparan bytes de `memory.json`.
- [ ] T05 (AC-10, AC-11, AC-12, AC-13): pruebas de nota `seal-reduce` válida (recuentos, `used_at`, `assertion_reductions`), ruta retirada con nota, nota incorrecta (fase `seal`, otra tarea, consumida, inexistente) sin consumo, y `seal-reduce` sin reducción.
- [ ] T06 (AC-14, AC-15, AC-16): pruebas de `sealed_assertions` malformado (`'2'`, `True`, `-1`, `[]`), de integridad frente a `HEAD` (con `git_repo`, con y sin evento, y tarea confirmada sin el campo) y de conservación tras reaprobar la spec.
- [ ] T07 (AC-01..AC-17): ejecutar `sh .microharness/python.sh -m unittest tests.test_sdd`; comprobar que solo fallan las pruebas nuevas. El líder sella `tests/test_sdd.py` antes de continuar.

## GREEN: implementación en `.microharness/sdd.py`
- [ ] T08 (AC-18): añadir `'seal-reduce'` a `NOTE_PHASES`; comprobar que la CLI lo admite.
- [ ] T09 (AC-15): añadir `sealed_assertions` a `INTEGRITY_FIELDS` con `sellado_tests`.
- [ ] T10 (AC-01, AC-02, AC-03, AC-19): añadir `import ast` y `count_assertions`, convirtiendo errores de análisis en `ValueError` con la ruta.
- [ ] T11 (AC-01, AC-04, AC-17): en `seal`, calcular recuentos de archivos Python y guardar `sealed_assertions`.
- [ ] T12 (AC-05, AC-06, AC-07, AC-08, AC-09, AC-14): en `seal`, validar el mapa previo, calcular reducciones y rechazar sin nota antes de cualquier escritura.
- [ ] T13 (AC-10, AC-11, AC-12, AC-13): en `seal`, elegir la fase de nota según haya reducciones, combinar el mensaje de error y añadir `assertion_reductions` al evento.
- [ ] T14 (AC-16): sin cambio de código en `approve`; comprobar que la prueba pasa.
- [ ] T15 (AC-01..AC-17): ejecutar `sh .microharness/python.sh -m unittest tests.test_sdd`; todo en verde.

## Documentación
- [ ] T16 (AC-18): en `assets/arnes-completo.md`, ajustar el párrafo de `seal` (ya no «sobrescribe sin control»), la lista de fases de `agent_may_approve`, la fila de integridad (`sealed_assertions`) y añadir qué cuenta, la vía `seal-reduce` y los límites conocidos.
- [ ] T17 (AC-18): en `assets/proceso-versionado.md`, añadir `seal-reduce` a las fases de API-01.

## Verificación
- [ ] T18 (AC-19): ejecutar `sh .microharness/python.sh .microharness/sdd.py check seal-monotonico --run`; salida `OK` con más de 434 pruebas.
