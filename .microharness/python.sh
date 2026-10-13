#!/bin/sh
# Lanzador portable: ejecuta los argumentos con el primer Python >= 3.10 válido.
# Orden: MICROSDD_PYTHON -> uv -> python3 -> python -> py -3. Uso: sh .microharness/python.sh <args...>

probe() {
    "$@" -c 'import sys; sys.exit(sys.version_info < (3, 10))' >/dev/null 2>&1
}

if [ -n "${MICROSDD_PYTHON:-}" ]; then
    if probe "$MICROSDD_PYTHON"; then
        exec "$MICROSDD_PYTHON" "$@"
    fi
    echo "Error: MICROSDD_PYTHON='$MICROSDD_PYTHON' no es un Python >= 3.10 ejecutable. Corrija o elimine la variable." >&2
    exit 2
fi

if command -v uv >/dev/null 2>&1 && probe uv run --no-project --quiet --python '>=3.10' python; then
    exec uv run --no-project --quiet --python '>=3.10' python "$@"
fi

for candidate in python3 python; do
    if command -v "$candidate" >/dev/null 2>&1 && probe "$candidate"; then
        exec "$candidate" "$@"
    fi
done

if command -v py >/dev/null 2>&1 && probe py -3; then
    exec py -3 "$@"
fi

echo "Error: no se encontró Python >= 3.10. Instale uv con su instalador oficial (https://docs.astral.sh/uv/) o Python >= 3.10." >&2
echo "En Windows, desactive los alias de ejecución de Microsoft Store para python/python3 o defina MICROSDD_PYTHON con la ruta del intérprete." >&2
exit 2
