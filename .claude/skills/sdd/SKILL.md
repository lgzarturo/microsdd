---
name: sdd
description: Inicia una tarea del flujo MicroSDD mediante el agente líder y especificación revisable.
---
Ejecuta el flujo de MicroSDD como `lider` para: $ARGUMENTS

Usa primero los cuatro documentos generales y memoria externa; inicializa o elige una sola `spec/<slug>/`. Delega a autor antes de codificar, solicita aprobación humana de especificación, implementa con implementador, valida con revisor y puerta automatizada, pide aprobación humana final antes de commit. No avances un estado si no hay evidencia.

`/sdd on|off|status`: con `status`, ejecuta `microsdd status` (o lee `.claude/settings.json`) e informa si el arnés está `activo`, `inactivo` o `parcial`; con `on` u `off`, no lo ejecutes: entrega al humano el comando `uvx --from git+https://github.com/lgzarturo/microsdd microsdd on` (u `off`) para su terminal, fuera de Claude Code, y recuérdale reiniciar la sesión.
