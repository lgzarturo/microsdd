# Arquitectura comprobada

Por inspeccionar. Documentar solo componentes, interfaces, módulos e invariantes reales que afecten decisiones de implementación. Incluir rutas concretas y dependencias relevantes; evitar describir arquitectura deseada como si existiera.

- `scripts/limpiar_arnes.py`: herramienta de mantenimiento del release del arnés (solo stdlib, no se distribuye). Exige árbol git limpio y todas las tareas en `terminado`; archiva `.microharness/memory.json`, `docs/` y `spec/<slug>/` en `historial/<versión>/` y restaura el estado inicial ejecutando `.microharness/sdd.py init`. No hace commit, tag ni push.
- `historial/<versión>/`: historial archivado del desarrollo del propio arnés; no forma parte de la instalación.
