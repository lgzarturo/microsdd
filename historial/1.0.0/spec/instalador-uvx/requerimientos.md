# QUÉ: requisitos

## Objetivo
Permitir instalar "MicroSDD for Claude Opus 5.5" en la raíz de un repositorio Git existente con un solo comando
`uvx --from git+https://github.com/lgzarturo/microsdd microsdd install [--target RUTA] [--dry-run] [--force]`,
de forma idempotente, sin sobrescribir archivos compartidos del usuario y dejando claro que MicroSDD es un micro arnés
por proyecto (agnóstico al stack, basado en el código base del repositorio) y no una configuración global de `~/.claude`.

## Precondiciones
- En la máquina del usuario: `git`, `uv` y un `python3` real >= 3.10 ejecutable desde el PATH (el hook y `sdd.py` lo invocan así).
- El destino es la raíz de un repositorio Git (`git rev-parse --show-toplevel`).
- Para desarrollo y pruebas: Python >= 3.10; `git` disponible; `uv` disponible solo para AC-10 (la prueba se omite si falta).
- El paquete solo usa la biblioteca estándar en tiempo de ejecución (`dependencies = []`).

## Requisitos EARS
- REQ-01: WHEN el usuario ejecuta `microsdd install` sobre la raíz de un repositorio Git limpio sin MicroSDD, THE instalador SHALL copiar los archivos propios del manifiesto byte a byte, crear `CLAUDE.md` con el bloque de registro e import `@CLAUDE.microsdd.md`, ejecutar `python3 .microharness/sdd.py init` y terminar con código 0.
- REQ-02: WHEN se ejecuta `install` por segunda vez sin cambios en el origen, THE instalador SHALL omitir los archivos idénticos, no duplicar el bloque `<!-- microsdd:begin -->` y dejar el árbol idéntico byte a byte.
- REQ-03: IF `CLAUDE.md` ya existe, THEN THE instalador SHALL conservar su contenido como prefijo intacto y anexar el bloque una sola vez, respetando LF/CRLF y el salto final.
- REQ-04: IF `CLAUDE.md` no existe y `AGENTS.md` existe en la raíz, THEN THE instalador SHALL crear `CLAUDE.md` anteponiendo `@AGENTS.md` al bloque.
- REQ-05: IF `.claude/settings.json` existe y difiere del payload, THEN THE instalador SHALL dejarlo intacto, escribir `.claude/settings.microsdd.json` y avisar en la salida que `agent: lider` y el hook no están activos hasta fusionar manualmente.
- REQ-06: IF un archivo propio existe y difiere del payload y no se pasó `--force`, THEN THE instalador SHALL terminar con código 1 sin escribir ningún archivo.
- REQ-07: WHEN se pasa `--force`, THE instalador SHALL sobrescribir solo los archivos propios que difieren y SHALL dejar intactos `CLAUDE.md` (salvo el anexo único) y `.claude/settings.json`.
- REQ-08: WHEN se pasa `--dry-run`, THE instalador SHALL imprimir el plan clasificado (crear / sin cambios / alterno / anexar registro / actualizar / conflicto) y terminar con código 0 sin escribir nada.
- REQ-09: IF el destino es el directorio home, está bajo `~/.claude`, no es un repositorio Git o no es la raíz del repositorio, THEN THE instalador SHALL terminar con código 1 sin escribir nada.
- REQ-10: IF `python3` (buscado en un PATH sin el directorio `bin`/`Scripts` del entorno aislado de uvx; WHILE `sys.platform == 'win32'`, buscando solo `python3.exe`, equivalente a la resolución de Git Bash, de modo que los shims `.cmd`/`.bat` se ignoran) no existe, no se ejecuta o reporta una versión < 3.10, THEN THE instalador SHALL terminar con código 1, mostrar remediación por sistema operativo (en Windows, mencionar el alias de ejecución cuando la ruta contiene `WindowsApps` y que los shims `.cmd`/`.bat` no sirven para Git Bash) y no escribir nada; en otros SO la búsqueda de `python3` no cambia.
- REQ-11: WHEN el instalador inicia, THE instalador SHALL imprimir un banner con "MicroSDD for Claude Opus 5.5", la versión (o `dev`) y la alerta de que no es un arnés global, sin emoji y tolerando consolas sin UTF-8.
- REQ-12: IF el árbol de trabajo tiene cambios sin confirmar, THEN THE instalador SHALL mostrar solo una advertencia y continuar.
- REQ-13: WHEN la instalación escribe los archivos, THE instalador SHALL ejecutar `python3 .microharness/sdd.py init` y un smoke test del hook (evento `revisor` + `Edit`) que exija `deny` con el motivo de la regla del revisor ("solo lectura"); IF `init` falla o el hook no responde con ese motivo (por ejemplo, `deny` por "Guardia inválida"), THEN THE instalador SHALL terminar con código 1; si ambos pasan, SHALL imprimir próximos pasos con `git add` de la lista exacta de archivos (nunca `git add .`).
- REQ-14: WHEN `microsdd` se ejecuta sin subcomando o con argumentos inválidos, THE CLI SHALL terminar con código 2 sin escribir nada.

## Criterios de aceptación
- AC-01: Instalación limpia en un repositorio Git temporal: los archivos propios son idénticos byte a byte al origen; `CLAUDE.md` contiene el bloque y `@CLAUDE.microsdd.md`; existen `docs/` (4 documentos), `spec/` y `.microharness/memory.json`; código de salida 0.
- AC-02: Idempotencia: una segunda ejecución deja el árbol idéntico byte a byte (snapshot) y no hay bloques duplicados.
- AC-03: Un `CLAUDE.md` del usuario se conserva como prefijo intacto y solo se anexa el bloque; con `AGENTS.md` y sin `CLAUDE.md`, el `CLAUDE.md` creado incluye `@AGENTS.md`.
- AC-04: Un `.claude/settings.json` distinto queda intacto; se crea `.claude/settings.microsdd.json` igual al payload; la salida contiene el aviso de fusión manual.
- AC-05: Con un archivo propio modificado: sin `--force` el código es 1 y el snapshot del árbol no cambia; con `--force` el archivo se sobrescribe y los compartidos (`CLAUDE.md` del usuario, `settings.json`) quedan intactos.
- AC-06: `--dry-run` produce cero cambios (snapshot igual), código 0 y plan impreso.
- AC-07: Destino igual a home, bajo `~/.claude`, directorio no Git o subdirectorio de un repositorio: código 1 y cero escrituras.
- AC-08: Un intérprete falso que sale con 9009 o reporta 3.9: código 1 y cero escrituras; la función pura de filtrado de PATH excluye el directorio del entorno de uvx; en Windows, un `python3.cmd` como único candidato en el PATH se ignora y produce código 1 con cero escrituras (prueba `skipUnless(sys.platform == 'win32')`).
- AC-09: El banner contiene "MicroSDD for Claude Opus 5.5" y la alerta de arnés no global.
- AC-10: `uv build` (sdist y luego wheel desde el sdist) en un directorio temporal: el wheel contiene `microsdd/payload/<cada ruta del manifiesto>` y su METADATA no tiene `Requires-Dist` (prueba omitida si `uv` no está disponible).
- AC-11: README: título "MicroSDD for Claude Opus 5.5", alerta `> [!WARNING]` de arnés no global, requisitos incluyendo `uv`, comando `uvx`, flags, tabla de política de conflictos, `git add` explícito, recomendación de fijar un tag, eliminación manual y árbol de archivos actualizado; además aclara que el código 1 también se devuelve si `sdd.py init` o el smoke test del hook fallan después de escribir, y que en Windows se exige `python3.exe` (los shims `.cmd`/`.bat` no cuentan).
- AC-12: `tests/test_sdd.py` sigue en verde.
- AC-13: Con un `source` temporal cuyo `.claude/hooks/pretool.py` responde `deny` con "Guardia inválida" en lugar de "solo lectura", el instalador termina con código 1.

## Fuera de alcance
- Corregir el comportamiento silencioso del hook `pretool.py` en Windows (tarea posterior).
- Cambios en `.claude/`, `.microharness/`, `CLAUDE.md` del repo, `.gitignore` y `docs/` de este repositorio.
- Archivo LICENSE, publicación en PyPI, creación de tags o push.
- Respaldos `.bak`, registro de hashes instalados y desinstalador automático.
- Scripts PowerShell o sh de instalación.
- Copiar los `docs/` de este repositorio al destino (los genera `sdd.py init`).
