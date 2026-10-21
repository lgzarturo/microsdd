# Testigo Quirúrgico: release-v1-5-3

- **Estado:** `terminado`
- **Criterios de Aceptación cubiertos:** AC-01, AC-02, AC-03, AC-04
- **Iteraciones del Loop:** 1 / 3 (Reintentos ODD: 0)

## 1. Sellos Criptográficos (SHA-256)
- **Spec Fingerprint (Contrato Humano):** `651ce83944ca9186fe620d19f5dd359f27b5d3b16752a44cd2b4de2063208cac`
- **Autorización Inicial:** por `Arturo López` en `2026-10-21T04:15:09+00:00` (@note:n1)
- **Recibo RDD Base (`receipt.digest`):** `42c055e56a02c167e51f28411629faf3c63ce800aea3e34af9ec7696a3059cc8`
- **Sello de Código Final (`code_fingerprint`):** `ea4b77d3163f637d6719623d934a37c43e66e2fc5e9b5b96824368096c2d9c63`
- **Cierre:** por `lider` en `2026-10-21T04:16:02+00:00` (Release 1.5.3 verificado: versión, changelog, uv.lock y suite en verde)

## 2. Pruebas Selladas (`sealed_tests`)
- (sin tests protegidos declarados)

## 3. Perímetro Quirúrgico Aplicado (`allowed_paths`)
- `.microharness/metrics.py`: `1b80f08ecc49` → `1b3e5de5ee8a`
- `.microharness/sdd.py`: `30775eef8f9a` → `da8124feb71b`
- `CHANGELOG.md`: `45e450eeae5d` → `cecc73388513`
- `pyproject.toml`: `29f9cac81898` → `8c914d89a49c`
- `tests/test_model_profiles.py`: `126456d14f44` → `8d56bc6e5a48`
- `tests/test_sdd.py`: `a3bb93a8615b` → `2427c4547503`
- `uv.lock`: `0f7e759bbeba` → `bb20453791d3`
