# arquitectura

- Hook `pretool.py`: `deny_or_allow_gated` exige `agent_type == lider` además de `agent_may_approve` y `--evidence @note:<id>` para `approve`/`seal`/`allow-test-command`. Fail closed si el rol falta o es desconocido.
- `sdd.py` valida TTL (≤30 min) y un solo uso de la nota; no valida rol (la puerta de rol es el hook).
