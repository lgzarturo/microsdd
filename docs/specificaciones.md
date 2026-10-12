# Índice de especificaciones

Cada tarea va en `spec/<slug>/` con exactamente cuatro documentos: `requerimientos.md`, `diseño.md`, `tareas.md`, `spec.json`.

- Estado: `pendiente`, `proceso`, `terminado` (únicos estados).
- Flujo: solicitud → autor → aprobación humana de spec → implementador → revisor y check → aprobación humana de cierre → commit.
- Rechazo: registra motivo en `.microharness/memory.json` y vuelve a `proceso` si quedan intentos; si necesita decisión humana o agota intentos, `pendiente`.
- Un cambio en requisitos aprobado reinicia revisión de impacto y requiere nueva aprobación.
- SDD es obligatorio; ODD = Organic Driven Development solo si se define operativamente para esa tarea. RDD es ambiguo: no se activa sin definición explícita; ninguno sustituye los criterios de aceptación.
- Se exige resultado ejecutado de pruebas declaradas antes de cerrar. Pruebas selladas se comparan contra hashes SHA-256; cambio autorizado requiere nuevo sellado humano. No es DRM ni garantía criptográfica frente a quien controle el repo.

| Tarea | Estado | Resumen |
|---|---|---|
| (ninguna) | — | Crear con `python3 .microharness/sdd.py new <slug>` |
