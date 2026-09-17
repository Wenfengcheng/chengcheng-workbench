param(
  [string]$GlobalSubscription = 'Win In China OfficePLUS Global',
  [string]$ChinaProdSubscription = 'c6dbcbd4-85b4-485e-acd4-7b018cd23e6d',
  [string]$ChinaEdogSubscription = '187a032c-caf1-4f22-bf1d-b01e42d11396'
)
$ErrorActionPreference = 'Stop'

if (-not (Get-Command az.cmd -ErrorAction SilentlyContinue)) {
  throw 'az.cmd is required.'
}

# Compatibility entrypoint retained from v0.5.0. It no longer creates or copies
# Azure CLI profiles. Scout reuses the host login and explicitly selects context.
$checks = @(
  @{ Cloud = 'AzureCloud'; Subscription = $GlobalSubscription },
  @{ Cloud = 'AzureChinaCloud'; Subscription = $ChinaProdSubscription },
  @{ Cloud = 'AzureChinaCloud'; Subscription = $ChinaEdogSubscription }
)

foreach ($check in $checks) {
  az.cmd cloud set --name $check.Cloud
  if ($LASTEXITCODE -ne 0) { throw "Failed to select cloud $($check.Cloud)" }
  az.cmd account set --subscription $check.Subscription
  if ($LASTEXITCODE -ne 0) {
    throw "Azure CLI login does not contain $($check.Cloud) subscription $($check.Subscription). Run az login only if the host login is expired."
  }
  $actual = az.cmd account show --query "{name:name,id:id,environmentName:environmentName}" -o json | ConvertFrom-Json
  if ($LASTEXITCODE -ne 0 -or $actual.environmentName -ne $check.Cloud) {
    throw "Azure account context read-back failed for $($check.Subscription)"
  }
  Write-Host ("PASS: {0} / {1} / {2}" -f $actual.environmentName,$actual.name,$actual.id) -ForegroundColor Green
}

# Leave the machine in the normal OfficePlus China Prod context.
az.cmd cloud set --name AzureChinaCloud
az.cmd account set --subscription $ChinaProdSubscription
Write-Host 'Host Azure CLI login is ready for Scout cost runtime; no profile was created or copied.' -ForegroundColor Green
