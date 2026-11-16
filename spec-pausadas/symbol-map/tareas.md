# PASOS: trabajo verificable

Estrategia `tdd`. Pruebas en un archivo nuevo, `tests/test_symbols.py`, creado con un solo `Write`, con raíz temporal, `GIT_CEILING_DIRECTORIES` como en `FitnessTests`, tablas y `subTest`.

**Topes: `tests/test_symbols.py` 200 líneas; `.microharness/sdd.py` 120 líneas añadidas; total 350.** Detente y reporta al líder, sin fragmentar ediciones ni recortar pruebas por tu cuenta, si superas un tope o si el hook rechaza por `rdd_max_lines`, por el recibo o por cualquier otra causa.

Requisito previo: DEC-01 y DEC-02 confirmadas. Interfaz para las pruebas: `sdd.symbols_of(data, relative)`, `sdd.symbols(paths)` y `sdd.main()`, definidas en `plan.md`.

## RED: pruebas en `tests/test_symbols.py`
- [ ] T01 (AC-01, AC-02, AC-03): crear el archivo con la carga de `sdd` y del hook, `setUp` y auxiliares, y los métodos `test_firmas`, `test_contenido_exacto` y `test_docstrings_y_omisiones`, por tabla, y los métodos de T02 a T05 en la misma escritura.
- [ ] T02 (AC-04, AC-05): `test_seleccion_con_git` y `test_seleccion_sin_git`, este último con filas sin repositorio y con `FileNotFoundError` simulado.
- [ ] T03 (AC-06, AC-07): `test_exclusiones_relativas`, por tabla y en ambos modos, con raíz en `<tmp>/tests/repo`, y `test_rutas`, vía `main()` para los códigos de salida.
- [ ] T04 (AC-08, AC-09, AC-10): `test_no_analizables`, `test_determinista` y `test_solo_lectura`, con una instantánea de rutas y contenido.
- [ ] T05 (AC-11, AC-12): `test_proceso_real`, con subproceso sobre este repositorio, y `test_hook`, por tabla.
- [ ] T06 (AC-01..AC-12): ejecutar `sh .microharness/python.sh -m unittest tests.test_symbols`; comprobar que los 12 métodos fallan por falta de comportamiento y no por errores de la prueba, y que el archivo no pasa de 200 líneas. El líder sella `tests/test_symbols.py` antes de continuar.

## GREEN: implementación en `.microharness/sdd.py`
- [ ] T07 (AC-01, AC-02, AC-03): añadir `_symbol_doc`, `_symbol_callable`, `_symbol_class` y `symbols_of`; `test_firmas`, `test_contenido_exacto` y `test_docstrings_y_omisiones` en verde.
- [ ] T08 (AC-04, AC-05, AC-06, AC-09): añadir las constantes, `_symbol_excluded`, `_symbol_listing` y `symbols`; `test_seleccion_con_git`, `test_seleccion_sin_git`, `test_exclusiones_relativas` y `test_determinista` en verde.
- [ ] T09 (AC-07, AC-08, AC-10, AC-11): registrar `symbols` en `main`; `test_rutas`, `test_no_analizables`, `test_solo_lectura` y `test_proceso_real` en verde.
- [ ] T10 (AC-13): comprobar con `git diff` que no hay imports nuevos ni cambio de `__version__`, y que las funciones nuevas no mencionan memoria, lock ni `emit`.

## Hook: paso humano
- [ ] T11 (AC-12): **detente.** Pide al líder que el humano aplique en su editor, fuera de Claude Code, las dos líneas de `plan.md` («Parche del hook») en `.claude/hooks/pretool.py`. Ningún agente puede hacerlo ni debe intentarlo por otra vía. Después, `test_hook` en verde.

## Documentación
- [ ] T12 (AC-14): en `assets/proceso-versionado.md`, añadir `symbols [ruta ...]` como experimental a API-01, añadir `symbols` a la lista de API-05 y añadir «el formato JSON de la salida de `symbols`, experimental» a «No forman parte de la API pública».
- [ ] T13 (AC-14): en `assets/arnes-completo.md`, añadir `symbols` a la lista de subcomandos permitidos de «Bloqueo de autoaprobación».
- [ ] T14 (AC-14): en `assets/arnes-completo.md`, añadir una subsección «Mapa de símbolos (`symbols`, experimental)» tras «Fitness estructural», con uso, selección de archivos, formato, límites conocidos (`plan.md`, Riesgos), la frase de que no hay medición de beneficio y de que integrarlo en el flujo es una decisión posterior sobre datos. Sin cifras.

## Verificación
- [ ] T15 (AC-13, AC-14): comprobar con `git diff --stat` que solo cambian las cinco rutas de `allowed_paths`, y que los topes se respetan; `tests/test_api_publica.py` en verde sin cambios.
- [ ] T16 (AC-01..AC-15): ejecutar `sh .microharness/python.sh .microharness/sdd.py check symbol-map --run`; salida `OK` con al menos 502 pruebas. No ejecutar el bench.
