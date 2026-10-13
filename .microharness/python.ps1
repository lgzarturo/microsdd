# Lanzador PowerShell 7+: ejecuta los argumentos con el primer Python >= 3.10 válido.
# Orden: MICROSDD_PYTHON -> uv -> python -> py -3.
# Uso: .\.microharness\python.ps1 <args...>
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Test-Python {
    param([Parameter(Mandatory)][string[]]$Command)
    try {
        $exe = $Command[0]
        $rest = @()
        if ($Command.Length -gt 1) { $rest = $Command[1..($Command.Length - 1)] }
        & $exe @rest -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)' 2>$null | Out-Null
        return ($LASTEXITCODE -eq 0)
    } catch {
        return $false
    }
}

if ($args.Count -eq 0) {
    Write-Error 'Uso: .\.microharness\python.ps1 <args...>'
    exit 2
}

if ($env:MICROSDD_PYTHON) {
    if (Test-Python @($env:MICROSDD_PYTHON)) {
        & $env:MICROSDD_PYTHON @args
        exit $LASTEXITCODE
    }
    Write-Error "MICROSDD_PYTHON='$env:MICROSDD_PYTHON' no es un Python >= 3.10 ejecutable. Corrija o elimine la variable."
    exit 2
}

if (Get-Command uv -ErrorAction SilentlyContinue) {
    if (Test-Python @('uv', 'run', '--no-project', '--quiet', '--python', '>=3.10', 'python')) {
        & uv run --no-project --quiet --python '>=3.10' python @args
        exit $LASTEXITCODE
    }
}

foreach ($candidate in @('python', 'python3')) {
    if (Get-Command $candidate -ErrorAction SilentlyContinue) {
        if (Test-Python @($candidate)) {
            & $candidate @args
            exit $LASTEXITCODE
        }
    }
}

if (Get-Command py -ErrorAction SilentlyContinue) {
    if (Test-Python @('py', '-3')) {
        & py -3 @args
        exit $LASTEXITCODE
    }
}

Write-Error 'No se encontró Python >= 3.10. Instale uv (https://docs.astral.sh/uv/) o Python >= 3.10. Desactive los alias de Microsoft Store para python o defina MICROSDD_PYTHON.'
exit 2
