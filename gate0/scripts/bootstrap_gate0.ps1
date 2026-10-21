[CmdletBinding()]
param(
  [switch]$SkipInstall
)

$ErrorActionPreference = 'Stop'
$gate0Root = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $gate0Root

# Resolve Python without assuming a specific launcher is on PATH.
$pyCommand = Get-Command py -ErrorAction SilentlyContinue
if ($pyCommand) {
  $pythonExe = $pyCommand.Source
  $pythonPrefix = @('-3')
} else {
  $pyCommand = Get-Command python -ErrorAction SilentlyContinue
  if (-not $pyCommand) { throw "Python 3.13 is unavailable. Install it or add python.exe to PATH." }
  $pythonExe = $pyCommand.Source
  $pythonPrefix = @()
}

# Resolve Node before installing Node dependencies.
if (-not $env:GATE0_NODE) {
  $nodeCommand = Get-Command node -ErrorAction SilentlyContinue
  if ($nodeCommand) {
    $env:GATE0_NODE = $nodeCommand.Source
  } else {
    $codexNode = "$env:USERPROFILE\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe"
    if (Test-Path -LiteralPath $codexNode) {
      $env:GATE0_NODE = $codexNode
    } else {
      throw "Node.js is unavailable. Install Node.js or set GATE0_NODE to node.exe."
    }
  }
}

function Invoke-Pnpm {
  param([string[]]$PnpmArgs)
  if ($env:GATE0_PNPM) {
    & $env:GATE0_NODE $env:GATE0_PNPM @PnpmArgs
  } elseif (Get-Command pnpm -ErrorAction SilentlyContinue) {
    & pnpm @PnpmArgs
  } elseif (Get-Command corepack -ErrorAction SilentlyContinue) {
    & corepack pnpm @PnpmArgs
  } elseif (Get-Command npx -ErrorAction SilentlyContinue) {
    & npx --yes pnpm@11.25.0 @PnpmArgs
  } else {
    throw "pnpm is unavailable. Install pnpm/corepack, or set GATE0_PNPM to pnpm.cjs."
  }
  if ($LASTEXITCODE -ne 0) { throw "pnpm failed: $LASTEXITCODE" }
}

if (-not $SkipInstall) {
  $pythonDeps = "$gate0Root\.gate0-python"
  if ($env:GATE0_WHEELHOUSE) {
    # Offline/bootstrap fallback: verify from a local wheel mirror without pip's temp dir.
    & $pythonExe @pythonPrefix "$gate0Root\scripts\install_python_wheels.py" $env:GATE0_WHEELHOUSE $pythonDeps
  } else {
    & $pythonExe @pythonPrefix -m pip install --disable-pip-version-check --target $pythonDeps --requirement "$gate0Root\tests\contract\requirements.txt"
  }
  if ($LASTEXITCODE -ne 0) { throw "Python dependency installation failed: $LASTEXITCODE" }
  Invoke-Pnpm -PnpmArgs @('install', '--frozen-lockfile')
}

$pythonDeps = "$gate0Root\.gate0-python"
if (Test-Path -LiteralPath $pythonDeps) {
  $env:PYTHONPATH = if ($env:PYTHONPATH) { "$pythonDeps;$env:PYTHONPATH" } else { $pythonDeps }
} elseif (-not $env:PYTHONPATH) {
  throw "Python dependencies are unavailable. Run without -SkipInstall or set PYTHONPATH."
}

if (-not $env:GATE0_PGLITE_MODULE) {
  $localPglite = "$gate0Root\node_modules\@electric-sql\pglite"
  if (Test-Path -LiteralPath $localPglite) {
    $env:GATE0_PGLITE_MODULE = $localPglite
  } else {
    throw "PGlite is unavailable. Run without -SkipInstall or set GATE0_PGLITE_MODULE."
  }
}

$env:PYTHONDONTWRITEBYTECODE = '1'
& $pythonExe @pythonPrefix "$gate0Root\scripts\verify_gate0.py"
if ($LASTEXITCODE -ne 0) { throw "Gate 0 verification failed: $LASTEXITCODE" }

Write-Output 'GATE0_BOOTSTRAP_VERIFY_OK'
