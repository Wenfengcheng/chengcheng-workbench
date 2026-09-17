param(
  [string]$PackageRoot = "$HOME\.scout\runtime\packages\chengcheng-cost-monitor"
)
$ErrorActionPreference = 'Stop'
$PreviousAzureConfigDir = $env:AZURE_CONFIG_DIR

if ($PackageRoot -match '\.concordia-client') {
  throw 'Scout Azure profiles must not be provisioned under .concordia-client.'
}
if (-not (Test-Path -LiteralPath (Join-Path $PackageRoot 'package-manifest.json'))) {
  throw "Scout cost package is missing: $PackageRoot"
}
if (-not (Get-Command az.cmd -ErrorAction SilentlyContinue)) {
  throw 'az.cmd is required.'
}

function New-ScoutAzureProfile {
  param(
    [Parameter(Mandatory=$true)][string]$Name,
    [Parameter(Mandatory=$true)][string]$Cloud,
    [Parameter(Mandatory=$true)][string]$Subscription
  )
  $ConfigDir = Join-Path $PackageRoot "fy27-cost-review\monitoring\azure-config\$Name"
  $Profile = Join-Path $ConfigDir 'azureProfile.json'
  if (Test-Path -LiteralPath $Profile) {
    throw "Create-only guard: Scout Azure profile already exists: $Profile"
  }
  New-Item -ItemType Directory -Path $ConfigDir -Force | Out-Null
  $env:AZURE_CONFIG_DIR = $ConfigDir
  az.cmd cloud set --name $Cloud
  if ($LASTEXITCODE -ne 0) { throw "Failed to select Azure cloud $Cloud" }
  Write-Host "Interactive Azure login for Scout profile '$Name' ($Cloud)..." -ForegroundColor Cyan
  az.cmd login
  if ($LASTEXITCODE -ne 0) { throw "Azure login failed for Scout profile $Name" }
  az.cmd account set --subscription $Subscription
  if ($LASTEXITCODE -ne 0) { throw "Subscription selection failed for Scout profile $Name" }
  $actual = az.cmd account show --query "{name:name,id:id,tenantId:tenantId,environmentName:environmentName}" -o json | ConvertFrom-Json
  if ($LASTEXITCODE -ne 0) { throw "Azure account read-back failed for Scout profile $Name" }
  Write-Host ("PASS {0}: {1} / {2} / {3}" -f $Name,$actual.environmentName,$actual.name,$actual.id) -ForegroundColor Green
}

New-ScoutAzureProfile -Name 'pbi-cost' -Cloud 'AzureCloud' -Subscription 'Win In China OfficePLUS Global'
New-ScoutAzureProfile -Name 'la' -Cloud 'AzureChinaCloud' -Subscription 'c6dbcbd4-85b4-485e-acd4-7b018cd23e6d'
New-ScoutAzureProfile -Name 'compute' -Cloud 'AzureChinaCloud' -Subscription 'c6dbcbd4-85b4-485e-acd4-7b018cd23e6d'

$env:AZURE_CONFIG_DIR = $PreviousAzureConfigDir
Write-Host 'Scout cost Azure profiles provisioned. Run preflight next; do not copy these profiles elsewhere.' -ForegroundColor Green
