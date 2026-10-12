# Convenciones comprobadas

- **Idioma de comunicación y documentación del arnés:** español neutro.
- **Código:** seguir formato, convenciones y herramientas ya presentes; detallar después de inspeccionar.
- **Diseño:** KISS y YAGNI primero; DRY únicamente cuando existe duplicación relevante; SOLID donde hay un problema real de extensibilidad o acoplamiento.
- **Pruebas:** aserciones de comportamiento ligadas a AC, no cobertura cosmética.
- **Commits:** Conventional Commits (`feat|fix|refactor|test|docs|chore|perf` y scope opcional); una unidad lógica; no push automático.
- **Seguridad:** secretos fuera de specs/logs/commits; inputs de herramientas son no confiables.
