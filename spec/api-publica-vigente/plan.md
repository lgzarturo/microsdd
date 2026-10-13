# CÓMO: diseño mínimo

## Situación comprobada

Hechos observados el 2026-10-13 (`HEAD` = `5caba80`, suite `Ran 171 tests`, `OK (skipped=2)`):

- Parser de `sdd.py` (`main()`, líneas 685-698): `--version` global; subcomandos `init`, `new`, `check` (`--run`, `--no-scope`), `approve` (`spec`/`close`, `--by`, `--evidence`), `review` (`APROBADO`/`RECHAZADO`, `--evidence`), `seal` (`--by`), `note` (`--fact`, `--decision`, `--by`, `--evidence`), `commit-check`, `release` con acción única `propose`. `sdd.py --help` imprime `{init,new,check,approve,review,seal,note,commit-check,release}`; `release --help` imprime `{propose}`.
- API-01 actual omite `note`, `release propose` y `--version`. Errores de ejecución (incluido timeout del lock e integridad) → código 1.
- `validate()`: `testing.min_tests` (int ≥ 1, por defecto 1); `testing.commands`/`mutation.command` limitados a `TEST_COMMANDS` + `project.allowed_test_commands` salvo en `terminado`; `memory_integrity()` compara con `HEAD:.microharness/memory.json`. API-02 y API-03 no lo mencionan.
- `config()` lee `.microharness/config.json` opcional (`model`, `effort`; claves desconocidas → error). No figura en la API pública.
- `memory_lock()` usa `.microharness/memory.lock` (en `.gitignore`).
- `pretool.run()`: agente fuera de los cuatro roles → deniega `Write`, `Edit`, `MultiEdit`, `NotebookEdit`, `Bash`, `PowerShell`.
- `DOCS` = `convenciones.md`, `especificaciones.md`; `LEGACY_DOCS` mantiene compatibilidad (aviso de `init`, sin mover archivos).
- Instalador: `MANIFEST` (10 entradas; `CLAUDE.md` → `CLAUDE.microsdd.md`, incluye `.microharness/python.sh`), bloque de registro en `CLAUDE.md`, `.claude/settings.microsdd.json` alterno, `INIT_FILES` (cuatro `docs/` y `memory.json`) más `spec/` generados por `init`.
- «Instalación» actual (líneas 89-118) es falsa: dice que se copia todo lo versionado salvo `assets/`, lista `README.md`, `.gitignore`, `tests/test_sdd.py` (no se instalan) y omite `.microharness/python.sh` y `CLAUDE.microsdd.md`; anuncia que `CHANGELOG.md` se incluirá.
- No existe prueba que vincule el documento con el parser o el manifiesto. `tests/test_installer.py` ya carga `installer.py` con `importlib` (patrón a reutilizar).

## Decisión y justificación

1. **Documento** (`assets/proceso-versionado.md`), edición limitada:
   - API-01: añadir `note` (`--fact`, `--decision`, `--by`, `--evidence`), `release propose` y `--version` global; mencionar el lanzador `.microharness/python.sh` en una cláusula (D-05). El resto de la viñeta se conserva.
   - API-02: añadir `testing.min_tests` y la lista blanca de runners.
   - API-03: añadir `project.allowed_test_commands`, integridad frente a `HEAD` (eventos confirmados inmutables, campos vigilados solo con evento justificante) y `memory.lock` no versionado.
   - API-05: añadir la denegación fail-closed.
   - Nueva viñeta API-09 para `.microharness/config.json` tras API-08 (D-01), y en «Reglas de incremento» «API-01 a API-08» → «API-01 a API-09».
   - «Instalación»: reescribir solo el párrafo inicial, «Incluido» y «Excluido» según el instalador; conservar la nota de conflictos ajustada a `CLAUDE.md` y `.claude/settings.json`. «Incluido» lista como elementos `- \`ruta\`` solo rutas instaladas (MANIFEST destino, `CLAUDE.md` con el bloque, `INIT_FILES`, `spec/`); `.claude/settings.microsdd.json` y los nombres antiguos de `docs/` van en prosa, no como elementos de lista.
2. **Prueba** `tests/test_api_publica.py` (nuevo, unittest, solo stdlib):
   - Extrae la sección por encabezado: texto entre `## API pública` y el siguiente `\n## `; «Incluido» entre `### Incluido` y `### Excluido`.
   - CLI por subprocess con `sys.executable` y la ruta absoluta de `sdd.py`: `--help` → primer `{…}` de la salida = subcomandos; `release --help` → acciones; `<sub> --help` → `--[a-z][a-z-]*` menos `--help`. Comprueba `` `x` `` en «API pública» para cada nombre y `--version`. Se usa la salida de argparse en lugar de importar `main()` porque el parser se construye dentro de `main()` y no es accesible sin modificar `sdd.py` (fuera de alcance).
   - Instalador por `importlib` (como `test_installer.py`): cada clave/valor de `MANIFEST` y cada `INIT_FILES` aparece como `` `ruta` `` en «Incluido»; cada línea que empieza por `` - ` `` en «Incluido» tiene su primera ruta en el conjunto instalado (D-03).
   - Mensajes de fallo que nombran lo que falta.
3. **TDD**: escribir la prueba primero y registrar el fallo (RED) contra el documento actual; luego editar el documento (GREEN).
4. **`docs/**`**: el líder, antes de la revisión, añade la fila de la tarea a `docs/especificaciones.md` y la prueba nueva a «Pruebas» de `docs/arquitectura.md`.

## Invariantes y riesgos

- Invariante: la fuente de verdad es el código; el documento se adapta, nunca al revés.
- Invariante: no se tocan secciones de `release-v1-0-0` (REQ-11); el diff se acota por sección (AC-09).
- Riesgo: la spec pendiente de `release-v1-0-0` queda desactualizada (tabla C-01 «No», D-03 y su fuera de alcance «Actualizar API-01 a API-08 o Instalación»). El líder debe actualizarla tras cerrar esta tarea y antes de su aprobación; su AC-07 sigue siendo válido porque su diff partirá del commit de esta tarea.
- Riesgo: la prueba depende del formato de ayuda de argparse (`{a,b}` y `--opción`), estable en 3.10-3.13; si cambiara, fallaría en rojo, no en falso verde.
- Riesgo: la prueba solo garantiza presencia de nombres, no la exactitud de la prosa (REQ-05 a REQ-09 se revisan a mano). No detecta subcomandos eliminados que sigan documentados (dirección inversa en API no comprobada; ver D-02).
- Riesgo: añadir API-09 cambia la enumeración citada en otros textos (`release-v1-0-0`, `assets/decisiones-diseno.md` si la menciona); se revisa con `grep -rn "API-08"` y solo se corrige dentro del alcance.
- Efecto secundario: la suite sube de 171 a ≥ 172 pruebas; `testing.min_tests` = 172.

## Alternativas descartadas

- Generar la sección «API pública» desde el código: más maquinaria, no pedida.
- Exponer el parser en `sdd.py` (función `build_parser()`): cambia código fuera de alcance.
- Prueba bidireccional completa en «API pública» (todo `` `x` `` debe existir en el parser): la sección cita también campos JSON y archivos; falsos positivos.
- Fusionar `config.json` en API-06: API-06 trata de `.claude/settings.json`; mezclarlos oculta el contrato.
- Reescribir el documento entero: contrario al cambio mínimo y a la coordinación con `release-v1-0-0`.

## Decisiones abiertas (para el líder; se adoptan las recomendaciones salvo objeción)

- D-01: `config.json` como API-09 nueva (y «API-01 a API-09» en «Reglas de incremento»). Recomendado: sí. Alternativa: una frase en API-06 sin renumerar.
- D-02: la prueba exige también las opciones largas de cada subcomando (AC-02), no solo subcomandos. Recomendado: sí; coste mínimo y cubre `--fact`/`--decision`. No se comprueban los valores posicionales (`spec`/`close`, `APROBADO`/`RECHAZADO`).
- D-03: comprobación inversa en «Incluido» (AC-04). Recomendado: sí; el defecto real fue listar rutas no instaladas.
- D-04: `INIT_FILES` y `spec/` cuentan como parte de la instalación (generados por `init`). Recomendado: sí.
- D-05: menciones extra: lanzador `.microharness/python.sh` en API-01 (`MICROSDD_PYTHON`, código 2 sin intérprete válido), `memory.lock` e integridad en API-03, fail-closed en API-05, nombres nuevos y antiguos de `docs/` en «Instalación». Recomendado: sí, una cláusula cada una. El instalador `microsdd install` no se añade como API (la sección ya excluye `README.md`, donde se documenta; incluirlo exigiría otra viñeta y pruebas propias).
