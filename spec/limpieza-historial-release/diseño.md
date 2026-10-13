# CÓMO: diseño mínimo

## Situación comprobada
Hechos leídos en este worktree (2026-10-12):
- `.microharness/sdd.py:14-16`: `ROOT = Path(__file__).resolve().parent.parent`; `MEMORY = ROOT/.microharness/memory.json`; `DOCS = ('AGENT.md', 'arquitectura.md', 'convensiones.md', 'specificaciones.md')`.
- `.microharness/sdd.py:23-25`: `dump` escribe JSON con `ensure_ascii=False`, `indent=2` y salto final.
- `.microharness/sdd.py:47-56`: `ensure_init()` crea `docs/` y `spec/`, escribe cada doc **solo si falta** (`# <nombre>\n\nPendiente de inspección.\n`) y crea `memory.json` **solo si falta** (`schema_version 1`, `observations`/`decisions` vacíos, `tasks` vacío). Imprime un mensaje. No borra nada.
- `.microharness/sdd.py:346`: el subcomando `init` llama a `ensure_init()` y devuelve 0; no hay subcomando de limpieza.
- El estado de una tarea vive en `spec/<slug>/spec.json` (`state`, `sdd.py:18`); `memory.json.tasks` no guarda estado.
- Estado actual de memoria: tareas `instalador-uvx` (sin directorio `spec/` en este worktree), `fix-sdd-rutas-unicode` (`terminado`) y `limpieza-historial-release` (`pendiente`). Ejecutar hoy la herramienta aquí debe abortar por D3, lo cual es el comportamiento esperado.
- `git ls-files spec` incluye `spec/.gitkeep` (git no versiona directorios vacíos).
- `docs/` contiene hoy solo los 4 documentos; `docs/specificaciones.md:12-15` incluye una tabla de historial de tareas.
- `sdd.py validate` (`sdd.py:236-241`) ignora en el control de alcance las rutas que empiezan por `spec/`, `docs/`, `.microharness/` y `CLAUDE.md`; por eso el alcance de esta tarea se limita a `scripts/limpiar_arnes.py` y `tests/test_limpiar_arnes.py`.
- `.claude/hooks/pretool.py:29-47`: el implementador no puede editar `.claude/`, `.microharness/`, `docs/`, `spec/` ni `CLAUDE.md`, y solo rutas que cumplan `scope.allowed_paths`. El hook busca specs con `root.glob('spec/*/spec.json')`, por lo que las copias en `historial/<v>/spec/` no interfieren.
- No existe `scripts/` ni `historial/`. `.gitignore` ignora `.claude/settings.local.json`, `__pycache__/`, `*.pyc`, `.coverage`, `.pytest_cache/` y `.mutmut-cache/`.
- `tests/test_sdd.py:1-52`: patrón de carga por ruta con `importlib.util`, `tempfile.TemporaryDirectory` y helper `git_repo` (`git init`, `config user.*`, commit con `-c commit.gpgsign=false --no-verify`).
- En esta máquina `git config core.autocrlf` = `true` y `python3` es el stub de Microsoft Store; `python` es 3.12.3.

Supuestos (no comprobables desde este worktree):
- S1: el manifiesto del instalador `uvx` (tarea `instalador-uvx`, en otro checkout) no incluye `scripts/` ni `historial/` (D1, D4).
- S2: el mantenedor ejecuta la herramienta desde un checkout con todas las tareas cerradas y comprometidas, justo antes de etiquetar el release.

## Decisión y justificación
Un único módulo `scripts/limpiar_arnes.py` (stdlib: `argparse`, `json`, `os`, `re`, `shutil`, `subprocess`, `sys`, `pathlib`) con una función de entrada `main(argv: list[str] | None = None, root: Path | None = None) -> int`; `root` por defecto es `Path(__file__).resolve().parent.parent`. El bloque `if __name__ == '__main__': sys.exit(main())`. El docstring del módulo y `--help` documentan uso, efectos y próximos pasos.

Flujo (todas las validaciones antes de la primera escritura):
1. `argparse`: posicional `version`, opción `--dry-run`. Uso inválido → `SystemExit(2)`.
2. Validar versión con `re.fullmatch(r'(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(-[0-9A-Za-z-]+(\.[0-9A-Za-z-]+)*)?', version)`. Se usa `fullmatch` y no `match` con `$`, porque `$` acepta un salto de línea final. La regex excluye `/`, `\`, `..` y `+`, lo que impide rutas inseguras. Fallo → código 1 (no 2: el 2 es solo de argparse).
3. Existe `<root>/.microharness/sdd.py`.
4. Git, siempre con `cwd=root` y un entorno copia de `os.environ` sin `GIT_DIR`, `GIT_WORK_TREE` ni `GIT_INDEX_FILE` (heredadas, p. ej. desde un hook, tienen prioridad sobre `cwd`):
   - `git rev-parse --show-toplevel` devuelve 0 y su salida, como `Path(...).resolve()`, es igual a `root.resolve()` (rechaza una raíz que es subdirectorio de otro repositorio; no se usa la existencia de `.git` porque en un worktree es un archivo).
   - `git status --porcelain` está vacío.
   - `git status --porcelain --ignored -- docs spec .microharness/memory.json` está vacío. `git status --porcelain` no informa de ignorados (`.gitignore` ignora `__pycache__/`, `*.pyc`, `.coverage`, `.pytest_cache/`, `.mutmut-cache/`); un ignorado en esas rutas se copiaría a un historial que tampoco lo versiona y se borraría sin que git pueda recuperarlo. Se limita a esas rutas (no a `.microharness/` completo ni al árbol entero) porque `.microharness/__pycache__/` y `tests/__pycache__/` aparecen legítimamente al ejecutar las pruebas y no se tocan.
   - `OSError` al lanzar `git` (no está en el PATH) → código 1 con mensaje, sin traza.
5. `historial/<v>` no existe y `historial`, si existe, es directorio y no enlace simbólico.
6. `memory.json` existe, no es enlace simbólico, es JSON válido y `tasks` es un objeto (`dict`).
7. `docs/` solo contiene nombres de los 4 documentos (los que falten simplemente no se archivan; `init` los recrea). Un `docs/` o `spec/` ausente equivale a vacío: no se lista ni se archiva, e `init` los recrea.
8. Ninguna ruta del plan es enlace simbólico: `docs/`, `spec/`, cada entrada de `docs/` y todo directorio o archivo bajo `spec/` recorrido con `os.walk` (que por defecto no sigue enlaces), comprobando `Path.is_symlink()`. Se rechaza en vez de copiar con `symlinks=True` porque `copytree` por defecto seguiría el enlace e introduciría contenido externo en un historial versionado, y `rmtree` falla sobre enlaces a directorio después de copiar (fallo parcial). Fallo → código 1.
9. Tareas = claves de `tasks` ∪ subdirectorios de `spec/`; abierta si no hay `spec/<slug>/spec.json` legible con `state == "terminado"`. Si hay abiertas → código 1 listando `slug: motivo`.
10. Plan: lista de rutas origen (memory.json, docs existentes, entradas de `spec/` salvo `.gitkeep`) y su destino en `historial/<v>/`. Con `--dry-run`: imprimir plan y devolver 0.
11. Copiar (`shutil.copy2` para archivos, `shutil.copytree` para directorios; sin enlaces simbólicos por el paso 8).
12. Verificar byte a byte cada archivo copiado (`read_bytes()` igual). Diferencia → código 1 sin borrar originales.
13. Borrar originales: entradas de `spec/` salvo `.gitkeep` (`shutil.rmtree`/`unlink`), los docs archivados y `memory.json`.
14. `subprocess.run([sys.executable, str(root/'.microharness'/'sdd.py'), 'init'], cwd=root)`; código distinto de 0 → fallo.
15. Si falta `spec/.gitkeep`, crearlo vacío.
16. Verificación posterior estructural: existen los 4 docs y `memory.json`, `docs/` contiene solo esos 4 y `spec/` solo `.gitkeep`. No se compara contenido contra una plantilla para no duplicar el texto de `ensure_init` (D2); el contenido queda garantizado por construcción (se borraron los originales y `init` solo escribe lo que falta) y las pruebas lo comparan contra un `init` real (AC-02).
17. Imprimir próximos pasos: `git add -- historial/<v> docs spec .microharness/memory.json` (en git >= 2.0 un pathspec explícito también prepara los borrados) y `git commit -m "chore(release): archiva historial <v>"`, indicando que la herramienta no hace commit, tag ni push.

Errores a partir del paso 11 (`OSError`, fallo de verificación o de `init`) → mensaje a `stderr` con remediación: `git restore --source=HEAD --staged --worktree -- docs spec .microharness/memory.json` y eliminar `historial/<v>/`; código 1. Mensajes de error y de salida en español neutro.

Docs con entradas desconocidas → fail-closed (preferencia del líder, adoptada): no se puede garantizar el estado inicial de `init` sin borrar contenido que el arnés no generó, y archivarlo en silencio podría ocultar documentación que sí debe distribuirse.

Entradas de `spec/` que no son directorios (salvo `.gitkeep`) se archivan y eliminan igual que las tareas: `spec/` solo debe contener `.gitkeep` tras la limpieza.

## Alternativas descartadas
- Subcomando `sdd.py clean`/`release`: viola D4 y choca con la tarea `deteccion-python-multiplataforma` que modificará `sdd.py`; además se distribuiría a los proyectos instalados, donde no tiene sentido.
- Copiar el texto de las plantillas en el script: duplica `ensure_init` (viola D2) y divergiría cuando cambien las plantillas.
- Importar `sdd.py` y llamar a `ensure_init()` en proceso: obliga a reasignar `ROOT`/`MEMORY` globales (acoplamiento a detalles internos); ejecutar el `sdd.py` del repositorio destino con `sys.executable` es la interfaz pública y respeta su `ROOT` derivado de `__file__`.
- Mover (`shutil.move`) en vez de copiar-verificar-borrar: más corto, pero un fallo a mitad dejaría datos repartidos sin verificación. La copia verificada mantiene los originales hasta comprobar el historial.
- Rollback propio: YAGNI; el paso 4 exige árbol limpio y ningún ignorado en las rutas archivadas, y el paso 8 excluye enlaces, así que todo lo que se borra está versionado en `HEAD` y git lo recupera por completo.
- Copiar enlaces simbólicos con `copytree(symlinks=True)`: conserva el enlace, pero `rmtree` sigue fallando sobre enlaces a directorio y el historial versionaría enlaces a rutas del mantenedor; rechazarlos es más simple.
- Comprobar ignorados en todo el árbol (`git status --porcelain --ignored`): abortaría siempre por `__pycache__/` legítimos fuera de las rutas archivadas.
- Usar `python3` en el subproceso o en el comando de pruebas: falla en la máquina del mantenedor.
- Archivar `docs/` con entradas desconocidas o dejarlas en su sitio: ver justificación fail-closed arriba.

## Invariantes
- I1: ninguna escritura ocurre antes de que pasen todas las validaciones 1-9; `--dry-run` nunca escribe.
- I2: ningún original se borra antes de verificar byte a byte su copia en el historial.
- I3: solo se escriben o borran rutas bajo `historial/<v>/`, `docs/` (los 4 nombres), `spec/` y `.microharness/memory.json`; nunca se sigue un enlace simbólico.
- I4: la herramienta no ejecuta `git add`, `commit`, `tag` ni `push`; solo `git rev-parse --show-toplevel` y `git status --porcelain [--ignored]`, con el entorno saneado del paso 4.
- I7: todo archivo que se borra está rastreado y sin cambios respecto a `HEAD` (pasos 4 y 8).
- I5: el estado inicial lo produce exclusivamente `sdd.py init` del repositorio destino.
- I6: las pruebas no ejecutan la herramienta sobre el repositorio real; siempre pasan `root` a un directorio temporal.

## Riesgos
- R1: finales de línea. `ensure_init` usa `write_text` en modo texto: en Windows escribe CRLF y con `core.autocrlf=true` git normaliza a LF. Las pruebas comparan contra un `init` ejecutado en la misma plataforma, por lo que son consistentes; el diff del commit de release depende de la configuración de git del mantenedor. Mitigación: no se altera; se documenta.
- R2: criterio de terminado. Una spec con `state: terminado` puesto a mano sin aprobación de cierre pasaría la validación. Mitigación: fuera de alcance por D3; `sdd.py check` sigue siendo el control de cierre.
- R3: S1 no verificado. Si el manifiesto `uvx` incluyera `historial/` o `scripts/`, se distribuiría el historial. Mitigación: verificarlo en la tarea `instalador-uvx`.
- R4: fallo parcial en Windows (archivo bloqueado por otro proceso o de solo lectura: `unlink`/`rmtree` lanzan `PermissionError` tras la copia). Mitigación: se captura como `OSError` → código 1 y remediación con git (REQ-12, AC-12); no se añade lógica para quitar el atributo de solo lectura (YAGNI).
- R5: prueba de `init` fallido (AC-12) requiere sustituir la copia de `sdd.py` en el repo temporal **antes del commit inicial** para que el árbol quede limpio.
- R6: entorno heredado. `GIT_DIR`, `GIT_WORK_TREE` y `GIT_INDEX_FILE` (p. ej. al ejecutar desde un hook de git) tienen prioridad sobre `cwd`: la herramienta consultaría otro repositorio y el helper de pruebas podría hacer commit en el repositorio real (violaría I6). Mitigación: tanto la herramienta como el helper de pruebas ejecutan `git` con una copia de `os.environ` sin esas tres variables.
- R7: `git` ausente del PATH no es probable en la máquina del mantenedor; se cubre con el manejo de `OSError` del paso 4, sin AC dedicado (simularlo exige manipular el PATH del proceso de pruebas).

## Efectos secundarios
- Tras usar la herramienta en el repositorio real, `docs/specificaciones.md` y demás docs vuelven a «Pendiente de inspección.»; el contexto del desarrollo del arnés queda solo en `historial/<v>/`. El líder y los agentes del siguiente ciclo deberán reinspeccionar.
- Las copias en `historial/<v>/spec/` no las ve `sdd.py` ni el hook (solo miran `spec/`).
