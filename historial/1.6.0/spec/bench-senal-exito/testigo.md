# Testigo Quirúrgico: bench-senal-exito

- **Estado:** `terminado`
- **Criterios de Aceptación cubiertos:** AC-01, AC-02, AC-03, AC-04, AC-05, AC-06, AC-07, AC-08, AC-09, AC-10, AC-11
- **Iteraciones del Loop:** 2 / 3 (Reintentos ODD: 0)

## 1. Sellos Criptográficos (SHA-256)
- **Spec Fingerprint (Contrato Humano):** `5081ea9bc003da05b3ba923eaa92dfb827750149d63aa9bc71fda7df25558473`
- **Autorización Inicial:** por `Arturo López` en `2026-10-31T13:11:10+00:00` (@note:n5)
- **Recibo RDD Base (`receipt.digest`):** `c9a404b22171d478833e24639b83be9d8b39c3f30c4b8d912479b3969c21c51c`
- **Sello de Código Final (`code_fingerprint`):** `cd6000c9e4de02a75fc5c032e47bb14b26ddfa61b993fb90efafff2eaeab1753`
- **Cierre:** por `lider` en `2026-10-31T13:50:56+00:00` (Dictamen APROBADO del revisor independiente tras corregir D1, D2 y D3 con autorización humana, y puerta check --run revalidada por approve close.)

## 2. Pruebas Selladas (`sealed_tests`)
- `tests/test_bench_senal.py`: `a1100c45db3f0e58…`

## 3. Perímetro Quirúrgico Aplicado (`allowed_paths`)
- `.microharness/bench.py`: `94cbe324b4f4` → `3b6b7880f956`
- `assets/eval-esfuerzo.md`: `cee78ddcfe21` → `bbf73400d45b`
- `bench/README.md`: `d9fd384589d3` → `bc174cf5e8f4`
- `bench/baseline/README.md`: `5dbfb67c9594` → `7ddf975b867c`
- `bench/config.json`: `5be6ce3beefa` → `c167bf77a40b`
- `bench/tareas/01-correccion-localizada/fixture/test_fixture.py`: `68cb0b14ac8d` → `a93a0c48fede`
- `bench/tareas/01-correccion-localizada/task.json`: `bb10b7605bfa` → `7820e05072b0`
- `bench/tareas/02-regla-nueva/fixture/test_fixture.py`: `b09a7b726e4a` → `6e2c14834c6f`
- `bench/tareas/02-regla-nueva/task.json`: `863b45f1b7d0` → `ae7565238885`
- `bench/tareas/03-refactor/fixture/test_fixture.py`: `343638d3e19a` → `be40f78b550d`
- `bench/tareas/03-refactor/task.json`: `12bb39fd2ba8` → `330fc4087d13`
- `bench/tareas/04-config-docs/fixture/fixture_mod.py`: `eb0d0622e4a7` → `80a4f4f668f3`
- `bench/tareas/04-config-docs/fixture/test_fixture.py`: `dc66f92b1d96` → `0458549d0f5e`
- `bench/tareas/04-config-docs/task.json`: `566ba8f4f5a4` → `60b35d989368`
- `bench/tareas/05-prueba-regresion/fixture/fixture_mod.py`: `d2eeac529fc1` → `fd4d1d91fccf`
- `bench/tareas/05-prueba-regresion/fixture/test_fixture.py`: `f29f479d689a` → `2e3ade506d82`
- `bench/tareas/05-prueba-regresion/task.json`: `7760d992a3db` → `576f77bc5d0b`
- `tests/test_bench.py`: `52eb798442b4` → `7201276b149f`
- `tests/test_bench_senal.py`: `new` → `a1100c45db3f`
