# CÓMO: diseño mínimo

## Situación comprobada
- Literales en `new()` (líneas 164-165) y en `validate()` (306-309) de `.microharness/sdd.py`. No hay otro lugar del código que lea el modelo.
- Precedente de configuración: `project.allowed_test_commands` vive en `memory.json`, pero `memory.json` es memoria mutada por `sdd.py` y `scripts/limpiar_arnes.py` la archiva y reinicia en cada release.
- `memory_lock()` deriva su ruta de `MEMORY.parent`; las pruebas solo reasignan `sdd.ROOT` y `sdd.MEMORY`.
- La tarea `bloquear-autoaprobacion` (pendiente) negará a todos los agentes editar `.microharness/` y mencionarlo por Bash fuera de formas permitidas.

## Decisión y justificación
- **Ubicación `.microharness/config.json`.** Junto al resto del arnés; cuando `bloquear-autoaprobacion` entre en vigor, solo el humano podrá escribirlo, así que ningún agente puede cambiar el modelo para pasar `check`. Se descartan: `microsdd.json` en la raíz (lo propone el análisis; ensucia la raíz y queda al alcance de las herramientas de edición del líder) y `memory.json` (`limpiar_arnes.py` lo reinicia en cada release y mezcla memoria con configuración).
- **Ruta derivada:** `MEMORY.parent / 'config.json'`, igual que `memory_lock()`; así las pruebas quedan aisladas sin otra constante parcheable.
- **Código (KISS):** constantes `DEFAULT_MODEL = 'claude-opus-5-5'`, `DEFAULT_EFFORT = 'medium'`, `EFFORTS = ('low', 'medium', 'high', 'xhigh', 'max')`, y una función `config() -> dict` que devuelve `{'model': …, 'effort': …}`: si el archivo no existe, los valores por defecto; si existe, lo carga y lanza `ValueError('… config.json: <motivo>')` si no es JSON válido (capturar `json.JSONDecodeError`), no es objeto, tiene claves distintas de `model`/`effort`, `model` no es cadena no vacía o `effort` no está en `EFFORTS`.
- `new()`: llamar a `config()` **antes** de `ensure_init()` y de crear el directorio, para no dejar escrituras parciales; usar sus valores en la plantilla.
- `validate()`: llamar a `config()` al inicio (un error de configuración es global y aborta con `ValueError`, que `main()` ya convierte en `ERROR:` y código 1; también afecta a `approve`, que llama a `validate`). Sustituir la comparación literal por `if s.get('state') != 'terminado' and s.get('model') != cfg['model']: errors.append(f"El modelo de spec.json ({s.get('model')}) no coincide con el configurado ({cfg['model']}) en .microharness/config.json")`. Mantener la validación de `effort` para todos los estados con `EFFORTS` y mensaje `Effort inválido; usa uno de: low, medium, high, xhigh, max`. No se compara `spec.effort` con el configurado: `effort` es preferencia por tarea (D-04) y el configurado solo es el valor inicial.
- **Instalador sin cambios:** la ausencia del archivo equivale a los valores actuales; distribuirlo obligaría a gestionar conflictos sobre un archivo humano y a tocar `MANIFEST`, `pyproject.toml` y AC-10 del instalador sin beneficio.
- **Settings y agentes:** solo documentación en README (sección 3 o 6). No se edita `.claude/` (el implementador no puede y la automatización es YAGNI).
- **Mini-eval:** `assets/eval-esfuerzo.md`, una página: objetivo, 5 tareas tipo (corrección localizada, regla nueva, refactor sin cambio de conducta, cambio de configuración/documentación, prueba de regresión), procedimiento (misma tarea con `medium` y `high`, mismo commit base, specs aprobadas idénticas), métricas (iteraciones de revisión, AC cumplidos, tokens y tiempo, defectos detectados por el humano) y criterio de lectura; con el aviso «Protocolo no ejecutado; no hay resultados». Opcional: una línea en README sección 8 que lo enlace.
- **Documentación de decisiones:** actualizar la decisión y la evidencia de D-04 en `assets/decisiones-diseno.md`; el líder añade una línea en `docs/arquitectura.md` al cierre.

## Archivos
- `.microharness/sdd.py`: constantes, `config()`, `new()`, `validate()`.
- `tests/test_sdd.py`: pruebas nuevas para AC-01..AC-06 (sin modificar las existentes).
- `README.md`, `assets/eval-esfuerzo.md` (nuevo), `assets/decisiones-diseno.md` (D-04).
- `docs/arquitectura.md`: solo el líder, al cierre.
- Sin cambios: `src/microsdd/installer.py`, `pyproject.toml`, `.claude/**`, `scripts/**`.

## Invariantes y riesgos
- Invariante: sin `config.json` la conducta observable de `new` y `check` es la actual, salvo el texto del error de modelo.
- Invariante: las tareas `terminado` no se invalidan al cambiar de modelo.
- Invariante: `check` no escribe nada; `config()` solo lee.
- **R-01, orden con `bloquear-autoaprobacion` (alto):** si se implementa antes, el implementador ya no podrá modificar `sdd.py` por Bash; esta tarea debería implementarse primero o el humano aplica el parche.
- **R-02, cambio de modelo con tareas abiertas (medio):** al cambiar `config.json`, las tareas `pendiente`/`proceso` fallan `check` hasta actualizar `spec.model`, lo que altera la huella y exige reaprobar. Es intencionado (el modelo forma parte del contrato aprobado); se documenta en README.
- **R-03, deriva entre fuentes (medio):** `config.json`, `settings.json` y el frontmatter pueden divergir; `check` solo valida `spec.json` contra `config.json`. Mitigación: documentación; no se automatiza.
- **R-04, error global:** un `config.json` inválido bloquea `check` de todas las tareas, incluidas las cerradas. Aceptable: el mensaje indica el archivo y el motivo.
- **R-05, cambio del texto de error:** desaparece «El modelo debe ser exclusivamente claude-opus-5-5»; ninguna prueba ni script lo busca (comprobado con grep en `tests/` y `scripts/`).
- Efecto secundario: `effort` en `spec.json` sigue sin afectar al runtime; README ya lo indica.

## Alternativas descartadas
- Comparar también `spec.effort` con el configurado: impediría ajustar el esfuerzo por tarea sin ganancia de control.
- Variables de entorno (`MICROSDD_MODEL`): no versionables y fáciles de alterar desde un agente.
- Generar `config.json` en `init`: añadiría estado por defecto que nadie necesita mientras el valor por defecto coincida.

## Decisiones abiertas (recomendación entre paréntesis)
- Q-01: ¿rechazar claves desconocidas en `config.json`? (Sí: detecta erratas como `efort` que dejarían el valor por defecto en silencio.)
- Q-02: ¿actualizar D-04 en `assets/decisiones-diseno.md` dentro de esta tarea? (Sí: si no, contradice el código.)
- Q-03: ¿dejar `.claude/agents/autor.md` línea 14 sin cambios? (Sí: `new` ya rellena el valor; se documenta como parte del cambio manual de modelo.)
