# QUÉ: requisitos

## Objetivo
Riesgos R7 y R10 del análisis externo (dato no confiable, contrastado con el código): que el modelo y el esfuerzo por defecto dejen de estar fijos en `.microharness/sdd.py`. Un archivo de configuración humana del proyecto, `.microharness/config.json`, define `model` y `effort`; si no existe, se usan los valores actuales (`claude-opus-5-5`, `medium`). `new` toma de ahí la plantilla de `spec.json` y `check` compara `spec.model` con el modelo configurado. Se añade, sin ejecutarlo, un protocolo breve de mini-eval de esfuerzo.

## Hechos comprobados
- `new()` escribe los literales `'model': 'claude-opus-5-5'` y `'effort': 'medium'` (`.microharness/sdd.py`, líneas 164-165).
- `validate()` rechaza cualquier `model` distinto de `claude-opus-5-5` con «El modelo debe ser exclusivamente claude-opus-5-5» y `effort` fuera de `low|medium|high|xhigh|max` con «Effort inválido» (líneas 306-309), sin distinguir el estado de la tarea.
- `validate()` ya exime a las tareas `terminado` de la lista blanca de runners, del mínimo de pruebas y de los sellos.
- `.claude/settings.json` fija `model` y `effortLevel`; los cuatro `.claude/agents/*.md` fijan `model` y `effort` en el frontmatter; `.claude/agents/autor.md` línea 14 nombra `claude-opus-5-5` y `medium`. El runtime toma modelo y esfuerzo de ahí, no de `spec.json` (README sección 6, D-04).
- `scripts/limpiar_arnes.py` archiva y reinicia `.microharness/memory.json` en cada release, pero no toca otros archivos de `.microharness/`.
- El instalador (`MANIFEST`) y `pyproject.toml` distribuyen `sdd.py` y `python.sh` de `.microharness/`; no distribuyen `memory.json` (lo crea `init`).
- Las pruebas de `sdd.py` aíslan el estado reasignando `sdd.ROOT` y `sdd.MEMORY` a un directorio temporal.
- `main()` convierte `ValueError` y `json.JSONDecodeError` en `ERROR: …` por stderr con código 1.

## Precondiciones
- Python 3.10+ solo con biblioteca estándar.
- El implementador puede modificar `.microharness/sdd.py` (hoy por Bash). Si `bloquear-autoaprobacion` se implementa antes, el cambio a `sdd.py` requiere decisión humana sobre cómo aplicarlo (ver plan, riesgo R-01).

## Definiciones
- **Archivo de configuración:** `config.json` en el mismo directorio que `memory.json` (`.microharness/config.json` en un proyecto real). Objeto JSON con claves opcionales `model` (cadena no vacía) y `effort` (uno de `low`, `medium`, `high`, `xhigh`, `max`). Otras claves no se admiten.
- **Valores configurados:** los del archivo; para cada clave ausente, o si el archivo no existe, `claude-opus-5-5` y `medium`.

## Requisitos EARS
- REQ-01: WHEN se ejecuta `sdd.py new <slug>` y no existe el archivo de configuración, THE CLI SHALL escribir en `spec.json` `model: "claude-opus-5-5"` y `effort: "medium"`, como hoy.
- REQ-02: WHEN se ejecuta `sdd.py new <slug>` y el archivo de configuración es válido, THE CLI SHALL escribir en `spec.json` el modelo y el esfuerzo configurados.
- REQ-03: WHEN `check` valida una tarea que no está `terminado` y `spec.model` difiere del modelo configurado, THE CLI SHALL informar un error que contenga el modelo de la spec, el modelo configurado y la ruta `.microharness/config.json`.
- REQ-04: WHEN `check` valida una tarea `terminado`, THE CLI SHALL no comparar `spec.model` con el modelo configurado.
- REQ-05: WHEN `spec.effort` no es uno de los cinco niveles, THE CLI SHALL informar un error que enumere los niveles válidos; un `effort` válido distinto del configurado no es error.
- REQ-06: IF el archivo de configuración existe y no es JSON válido, no es un objeto, contiene claves no admitidas o valores inválidos, THEN THE CLI SHALL terminar `new` y `check` con código 1 y un mensaje `ERROR:` por stderr que nombre `config.json` y el motivo, sin crear `spec/<slug>/` ni modificar `memory.json`.
- REQ-07: THE instalador SHALL seguir sin distribuir el archivo de configuración (`MANIFEST` y `pyproject.toml` sin cambios).
- REQ-08: THE `README.md` SHALL documentar el archivo, su formato y valores por defecto, la comparación en `check` y la exención de tareas `terminado`, y que cambiar de modelo o esfuerzo exige editar a mano también `.claude/settings.json`, el frontmatter de `.claude/agents/*.md` y la línea 14 de `autor.md`.
- REQ-09: THE `assets/eval-esfuerzo.md` SHALL describir un protocolo de mini-eval `medium` frente a `high` y declarar explícitamente que no se ha ejecutado, sin resultados.

## Criterios de aceptación
- AC-01: Sin archivo de configuración, `sdd.new('x')` produce `spec.json` con `model == "claude-opus-5-5"` y `effort == "medium"`; las pruebas existentes de `tests/test_sdd.py` pasan sin modificarse.
- AC-02: Con `config.json` = `{"model": "claude-prueba-1", "effort": "high"}`, `sdd.new('x')` produce `model == "claude-prueba-1"` y `effort == "high"`. Con `{"model": "claude-prueba-1"}` el esfuerzo es `medium`; con `{"effort": "low"}` el modelo es `claude-opus-5-5`.
- AC-03: Con `config.json` = `{"model": "claude-prueba-1"}` y una tarea en `pendiente` o `proceso` cuyo `spec.model` es `claude-opus-5-5`, `validate()` devuelve un error que contiene `claude-opus-5-5`, `claude-prueba-1` y `.microharness/config.json`; con `spec.model == "claude-prueba-1"` no hay error de modelo. Sin archivo, `spec.model == "claude-otro"` da error y `claude-opus-5-5` no.
- AC-04: Con `spec.effort == "ultra"`, `validate()` devuelve un error que contiene `low, medium, high, xhigh, max`; con `config.json` = `{"effort": "medium"}` y `spec.effort == "max"` no hay error de esfuerzo.
- AC-05: Para una tarea `terminado` (aprobaciones registradas, como en las pruebas existentes de cierre) con `spec.model == "claude-opus-5-5"` y `config.json` = `{"model": "claude-prueba-1"}`, `validate()` no devuelve error de modelo.
- AC-06: Para cada `config.json` inválido (`{`, `[]`, `{"model": ""}`, `{"model": 5}`, `{"effort": "ultra"}`, `{"efort": "high"}`), `main()` con argv `new y` y con argv `check fix-sesiones --no-scope` devuelve 1 y escribe en stderr `ERROR:` seguido de un texto que contiene `config.json`; tras `new y` no existe `spec/y/` y `memory.json` queda byte a byte igual.
- AC-07: `src/microsdd/installer.py` y `pyproject.toml` no cambian (`git diff` vacío en ambos) y la suite completa `python -m unittest discover -s tests -v` termina con código 0, incluida `tests/test_installer.py`.
- AC-08: `README.md` contiene: ruta y formato de `.microharness/config.json` con un ejemplo; valores por defecto si falta; que `check` exige `spec.model` igual al configurado salvo en tareas `terminado`; que el archivo es configuración humana y el instalador no lo crea; que cambiar de modelo o esfuerzo requiere editar a mano `.claude/settings.json` (`model`, `effortLevel`), el frontmatter `model`/`effort` de los cuatro agentes y la línea 14 de `.claude/agents/autor.md`; y que las tareas en `pendiente` o `proceso` deben actualizar `spec.model`, lo que exige reaprobar la spec.
- AC-09: `assets/eval-esfuerzo.md` existe, describe 5 tareas tipo, la comparación `medium` frente a `high` y las métricas iteraciones de revisión, AC cumplidos, tokens y tiempo; contiene una declaración explícita de que el protocolo no se ha ejecutado y no contiene resultados ni cifras medidas.
- AC-10: D-04 de `assets/decisiones-diseno.md` refleja que el modelo y el esfuerzo por defecto vienen de `.microharness/config.json` (por defecto `claude-opus-5-5`/`medium`), y `docs/arquitectura.md` (escrito por el líder al cierre) registra el invariante de configuración.

## Fuera de alcance
- Reescribir automáticamente `.claude/settings.json` o el frontmatter de los agentes (YAGNI); cambiar `.claude/agents/autor.md`.
- Distribuir o crear `config.json` desde el instalador o desde `sdd.py init`; versionar un `config.json` en este repositorio.
- Ejecutar la mini-eval o publicar resultados.
- Validar que el nombre de modelo exista en la API, admitir varios modelos simultáneos o migrar specs existentes.
- Cambiar el título del proyecto ni la descripción de `pyproject.toml`.
