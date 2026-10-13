# CÓMO: diseño mínimo

## Situación comprobada
Hechos verificados en el repositorio el 2026-10-12:
- No existe `LICENSE` en la raíz ni `.gitattributes`. `git config core.autocrlf` vale `true`, así que en Windows el archivo puede quedar con CRLF en el árbol de trabajo.
- Historial Git: un solo autor, `Arturo López` (16 commits).
- `pyproject.toml` usa `requires = ["hatchling>=1.24"]` y `build-backend = "hatchling.build"`. `[project]` no tiene `license` ni `license-files`. El sdist usa una lista `include` explícita (manifiesto, `src`, `README.md`, `pyproject.toml`) que hoy no contiene `LICENSE`.
- `tests/test_installer.py`, prueba `test_wheel_from_sdist_contains_payload_without_dependencies` (comentario `# AC-10`, `skipUnless(shutil.which('uv'))`), funciona así: copia a un directorio temporal solo `pyproject.toml`, `README.md`, `installer.MANIFEST` y `src/`; ejecuta `uv build --sdist` y después `uv build --wheel` desde el sdist; comprueba el payload, `microsdd/installer.py` y que `METADATA` no tenga `Requires-Dist`. Ya importa `zipfile`, pero no `tarfile`.
- **Consecuencia crítica:** cuando `pyproject.toml` declare `license-files = ["LICENSE"]`, esa prueba fallará al construir si no copia también `LICENSE` a la copia temporal, porque hatchling exige que existan los archivos declarados. Por eso `tests/test_installer.py` entra en el alcance.
- `README.md`: el título es "MicroSDD for Claude Opus 5.5" y las secciones van de `## 1.` a `## 9. Fuentes`, seguidas de un párrafo "**Limitaciones conocidas:** ..." que cierra el archivo.
- El instalador (`src/microsdd/installer.py`) copia los archivos de `MANIFEST` al repositorio destino y **no** copia `LICENSE`. Esta tarea no lo cambia.
- `uv 0.12.21` está disponible en esta máquina. `hatchling` no está instalado localmente; `uv build` lo resuelve en un entorno aislado. En el índice hay versiones de 1.24.0 a 1.32.4.

## Supuestos (a verificar por el implementador)
- S1: hatchling soporta PEP 639 (`license` como cadena SPDX, `license-files`, Core Metadata 2.4 con `License-Expression`/`License-File` y copia en `.dist-info/licenses/`) desde la **1.27.0**. Si la verificación (changelog de hatchling o construcción real) muestra otra versión mínima, se usa esa, nunca una menor que la que funcione.
- S2: con `license-files` declarado, hatchling puede incluir `LICENSE` en el sdist aunque no figure en `include`. Igualmente se añade `"LICENSE"` a `include` de forma explícita, para no depender de ese comportamiento implícito y por coherencia con la lista existente.

## Decisión y justificación
1. **`LICENSE`** (nuevo, raíz, UTF-8 sin BOM, saltos LF, salto final). Contiene exactamente el texto MIT canónico (versión SPDX/choosealicense), sin traducir:

```
MIT License

Copyright (c) 2026 Arturo López

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

2. **`pyproject.toml`**, solo tres cambios:
   - `[build-system] requires = ["hatchling>=1.27"]` (o la mínima verificada según S1).
   - En `[project]`, añadir `license = "MIT"` y `license-files = ["LICENSE"]`.
   - En `[tool.hatch.build.targets.sdist] include`, añadir `"LICENSE"`.
   - No se añade clasificador `License ::`, porque PEP 639 lo desaconseja junto con `License-Expression` y algunas herramientas lo rechazan. Tampoco se toca `force-include` del wheel, porque la copia en `.dist-info/licenses/` la hace hatchling.

3. **`tests/test_installer.py`**, cambios mínimos con el estilo existente (unittest, comentarios `# AC-xx`):
   - Prueba nueva `test_license_file_is_canonical_mit` (`# AC-01`). Lee `SOURCE / 'LICENSE'` como UTF-8, normaliza `\r\n` a `\n`, quita el salto final y compara con una constante del módulo que contiene el texto anterior. No depende de `uv`.
   - En la prueba de wheel existente (`# AC-10`, ahora también `# AC-02`, `# AC-03`): añadir `'LICENSE'` a la lista de archivos que se copian; abrir el sdist con `tarfile` (stdlib) y comprobar que algún miembro termina en `/LICENSE` con un solo nivel de raíz; en el wheel, comprobar `License-Expression: MIT` y `License-File: LICENSE` en `METADATA`, la presencia de `*.dist-info/licenses/LICENSE` y su igualdad byte a byte con el `LICENSE` extraído del sdist. Las aserciones actuales se conservan.
   - Se amplía la prueba existente en vez de crear otra con `uv build`, para no duplicar dos construcciones lentas que comparten la misma preparación (DRY/KISS).

4. **`README.md`**: añadir al final una sección `## 10. Licencia` de 3 a 5 líneas en español neutro. Debe decir que el proyecto es MIT, `Copyright (c) 2026 Arturo López`, con enlace `[LICENSE](LICENSE)`, y avisar de que los archivos que `microsdd install` copia en otro repositorio siguen bajo MIT, por lo que al redistribuirlos hay que conservar el aviso de copyright y de permiso. No se afirma que el instalador copie `LICENSE`. No se toca el resto del archivo.

**TDD:** primero las aserciones nuevas (RED: falta `LICENSE`, `METADATA` sin `License-Expression`), después `LICENSE` y `pyproject.toml` (GREEN). Aporta valor porque el empaquetado con PEP 639 depende de la versión de hatchling y la prueba demuestra el efecto real en los artefactos.

## Alternativas descartadas
- `license = {text = "MIT"}` o `{file = "LICENSE"}` (forma anterior a PEP 639): está obsoleta y no produce `License-Expression`.
- Solo un clasificador `License :: OSI Approved :: MIT License`: está desaconsejado por PEP 639 y no incluye el archivo.
- Comprobar `LICENSE` en el wheel mediante `force-include`: duplica lo que hatchling ya hace con `license-files`.
- Copiar `LICENSE` al destino desde el instalador o añadir cabeceras SPDX: queda fuera de alcance por decisión humana.
- Prueba separada para el sdist: duplicaría la construcción con `uv`.
- Prueba automática del README: el contenido es prosa y basta con la inspección del revisor y `git diff` (YAGNI).

## Invariantes y riesgos
**Invariantes:**
- `dependencies = []` y el wheel sin `Requires-Dist`.
- Payload del manifiesto y `force-include` sin cambios.
- `src/microsdd/**` sin cambios.
- Secciones 1 a 9 del README intactas.
- El texto MIT es literal, con la "ó" en UTF-8.

**Riesgos:**
- R1: la versión mínima de hatchling es incorrecta y la construcción falla o no emite `License-Expression`. Mitigación: S1 más las aserciones de AC-03 sobre el artefacto real.
- R2: con `autocrlf=true`, el `LICENSE` del árbol de trabajo puede tener CRLF. La prueba AC-01 normaliza los saltos. En AC-03 se compara el wheel con el sdist, no con el archivo fuente, así que los saltos no influyen.
- R3: si `uv` no está o no hay red, la prueba de empaquetado se omite y AC-02/AC-03 quedan sin evidencia. El revisor debe exigir que conste como ejecutada (no `skipped`) en la evidencia de cierre.
- R4: la ruta exacta del archivo dentro de `.dist-info/licenses/` depende de hatchling (se espera `licenses/LICENSE`). Si difiere, el implementador lo informa al líder y no relaja la aserción por su cuenta.
- R5 (legal, informativo): el README no debe prometer que el aviso viaja automáticamente con los archivos instalados, porque no es así.

**Efectos secundarios:** construir requiere `hatchling>=1.27` (o la mínima verificada) en lugar de `>=1.24`. No hay impacto en tiempo de ejecución.
