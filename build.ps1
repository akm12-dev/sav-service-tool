# Construit release\SAVServiceTool-<version>-windows.zip (exe + commands.json + licences + LISEZMOI).
# Prérequis : Python 3 + PyInstaller (py -m pip install pyinstaller pywin32 si nécessaire).
$ErrorActionPreference = 'Stop'
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $here
$version = (Select-String -Path service_tool.py -Pattern 'APP_VERSION = "(.+)"').Matches[0].Groups[1].Value
$work = Join-Path $env:TEMP 'savst_build'
py -m PyInstaller --noconfirm --clean --onefile --windowed --name SAVServiceTool `
  --add-data "$here\commands.json;." --version-file "$here\version_info.txt" `
  --distpath "$here\dist" --workpath $work --specpath $work service_tool.py
if ($LASTEXITCODE -ne 0) { throw 'Echec PyInstaller' }
$pkg = Join-Path $here "release\SAVServiceTool-$version-windows"
Remove-Item -Recurse -Force $pkg -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force $pkg | Out-Null
Copy-Item dist\SAVServiceTool.exe, commands.json, THIRD_PARTY_NOTICES.txt, LISEZMOI.txt $pkg
$zip = "$pkg.zip"
Remove-Item -Force $zip -ErrorAction SilentlyContinue
Compress-Archive -Path "$pkg\*" -DestinationPath $zip
Get-FileHash $zip -Algorithm SHA256 | ForEach-Object { "$($_.Hash.ToLower())  $(Split-Path $zip -Leaf)" }
