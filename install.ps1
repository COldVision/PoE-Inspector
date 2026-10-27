# Personal "installer": creates a Desktop and Start-menu shortcut that starts PoE Inspector (server + app window) in one click.
# Nothing is downloaded or copied; the project stays where it is. Remove the shortcuts to uninstall.
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$pyw = Join-Path (Split-Path (Get-Command python).Source) 'pythonw.exe'
if (-not (Test-Path $pyw)) { throw 'pythonw.exe not found: install Python 3' }
$ico = Join-Path $root 'web\logo.ico'
$sh = New-Object -ComObject WScript.Shell
foreach ($dir in @([Environment]::GetFolderPath('Desktop'), (Join-Path $env:APPDATA 'Microsoft\Windows\Start Menu\Programs'))) {
  $lnk = $sh.CreateShortcut((Join-Path $dir 'PoE Inspector.lnk'))
  $lnk.TargetPath = $pyw
  $lnk.Arguments = '"' + (Join-Path $root 'launcher.pyw') + '"'
  $lnk.WorkingDirectory = $root
  if (Test-Path $ico) { $lnk.IconLocation = $ico }
  $lnk.Description = 'PoE Inspector'
  $lnk.Save()
  Write-Host "Created: $dir\PoE Inspector.lnk"
}
