param(
  [string]$ScoutRuntimeRoot = (Split-Path -Parent $PSScriptRoot)
)
$ErrorActionPreference = 'Stop'
$PackageRoot = Join-Path $ScoutRuntimeRoot 'runtime\packages\chengcheng-cost-monitor'
$Preflight = Join-Path $ScoutRuntimeRoot 'scripts\preflight_cost_runtime.py'
$Wrapper = Join-Path $ScoutRuntimeRoot 'jobs\cost-daily-shadow.py'
python $Preflight --package-root $PackageRoot
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
python $Wrapper --package-root $PackageRoot
exit $LASTEXITCODE
