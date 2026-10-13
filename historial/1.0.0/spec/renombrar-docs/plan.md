# CÓMO: diseño mínimo

## Situación comprobada
- `.microharness/sdd.py:21` define `DOCS = ('AGENT.md', 'arquitectura.md', 'convensiones.md', 'specificaciones.md')`; solo lo usa `ensure_init()` (líneas 166-175), que crea cada documento ausente con `# <nombre>\n\nPendiente de inspección.\n`, sin sobrescribir. `ensure_init()` también lo llaman `new` y `note` (si falta la memoria), bajo el lock de memoria.
- `scripts/limpiar_arnes.py:24` repite `DOCS`; lo usa en `validate()` (aborta si `docs/` tiene entradas fuera de `DOCS`) y en `archive()` (exige `docs == sorted(DOCS)` tras ejecutar `sdd.py init`).
- `src/microsdd/installer.py:30-31` `INIT_FILES` nombra los docs viejos; solo sirve para el `git add` sugerido. `install()` ejecuta `sdd.py init` con `capture_output=True` y descarta su salida (líneas 202-205). `MANIFEST` y `pyproject.toml` no incluyen `docs/` (los docs del destino los genera `init`).
- `.claude/agents/lider.md:9` y `CLAUDE.md:7` (que se distribuye como `CLAUDE.microsdd.md`) nombran los cuatro docs.
- `.claude/hooks/pretool.py` no nombra los docs: la coincidencia de `git grep` es la palabra «especificaciones» (contiene la subcadena). Lo mismo ocurre con `README.md:169` y la línea 1 de `docs/specificaciones.md`. No se tocan.
- `README.md:113` (`git add` de ejemplo) y `README.md:145-146` (árbol) nombran los docs viejos; la sección de instalación del README tiene la nota «Migración de `diseño.md` a `plan.md`», modelo para la nueva nota.
- `assets/decisiones-diseno.md` líneas 34, 76, 83, 97, 104 citan los docs viejos como evidencia vigente.
- `tests/test_installer.py:96` y `tests/test_limpiar_arnes.py:20` fijan los nombres viejos.
- Las pruebas usan repositorios temporales y copian `sdd.py`; ninguna lee los `docs/` reales de este repositorio, así que pasan igual antes y después del `git mv` del líder.
- `code_fingerprint()` incluye todo archivo del diff que case con `allowed_paths`; con `docs/**` en el alcance, cualquier edición de `docs/` posterior a la revisión invalida el cierre.

## Decisión y justificación
1. **`sdd.py`**: `DOCS` pasa a los nombres nuevos y se añade un único mapa `LEGACY_DOCS = {'convenciones.md': 'convensiones.md', 'especificaciones.md': 'specificaciones.md'}`. En `ensure_init()`, por cada documento:
   - si existe el antiguo y no el nuevo: no crear, imprimir `AVISO: docs/<antiguo> usa el nombre antiguo; no se crea docs/<nuevo>. Migra con: git mv docs/<antiguo> docs/<nuevo>`;
   - si existen ambos: no tocar, imprimir `AVISO: existen docs/<antiguo> y docs/<nuevo>; fusiona el contenido en docs/<nuevo> y elimina docs/<antiguo>`;
   - si no existe ninguno: crear el nuevo como hasta ahora.
   Código de salida 0 (el instalador exige `init` con éxito). Justificación: es la opción más segura (no mueve archivos del usuario, que pueden estar versionados o tener cambios locales) y la más simple (sin script de migración ni lógica de fusión); evita que coexistan dos documentos con el mismo papel.
2. **`scripts/limpiar_arnes.py`**: `DOCS` pasa a los nombres nuevos y se añade `LEGACY_DOCS = ('convensiones.md', 'specificaciones.md')`; `validate()` acepta `DOCS + LEGACY_DOCS`; `archive()` sigue comparando con `sorted(DOCS)` (nuevos), porque tras borrar `docs/` el `init` crea los nuevos. Así un release migra de forma natural. No se importa desde `sdd.py`: el script no se distribuye y `sdd.py` debe seguir autocontenido; la duplicación es de dos tuplas cortas.
3. **Instalador**: `INIT_FILES` con los nombres nuevos (el antiguo, si existe, ya es del usuario y no lo crea el instalador). Tras `init`, imprimir las líneas de su salida estándar que empiecen por `AVISO:` (decodificadas UTF-8 con `errors='replace'`); sin esto el aviso de REQ-02 nunca llegaría al usuario que instala con `uvx`. No cambian `MANIFEST` ni `pyproject.toml`.
4. **`lider.md` y `CLAUDE.md`**: nombrar los nuevos y añadir «si no existen, sus nombres antiguos `docs/convensiones.md` / `docs/specificaciones.md`». Justificación: proyectos actualizados con `--force` reciben el `lider.md` nuevo pero conservan los docs antiguos; sin la alternativa, el líder los daría por ausentes. Es una frase, no una capa.
5. **README**: nombres nuevos en el árbol y en el `git add`; nota «Migración de nombres de `docs/`» junto a la de `plan.md`: actualizar con `--force`, `git mv docs/convensiones.md docs/convenciones.md` y `git mv docs/specificaciones.md docs/especificaciones.md`; hasta entonces `init` avisa y no duplica.
6. **`assets/decisiones-diseno.md`**: actualizar las cinco rutas de evidencia (son referencias vigentes, no historial).
7. **Docs de este repositorio (líder)**: `git mv docs/convensiones.md docs/convenciones.md`, `git mv docs/specificaciones.md docs/especificaciones.md` y la fila de la tarea en el índice; opcionalmente una línea en `docs/arquitectura.md` sobre la compatibilidad.

### Orden propuesto
1. Líder, tras aprobar la spec y antes de pasar a `proceso`/delegar: los dos `git mv` (y, si quiere, la línea de `arquitectura.md`). Las pruebas no dependen de `docs/` reales, así que no se rompen; el repositorio queda coherente con el `CLAUDE.md` nuevo durante el trabajo.
2. Implementador: TDD sobre `tests/`, después `sdd.py`, `limpiar_arnes.py`, `installer.py`, `lider.md`, `CLAUDE.md`, README y `assets/`.
3. Líder, **antes de pedir la revisión**: fila del índice en `docs/especificaciones.md`. Cualquier edición de `docs/` posterior al dictamen del revisor cambia `code_fingerprint` y exige revisión nueva.

### Alternativas descartadas
- Renombrar automáticamente en `init`: mueve archivos del usuario, puede chocar con cambios no confirmados y con Git; más riesgo que valor.
- Crear siempre el nombre nuevo además del antiguo: duplica documentos y deja al líder sin fuente única.
- Script de migración (como `migrar_plan_md.py`): aquí no hay huellas que recalcular; dos `git mv` bastan (YAGNI).
- Enlaces simbólicos o lectura indistinta en el hook: el hook no lee docs; innecesario.
- Mantener los nombres viejos: el programador autorizó la corrección.

## Invariantes y riesgos
- Invariantes: `init` nunca sobrescribe, mueve ni borra documentos; sigue siendo idempotente; código 0 con avisos. `MANIFEST`/wheel sin cambios (AC-10 del instalador). `limpiar_arnes` sigue abortando ante entradas desconocidas.
- Efecto secundario: el aviso se repite en cada `init`, `new` y `note` (cuando este llama a `init`) hasta que el usuario migre. Es deseable como recordatorio y no altera códigos de salida.
- Efecto secundario: el instalador imprime líneas adicionales (`AVISO:`); ninguna prueba compara la salida completa (a verificar por el implementador).
- Riesgo: falsos positivos de `git grep` por la subcadena «especificaciones»; usar `-w` (AC-10).
- Riesgo: conflicto con `bloquear-autoaprobacion` (mismos archivos `sdd.py`, `lider.md`); ejecutar en serie y rebasar el texto de `lider.md:9`.
- Riesgo: edición de `docs/` tras la revisión invalida la huella de cierre (ver orden).
- Riesgo: el implementador edita `.microharness/sdd.py`, `.claude/agents/lider.md` y `CLAUDE.md` por Bash; el revisor debe comprobar que el diff de esos archivos se limita a lo descrito.
- Mutación desactivada: la lógica nueva son tres ramas en `ensure_init()` y una tupla ampliada, cubiertas por pruebas de casos límite.
