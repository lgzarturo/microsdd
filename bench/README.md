# Bench microsdd (m2)

Suite fija de 5 tareas (`tareas/`) tomadas de `assets/eval-esfuerzo.md`, con specs congeladas y fixtures mínimas.

```bash
# Prueba determinista (sin modelos ni key)
python .microharness/metrics.py bench run --provider fake --out /tmp/microsdd-bench
python .microharness/metrics.py bench run --cheap --provider fake --out /tmp/microsdd-bench-cheap
python .microharness/metrics.py bench report --from /tmp/microsdd-bench
python .microharness/metrics.py prompt-diff . /otra/copia
```

Resultados: fuera del repo (estado XDG/LOCALAPPDATA o `--out`). Nunca en `docs/` ni `spec/`.
