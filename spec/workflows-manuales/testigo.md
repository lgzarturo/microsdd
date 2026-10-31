# Testigo Quirúrgico: workflows-manuales

- **Estado:** `terminado`
- **Criterios de Aceptación cubiertos:** AC-01, AC-02, AC-03, AC-04, AC-05, AC-06, AC-07
- **Iteraciones del Loop:** 1 / 3 (Reintentos ODD: 0)

## 1. Sellos Criptográficos (SHA-256)
- **Spec Fingerprint (Contrato Humano):** `7b7148c87c048e934f35198833d12dc9d8da52285b83b91495efc82151ef1f87`
- **Autorización Inicial:** por `Arturo López` en `2026-10-31T05:33:02+00:00` (@note:n1)
- **Recibo RDD Base (`receipt.digest`):** `de7ee2d97e7cbcde07f8660529c8b4e680524be3639cbfe58afc6d4ea2d5aee0`
- **Sello de Código Final (`code_fingerprint`):** `dc6abb90fe304cb532fe181f78dc72f710dd308b4ea0f06eaf96e07f6e444cdb`
- **Cierre:** por `lider` en `2026-10-31T05:41:30+00:00` (Dictamen APROBADO y check --run verde: 434 pruebas OK, 4 omitidas. AC-01, AC-02, AC-03 y AC-05 con salida literal del implementador, no del revisor.)

## 2. Pruebas Selladas (`sealed_tests`)
- (sin tests protegidos declarados)

## 3. Perímetro Quirúrgico Aplicado (`allowed_paths`)
- `.github/workflows/bench-baseline.yml`: `54c8de373dd3` → `ae4893358fa2`
- `.github/workflows/tests.yml`: `b7476a14bcda` → `442a12894304`
- `assets/arnes-completo.md`: `91f8746968c6` → `03cec706c383`
