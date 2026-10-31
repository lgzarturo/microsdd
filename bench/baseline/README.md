# Línea base

> **AVISO: este baseline no es evidencia sobre MicroSDD.** Su veredicto `RECHAZA` no compara con y sin arnés. Los datos se conservan solo como registro histórico.
>
> - **Brazos equivalentes (confirmado).** Según `1f3a731`, `treatment` solo copiaba el fixture. En `eb3d43e` (16 celdas, run 39802356050) y `ef3955f` (14 celdas, run 39878723841), `run_bench` llama a `copy_fixture` en ambos brazos y el prompt no depende del brazo.
> - **Señal de éxito no fiable (confirmado).** Las cinco pruebas eran funciones sueltas sin `TestCase`: sin editarlas, `python -m unittest test_fixture` da `Ran 0 tests` y código 5 con Python 3.12, la versión que fija el workflow. Además, las tareas 03, 04 y 05 ya cumplían sus aserciones.
> - **Inferido, no observado.** Las 19 celdas con éxito exigen que el agente alterara algo para que `unittest` recogiera pruebas; los diffs no se conservaron. Un éxito tampoco indica que la lógica se corrigiera.
>
> `complete` significa que terminaron las 30 celdas, no que el resultado sea válido. Solo el gasto sirve, como orden de magnitud.

> **Estado: `complete`.** DeepSeek cheap N=3 completo (30/30). Veredicto: **RECHAZA**.

## Fill + fusión (Arturo 22 oct 19:30 Cancún) — run 39878723841

| Campo | Valor |
|---|---|
| Modelo | `deepseek/deepseek-v4-flash` |
| HEAD fill | `ef3955f` |
| maxTurnsPerCell | 6 |
| Celdas | **30/30** (0 pending) |
| Success | base **11/15** → treatment **8/15** |
| Tokens Δ | **2085.0** IC95 **[-3921.0, 5342.0]** |
| Iterations Δ | **0.0** IC95 **[0.0, 0.0]** |
| Requests fill | **85 / 100** (presupuesto nuevo; prior=0) |
| Gasto real (usage Δ) | **≈ $0.080** ≤ $0.10 (spendOk; approach $0.08) |
| costUsdModelEstimate | ≈ **$7.97** (suma `total_cost_usd` Claude Code; **no** es el candado) |
| Previas | 16 celdas run 39802356050 (candado $0.49; Δ ≈ $0.078) |
| Veredicto | **RECHAZA** (claim efficiency) |

## Archivos

- Resultado final: `bench-report.sanitized.*`, `fill-pending-2026-10-23/`
- Parcial 16/30: `archive-deepseek-cheap-partial-2026-10-22/`
- Sonda OK @6: `probe-maxturns6-ok-2026-10-22/`
- Sonda fallida @3: `archive-deepseek-probe-failed-maxturns3-2026-10-22/`
- gpt-oss / nemotron: archives (no mezclar)
