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
| `fix-sdd-rutas-unicode` | terminado | `diff_files()` usa `git -z` y UTF-8: rutas no ASCII (p. ej. `diseño.md`) ya no rompen el alcance ni la huella |
| `instalador-uvx` | terminado | Instalador por proyecto `uvx ... microsdd install`: idempotente, sin pisar archivos compartidos, exige `python3` real (en Windows `python3.exe`) |
| `licencia-mit` | terminado | Licencia MIT (2026, Arturo López) en `LICENSE`, metadatos PEP 639 en `pyproject.toml` y sección 10 del README |
