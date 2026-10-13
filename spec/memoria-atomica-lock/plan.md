# CÓMO: diseño mínimo

## Situación comprobada

Hechos verificados en el repositorio (rama `main`, commit `bae6622`):

- `.microharness/sdd.py`:
  - `dump(path, data)` hace `mkdir` del padre y `path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')`. No es atómico.
  - `dump` se usa para `memory.json` en `ensure_init`, `new`, `approve`, `review`, `seal` y `note`, y para `spec/<slug>/spec.json` en `new`, `approve` y `review`.
  - `load` hace `json.loads(read_text)`.
- Ciclos leer-modificar-escribir sin coordinación:
  - `new` llama a `ensure_init`, luego a `load(MEMORY)` y a `dump`.
  - `approve`, `review` y `seal` leen con `task_files` y luego hacen `dump`.
  - `note` llama a `ensure_init` si falta `MEMORY`, luego hace `load` y `dump`.
  - `approve close` ejecuta `validate(run=True)`, que corre las pruebas con timeout de 300 s por comando, antes de escribir.
- `main()` captura `OSError`, `ValueError`, `KeyError`, `TypeError` y `JSONDecodeError`, imprime `ERROR: …` y devuelve 1.
- Imports actuales: `argparse`, `hashlib`, `json`, `re`, `subprocess`, `sys`, `datetime` y `pathlib`. No importa `os`.
- Pruebas (`tests/test_sdd.py`):
  - Cargan `sdd.py` con `importlib` y redirigen `sdd.ROOT` y `sdd.MEMORY` en `setUp`.
  - `ReleaseProposeTests` crea un repo Git temporal sin `.gitignore` y hace `git add -A` tras `ensure_init`.
  - `NoteTests` usa `run_main` con `argv` parcheado.
- `release_propose` rechaza cualquier ruta de `git status --porcelain` que no empiece por `spec/` ni sea `.microharness/memory.json`.
- `.gitignore` actual: `.claude/settings.local.json`, `__pycache__/`, `*.pyc`, `.coverage`, `.pytest_cache/` y `.mutmut-cache/`. No incluye `memory.lock` (`git check-ignore` devuelve 1).
- Instalador (`src/microsdd/installer.py`):
  - `MANIFEST` y `force-include`/`sdist include` de `pyproject.toml` son listas explícitas, así que `memory.lock` nunca se distribuye.
  - Ejecuta `sdd.py init` en el destino, que a partir de ahora creará `memory.lock` allí.
  - «Próximos pasos» solo lista `INIT_FILES`.
  - `tests/test_installer.py` compara instantáneas por bytes entre dos instalaciones. El lock vacío no cambia esos bytes.
- `scripts/limpiar_arnes.py` no escribe `memory.json`: lo archiva con `copy2`, lo borra y ejecuta `sdd.py init`. `scripts/migrar_plan_md.py` sí lo escribe con `write_text`, pero es una migración puntual y no se distribuye.
- La tarea `bloquear-autoaprobacion`, en estado pendiente, también modifica `.microharness/sdd.py` (`main()`) y el hook. Según su riesgo R-01, después de ella el implementador ya no podrá modificar `sdd.py` por Bash.
- Referencia no confiable (parche externo sobre una base antigua, `b19fe30`): propone el mismo diseño (`mkstemp` + `fsync` + `os.replace`, `memory_lock()` reentrante con `LOCK_TIMEOUT` y un decorador `@locked`), pero no envuelve `note` (no existía), no conserva permisos y usa `os.fdopen` en modo texto. Se adapta según los puntos siguientes.

## Decisión y justificación

Todo en `.microharness/sdd.py`, sin módulos nuevos.

1. **`dump` atómico.** Pasos:
   - `mkdir` del padre (como hoy).
   - `fd, tmp = tempfile.mkstemp(prefix=f'.{path.name}.', suffix='.tmp', dir=path.parent)`.
   - Escribir con `os.fdopen(fd, 'w', encoding='utf-8')`. Es texto con `newline` por defecto, igual que `write_text`, de modo que los bytes por plataforma no cambian (en Windows, CRLF como hoy; las huellas ya normalizan CRLF).
   - `flush`, luego `os.fsync`.
   - Permisos: con `path` existente, `os.chmod(tmp, stat.S_IMODE(path.stat().st_mode))`. Si no existe, `0o666 & ~umask`, leyendo la umask con `os.umask(0)` y restaurándola de inmediato (el CLI es de un solo hilo). Hace falta porque `mkstemp` crea con `0o600` y, sin esto, `memory.json` y `spec.json` cambiarían de modo.
   - `os.replace(tmp, path)`.
   - Ante cualquier excepción (`BaseException`, que incluye `KeyboardInterrupt`), `os.unlink(tmp)` dentro de `contextlib.suppress(OSError)` y luego `raise`.
   - Después, si `os.name != 'nt'`: `fsync` del directorio (`os.open(dir, os.O_RDONLY)`, `os.fsync`, `os.close`) dentro de `suppress(OSError)`.

   La atomicidad se aplica igual a `spec.json`. No tiene efectos indeseados: el temporal vive unos milisegundos en `spec/<slug>/` con un nombre ASCII, que `validate` tolera; los bytes y los permisos se conservan, y la huella `spec_fingerprint` lee el contenido, no metadatos.

2. **Lock.** Un único context manager `memory_lock()` con `@contextlib.contextmanager` y una constante de módulo `LOCK_TIMEOUT = 10.0`:
   - Reentrancia: el contador de módulo `_LOCK_DEPTH`. Si es mayor que 0, se incrementa, se cede el control (`yield`) y se decrementa en el `finally`.
   - Si no, `MEMORY.parent.mkdir(parents=True, exist_ok=True)` y se abre `MEMORY.parent / 'memory.lock'` en modo `'a+b'`. La ruta se calcula en la llamada, así que respeta la redirección de las pruebas.
   - Adquisición no bloqueante con reintento cada 0,05 s hasta `time.monotonic() + LOCK_TIMEOUT`. En POSIX, `fcntl.flock(fd, LOCK_EX | LOCK_NB)`. En Windows, `handle.seek(0)` y `msvcrt.locking(fd, LK_NBLCK, 1)`. Los imports `fcntl` y `msvcrt` se hacen dentro de la rama de cada plataforma.
   - Al vencer el plazo: `ValueError(f'No se pudo obtener {lock} en {LOCK_TIMEOUT:g} s: otro proceso de sdd.py está modificando la memoria; reintenta.')`. `main` la convierte en `ERROR:` y código 1.
   - Liberación en el `finally`: `_LOCK_DEPTH = 0` y luego `LOCK_UN` o `LK_UNLCK`. El archivo se cierra al salir del `with open`.

3. **Aplicación.** Se decoran `ensure_init`, `new`, `approve`, `review`, `seal` y `note` con `@memory_lock()`. Un generador decorado con `contextlib.contextmanager` es un `ContextDecorator` y crea un context manager nuevo en cada llamada. Así se evita un decorador `locked` adicional y no se reescribe el cuerpo de las funciones. Si el revisor lo prefiere por legibilidad, se admite un `locked` de 4 líneas con `functools.wraps`, con el mismo comportamiento.

4. **`release_propose`.** Se añade `'.microharness/memory.lock'` a las rutas toleradas en el filtro `outside`, junto a `.microharness/memory.json`. Es un cambio de una expresión, sujeto a D-01.

5. **`.gitignore`.** Se añade la línea `.microharness/memory.lock`.

6. **Imports nuevos:** `contextlib`, `os`, `stat`, `tempfile` y `time`, todos de la biblioteca estándar. `functools` solo si se usa `locked`.

7. **Documentación (la escribe el líder al cierre):** una viñeta en `docs/arquitectura.md` con el invariante «`dump` es atómico; las mutaciones de memoria se serializan con `.microharness/memory.lock`». La fila de `docs/specificaciones.md` también la gestiona el líder; el chequeo de alcance ignora `docs/`.

## Alternativas descartadas

- **Lock con `O_CREAT | O_EXCL` y borrado al terminar:** si el proceso muere deja un lock huérfano y obliga a detectar locks obsoletos. `flock` y `msvcrt` se liberan solos al morir el proceso.
- **Lock dentro de `dump` o `load`:** no protege el ciclo leer-modificar-escribir, que es donde se pierden eventos.
- **Decorar `validate` o `check`:** son de solo lectura y `os.replace` garantiza que siempre leen un JSON completo. Bloquearlos haría esperar al revisor sin motivo.
- **Que `approve close` tome el lock solo para la escritura final, releyendo la memoria tras las pruebas:** reduce el tiempo de retención, pero obliga a reescribir `approve` y contradice la consigna de solo envolver. Queda como riesgo R-03.
- **Dependencias (`filelock`, `portalocker`):** prohibidas por la regla de usar solo la biblioteca estándar.
- **Que el instalador añada `memory.lock` al `.gitignore` del destino:** requiere tocar `installer.py`, cambia archivos que el instalador hoy no toca y no evita el problema en `release propose` si el usuario no versiona `.gitignore`. Se cubre con D-01 en `sdd.py`.

## Invariantes y riesgos

Invariantes:

- Los bytes que escribe `dump` son idénticos a los de la versión anterior en cada plataforma. Las huellas, los sellos y las pruebas existentes no cambian.
- `memory.json` y `spec.json` nunca quedan truncados por un fallo de `dump`: el contenido es el anterior completo o el nuevo completo.
- Solo hay un lock por directorio de memoria. Siempre se libera al salir, también con excepción. Un proceso que muere lo libera el sistema operativo.
- Las funciones de solo lectura no toman el lock.
- `memory.lock` no se distribuye (el manifiesto es explícito) ni se versiona en este repositorio.

Riesgos:

- **R-01, Windows y `os.replace`:** en Windows, `os.replace` falla con `PermissionError` si otro proceso tiene abierto el destino sin `FILE_SHARE_DELETE` (editor, indexador, antivirus o un `git` simultáneo). Efecto: `dump` falla, el temporal se borra, el original queda intacto y el CLI devuelve 1 con `ERROR:`. No se reintenta (YAGNI). Si se observa en la práctica, la solución sería un reintento corto. La rama `msvcrt` no se puede ejecutar en las pruebas de este entorno (Linux): solo se revisa y queda pendiente comprobarla manualmente en Windows 11 + Git Bash.
- **R-02, escritura en dos pasos en `approve` y `review`:** el lock evita las carreras entre procesos, pero no la incoherencia si el proceso muere entre los dos `dump`. Es un riesgo previo y queda fuera de alcance.
- **R-03, lock largo en `approve close`:** se mantiene durante `validate(run=True)`, hasta 300 s por comando. Un `note` o `review` concurrente fallará por timeout a los 10 s con un error claro. Si una suite de pruebas invocara comandos de `sdd.py` que mutan la memoria sobre el mismo repositorio, fallaría por timeout (sin interbloqueo indefinido). Las pruebas de este repositorio usan directorios temporales.
- **R-04, temporales huérfanos:** si el proceso muere con `SIGKILL` entre `mkstemp` y `os.replace`, queda `.memory.json.XXXX.tmp` o `.spec.json.XXXX.tmp`. No se ignoran en Git (YAGNI) y se ven en `git status`. `release propose` los rechazaría en `.microharness/`, lo que es aceptable porque obliga a revisarlos.
- **R-05, `flock` en sistemas de archivos de red o WSL `/mnt/c`:** puede no ser efectivo. Se documenta y no se mitiga.
- **R-06, cambio de modo de archivos:** se mitiga conservando el modo (REQ-03). Git solo registra el bit de ejecución, que de todos modos no cambia.
- **R-07, `memory.lock` sin ignorar en los proyectos instalados:** aparece como archivo sin rastrear en `git status`. Mitigado para `release propose` por D-01. Para el usuario es ruido visual hasta que lo añada a su `.gitignore`. Se podría documentar en el README, pero queda fuera de alcance salvo que el líder decida otra cosa.
- **R-08, orden con `bloquear-autoaprobacion`:** ambas tareas modifican `sdd.py`. Si aquella se cierra antes, el implementador ya no podrá aplicar esta por Bash y hará falta otra decisión humana (parche aplicado por el humano). Conviene implementar esta primero o secuenciarlas de forma explícita.
- **R-09, `mock.patch.object(sdd.os, …)` es global:** `sdd.os` es el módulo `os`. Al parchear `os.open` para AC-05 hay que discriminar por argumento, porque `mkstemp` también lo usa.

Decisiones pendientes para el líder:

- **D-01 (material, no bloquea el resto):** ¿se acepta tolerar `.microharness/memory.lock` en `release propose` (REQ-12 y AC-13)? Recomendación: sí, porque sin ello `release propose` falla en cualquier proyecto instalado tras el primer `sdd.py init`. Si se rechaza, se eliminan REQ-12 y AC-13 y R-07 pasa a ser una limitación documentada.
- **D-02 (menor):** los permisos de los archivos nuevos se calculan con `0o666 & ~umask` mediante `os.umask` (lectura y restauración). La alternativa es fijar `0o644`. Recomendación: `umask`, porque replica a `write_text`.
