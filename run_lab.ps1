# Run the prepared environment or provide an actionable setup message.
$projectDirectory = Split-Path -Parent $MyInvocation.MyCommand.Path
$labPython = Join-Path $projectDirectory '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $labPython)) {
    Write-Error 'Create .venv and install requirements.txt using the commands in README.md.'
    exit 1
}
Set-Location -LiteralPath $projectDirectory
$env:MPLCONFIGDIR = Join-Path $projectDirectory '.mplconfig'
& $labPython -m streamlit run app.py
