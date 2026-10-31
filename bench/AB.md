# A/B CON vs SIN arnés (T-034)

```bash
python .microharness/metrics.py bench dry-run --provider deepseek --model deepseek/deepseek-v4-flash
export OPENROUTER_API_KEY=…   # o DEEPSEEK_API_KEY; nunca en archivos/PR
python .microharness/metrics.py bench ab --provider deepseek --out ~/.cache/microsdd-ab
```

Presupuesto (N=5×5 tareas×2 brazos=50 celdas; margen bajo el tope):
- free: maxTurns=6 → 50×6=300 < 500 (margen 200)
- deepseek: maxTurns=5 → 50×5=250 < 300 (margen 50; evita 50×6=300 exacto)
Si el proxy alcanza el tope (extras/small-fast), corta y marca el resto `pending` / `tope alcanzado`. RPM 20 (espera). Mismo `--model` en ambos brazos (treatment reescribe settings.model). `--dangerously-skip-permissions` solo en el temp.
