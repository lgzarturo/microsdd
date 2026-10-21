# Testigo Quirúrgico: release-v1-5-0

- **Estado:** `terminado`
- **Criterios de Aceptación cubiertos:** AC-01, AC-02, AC-03, AC-04
- **Iteraciones del Loop:** 1 / 3 (Reintentos ODD: 0)

## 1. Sellos Criptográficos (SHA-256)
- **Spec Fingerprint (Contrato Humano):** `874871ed3c79a8346604ec4e8873f3a15bdbaa037bf3430121a714fc85b8abb4`
- **Autorización Inicial:** por `Arturo López` en `2026-10-21T02:57:46+00:00` (@note:n2)
- **Recibo RDD Base (`receipt.digest`):** `bc3fe58a65d616c2fe941a1b2ab98dbee8a09d45d49c369d4ecdd6127212f51f`
- **Sello de Código Final (`code_fingerprint`):** `bea5df6d3f2d127f40ebd1ba14a3892c077c11aac586327889a2b271a99710d3`
- **Cierre:** por `lider` en `2026-10-21T03:00:37+00:00` (Release 1.5.0 verificado: versión, changelog y suite en verde)

## 2. Pruebas Selladas (`sealed_tests`)
- (sin tests protegidos declarados)

## 3. Perímetro Quirúrgico Aplicado (`allowed_paths`)
- `.microharness/sdd.py`: `04ac8c7690b7` → `04ac8c7690b7`
- `CHANGELOG.md`: `ca2ff864148c` → `ca2ff864148c`
- `pyproject.toml`: `7edc019acc84` → `7edc019acc84`
- `tests/test_model_profiles.py`: `cdaa42cd6785` → `1e05d6261813`
- `tests/test_sdd.py`: `3ff0f7ca4ed0` → `1267e74cd2e1`
