# PASOS: trabajo verificable

Estrategia TDD: primero las pruebas en rojo (RED) y después el cambio mínimo que las pone en verde (GREEN).

Archivos:
- `tests/test_sdd.py`: clase nueva `MemoryAtomicLockTests`, con `ROOT` y `MEMORY` redirigidos a un temporal igual que `NoteTests`; además, un caso en `ReleaseProposeTests` y otro en `GitAttributesTests` o en una clase equivalente que use la raíz real.
- `.microharness/sdd.py`: se modifica por Bash (decisión humana previa).
- `.gitignore`.

Las pruebas POSIX llevan `@unittest.skipIf(os.name == 'nt', …)`. Las que cambian `sdd.LOCK_TIMEOUT` lo restauran con `addCleanup`.

- [ ] T01 (AC-01, AC-02, AC-03): pruebas de atomicidad de `dump`.
  - Éxito: `os.replace` envuelto (`side_effect=os.replace`), con aserciones de una sola llamada, origen en el mismo directorio y `os.fsync` llamado. Bytes iguales a `(json.dumps(data, ensure_ascii=False, indent=2) + '\n')` escritos con `write_text` en un archivo de control. El directorio queda solo con `m.json`.
  - Fallo: `os.replace` lanza `OSError` con un archivo previo y sin él. Se repite con fallo en el primer `os.fsync`. En ambos casos el contenido previo queda intacto, el archivo no se crea si no existía y no quedan temporales.
  - CLI: `note --fact` con `os.replace` fallando devuelve código 1, `ERROR:` en stderr, `memory.json` igual y ningún temporal en `.microharness/`.
  - Confirmar RED: hoy `os.replace` no se llama y el fallo simulado no aplica.
- [ ] T02 (AC-04, AC-05): pruebas de permisos y de `fsync` del directorio.
  - Permisos (POSIX): un archivo existente con `0o640` lo conserva tras `dump`. Un archivo nuevo con `os.umask(0o022)`, restaurada en `addCleanup`, queda en `0o644`.
  - `fsync` del directorio: `os.open` parcheado con `side_effect` que lanza `OSError` solo cuando la ruta es el directorio padre y delega en el `os.open` real en los demás casos. `dump` termina sin error con el contenido nuevo.
  - Confirmar RED donde aplique (la de `0o644` puede pasar hoy; se mantiene como regresión).
- [ ] T03 (AC-06, AC-10): pruebas del lock retenido.
  - Tras `sdd.ensure_init()`, se comprueba que existe `sdd.MEMORY.parent / 'memory.lock'` dentro del temporal.
  - Con `fcntl.flock(LOCK_EX)` retenido por la prueba sobre ese archivo y `LOCK_TIMEOUT = 0.2`, se recorren con `subTest` las seis operaciones: `ensure_init`, `new('otra')`, `approve(slug, 'spec', 'P', 'ok')`, `review(slug, 'RECHAZADO', 'ev')`, `seal(slug, 'P')` y `note('f', None, None, 'e')`. Para cada una: `ValueError` con `memory.lock` en el mensaje, bytes de `memory.json` y `spec.json` sin cambios y `spec/otra/` inexistente.
  - Además, `main()` con `note` devuelve código 1 y stderr contiene `ERROR:` y `memory.lock`.
  - Preparar la tarea (slug con `spec.json` válido y `protected_tests`) antes de retener el lock.
  - Confirmar RED.
- [ ] T04 (AC-07, AC-08, AC-09): pruebas de espera, reentrancia y liberación.
  - Espera: con el lock retenido, un `threading.Timer(0.2)` lo libera (`LOCK_UN`). Con `LOCK_TIMEOUT = 5`, `note --fact` termina con éxito y la observación queda registrada.
  - Reentrancia: dentro de `with sdd.memory_lock():` y con `LOCK_TIMEOUT = 0.2`, `note` y `new` terminan con éxito.
  - Liberación: tras un `approve` con evidencia vacía (`ValueError`) y tras un `note` correcto, la prueba obtiene `flock(LOCK_EX | LOCK_NB)` sin error. Después, con el lock retenido, `note` vuelve a fallar por timeout.
  - Confirmar RED (`memory_lock` no existe).
- [ ] T05 (AC-11): prueba de solo lectura. Con el lock retenido y `LOCK_TIMEOUT = 5`, `main()` con `check <slug> --no-scope` termina en menos de 2 s (`time.monotonic`) con el mismo código que sin el lock. Puede pasar ya hoy; se mantiene como regresión.
- [ ] T06 (AC-13): en `ReleaseProposeTests`, sacar `memory.lock` del índice (`git rm --cached -q .microharness/memory.lock` y commit) o crearlo sin rastrear tras el commit inicial.
  - Comprobar que `release propose` propone la versión esperada con `memory.lock` sin rastrear.
  - Con `.microharness/otro.txt` sin rastrear, la rechaza nombrando ese archivo.
  - Confirmar RED en el primer caso. Sujeto a D-01: si el líder la rechaza, se omite este paso junto con T09.
- [ ] T07 (AC-12): prueba que, en la raíz real (`Path(__file__).resolve().parents[1]`), `git check-ignore -q .microharness/memory.lock` devuelve 0. Confirmar RED.
- [ ] T08 (AC-01 a AC-05): en `.microharness/sdd.py`, reescribir solo el cuerpo de `dump` según el punto 1 de `plan.md` y añadir los imports necesarios. Verificar GREEN de T01 y T02.
- [ ] T09 (AC-06 a AC-11, AC-13):
  - En `.microharness/sdd.py`, añadir `LOCK_TIMEOUT = 10.0`, `_LOCK_DEPTH = 0` y `memory_lock()` según el punto 2 de `plan.md`.
  - Decorar con `@memory_lock()` las seis funciones (`ensure_init`, `new`, `approve`, `review`, `seal` y `note`) sin cambiar su cuerpo.
  - Añadir `'.microharness/memory.lock'` a las rutas toleradas por `release_propose`.
  - Ningún otro cambio. Verificar GREEN de T03 a T06.
- [ ] T10 (AC-12): añadir `.microharness/memory.lock` a `.gitignore`. Verificar GREEN de T07.
- [ ] T11 (AC-14):
  - Ejecutar `sh .microharness/python.sh -m unittest discover -s tests -v` y comprobar código 0, sin cambiar aserciones de pruebas existentes.
  - Ejecutar `sh .microharness/python.sh .microharness/sdd.py check memoria-atomica-lock --run` y comprobar `OK`.
  - Comprobar con `git status --short` que solo cambian `.microharness/sdd.py`, `tests/test_sdd.py`, `.gitignore` y `spec/memoria-atomica-lock/`, y que no queda `memory.lock` sin ignorar ni temporales.
