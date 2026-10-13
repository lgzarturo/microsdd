# QUÉ: requisitos

## Objetivo

Cerrar el riesgo R9: hoy `dump()` escribe `memory.json` y `spec.json` con `Path.write_text` (truncar y escribir en el mismo archivo) y ninguna operación que muta la memoria se coordina con otras. Una interrupción o un error de disco puede dejar el JSON truncado. Dos procesos de `sdd.py` simultáneos, por ejemplo `note` del líder y `review`, pueden pisarse en el ciclo leer-modificar-escribir y perder un evento.

Se quiere:

1. Que `dump()` escriba de forma atómica: el archivo queda con el contenido anterior completo o con el nuevo completo, nunca a medias.
2. Que las operaciones que mutan la memoria (`ensure_init`, `new`, `approve`, `review`, `seal` y `note`) se serialicen con un lock exclusivo de archivo. El lock tiene timeout, da un error claro y es reentrante dentro del proceso.
3. Que el archivo de lock no aparezca como cambio en Git: ni en este repositorio ni en `release propose` de los proyectos instalados.

## Precondiciones

- Python 3.10 o superior, solo biblioteca estándar. Sin dependencias nuevas.
- Se ejecuta desde la raíz del repositorio con `.microharness/sdd.py` presente.
- Decisión humana previa, comunicada por el líder: el implementador modifica `.microharness/sdd.py` por Bash, porque el hook le niega Write/Edit en `.microharness/`.
- Las pruebas redirigen `sdd.ROOT` y `sdd.MEMORY` a un directorio temporal (`MicroSDDTests`, `ReleaseProposeTests`, `NoteTests`). Por eso la ruta del lock debe derivarse de `MEMORY` en cada llamada y no fijarse al importar el módulo.

## Requisitos EARS

- REQ-01: WHEN `dump(path, data)` termina sin error, THE sistema SHALL dejar en `path` exactamente los bytes que producía la versión anterior (`json.dumps(data, ensure_ascii=False, indent=2) + '\n'` en UTF-8, con la traducción de saltos de línea propia de la plataforma). El sistema SHALL escribir antes en un temporal del mismo directorio, con `flush` y `fsync`, y sustituir `path` con `os.replace`.
- REQ-02: IF la escritura del temporal, su `fsync` o `os.replace` fallan, THEN el sistema SHALL borrar el temporal, propagar la excepción y dejar `path` con su contenido anterior byte a byte, o sin crear si no existía.
- REQ-03: WHEN `dump` reemplaza un archivo existente en POSIX, THE sistema SHALL conservar sus bits de permiso. WHEN crea un archivo nuevo, THE sistema SHALL aplicarle `0o666 & ~umask`, igual que `write_text`.
- REQ-04: WHEN `os.replace` termina, THE sistema SHALL intentar `fsync` del directorio en POSIX como best effort: un `OSError` en ese paso no hace fallar `dump`. En Windows (`os.name == 'nt'`) no lo intenta.
- REQ-05: WHEN se invoca `ensure_init`, `new`, `approve`, `review`, `seal` o `note`, THE sistema SHALL adquirir antes un lock exclusivo sobre `<directorio de MEMORY>/memory.lock` y mantenerlo durante toda la operación. El directorio se crea si falta. El mecanismo es `fcntl.flock` en POSIX y `msvcrt.locking` en Windows.
- REQ-06: IF otro proceso mantiene el lock durante más de `LOCK_TIMEOUT` segundos (constante de módulo, 10 por defecto), THEN el sistema SHALL abortar la operación sin leer ni escribir `memory.json` ni `spec.json`, con un `ValueError` que nombre `memory.lock` y el timeout. Por CLI se ve como `ERROR: …` en stderr y código de salida 1.
- REQ-07: WHEN el lock se libera antes del timeout, THE sistema SHALL continuar con la operación pendiente y completarla.
- REQ-08: WHILE el proceso ya mantiene el lock, THE sistema SHALL permitir operaciones anidadas que también lo pidan sin esperar ni fallar. Ejemplos: `new` y `note` llaman a `ensure_init`.
- REQ-09: WHEN termina una operación con lock, sea con éxito o con excepción, THE sistema SHALL liberar el lock del sistema operativo y restablecer el contador de reentrancia.
- REQ-10: WHILE otro proceso mantiene el lock, THE sistema SHALL ejecutar sin esperarlo los comandos de solo lectura: `check` (con y sin `--run`), `commit-check`, `release propose` y `--version`.
- REQ-11: `.gitignore` del repositorio SHALL incluir `.microharness/memory.lock`.
- REQ-12: WHEN `release propose` analiza `git status` y `.microharness/memory.lock` aparece como cambio (sin rastrear o modificado), THE sistema SHALL no contarlo como cambio fuera de `spec/` y `memory.json`. Cualquier otro archivo de `.microharness/` se sigue rechazando. (Pendiente de confirmación del líder, ver D-01 en `plan.md`).

## Criterios de aceptación

- AC-01: Con `ROOT` temporal y un `m.json` previo, `dump(m.json, {'nuevo': True})` deja en `m.json` el JSON nuevo, con bytes iguales a los de la implementación anterior. `os.replace` se llama una vez con origen en el mismo directorio y `os.fsync` se llama al menos una vez. Al terminar, el directorio contiene solo `m.json`.
- AC-02: Con `m.json` previo, si `os.replace` (u `os.fsync` del temporal) lanza `OSError` simulado, `dump` propaga `OSError`, `m.json` conserva sus bytes anteriores y el directorio contiene solo `m.json`. Si `m.json` no existía, tampoco existe después y no quedan temporales.
- AC-03: Por CLI (`main()` con `argv` parcheado), `note --fact x --evidence y` con `os.replace` fallando devuelve código 1 y `ERROR:` en stderr. `memory.json` queda byte a byte igual y sin temporales en `.microharness/`.
- AC-04 (POSIX; se omite en Windows): un archivo existente con modo `0o640` conserva `0o640` tras `dump`. Un archivo nuevo creado por `dump` con `umask` 022 queda en `0o644`.
- AC-05: si el `fsync` del directorio lanza `OSError` (por ejemplo, el `os.open` del directorio falla sin afectar a `mkstemp`), `dump` termina sin error y el contenido nuevo queda escrito.
- AC-06 (POSIX; se omite en Windows): con el test reteniendo `fcntl.flock(LOCK_EX)` sobre `<MEMORY.parent>/memory.lock` y `LOCK_TIMEOUT = 0.2`, cada una de `ensure_init`, `new`, `approve`, `review`, `seal` y `note` lanza `ValueError` con `memory.lock` en el mensaje. En todos los casos `memory.json` y `spec.json` quedan byte a byte iguales y `new` no crea `spec/<slug>/`. Por CLI, `note` devuelve código 1 con `ERROR:` y la mención de `memory.lock` en stderr.
- AC-07 (POSIX; se omite en Windows): con el lock retenido por el test y liberado a los 0,2 s desde otro hilo, y con `LOCK_TIMEOUT = 5`, `note --fact` termina con éxito y la observación queda registrada.
- AC-08: dentro de `with sdd.memory_lock():` (o el nombre que fije el plan), `note` y `new` (que anida `ensure_init`) terminan con éxito sin esperar, con `LOCK_TIMEOUT = 0.2`.
- AC-09 (POSIX; se omite en Windows): después de una operación con lock que termina con excepción (por ejemplo `approve` con evidencia vacía) y después de una que termina con éxito, el test obtiene `flock(LOCK_EX | LOCK_NB)` sobre `memory.lock` sin error. Una operación posterior con el lock retenido por el test vuelve a fallar por timeout, lo que demuestra que el contador de reentrancia volvió a 0.
- AC-10: tras `ensure_init()` con `ROOT` y `MEMORY` temporales, existe `<MEMORY.parent>/memory.lock` en el temporal y el lock del repositorio real no se usa.
- AC-11 (POSIX; se omite en Windows): con el lock retenido por el test y `LOCK_TIMEOUT = 5`, `check <slug> --no-scope` por `main()` termina en menos de 2 s con su resultado habitual.
- AC-12: en la raíz real del repositorio, `git check-ignore -q .microharness/memory.lock` devuelve 0.
- AC-13: en el repositorio temporal de `ReleaseProposeTests` con `.microharness/memory.lock` sin rastrear, `release propose` propone la versión esperada. Con un `.microharness/otro.txt` sin rastrear, la rechaza nombrando ese archivo.
- AC-14: `python -m unittest discover -s tests -v` termina con código 0, incluidas las pruebas existentes sin cambiar sus aserciones, y `sdd.py check memoria-atomica-lock --run` devuelve `OK`.

## Fuera de alcance

- Atomicidad entre archivos. `approve` y `review` escriben `memory.json` y `spec.json` en dos pasos y una interrupción entre ambos puede dejarlos incoherentes; esto ya ocurre hoy y no se resuelve aquí.
- Lock o atomicidad en `scripts/migrar_plan_md.py`, que escribe `memory.json` con `write_text`. Es una migración puntual ya ejecutada en este repositorio y no se distribuye. `scripts/limpiar_arnes.py` no escribe `memory.json`: lo copia, lo borra y llama a `sdd.py init`, que sí tomará el lock.
- Escrituras de `requerimientos.md`, `plan.md`, `tareas.md` y `docs/*.md` con `write_text` en `new` y `ensure_init`: siguen igual, aunque ocurren con el lock tomado.
- Cambios en `src/microsdd/installer.py` y `pyproject.toml`. El manifiesto es explícito (`MANIFEST` y `force-include`) y nunca incluye `memory.lock`; los «Próximos pasos» del instalador solo listan `INIT_FILES`.
- Modificar el `.gitignore` de los proyectos destino: el instalador no lo toca.
- Borrar `memory.lock` al terminar. Se conserva a propósito porque borrarlo crea carreras.
- Locks entre hilos de un mismo proceso (el CLI es de un solo hilo), sistemas de archivos de red y garantías frente a quien controle el repositorio.
- Cambiar el comportamiento de `check`, `validate` y del hook.
