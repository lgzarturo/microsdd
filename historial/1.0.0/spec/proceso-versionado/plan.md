# CÓMO: diseño mínimo

## Situación comprobada
- `assets/` contiene `decisiones-diseno.md` (tarea `fundamentos-diseno`, terminada; su D-11 registra Conventional Commits, commit atómico y ausencia de `push` automático) y `microsdd-prompting.png`. No hay documento de versionado.
- Sin tags (`git tag` vacío), sin `CHANGELOG.md`, sin `VERSION` y sin constante de versión en `.microharness/sdd.py`. El único indicio de versión es el título «MicroSDD 0.1» de `README.md`.
- `COMMIT_RE = ^(feat|fix|docs|test|refactor|perf|chore)(\([a-z0-9][a-z0-9-]*\))?(!)?: [^\n]{1,72}$` con `fullmatch`: `feat!: x` es válido; `feat: x` seguido de línea vacía y `BREAKING CHANGE: y` no lo es (comprobado). `chore(release): v1.0.0` es válido.
- `SLUG_RE = ^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$`: `release-v1-0-0` es válido; `release-v1.0.0` no.
- `validate` excluye del control de alcance `spec/`, `docs/`, `.microharness/` y `CLAUDE.md`; `README.md` y `assets/` sí se controlan.
- `git ls-files` (archivos versionados): `.claude/agents/{autor,implementador,lider,revisor}.md`, `.claude/hooks/pretool.py`, `.claude/settings.json`, `.claude/skills/sdd/SKILL.md`, `.gitignore`, `.microharness/memory.json`, `.microharness/sdd.py`, `CLAUDE.md`, `README.md`, `assets/*`, `docs/*.md`, `spec/.gitkeep`, `spec/fundamentos-diseno/*`, `tests/test_sdd.py`. `.claude/settings.local.json` está en `.gitignore`.
- `ensure_init` crea `docs/*.md` y `.microharness/memory.json` si faltan, por lo que la memoria no necesita copiarse para instalar.
- `README.md` usa CRLF en el árbol de trabajo (`core.autocrlf=true`); `git show HEAD:README.md` devuelve LF. La verificación normaliza finales de línea.
- El hook no restringe `Bash` del líder; el `push` solo está limitado por la regla de `lider.md` punto 6 y por la autorización humana.

## Decisión y justificación

### Estructura de `assets/proceso-versionado.md`
Título `# Proceso de versionado de MicroSDD` y exactamente estas secciones `##`, en orden:

1. **Propósito y alcance**: qué regula el documento; referencia a SemVer 2.0.0 (https://semver.org/lang/es/) y a Conventional Commits 1.0.0 (https://www.conventionalcommits.org/es/v1.0.0/); aclarar que `assets/` es material de consulta fuera de la instalación y que lo marcado como futuro no existe aún.
2. **Estado actual**: sin tags, sin `CHANGELOG.md` ni `VERSION`; título «MicroSDD 0.1» en `README.md`; versión vigente no publicada.
3. **API pública**: viñetas `- **API-NN** · <nombre>: <qué cubre>`:
   - API-01 CLI de `.microharness/sdd.py`: subcomandos `init`, `new`, `check` (`--run`, `--no-scope`), `approve` (`spec`/`close`, `--by`, `--evidence`), `review` (`APROBADO`/`RECHAZADO`, `--evidence`), `seal` (`--by`), `commit-check`; código de salida 0 en éxito y 1 en error.
   - API-02 Esquema de `spec.json` (`schema_version` 1): campos y valores que acepta `validate`.
   - API-03 Esquema de `.microharness/memory.json` (`schema_version` 1): `project` y `tasks` con aprobaciones, sellos, revisión, iteraciones y eventos.
   - API-04 Estructura de tarea `spec/<slug>/`: cuatro archivos, formato de slug y los tres estados.
   - API-05 Contratos de agentes en `.claude/agents/`: nombres, responsabilidades, frontmatter (`model`, `effort`, `tools`) y restricciones por rol de `.claude/hooks/pretool.py`.
   - API-06 `.claude/settings.json` (agente predeterminado, modelo, esfuerzo, registro del hook) y la skill `/sdd`.
   - API-07 Formato de mensaje aceptado por `commit-check`.
   - API-08 Conjunto de rutas instaladas (sección «Instalación»).
   - Párrafo «No forman parte de la API pública»: textos de mensajes de salida y error (sí sus códigos de salida), funciones internas de `sdd.py`, `tests/`, `README.md`, `assets/`, `CHANGELOG.md` y las specs y memoria del propio arnés.
   - Justificación: son los elementos de los que dependen un repositorio instalado, sus specs y memoria existentes y los hábitos del programador; cambiarlos de forma incompatible rompe instalaciones o tareas en curso.
4. **Reglas de incremento**: tabla y reglas:

   | Señal en el commit | Efecto en la API pública | Incremento (desde 1.0.0) |
   |---|---|---|
   | `!` en el asunto o pie `BREAKING CHANGE` | incompatible | MAJOR |
   | `feat` | funcionalidad compatible | MINOR |
   | `fix`, `perf` | corrección compatible | PATCH |
   | `docs`, `test`, `refactor`, `chore` | sin cambio de API | ninguno propio |

   - El tipo es una señal; manda el efecto real sobre API-01 a API-08. Un `docs` o `refactor` que cambie un contrato de agente de forma incompatible debe llevar `!`.
   - El release toma el mayor incremento entre los commits desde el último tag; MAJOR pone MINOR y PATCH a 0; MINOR pone PATCH a 0. Si solo hay commits sin incremento propio, no se publica versión.
   - Marcar lo incompatible con `!` en el asunto, porque `commit-check` solo valida una línea; el pie `BREAKING CHANGE:` puede añadirse en el cuerpo, pero `commit-check` se aplica solo a la primera línea.
5. **Fase 0.y.z**: la API puede cambiar; mientras la versión mayor sea 0, lo incompatible incrementa MINOR y `feat`, `fix` y `perf` incrementan PATCH. «MicroSDD 0.1» equivale a la línea `0.1.0`, aún no publicada; el primer tag será `v0.1.0`, creado por la primera tarea de release (no por esta).
6. **Criterios para declarar 1.0.0**: viñetas de una línea `- **C-NN** <criterio>. Verificación: <cómo>`:
   - C-01 API pública documentada y vigente (este documento coincide con el repositorio). Verificación: revisión independiente de la tarea de release 1.0.0.
   - C-02 Herramienta de release implementada. Verificación: su tarea en `memory.json` está `terminado` y `check --run` pasa.
   - C-03 Al menos un release 0.y.z completo con este proceso. Verificación: `git tag -l "v0.*"` no vacío y release visible en GitHub.
   - C-04 Evaluación del MVP de la sección 8 del `README.md` con tres tareas reales. Verificación: resultados registrados en `memory.json` como observaciones del proyecto.
   - C-05 Defectos de instalación conocidos (hook con `python3` en Windows; `core.quotePath` en la comprobación de alcance) corregidos o declarados como limitación en `README.md`. Verificación: tarea terminada o texto en `README.md`.
   - C-06 `CHANGELOG.md` con entrada para 1.0.0. Verificación: lectura del archivo en el commit del release.
   - C-07 Suite completa en verde. Verificación: `python -m unittest discover -s tests` con código 0 en el commit candidato.
   - C-08 Decisión humana explícita de declarar 1.0.0. Verificación: aprobación `spec` registrada en la tarea `release-v1-0-0`.
7. **Tags y prereleases**: tag anotado `vX.Y.Z` con `git tag -a vX.Y.Z -m "MicroSDD X.Y.Z"` sobre el commit de release en `main`; prereleases solo `vX.Y.Z-rc.N` (N ≥ 1), sin metadatos de compilación; expresión de referencia `^v(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)(-rc\.[1-9][0-9]*)?$`; un tag publicado no se mueve ni se borra (un error se corrige con una nueva versión PATCH); un tag local aún no publicado puede borrarse solo con autorización humana; push individual `git push origin vX.Y.Z`, nunca `git push --tags` ni `--force`.
8. **Release dentro del flujo MicroSDD**: lista numerada (al menos diez pasos):
   1. Precondiciones: `main` actualizado, árbol limpio, ninguna tarea en `proceso`, suite en verde.
   2. El líder crea `python3 .microharness/sdd.py new release-vX-Y-Z`.
   3. El autor especifica: commits desde el último tag (o desde el inicio si no hay), clasificación según «Reglas de incremento», versión propuesta, entradas de `CHANGELOG.md` y alcance (`CHANGELOG.md` y la fuente de versión).
   4. El humano aprueba la spec y la versión; el líder registra `approve release-vX-Y-Z spec`.
   5. El implementador aplica los cambios del alcance.
   6. El revisor dictamina y se ejecuta `check release-vX-Y-Z --run`; el líder registra `review`.
   7. El humano aprueba cierre, commit y creación del tag; el líder registra `approve release-vX-Y-Z close`.
   8. El líder valida `commit-check 'chore(release): vX.Y.Z'` y hace el commit atómico con stage explícito.
   9. El líder crea el tag anotado `git tag -a vX.Y.Z` sobre ese commit y lo muestra con `git show vX.Y.Z`.
   10. Solo con autorización explícita e independiente del humano: `git push origin main` y `git push origin vX.Y.Z`.
   11. Solo con autorización explícita: release de GitHub desde el tag existente, con las notas de la sección de `CHANGELOG.md` y marcado como prerelease si es `-rc.N`; lo crea el humano en la interfaz web o el líder con la CLI `gh` si está disponible y autorizada.
   12. El líder registra en `memory.json` una observación con el tag y el enlace del release.
   Mientras no exista la herramienta de release, los pasos 3 y 5 se hacen a mano; cuando exista, la tarea de release la usará sin saltarse aprobaciones.
9. **Instalación** (decisión H-06 del programador): una instalación copia todo el contenido versionado del arnés salvo `assets/`. `### Incluido`: frase «todo el contenido versionado salvo `assets/`» y lista de los elementos principales: `README.md`, `CLAUDE.md`, `.gitignore`, `.claude/settings.json`, `.claude/agents/` (cuatro agentes), `.claude/hooks/pretool.py`, `.claude/skills/sdd/SKILL.md`, `.microharness/sdd.py`, `.microharness/memory.json`, `docs/` (cuatro documentos generales), `spec/` y `tests/test_sdd.py`; cuando exista, `CHANGELOG.md` también se incluye por estar versionado. `### Excluido`: solo `assets/`, material de consulta. Como hecho, no como exclusión nueva: `.claude/settings.local.json` no se versiona porque figura en `.gitignore`, por lo que no forma parte del contenido copiado. Nota: revisar conflictos con archivos homónimos del repositorio destino (en especial `README.md`, `CLAUDE.md`, `.gitignore` y `.claude/settings.json`).
10. **Herramienta de release (futura)**: declarar que hoy no existe ni la herramienta, ni `CHANGELOG.md`, ni la fuente de versión; requisitos `- **R-NN**` que deberá cumplir:
    - R-01 Biblioteca estándar de Python y subcomando de `.microharness/sdd.py` (nombre a definir en su tarea).
    - R-02 Rechazar ejecución si el árbol no está limpio, la rama no es `main`, hay una tarea en `proceso` o el tag ya existe.
    - R-03 Proponer el incremento según «Reglas de incremento» y «Fase 0.y.z» leyendo los asuntos de commit desde el último tag; la versión final la confirma el humano.
    - R-04 Actualizar `CHANGELOG.md` (una sección `## [X.Y.Z] - AAAA-MM-DD` por versión, entradas agrupadas en «Incompatible», «Añadido», «Corregido» y «Otros») y la fuente única de versión, que deberá coincidir con el tag.
    - R-05 Crear el tag anotado solo tras la aprobación `close` registrada y validar el formato de la sección «Tags y prereleases».
    - R-06 No ejecutar `push` ni crear releases en GitHub; como máximo, imprimir los comandos para que el humano los autorice.
    - R-07 Código de salida 0 en éxito y 1 en error, coherente con API-01, con pruebas unitarias en `tests/`.
    - Fuente única de versión en el árbol (propuesta): constante en `.microharness/sdd.py` expuesta con `--version`, para que una instalación conozca su versión sin acceso a los tags.

### Corrección de `README.md`
Sustituir solo el primer párrafo de la sección 2 (una línea), conservando el resto del párrafo y de la sección. Redacción propuesta:

> Copia **el contenido** de esta carpeta a la raíz de un repositorio Git existente, salvo `assets/`, que es material de consulta y no forma parte de la instalación (ver el [proceso de versionado](https://github.com/lgzarturo/microsdd/blob/main/assets/proceso-versionado.md)); no copies una carpeta `microsdd-opus55/` dentro del proyecto. Revisa conflictos con `.claude/settings.json`, `CLAUDE.md` y otras reglas. Se recomienda un repositorio de prueba o una rama nueva con working tree limpio. Verifica antes los [requisitos mínimos](#1-requisitos-mínimos); Python 3 es indispensable.

El enlace usa la URL absoluta de GitHub porque `README.md` se instala y `assets/` no: una ruta relativa quedaría rota en la instalación.

### Verificación
Un `python -c` en `spec.json` comprueba AC-01 a AC-10 de forma estructural (títulos, identificadores consecutivos, términos obligatorios, diff del README por secciones frente a `git show HEAD:README.md`). Lo semántico (correspondencia de la tabla, ausencia de pasos sin autorización, ortografía) lo confirma el revisor. No se crean pruebas permanentes: el entregable es documentación.

### Alternativas descartadas
- Archivo `VERSION` o `CHANGELOG.md` en esta tarea: fuera de alcance; su contrato se fija como futuro (YAGNI hasta que exista el proceso de release real).
- Documentar el proceso en `docs/` o en `README.md`: `docs/` es contexto general instalado y el programador pidió `assets/`; el README solo recibe el enlace.
- Prereleases `alpha`/`beta`: sin necesidad observada; basta `rc.N`.
- Tags firmados (`git tag -s`): exige gestionar claves; no aporta autenticación nueva dentro del MVP. Puede revisarse antes de 1.0.0.
- Prueba unitaria permanente del documento: añadiría código fuera del alcance.

## Invariantes y riesgos
- Invariante: solo cambian `assets/proceso-versionado.md` y el primer párrafo de la sección 2 de `README.md`, además de `spec/proceso-versionado/` y `.microharness/memory.json`.
- Invariante: ninguna afirmación del documento sobre el estado actual carece de respaldo en el repositorio; lo no existente aparece solo en la sección futura o marcado como propuesta.
- Invariante: ningún paso documentado hace `push`, mueve tags ni publica sin autorización humana explícita.
- Riesgo: la URL de GitHub del README solo resuelve después de que el documento llegue a `main` en `origin` mediante un `push` autorizado. Mitigación: aceptado; hasta entonces el enlace devuelve 404, sin efecto sobre el arnés.
- Riesgo: al instalar todo lo versionado, el repositorio destino recibe `README.md`, `.gitignore`, `.microharness/memory.json` y `spec/` del propio arnés, con sus tareas e historial. Mitigación: decisión explícita del programador (H-06); el documento advierte revisar conflictos con archivos homónimos.
- Riesgo: `check` falla de forma espuria por la `ñ` de `diseño.md` si `core.quotePath` está activo. Mitigación: ejecutar con `core.quotePath=false` (defecto fuera de alcance).
- Efecto secundario: ninguno sobre código o pruebas; la suite no cambia.

### Decisiones del programador (comunicadas por el líder)
- H-01 Equivalencia de «0.1»: «0.1» = `0.1.0` no publicada; primer tag `v0.1.0` en la primera tarea de release.
- H-02 Criterios de 1.0.0: C-01 a C-08.
- H-03 Reglas en 0.y.z: incompatible → MINOR; `feat`/`fix`/`perf` → PATCH.
- H-04 Fuente de verdad de la versión: el tag anotado registra la publicación y una constante futura en `sdd.py` (`--version`) es la fuente en el árbol.
- H-05 `CHANGELOG.md`: obligatorio desde el primer release, en la raíz; al estar versionado, se incluye en la instalación (consecuencia de H-06).
- H-06 Conjunto instalado: todo el contenido versionado del arnés salvo `assets/`.
- H-07 Cambios incompatibles: `!` obligatorio en el asunto; pie `BREAKING CHANGE` opcional y fuera de `commit-check`.
- H-08 Prereleases: solo `-rc.N`.
- H-09 Autorizaciones: el tag local se autoriza junto con el cierre; `push` y release de GitHub requieren autorización separada; tags solo sobre `main`.
