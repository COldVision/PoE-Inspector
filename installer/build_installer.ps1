# Builds "PoE Inspector Setup 1.0.exe": embeddable Python + dependencies + the app, packed with Inno Setup.
# Run from PowerShell:  powershell -ExecutionPolicy Bypass -File installer\build_installer.ps1
# Downloads (official sites only, saved to ..\poe_inspector_build\downloads and checked for a valid signature where the vendor signs):
#   python-3.12.10-embed-amd64.zip (python.org), get-pip.py (pypa.io), Inno Setup (jrsoftware.org), pip packages pillow numpy texture2ddecoder pywebview.
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
$proj = Split-Path -Parent $PSScriptRoot
$work = Join-Path (Split-Path -Parent $proj) 'poe_inspector_build'
$dl = Join-Path $work 'downloads'; $stage = Join-Path $work 'stage'; $out = Join-Path $work 'out'
$app = Join-Path $stage 'app'; $rt = Join-Path $stage 'runtime'
New-Item -ItemType Directory -Force $dl, $out | Out-Null

function Get-File($url, $name) {
  $f = Join-Path $dl $name
  if (-not (Test-Path $f)) { Write-Host "Downloading $name"; Invoke-WebRequest $url -OutFile $f }
  return $f
}

# ---- 1. embeddable Python
$pyzip = Get-File 'https://www.python.org/ftp/python/3.12.10/python-3.12.10-embed-amd64.zip' 'python-3.12.10-embed-amd64.zip'
if (Test-Path $stage) { Remove-Item $stage -Recurse -Force }
New-Item -ItemType Directory -Force $app, $rt | Out-Null
Expand-Archive $pyzip $rt -Force
Set-Content (Join-Path $rt 'python312._pth') "python312.zip`r`n.`r`n..\app`r`nLib\site-packages`r`nimport site`r`n" -Encoding ascii

# ---- 2. pip + dependencies
$getpip = Get-File 'https://bootstrap.pypa.io/get-pip.py' 'get-pip.py'
$py = Join-Path $rt 'python.exe'
& $py $getpip --no-warn-script-location | Out-Host
& $py -m pip install --no-warn-script-location --no-cache-dir setuptools wheel | Out-Host   # the embeddable Python has none; bottle / proxy_tools (pywebview) build from source
& $py -m pip install --no-warn-script-location --no-cache-dir pillow numpy texture2ddecoder "pywebview>=5" | Out-Host
if ($LASTEXITCODE) { throw 'pip install failed' }

# ---- 3. the app itself (no game data, no caches, no database)
New-Item -ItemType Directory -Force (Join-Path $app 'poe_inspector') | Out-Null
Copy-Item (Join-Path $proj 'poe_inspector\*.py') (Join-Path $app 'poe_inspector')
Copy-Item (Join-Path $proj 'poe_inspector\oo2core.dll') (Join-Path $app 'poe_inspector')
Copy-Item (Join-Path $proj 'web') (Join-Path $app 'web') -Recurse
Get-ChildItem (Join-Path $app 'web') -Recurse -Include *.bak* | Remove-Item -Force
Copy-Item (Join-Path $proj 'schema.min.json') $app
Copy-Item (Join-Path $proj 'app_main.pyw') $app
Copy-Item (Join-Path $proj 'VERSION') $app
if (Test-Path (Join-Path $proj 'update.json')) { Copy-Item (Join-Path $proj 'update.json') $app }
Copy-Item (Join-Path $proj 'web\logo.ico') (Join-Path $stage 'poe_inspector.ico')   # a fresh file name: the shell caches icons per path
& $py -m compileall -q $app | Out-Null

# ---- 3b. update package for GitHub Releases (the app folder without the runtime) + its SHA-256
$ver = (Get-Content (Join-Path $proj 'VERSION')).Trim()
$upd = Join-Path $out 'app-update.zip'
if (Test-Path $upd) { Remove-Item $upd }
Get-ChildItem $app -Recurse -Directory -Filter __pycache__ | ForEach-Object { $_.FullName } | Out-Null
Compress-Archive -Path (Get-ChildItem $app -Exclude update.json,__pycache__) -DestinationPath $upd
(Get-FileHash $upd -Algorithm SHA256).Hash.ToLower() + '  app-update.zip' | Set-Content "$upd.sha256" -Encoding ascii
Write-Host ("Update package v" + $ver + ": " + $upd + " (+ .sha256)")

# ---- 4. Inno Setup
$iscc = @("$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe", "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe", "$env:ProgramFiles\Inno Setup 6\ISCC.exe") | ? { Test-Path $_ } | Select-Object -First 1
if (-not $iscc) {
  $is = Get-File 'https://jrsoftware.org/download.php/is.exe' 'innosetup.exe'
  $sig = Get-AuthenticodeSignature $is
  if ($sig.Status -ne 'Valid') { throw "Inno Setup installer signature is $($sig.Status)" }
  Write-Host "Installing Inno Setup for the current user (signed by $($sig.SignerCertificate.Subject))"
  Start-Process $is -ArgumentList '/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART', '/CURRENTUSER' -Wait
  $iscc = "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe"
}
& $iscc "/DStage=$stage" "/DOut=$out" (Join-Path $PSScriptRoot 'installer.iss') | Out-Host
if ($LASTEXITCODE) { throw 'ISCC failed' }
Write-Host ("Done: " + $out + "\PoE Inspector Setup 1.0.exe")
