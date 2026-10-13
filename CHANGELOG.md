# Registro de cambios

Formato y reglas: `assets/proceso-versionado.md` (R-04). Entradas derivadas de los asuntos de commit; se omiten los commits de merge, que no aportan cambios propios (su contenido figura en los commits integrados).

## [1.0.0] - 2026-10-13

### Incompatible
- `spec`: renombra diseño.md a plan.md en las 15 tareas (289b996)
- `docs`: renombra convensiones.md y specificaciones.md (64e4733)

### Añadido
- definir espacio de memoria (bd91f95)
- documento base para el contexto (bb78aba)
- definición del agente líder (c203f0d)
- definición del agente autor (36d0181)
- definición del agente implementador (f1cd53b)
- hook simple para el orquestador (9629e37)
- definición del flujo sdd para el arnés (471508d)
- `instalador`: instalación por proyecto con uvx (b19fe30)
- `release`: archiva el historial del arnés y restaura el estado inicial (ff1e241)
- `arnes`: detecta y usa Python >=3.10 en cualquier SO, con uv (4c1ef0e)
- `hook`: aplica la guardia del revisor también a PowerShell (8bd4842)
- `sdd`: añade --version y release propose (9778355)
- migrar de diseño.md por plan.md (cddb31a)
- `sdd`: añade subcomando note para observaciones y decisiones (446ca07)
- `sdd`: exige un mínimo de pruebas ejecutadas en check --run (77755eb)
- `sdd`: restringe testing.commands a una lista blanca de runners (3798da3)
- `sdd`: lee modelo y esfuerzo por defecto de .microharness/config.json (9f7c57d)
- `sdd`: detecta alteraciones del historial de memory.json respecto a HEAD (c924414)

### Corregido
- `sdd`: decodifica rutas no ASCII del diff de git (5aba938)
- `sdd`: devuelve rutas no ASCII literales en diff_files (07a4d8d)
- `sdd`: hashes de sellos y specs estables ante CRLF; *.sh con LF (b74c472)
- `sdd`: sellos de pruebas solo se comparan hasta el cierre (7700d3d)
- `hook`: endurece las expresiones permitidas al revisor (e784119)
- `instalador`: exige uv en lugar de python3 y usa sys.executable para init (61bd1ee)
- `hook`: deniega --textconv, -O y --open-files-in-pager al revisor (ad11369)
- `sdd`: escribe memory.json de forma atómica y con lock exclusivo (ffe55d6)
- `hook`: deniega edición y shell a agentes sin rol MicroSDD (5caba80)

### Otros
- información del micro arness sdd (1e73336)
- convenciones, carpeta de trabajo (d3fae00)
- reglas del mini Claude conciso. (54dbf1c)
- buenas prácticas cheatsheet (29611d8)
- información base del arnés (c34c96a)
- se define el requerimiento python3 para el arnés (ee71e32)
- definición del agente revisor (8034cb2)
- `assets`: registra decisiones de diseño del arnés (4f2b274)
- `assets`: define proceso de versionado semver del arnés (aeea32c)
- `licencia`: publica el proyecto bajo licencia MIT (7972c91)
- `assets`: actualiza API pública e instalación del proceso de versionado (5bd110e)
