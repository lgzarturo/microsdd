# QUÉ: requisitos

## Objetivo
Hoy `seal` sobrescribe `tasks.<slug>.sealed_tests` sin comparar nada. Un resellado no debe poder reducir silenciosamente el número de aserciones de un archivo de prueba Python ya sellado. Para ello `seal` registra un recuento de aserciones por archivo Python y rechaza un resellado que lo reduzca, salvo autorización explícita.

## Definiciones
- **Archivo Python:** ruta de `testing.protected_tests` cuyo sufijo, sin distinguir mayúsculas, es `.py`.
- **Recuento registrado:** valor de `tasks.<slug>.sealed_assertions[<ruta>]` en la memoria. `sealed_tests` conserva su forma `{ruta: sha256}`.
- **Sello antiguo:** archivo presente en `sealed_tests` sin entrada en `sealed_assertions`, o tarea sin ese campo.
- **Reducción:** archivo con recuento registrado `N` cuyo recuento actual es `M < N`, o archivo con recuento registrado `N > 0` que ya no figura en `testing.protected_tests`.
- **Recuento de aserciones:** recorrido estático con `ast.walk` del archivo completo (incluidas funciones auxiliares, ramas no ejecutadas y bucles, una vez por nodo). Cada nodo suma 1 si es:
  1. `ast.Assert`.
  2. `ast.Call` sobre `self.<attr>`, donde el receptor es exactamente el nombre `self` y `<attr>` empieza por `assert` o es `fail`. Incluye `self.assertRaises`, sea como gestor de contexto o llamada directa.
  3. `ast.Call` sobre `pytest.raises`, donde el receptor es exactamente el nombre `pytest`.
- **No cuenta:** comentarios y cadenas; `self.mock.assert_called()` y `mock.assert_called()`; `cls.assertTrue(...)`; `self.assertTrue` sin llamar; `pytest.fail`, `pytest.warns`; `raises(...)` importado con `from pytest import raises`; `pt.raises(...)` con `import pytest as pt`.
- **Nota de reducción:** nota creada con `note --fact … --evidence '<cita humana>' --for-task <slug> --for-phase seal-reduce` (fase nueva) y citada con `seal … --evidence @note:<id>`. Aplica las reglas vigentes de `consume_note`: sin usar, misma tarea, misma fase, edad de hasta 30 min.

## Precondiciones
- Rama `main`; `seal` y `validate` se comportan como en `.microharness/sdd.py` versión 1.5.3.
- `.microharness/sdd.py` es editable por el implementador solo si figura en `scope.allowed_paths` (lo hace en esta tarea).
- La suite actual está en verde: 434 pruebas, 4 omitidas (ejecutada al redactar esta spec con `python -m unittest discover -s tests`).

## Decisión a confirmar por el humano al aprobar esta spec
- **DEC-01 (propuesta):** la reducción legítima se autoriza únicamente con una nota de la fase nueva `seal-reduce` (REQ-07). Es la vía mínima: no añade opciones a `seal` ni estados, y usa las mismas reglas de `@note` que `approve spec`. Límite heredado: MicroSDD no puede demostrar que la cita la escribió un humano. Con `agent_may_approve: false` el comando sigue exigiendo TTY. Si el humano prefiere otra vía (p. ej. solo TTY, sin atajo de nota para el líder), debe indicarlo antes de aprobar; esta spec no da por aprobada la propuesta.

## Requisitos EARS
- REQ-01: WHEN `seal` se ejecuta con éxito, THE sistema SHALL guardar en `tasks.<slug>.sealed_assertions` el recuento actual de cada archivo Python de `protected_tests`, sin entradas para otros archivos, y SHALL mantener `sealed_tests` como `{ruta: sha256}`.
- REQ-02: THE recuento de aserciones SHALL seguir exactamente la definición de este documento, usando solo `ast` de la biblioteca estándar.
- REQ-03: IF un archivo Python de `protected_tests` no se puede analizar al sellar, THEN THE sistema SHALL terminar con `ERROR:` y código 1 nombrando el archivo, sin modificar la memoria.
- REQ-04: WHEN se resella y un archivo no tiene recuento registrado, THE sistema SHALL tratarlo como sello antiguo: no es reducción y se registra su recuento actual.
- REQ-05: IF un resellado contiene una o más reducciones y `--evidence` no cita una nota, THEN THE sistema SHALL terminar con `ERROR:` y código 1 nombrando cada archivo, su recuento anterior y actual, sin modificar la memoria; esto incluye al líder bajo lease y al humano en TTY con evidencia de texto libre.
- REQ-06: WHEN el recuento actual es igual o mayor que el registrado, THE sistema SHALL aceptar el resellado por las vías actuales y SHALL registrar el recuento actual como nueva base.
- REQ-07: IF un resellado contiene reducciones y `--evidence` cita una nota de reducción válida, THEN THE sistema SHALL aceptarlo, consumir la nota y registrar en el evento `sellado_tests` el campo `assertion_reductions` con `file`, `previous` y `current` de cada reducción.
- REQ-08: IF un resellado contiene reducciones y la nota citada no es una nota de reducción válida, THEN THE sistema SHALL terminar con `ERROR:` y código 1 nombrando archivo y recuentos junto con el motivo de la nota, sin modificar la memoria ni consumir la nota.
- REQ-09: IF un resellado no contiene reducciones y `--evidence` cita una nota de fase `seal-reduce` con `agent_may_approve` activo, THEN THE sistema SHALL rechazarlo con el error vigente de fase incorrecta, sin modificar la memoria.
- REQ-10: IF `sealed_assertions` no es un objeto o un valor de los archivos a comparar no es un entero mayor o igual a 0, THEN THE sistema SHALL terminar con `ERROR:` y código 1, sin modificar la memoria, en lugar de tratarlo como sello antiguo.
- REQ-11: WHEN `sealed_assertions` difiere de `HEAD` en una tarea abierta sin evento nuevo `sellado_tests`, THE comprobación de integridad SHALL informar el error, igual que para `sealed_tests`.
- REQ-12: WHEN se ejecuta `approve <slug> spec`, THE sistema SHALL conservar `sealed_assertions` sin cambios.
- REQ-13: WHEN el archivo de `protected_tests` no es Python, THE sistema SHALL sellarlo solo por hash, como hoy.

## Criterios de aceptación
Salvo indicación, cada caso parte de una tarea con `protected_tests = ['tests/test_x.py']`, se ejecuta en una raíz temporal, y «memoria intacta» significa `memory.json` idéntico byte a byte antes y después.

- AC-01 (REQ-01, REQ-02): dado este contenido, `seal` guarda `sealed_assertions == {'tests/test_x.py': 5}` y `sealed_tests['tests/test_x.py']` es la cadena SHA-256 de `hash_file`.
  ```python
  import unittest, pytest
  class T(unittest.TestCase):
      def test_a(self):
          assert 1 == 1                        # cuenta
          self.assertEqual(1, 1)               # cuenta
          self.fail('x')                       # cuenta
          with self.assertRaises(ValueError):  # cuenta
              int('x')
          with pytest.raises(ValueError):      # cuenta
              int('x')
          self.mock.assert_called_once()       # no cuenta
          cls.assertTrue(1)                    # no cuenta
          pytest.fail('x')                     # no cuenta
          raises(ValueError)                   # no cuenta
          # assert comentado                   # no cuenta
          s = 'assert en cadena'               # no cuenta
  ```
- AC-02 (REQ-02): un archivo vacío cuenta 0 y `def h(self):\n    self.assertTrue(1)\n` cuenta 1 aunque `h` no se invoque.
- AC-03 (REQ-03): con `tests/test_x.py` = `def (:\n`, `main()` con `seal` imprime en stderr `ERROR:` con `tests/test_x.py`, devuelve 1 y deja la memoria intacta. Lo mismo con bytes no decodificables (`b'\xff\xfe\n'`).
- AC-04 (REQ-04): con memoria cuyo `sealed_tests` tiene la ruta y sin `sealed_assertions`, resellar un archivo de 1 aserción termina con éxito y registra `{'tests/test_x.py': 1}`. `validate` tampoco reporta error por un sello antiguo cuyo hash coincide.
- AC-05 (REQ-05): con recuento registrado 2, resellar el archivo con 1 aserción y evidencia de texto mediante `main()` en TTY devuelve 1; stderr contiene `ERROR:`, `tests/test_x.py`, `anterior 2` y `actual 1`; memoria intacta.
- AC-06 (REQ-05): con spec en `proceso` y lease íntegro, sin TTY, `seal(<slug>, 'lider', 'texto')` con recuento 2 → 1 lanza `ValueError` con esos mismos datos; memoria intacta.
- AC-07 (REQ-05): con dos archivos reducidos, el error nombra ambos con sus recuentos.
- AC-08 (REQ-05): con recuento registrado 2 y la ruta retirada de `protected_tests`, resellar otro archivo protegido con texto libre falla nombrando la ruta retirada, `anterior 2` y `actual 0`; memoria intacta. Con recuento registrado 0 la retirada no es reducción.
- AC-09 (REQ-06): resellar con recuento 2 → 2 y 2 → 3 termina con éxito por lease y texto en TTY; `sealed_assertions` queda en 2 y 3 respectivamente, y el evento no contiene `assertion_reductions`. Después, bajar de 3 a 2 falla (la base subió).
- AC-10 (REQ-07): con recuento 2 → 1 y nota `seal-reduce` válida, `seal(<slug>, 'Humano', '@note:<id>')` termina con éxito: `sealed_assertions` queda en 1, la nota tiene `used_at` y el último evento `sellado_tests` contiene `assertion_reductions == [{'file': 'tests/test_x.py', 'previous': 2, 'current': 1}]`.
- AC-11 (REQ-07): con recuento 2 y ruta retirada de `protected_tests`, una nota `seal-reduce` válida permite resellar; la ruta desaparece de `sealed_tests` y `sealed_assertions`, y `assertion_reductions` registra `current: 0`.
- AC-12 (REQ-08): con recuento 2 → 1 y una nota de fase `seal` (o de otra tarea, consumida o inexistente), `seal` falla nombrando archivo y recuentos además del motivo de la nota; memoria intacta, por lo que una nota aún sin usar conserva `used_at` en `None`.
- AC-13 (REQ-09): sin reducciones, una nota `seal-reduce` falla con `no corresponde a la fase seal`; memoria intacta.
- AC-14 (REQ-10): con `sealed_assertions['tests/test_x.py']` igual a `'2'`, `True` o `-1`, o con `sealed_assertions` igual a `[]`, `seal` falla con `ERROR`/`ValueError` que menciona `sealed_assertions`; memoria intacta.
- AC-15 (REQ-11): en un repositorio con memoria confirmada, cambiar solo `sealed_assertions` sin evento nuevo produce el error `sealed_assertions cambió sin evento sellado_tests`; con evento `sellado_tests` nuevo no hay error de integridad. Un `seal` real seguido de `memory_integrity` no da errores, también partiendo de una tarea confirmada sin ese campo.
- AC-16 (REQ-12): tras un `seal` con recuento 2, modificar la spec y reaprobar con `approve spec` conserva `sealed_assertions`; resellar con 1 aserción sigue fallando.
- AC-17 (REQ-13): `protected_tests = ['tests/datos.txt']` con contenido no Python sella por hash y deja `sealed_assertions == {}`. Modificar el archivo y resellar termina con éxito. El contenido `def (:` en `.txt` no provoca error.
- AC-18: `note --for-phase seal-reduce` se admite en la CLI; `assets/arnes-completo.md` documenta el recuento, la vía de reducción y los límites conocidos; `assets/proceso-versionado.md` lista `seal-reduce` en API-01.
- AC-19: `python -m unittest discover -s tests` termina en verde sin modificar pruebas existentes de otros módulos, con más de 434 pruebas; `sdd.py` solo añade imports de la biblioteca estándar.

## Límites conocidos (a documentar)
- No detecta debilitamiento semántico: `assert True` cuenta igual que una aserción real.
- No detecta mover aserciones entre archivos: cada archivo se compara por separado, sin suma global.
- Conteo estático por receptor literal: alias (`tc = self`, `import pytest as pt`) y nuevas funciones auxiliares no se reconocen; se pueden añadir aserciones inertes para compensar otras eliminadas.
- La base es por tarea: la primera vez que se sella no hay comparación, y otra tarea con otro slug empieza sin base.
- Quien edite y confirme `memory.json` fija una nueva base (misma limitación de `sealed_tests`). No es control de seguridad.
- La nota de reducción declara una cita; no autentica al humano.

## Fuera de alcance
Estados o roles nuevos; motor de estados; stubs obligatorios; `chmod`; árbitro; hooks de git; SYMBOL_MAP; límites AST de código de producción; dependencias externas (solo biblioteca estándar); nuevas opciones de `seal`; comparar recuentos en `check`/`validate` (el hash ya detecta cambios); recuento para lenguajes distintos de Python; cambios en `write_witness`, `.claude/hooks/pretool.py`, `.claude/agents/`, `src/microsdd/`; migrar sellos antiguos o tareas cerradas; impedir `seal` en tareas `terminado`.
