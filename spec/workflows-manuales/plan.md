# CÓMO: diseño mínimo

## Situación comprobada
- `.github/workflows/tests.yml:4-7`: `on:` con `push: branches: [main]` y `pull_request:`.
- `.github/workflows/bench-baseline.yml:9-13`: `on:` con `workflow_dispatch:` y `push: branches: [bench/baseline-m2-run]`. Su línea 2 de comentario menciona ese push.
- `assets/arnes-completo.md:7` describe la suite como ejecutada en push a `main` y en PR.
- `assets/ci-matrix-windows.yml` conserva los disparadores automáticos, pero está fuera de `.github/workflows/` y GitHub no la ejecuta.
- Sin badges ni pruebas que dependan de los disparadores (`git grep`).
- `dependencies = []` en `pyproject.toml`; PyYAML está en el entorno local, no en el proyecto.

## Supuestos no verificables desde el repositorio
- Si `main` tiene protección de rama con checks requeridos.
- Si la rama remota `bench/baseline-m2-run` existe; no aparece entre las refs locales conocidas.

## Decisión y justificación
Dejar en ambos archivos exactamente:

```yaml
on:
  workflow_dispatch:
```

y corregir las dos frases que el cambio vuelve falsas:

- `bench-baseline.yml:2`: `# Solo workflow_dispatch.`
- `assets/arnes-completo.md:7`: sustituir "ejecuta la suite en push a `main` y en pull requests (Python 3.12)" por "ejecuta la suite solo por activación manual (`workflow_dispatch`; Python 3.12)". El resto de la línea no cambia.

KISS/YAGNI: sin `inputs`, sin pruebas nuevas ni dependencias. La definición se verifica con comandos de una línea.

`testing.commands` usa la suite existente como regresión, porque `check --run` exige un recuento de pruebas y rechaza `python -c`. Los comandos de parseo y grep de los AC los ejecutan a mano implementador y revisor.

## Alternativas descartadas
- **Eliminar los workflows o moverlos:** impide la activación manual pedida.
- **Condición `if:` en los jobs:** los eventos seguirían iniciando corridas omitidas y tocaría los jobs.
- **Deshabilitarlos en la interfaz de GitHub:** no queda en el repositorio e impediría también lanzarlos a mano.
- **Actualizar `assets/ci-matrix-windows.yml`:** la solicitud cubre los workflows, y la plantilla no se ejecuta. Se declara como límite.
- **Prueba unitaria sobre los YAML:** añadiría una dependencia de PyYAML o un parser ad hoc para un cambio de una sola vez.

## Invariantes
- `jobs:`, `env:`, `permissions:` y `name:` idénticos en ambos workflows.
- Los comentarios de `tests.yml` no cambian.
- Solo cambian los tres archivos de `scope.allowed_paths`.

## Riesgos y efectos secundarios
- **R-01:** los PR y push dejan de ejecutar pruebas en CI, salvo lanzamiento manual. Puede integrarse código sin verificar en Windows, plataforma con un fallo reciente detectado solo en CI (`CHANGELOG.md`, 1.5.3). Es consecuencia aceptada por la solicitud; mitigación: lanzarlo a mano antes de fusionar.
- **R-02:** con checks requeridos en la protección de rama, los PR podrían quedar bloqueados. No verificable desde el repositorio; lo comprueba el programador.
- **R-03:** copiar `assets/ci-matrix-windows.yml` sobre `tests.yml` restaura los disparadores automáticos.
- **R-04:** una ref sin este cambio conserva su definición antigua: no se puede lanzar `tests` a mano sobre ella, y los push a una rama `bench/baseline-m2-run` antigua seguirían disparando la corrida.
- **R-05:** el token que publique el cambio necesita el permiso `workflow`.
- **R-06:** `bench-baseline` no queda útil a mano con el informe actual: su paso de configuración exige 14 celdas pendientes y `bench/baseline/bench-report.sanitized.json` no tiene ninguna (`"pending": true` aparece 0 veces), así que fallaría antes de lanzar la corrida. Es comportamiento preexistente del job y queda fuera de alcance. Con celdas pendientes, una corrida consumiría crédito de OpenRouter.
