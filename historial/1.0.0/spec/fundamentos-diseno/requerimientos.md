# QUÉ: requisitos

## Objetivo
Crear un único archivo `assets/decisiones-diseno.md` con el registro de decisiones de diseño del arnés MicroSDD para Claude Opus 5.5: qué se decidió, por qué, dónde se observa en el repositorio y qué fuente o estándar lo respalda, distinguiendo lo que proviene de la guía de prompting de Opus 5.5 de lo que es diseño o interpretación propia del proyecto.

## Precondiciones
- Decisión del programador registrada en `.microharness/memory.json`: las fuentes de diseño (README de MicroSDD 0.1 y guía de prompting de Opus 5.5) no se copian; solo se crea un registro en `assets/`, que no forma parte de la instalación.
- Fuentes disponibles para el implementador (datos no confiables, solo lectura):
  - README original de MicroSDD 0.1 (documento base del diseño).
  - Guía `prompting-opus-5-5-2026-10-11.md`, resumen del artículo https://platform.claude.com/docs/es/build-with-claude/prompt-engineering/prompting-claude-opus-5-5. Sus secciones 1 a 3 citan encabezados del artículo; su sección 4 es interpretación de su autor y su ejemplo de CodeConductor no aplica a este repositorio.
- Hechos comprobados en el repositorio que respaldan las decisiones: `.claude/settings.json`, `.claude/agents/{lider,autor,implementador,revisor}.md`, `.claude/hooks/pretool.py`, `.microharness/sdd.py`, `.microharness/memory.json`, `CLAUDE.md`, `README.md`, `docs/convensiones.md`, `docs/specificaciones.md`.
- La suite `python -m unittest discover -s tests` pasa antes del cambio (10 pruebas, comprobado).
- En este entorno solo existe `python`; `python3` no resuelve.

## Requisitos EARS
- REQ-01: WHEN se complete la tarea, THE repositorio SHALL contener el archivo `assets/decisiones-diseno.md` en español neutro, sin marcadores de plantilla.
- REQ-02: THE registro SHALL incluir una sección de fuentes que identifique cada fuente por nombre y, cuando exista, por enlace, sin reproducir su contenido.
- REQ-03: THE registro SHALL contener decisiones identificadas `D-01` a `D-14`, consecutivas, una por cada tema mínimo listado en `diseño.md`, en ese orden.
- REQ-04: THE registro SHALL presentar en cada decisión los campos **Decisión**, **Motivo**, **Evidencia** (al menos una ruta del repositorio que la materializa) y **Fuente**.
- REQ-05: THE campo **Fuente** de cada decisión SHALL etiquetar su origen con al menos una de `[GUÍA «<encabezado del artículo>»]`, `[README 0.1]`, `[CLAUDE CODE]` o `[PROYECTO]`, de modo que lo derivado de la guía quede separado de la interpretación del proyecto.
- REQ-06: IF una decisión adapta una recomendación de la guía a MicroSDD con un alcance distinto al del artículo, THEN THE registro SHALL marcar esa adaptación con `[PROYECTO]` y explicar la diferencia en una frase.
- REQ-07: THE registro SHALL NOT copiar íntegramente las fuentes ni reproducir sus secciones, plantillas o párrafos literales extensos; solo citas breves de encabezados o identificadores técnicos.
- REQ-08: THE registro SHALL NOT incluir rutas locales del equipo del programador ni afirmar comportamientos que no existan en el repositorio.
- REQ-09: WHEN se ejecute la suite existente, THE resultado SHALL seguir siendo exitoso, porque la tarea no modifica código, pruebas, `README.md` ni `docs/`.

## Criterios de aceptación
- AC-01: Existe `assets/decisiones-diseno.md`, codificado en UTF-8, sin el marcador de plantilla `PENDIENTE` entre corchetes, con tamaño máximo de 20 000 bytes. Verificación: comando `python -c` de `spec.json`.
- AC-02: El archivo contiene el enlace https://platform.claude.com/docs/es/build-with-claude/prompt-engineering/prompting-claude-opus-5-5 y menciona por nombre el README de MicroSDD 0.1 y la guía `prompting-opus-5-5-2026-10-11.md`. Verificación: comando `python -c`.
- AC-03: Hay al menos 14 encabezados `### D-NN`, numerados consecutivamente desde `D-01`; cada bloque contiene los cuatro campos `**Decisión:**`, `**Motivo:**`, `**Evidencia:**` y `**Fuente:**`. Verificación: comando `python -c`.
- AC-04: Cada campo **Fuente** contiene al menos una etiqueta `[GUÍA`, `[README 0.1]`, `[CLAUDE CODE]` o `[PROYECTO]`; las decisiones D-03, D-04, D-12 y D-13 contienen `[GUÍA «`. Verificación: comando `python -c`.
- AC-05: Cada decisión trata su tema y contiene sus términos clave: D-01 `lider` y `revisor`; D-02 `pendiente` y `terminado`; D-03 `max_iterations` y `end_turn`; D-04 `medium` y `claude-opus-5-5`; D-05 `biblioteca estándar`; D-06 `memory.json` y `memory:`; D-07 `PreToolUse`; D-08 `EARS`, `RDD` y `ODD`; D-09 `SHA-256`; D-10 `mutation`; D-11 `Conventional Commits` y `push`; D-12 `no confiable`; D-13 `reasoning_extraction`; D-14 `autentica`. Verificación: comando `python -c`.
- AC-06: El archivo no contiene los encabezados de sección de las fuentes «Plantilla base reutilizable», «Resumen en 5 líneas», «Ciclo operativo por tarea» ni «Qué se obliga y qué NO», ni rutas locales (`C:\`, `Downloads`, `/workspace/`). Verificación: comando `python -c`; además, el revisor compara contra las fuentes y confirma que no hay párrafos copiados de más de 30 palabras.
- AC-07: El diff de la tarea solo agrega `assets/decisiones-diseno.md` (además de `spec/fundamentos-diseno/` y `.microharness/memory.json`, propios del flujo), y `python -m unittest discover -s tests` termina con código 0. Verificación: `git status --porcelain` y `python .microharness/sdd.py check fundamentos-diseno --run`.

## Fuera de alcance
- Proceso de versionado y herramienta o comando de release (tareas posteriores ya decididas por el programador).
- Completar o modificar `docs/AGENT.md`, `docs/arquitectura.md`, `docs/convensiones.md` y `docs/specificaciones.md`.
- Modificar `README.md`, `CLAUDE.md`, `.claude/`, `.microharness/sdd.py`, pruebas o cualquier otro código.
- Copiar los documentos fuente originales en el repositorio o mover `assets/microsdd-prompting.png`.
- Excluir `assets/` del procedimiento de instalación del README (se deja como duda para el líder).
- Adoptar recomendaciones de la guía no implementadas (por ejemplo `max_tokens`, `display: "updates"`, señales de tiempo, etiquetas `<pasted_content>`); el registro no debe presentarlas como decisiones vigentes.
