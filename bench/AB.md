# A/B CON vs SIN arnés (T-034)

```bash
# Dry-run (sin red ni requests): verifica que treatment carga el arnés y base no
python .microharness/metrics.py bench dry-run
# o: python .microharness/metrics.py bench ab --provider deepseek --dry-run

# Corrida real (Arturo): ambos brazos, N=5, intercalado; reporte fuera del repo
export OPENROUTER_API_KEY=…   # nunca en archivos/PR
python .microharness/metrics.py bench ab --provider deepseek --out ~/.cache/microsdd-ab
# :free → --provider free (tope 500). DeepSeek → tope 300. RPM 20 (espera).
```

Qué hace: 5 tareas × 2 brazos × 5 reps; treatment instala microsdd en el temp; base solo fixture. maxTurns≥6. Al tope: 403, exit≠0, reporte `tope alcanzado`. `--dangerously-skip-permissions` solo en el temp de la corrida.
