# Setup local: dependencias, MySQL, ingestao. Requer .env com OPENROUTER_API_KEY e DB_*.
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)
python scripts/setup_local.py @args
