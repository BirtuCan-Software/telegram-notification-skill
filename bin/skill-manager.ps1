# PowerShell wrapper for skill-manager.py
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
python "$ScriptDir\skill-manager.py" @args
