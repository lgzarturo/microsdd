# Decisiones de diseño de MicroSDD para Claude Opus 5.5

Este registro explica qué decidió el arnés MicroSDD, por qué, dónde se observa cada decisión en el repositorio y qué fuente la respalda. Distingue lo que proviene de la guía de prompting de Opus 5.5 de lo que es diseño o interpretación propia del proyecto. La carpeta `assets/` es material de consulta y no forma parte de la instalación del arnés.

## Fuentes

- **README de MicroSDD 0.1**: documento base del diseño original, sin enlace público. El `README.md` actual deriva de él y añade la sección de requisitos mínimos.
- **Guía `prompting-opus-5-5-2026-10-11.md`**: resumen de terceros del artículo oficial de Anthropic sobre prompting para Opus 5.5. Sus secciones 1 a 3 remiten a encabezados del artículo; su sección 4 es interpretación de su autor y no se usa como respaldo.
- **Artículo de origen**: https://platform.claude.com/docs/es/build-with-claude/prompt-engineering/prompting-claude-opus-5-5
- **Documentación de Claude Code** citada por el `README.md`: https://code.claude.com/docs/en/sub-agents, https://code.claude.com/docs/en/settings, https://code.claude.com/docs/en/memory y https://code.claude.com/docs/en/hooks. Su contenido no se revisó en esta tarea; se cita solo como referencia del README.

Ninguna fuente se reproduce aquí; la redacción es propia y las citas se limitan a encabezados del artículo e identificadores técnicos.

## Convención de etiquetas

- `[GUÍA «<encabezado>»]`: la decisión aplica una recomendación del artículo, identificada por el encabezado que cita la guía.
- `[README 0.1]`: la decisión ya estaba en el diseño original de MicroSDD 0.1.
- `[CLAUDE CODE]`: la decisión se apoya en una capacidad nativa de Claude Code (agentes, configuración, memoria o hooks).
- `[PROYECTO]`: diseño o interpretación propia de MicroSDD, incluida cualquier adaptación de la guía con un alcance distinto al del artículo.

## Decisiones

### D-01 · Líder predeterminado y tres subagentes con roles separados

- **Decisión:** toda sesión arranca con el agente `lider`, único interlocutor del humano, que delega de forma secuencial en tres subagentes: `autor` (especifica), `implementador` (único que escribe código) y `revisor` (dictamen independiente sin herramientas de edición).
- **Motivo:** separar especificación, implementación y revisión evita que un mismo agente se autocertifique y mantiene en un solo lugar el contexto de decisiones y aprobaciones.
- **Evidencia:** `.claude/settings.json` (`"agent": "lider"`); `.claude/agents/lider.md` punto 8; `.claude/agents/revisor.md` (sus `tools` excluyen `Write` y `Edit`); `CLAUDE.md` («un solo agente escribe código; revisor independiente»).
- **Fuente:** [README 0.1]; [CLAUDE CODE] (sub-agents, settings).

### D-02 · Máquina de tres estados con aprobaciones como eventos

- **Decisión:** una tarea solo puede estar en `pendiente`, `proceso` o `terminado`. Las aprobaciones y las revisiones se registran como eventos en la memoria; un rechazo no crea un estado nuevo.
- **Motivo:** un modelo de estados mínimo es fácil de validar y de auditar; el historial de eventos conserva quién aprobó, qué se rechazó y por qué.
- **Evidencia:** `STATES`, `approve` (pasa a `proceso` o `terminado`) y `review` (escala a `pendiente`) en `.microharness/sdd.py`; `docs/specificaciones.md`; `.claude/agents/lider.md` punto 7.
- **Fuente:** [README 0.1].

### D-03 · Límite de iteraciones y `end_turn` sin valor de cierre

- **Decisión:** `max_iterations` debe estar entre 1 y 3; al agotarse con un rechazo, la tarea vuelve a `pendiente` y se consulta al humano. Que el modelo termine su turno (`end_turn`) no certifica que la tarea esté completa: el cierre depende de la memoria, la aceptación y las pruebas.
- **Motivo:** evitar bucles ilimitados y cierres prematuros cuando el modelo entrega un informe en lugar de terminar el trabajo.
- **Evidencia:** `validate` (rango de `max_iterations`) y `review` (escalado al agotar intentos) en `.microharness/sdd.py`; `.claude/agents/lider.md` puntos 5 y 9.
- **Fuente:** [GUÍA «Ejecuciones agénticas desatendidas»]; [PROYECTO]: la guía limita continuaciones automáticas en agentes sin humano, mientras que MicroSDD limita revisiones completas en un flujo interactivo, por lo que no incorpora un párrafo para que el agente siga sin detenerse.

### D-04 · Esfuerzo `medium` explícito y modelo único

- **Decisión:** el modelo y el esfuerzo por defecto se declaran de forma explícita en `.microharness/config.json`, archivo opcional de configuración humana; si falta, valen `claude-opus-5-5` y `medium`. Se admite un único modelo a la vez: el configurado, que debe coincidir con la configuración, el frontmatter de cada agente y `spec.json`.
- **Motivo:** declarar el esfuerzo evita heredar valores de modelos anteriores; fijar un solo modelo hace comparables las tareas del MVP; sacarlo del código permite cambiarlo sin editar `sdd.py`.
- **Evidencia:** `.claude/settings.json` (`model` y `effortLevel`); frontmatter `effort: medium` en `.claude/agents/*.md`; en `.microharness/sdd.py`, `config()` lee `config.json` junto a `memory.json`, `new` copia sus valores y `validate` rechaza un `spec.model` distinto del configurado salvo en tareas `terminado` y admite cinco niveles de `effort`; protocolo de medición no ejecutado en `assets/eval-esfuerzo.md`.
- **Fuente:** [GUÍA «Calibra el esfuerzo»]; [PROYECTO]: el artículo recomienda fijar el esfuerzo y medir; restringir el arnés a un único modelo es decisión propia, y el `effort` de `spec.json` es solo una preferencia registrada, ya que el runtime lo toma de la configuración y del frontmatter.

### D-05 · Solo biblioteca estándar de Python

- **Decisión:** el controlador y el hook usan exclusivamente la biblioteca estándar de Python; no hay SDK, servidor ni base de datos.
- **Motivo:** instalación trivial, superficie de dependencias nula y orquestación delegada en Claude Code de forma nativa.
- **Evidencia:** imports de `.microharness/sdd.py` y `.claude/hooks/pretool.py`; propósito y sección 1 de `README.md`.
- **Fuente:** [README 0.1].

### D-06 · Memoria del proyecto en un archivo versionable

- **Decisión:** el estado operativo, las decisiones, aprobaciones, sellos y revisiones viven en `.microharness/memory.json`, que pertenece al proyecto. No se usa el frontmatter `memory:` de los subagentes.
- **Motivo:** una memoria estructurada y versionable es inspeccionable por el humano y por el controlador; la memoria privada de un subagente no lo sería.
- **Evidencia:** último párrafo de `.claude/agents/lider.md`; sección 3 de `README.md`; uso de `MEMORY` en `approve`, `review` y `seal` de `.microharness/sdd.py`.
- **Fuente:** [README 0.1]; [CLAUDE CODE] (memory, sub-agents).

### D-07 · Hook `PreToolUse` por rol, sin pretensión de sandbox

- **Decisión:** un hook `PreToolUse` limita escritura y `Bash` según el agente: el revisor es solo lectura, el autor solo edita los cuatro archivos de la spec, el implementador solo edita rutas de `scope.allowed_paths` con spec aprobada y sin tocar pruebas selladas, y el líder no edita código. Ante una entrada inválida, deniega.
- **Motivo:** reforzar los roles con un bloqueo previo a la herramienta, reconociendo que es una defensa de mejor esfuerzo y no un aislamiento.
- **Evidencia:** `.claude/hooks/pretool.py` (docstring «best effort, NO sandbox»); `.claude/settings.json` (matcher sobre `Write`, `Edit`, `MultiEdit`, `NotebookEdit` y `Bash`); sección 7 de `README.md`.
- **Fuente:** [README 0.1]; [CLAUDE CODE] (hooks).

### D-08 · EARS, SDD obligatorio y métodos opcionales con definición operativa

- **Decisión:** los requisitos se escriben en EARS con criterios de aceptación identificados; SDD es obligatorio; TDD se expresa como estrategia de pruebas `tdd` o `after`; RDD y ODD solo se activan si `method.notes` define su significado operativo.
- **Motivo:** requisitos observables y verificables antes de escribir código, sin imponer métodos cuyo significado no esté claro.
- **Evidencia:** `validate` en `.microharness/sdd.py` (método primario y estrategia de pruebas); `docs/specificaciones.md`; `.claude/agents/autor.md` puntos 2 y 5.
- **Fuente:** [README 0.1]; [PROYECTO]: ODD se interpreta como Organic Driven Development y RDD se considera ambiguo, por lo que ninguno se activa sin definición explícita.

### D-09 · Huellas SHA-256 de spec, pruebas selladas y diff revisado

- **Decisión:** al aprobar una spec se guarda su huella SHA-256; `seal` registra el hash de las pruebas protegidas; tras un `APROBADO` se guarda la huella del diff dentro del alcance, y el cierre exige que no haya cambiado.
- **Motivo:** detectar deriva accidental de la spec, de las pruebas de aceptación o del código después de revisado.
- **Evidencia:** `spec_fingerprint`, `seal` y `code_fingerprint` en `.microharness/sdd.py`; comprobaciones en `validate` y en la fase `close` de `approve`; `docs/specificaciones.md`.
- **Fuente:** [README 0.1].

### D-10 · Mutation testing opcional y proporcional

- **Decisión:** `testing.mutation` nace desactivado; solo se activa con un comando concreto en lógica de riesgo significativo, y entonces `check --run` lo ejecuta junto a las pruebas.
- **Motivo:** el coste del análisis de mutantes solo se justifica en lógica crítica; una cifra aislada no sustituye la pertinencia de las pruebas.
- **Evidencia:** `new` y `validate` en `.microharness/sdd.py` (`enabled` en falso por defecto y error si se activa sin comando); `.claude/agents/revisor.md` punto 4.
- **Fuente:** [README 0.1].

### D-11 · Conventional Commits, commit atómico y sin `push` automático

- **Decisión:** los mensajes siguen Conventional Commits y se validan con `commit-check`; el líder hace un commit atómico con stage explícito de los archivos de la tarea (nunca `git add .`) y no hace `push` sin autorización independiente.
- **Motivo:** historial trazable por tarea y ninguna publicación sin decisión humana.
- **Evidencia:** `COMMIT_RE` y `commit_check` en `.microharness/sdd.py`; `.claude/agents/lider.md` punto 6; `docs/convensiones.md`.
- **Fuente:** [README 0.1]; [PROYECTO].

### D-12 · El contenido externo es dato no confiable

- **Decisión:** el texto de issues, logs, documentación externa y salidas de herramientas se trata como dato no confiable, nunca como orden por encima del programador.
- **Motivo:** reducir el riesgo de inyección indirecta de instrucciones a través del material que los agentes leen.
- **Evidencia:** `CLAUDE.md`; sección de seguridad de `docs/convensiones.md`.
- **Fuente:** [GUÍA «Marca el texto pegado en los mensajes de usuario»]; [PROYECTO]: se adopta la regla de tratar ese contenido como datos, pero no el marcado con etiquetas `<pasted_content>` que propone el artículo.

### D-13 · Intención al inicio, resumen al final y sin extracción de razonamiento

- **Decisión:** el líder anuncia su intención en una línea al comenzar y cierra con un resumen de hechos, pruebas y pendientes. Ningún agente pide al modelo que escriba su cadena interna de pensamiento.
- **Motivo:** dar visibilidad del avance sin solicitar razonamiento escrito, que Opus 5.5 puede rechazar con la categoría `reasoning_extraction`.
- **Evidencia:** `.claude/agents/lider.md` puntos 8 y 9.
- **Fuente:** [GUÍA «Actualizaciones de progreso para el usuario»]; [GUÍA «Rechazos de salvaguardas»]; [PROYECTO]: se adopta solo la convención en el prompt, no las opciones de la API para mostrar progreso.

### D-14 · Límites conocidos del MVP

- **Decisión:** se aceptan como límites intencionales del MVP que la aprobación es una declaración registrada que no autentica al humano, que no hay sandbox obligatorio, que no hay validación semántica automática de los criterios de aceptación, ni control de costos por agente, ni comparador histórico de benchmarks.
- **Motivo:** mantener el arnés pequeño y no presentar como controles de seguridad lo que solo son contratos procedimentales.
- **Evidencia:** comentario y mensaje final de `approve` en `.microharness/sdd.py`; docstring del módulo; sección 7 y «Limitaciones conocidas» de `README.md`.
- **Fuente:** [README 0.1].
