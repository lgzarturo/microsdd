# Línea base

> **Estado: pendiente (matriz DeepSeek).** gpt-oss-20b cheap-partial archivado en
> `archive-gpt-oss-20b-cheap-partial-2026-10-22/` — **no comparable**.

## Baseline DeepSeek (22 oct 2026, 9:51 Cancún)

| Campo | Valor |
|---|---|
| Modelo | `deepseek/deepseek-v4-flash` |
| Precio | ~$0.091 / $0.182 por 1M (prompt/completion) |
| Tope HTTP | **100 nuevos** (contador reiniciado; documentado) |
| Candado | gasto máx. **$0.49**/repo (usage Δ; fail-closed) |
| Sonda | 1 celda `01-correccion-localizada` / `base`; sin éxito → no matriz |
| Matriz | N=3 balanceado si sonda OK |
| Proxy | `0755fde+` (solo POST mensajes; rpm espera/cola) |

Ver `request-estimate.md`.
