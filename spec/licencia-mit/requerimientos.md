# QUÉ: requisitos

## Objetivo
Publicar MicroSDD bajo licencia MIT (titular Arturo López, año 2026). Para ello se añade `LICENSE` en la raíz, se declaran los metadatos de licencia en `pyproject.toml` (PEP 639) para que el sdist y el wheel la lleven, y se agrega al `README.md` una sección breve "## 10. Licencia".

Decisiones humanas ya tomadas (no se reabren): licencia MIT, titular "Arturo López", año 2026. El alcance son `LICENSE`, `pyproject.toml` y `README.md`, más `tests/test_installer.py` para verificar.

## Precondiciones
- Python >= 3.10 para la suite (en Windows se invoca como `python`).
- `git` en PATH (lo usan las pruebas existentes).
- `uv` en PATH y acceso a un índice de paquetes para resolver `hatchling` durante `uv build`. Si falta `uv`, la prueba de empaquetado se omite (`skipUnless`), igual que hoy AC-10 de `instalador-uvx`.
- Sin dependencias de terceros en tiempo de ejecución (`dependencies = []` se mantiene).

## Requisitos EARS
- REQ-01: THE repositorio SHALL contener en la raíz un archivo `LICENSE` codificado en UTF-8 con el texto MIT estándar íntegro, en inglés. La única línea variable es `Copyright (c) 2026 Arturo López`.
- REQ-02: WHEN se construye el sdist a partir del repositorio, THE sdist SHALL incluir `LICENSE`.
- REQ-03: WHEN se construye el wheel a partir del sdist, THE `METADATA` del wheel SHALL declarar `License-Expression: MIT` y `License-File: LICENSE`, y THE wheel SHALL incluir el archivo de licencia en `*.dist-info/licenses/LICENSE`, idéntico byte a byte al `LICENSE` del sdist.
- REQ-04: THE `pyproject.toml` SHALL declarar la licencia con la forma PEP 639 (`license = "MIT"` como expresión SPDX y `license-files = ["LICENSE"]`) y SHALL exigir una versión mínima de `hatchling` que soporte PEP 639.
- REQ-05: THE `README.md` SHALL terminar con una sección `## 10. Licencia` que indique que el proyecto usa la licencia MIT y enlace a `LICENSE`. También SHALL avisar que los archivos que el instalador copia en otro repositorio están cubiertos por la licencia MIT, que exige conservar el aviso de copyright y de permiso al redistribuirlos, sin afirmar que el instalador copie `LICENSE`.
- REQ-06: IF se construye el paquete con las pruebas existentes, THEN THE contenido actual del wheel SHALL seguir igual: payload del manifiesto, `microsdd/installer.py` y ausencia de `Requires-Dist`.

## Criterios de aceptación
- AC-01: El archivo `LICENSE` de la raíz se lee como UTF-8. Tras normalizar los saltos de línea a LF y quitar el salto final, su contenido es exactamente el texto MIT canónico registrado en `diseño.md`, con la línea `Copyright (c) 2026 Arturo López`. Lo verifica una prueba en `tests/test_installer.py`.
- AC-02: Al construir con `uv build --sdist` una copia temporal del proyecto, el `.tar.gz` resultante contiene `<raíz-del-sdist>/LICENSE`. Lo verifica una prueba en `tests/test_installer.py`.
- AC-03: El wheel construido desde ese sdist cumple tres condiciones. (a) Su `*.dist-info/METADATA` contiene la línea `License-Expression: MIT` y la línea `License-File: LICENSE`. (b) Contiene `*.dist-info/licenses/LICENSE`. (c) Ese archivo es igual byte a byte al `LICENSE` de la raíz del sdist. Lo verifica una prueba en `tests/test_installer.py`.
- AC-04: `pyproject.toml` contiene `license = "MIT"` y `license-files = ["LICENSE"]` en `[project]`. Su `[build-system].requires` exige `hatchling>=1.27` (o la mínima con soporte PEP 639 que verifique el implementador, nunca menor) y la lista `include` del sdist contiene `"LICENSE"`. No hay clasificador `License ::` ni la forma de tabla `license = {text = ...}`. Se verifica por inspección del revisor; el efecto lo cubren AC-02 y AC-03.
- AC-05: `README.md` termina con la sección `## 10. Licencia`, situada después de `## 9. Fuentes` y del párrafo de limitaciones conocidas, que es su contenido final actual. Esa sección (a) nombra la licencia MIT, (b) enlaza a `LICENSE` con un enlace relativo y (c) explica en pocas frases que los archivos que el instalador copia en otro repositorio están cubiertos por la licencia MIT, que exige conservar el aviso de copyright y de permiso al redistribuirlos. No afirma que el instalador copie `LICENSE` ni añada cabeceras. Las secciones 1 a 9 no cambian. Se verifica por inspección del revisor (`git diff README.md` solo añade líneas al final).
- AC-06: `python -m unittest discover -s tests -v` termina en verde, incluidos `tests/test_sdd.py` y la prueba de wheel existente con sus aserciones actuales (REQ-06).
- AC-07: `python .microharness/sdd.py check licencia-mit` no reporta archivos fuera de `scope.allowed_paths`.

## Fuera de alcance
- Cambiar el instalador (`src/microsdd/**`) o su manifiesto, por ejemplo para copiar `LICENSE` al destino o añadir cabeceras SPDX a los archivos copiados.
- Cabeceras de licencia en archivos fuente.
- CONTRIBUTING, CLA, código de conducta, NOTICE.
- Traducir el texto de la licencia.
- Publicación en PyPI, cambio de versión, push o tag.
- Cambios en `docs/**`, `.claude/**`, `.microharness/**` y `CLAUDE.md`.
