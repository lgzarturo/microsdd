# QUÉ: requisitos

## Objetivo
Solicitud literal del programador: "debes detener la ejecucion automatica con el commit de los wokflows de github, debe ser activacion manual".

Los dos workflows de GitHub Actions del repositorio solo deben ejecutarse por activación manual (`workflow_dispatch`). Un commit, un push o un pull request ya no deben iniciarlos.

## Precondiciones
- PRE-01: rama `main`, HEAD `17dab04`. Los comandos de los AC comparan contra ese commit.
- PRE-02: `.github/workflows/` contiene solo `tests.yml` y `bench-baseline.yml`.
- PRE-03: `tests.yml` tiene `push: branches: [main]` y `pull_request:`, sin `workflow_dispatch`. `bench-baseline.yml` tiene `workflow_dispatch:` y `push: branches: [bench/baseline-m2-run]`.
- PRE-04: PyYAML disponible para AC-01 y AC-02 (comprobado: 6.0.3 en el entorno local). No es dependencia del proyecto; si falta, AC-03 cubre los disparadores por grep y se declara que no se parseó el YAML.

## Requisitos EARS
- REQ-01: IF se produce un push a cualquier rama actualizada con este cambio o se abre o actualiza un pull request, THEN los workflows `tests` y `bench-baseline` SHALL NOT iniciarse.
- REQ-02: WHEN una persona lanza manualmente `tests` o `bench-baseline`, sobre una ref que contenga este cambio, THE workflow SHALL ejecutar sus jobs tal como están definidos hoy.
- REQ-03: THE documentación de referencia SHALL describir `tests.yml` como de activación manual, y el comentario de cabecera de `bench-baseline.yml` SHALL dejar de mencionar el push como disparador.

## Criterios de aceptación
Todos se ejecutan desde la raíz del repositorio.

- AC-01 (REQ-01, REQ-02): `python -c "import yaml; print(yaml.safe_load(open('.github/workflows/tests.yml', encoding='utf-8'))[True])"` imprime exactamente `{'workflow_dispatch': None}`. La clave es `True` porque PyYAML interpreta `on` como booleano (YAML 1.1).
- AC-02 (REQ-01, REQ-02): el mismo comando sobre `.github/workflows/bench-baseline.yml` imprime exactamente `{'workflow_dispatch': None}`.
- AC-03 (REQ-01): `git grep -n -E "^[[:space:]]*(push|pull_request|pull_request_target|schedule|workflow_run):" -- .github/workflows` no imprime nada y termina con código 1.
- AC-04 (REQ-02): `git diff --numstat 17dab04 -- .github/workflows assets/arnes-completo.md` muestra exactamente `1 3` para `tests.yml`, `1 4` para `bench-baseline.yml` y `1 1` para `arnes-completo.md`. `git diff 17dab04 -- .github/workflows` solo toca el bloque `on:` y la línea 2 de comentario de `bench-baseline.yml`; ninguna línea de `jobs:`, `env:` ni `permissions:`.
- AC-05 (REQ-03): `git grep -n -F "ejecuta la suite en push" -- assets/arnes-completo.md` y `git grep -n -F "o push a bench/baseline-m2-run" -- .github/workflows` no imprimen nada; `git grep -n -F "workflow_dispatch" -- assets/arnes-completo.md` encuentra la línea `**CI:**`.
- AC-06 (regresión): `python -m unittest discover -s tests` termina en verde y sin cambios en las pruebas.
- AC-07 (alcance): `git status --short` no muestra archivos modificados por esta tarea fuera de `scope.allowed_paths`.

## Impacto
- **Pruebas en CI:** los PR y los push dejan de ejecutar pruebas en CI, salvo que alguien lance el workflow a mano. Un PR puede fusionarse sin ninguna verificación de CI en Ubuntu ni Windows si nadie la lanza; la única red automática restante es la local (`sdd.py check --run`).
- **Protección de rama:** si `main` exige checks requeridos, los PR podrían quedar bloqueados esperando un check que no se inicia. No es verificable desde el repositorio.
- **Bench:** un push a `bench/baseline-m2-run` deja de lanzar la corrida, que consume crédito de OpenRouter.
- **Documentación:** `assets/arnes-completo.md:7` afirma que la suite corre en push a `main` y en PR; quedaría falso y se corrige en esta tarea.

## Dependencias revisadas con `git grep`
- Sin badges de estado ni enlaces a `actions/workflows` en el repositorio.
- Ninguna prueba de `tests/` lee estos workflows ni sus disparadores.
- `README.md:35` dice "CI: `.github/workflows/tests.yml` (unittest en Ubuntu y Windows)": sigue siendo cierto, no se cambia.
- `assets/ci-matrix-windows.yml`: plantilla "Copiar a `.github/workflows/tests.yml`" con los disparadores automáticos. Ver límites.
- `CHANGELOG.md` e `historial/`: registro histórico, no se reescriben.

## Fuera de alcance y límites
- Cambios en jobs, pasos, `env`, `permissions`, runners o versiones de acciones. Tampoco se agregan `inputs` a `workflow_dispatch`.
- `assets/ci-matrix-windows.yml` no se modifica: GitHub no la ejecuta, pero si alguien vuelve a copiarla sobre `tests.yml` restaura la ejecución automática.
- Configuración de protección de rama o ajustes del repositorio en GitHub.
- Ramas que aún no contengan este cambio: GitHub usa la definición de workflow de cada commit, así que un push a una rama con el archivo antiguo sigue aplicando sus disparadores antiguos.
- La entrada de `CHANGELOG.md`: se deriva de los commits al publicar una versión (`assets/proceso-versionado.md`, R-04).
- Commit y push: solo con orden del programador. Publicar cambios en workflows requiere el permiso `workflow` en el token.
- El comportamiento real en GitHub no es comprobable localmente; los AC verifican la definición. Tras integrar, y como comprobación del programador, `gh run list --workflow tests.yml` no debería mostrar corridas nuevas con evento `push` o `pull_request`.
