# Testigo Quirúrgico: release-v1-5-1

- **Estado:** `terminado`
- **Criterios de Aceptación cubiertos:** AC-01, AC-02, AC-03, AC-04
- **Iteraciones del Loop:** 1 / 3 (Reintentos ODD: 0)

## 1. Sellos Criptográficos (SHA-256)
- **Spec Fingerprint (Contrato Humano):** `1f3204c2c5eba5c8438936b62a739b098e09bcc5aab024e0ecbcbe606ef9b207`
- **Autorización Inicial:** por `Arturo López` en `2026-10-21T03:12:34+00:00` (@note:n1)
- **Recibo RDD Base (`receipt.digest`):** `f5e587873a22c69ea14a8a579a88568cb7de7e5537255a419f2bd96c064b7a8a`
- **Sello de Código Final (`code_fingerprint`):** `ea7eaaa295a9caede292c73a65f578e3b8323d027b383b943ba7810caf8620b1`
- **Cierre:** por `lider` en `2026-10-21T03:14:31+00:00` (Release 1.5.1 verificado: versión, changelog y suite en verde)

## 2. Pruebas Selladas (`sealed_tests`)
- (sin tests protegidos declarados)

## 3. Perímetro Quirúrgico Aplicado (`allowed_paths`)
- `.microharness/metrics.py`: `fcbad6f6cc07` → `1b80f08ecc49`
- `.microharness/sdd.py`: `04ac8c7690b7` → `30775eef8f9a`
- `CHANGELOG.md`: `ca2ff864148c` → `45e450eeae5d`
- `pyproject.toml`: `7edc019acc84` → `29f9cac81898`
- `tests/test_metrics.py`: `965b8b2c3850` → `1316bbd321de`
- `tests/test_model_profiles.py`: `1e05d6261813` → `126456d14f44`
- `tests/test_sdd.py`: `1267e74cd2e1` → `a3bb93a8615b`
