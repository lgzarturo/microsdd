# Testigo Quirúrgico: seal-monotonico

- **Estado:** `terminado`
- **Criterios de Aceptación cubiertos:** AC-01, AC-02, AC-03, AC-04, AC-05, AC-06, AC-07, AC-08, AC-09, AC-10, AC-11, AC-12, AC-13, AC-14, AC-15, AC-16, AC-17, AC-18, AC-19
- **Iteraciones del Loop:** 1 / 3 (Reintentos ODD: 0)

## 1. Sellos Criptográficos (SHA-256)
- **Spec Fingerprint (Contrato Humano):** `1cb37936da4582482ebb035f8bed82c76af03f73c87f596925228e8b9230e65c`
- **Autorización Inicial:** por `Arturo López` en `2026-10-31T06:33:21+00:00` (@note:n3)
- **Recibo RDD Base (`receipt.digest`):** `ab762906b9daa9499fd81ee83aeb14b3efff243bae1fb0e608c4930ed0d120bd`
- **Sello de Código Final (`code_fingerprint`):** `ac42fb482b951a6a15ff1acc1217030b1b6be7c9667e4497e2bb000bdc2b9567`
- **Cierre:** por `lider` en `2026-10-31T06:38:42+00:00` (Dictamen APROBADO del revisor independiente y puerta check --run revalidada por approve close. D1 y D2 corregidos bajo reaprobación humana n3.)

## 2. Pruebas Selladas (`sealed_tests`)
- `tests/test_sdd.py`: `b4b13412778b84da…`

## 3. Perímetro Quirúrgico Aplicado (`allowed_paths`)
- `.microharness/sdd.py`: `d48d2b0ea9e3` → `cc85cf10c445`
- `assets/arnes-completo.md`: `72de653bacb5` → `18be0e25e553`
- `assets/proceso-versionado.md`: `be5324b51565` → `be5324b51565`
- `tests/test_sdd.py`: `b4b13412778b` → `b4b13412778b`
