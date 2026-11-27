[CmdletBinding()]
param(
    [Parameter(Mandatory)][string]$Serial,
    [ValidateSet('inventory','observe','return','status')][string]$Mode = 'inventory',
    [string]$Adb = 'adb'
)
$ErrorActionPreference = 'Stop'
# Address one explicitly selected device. Never connect, grant root or install from this script.
if ($Serial -notmatch '^[a-zA-Z0-9._:-]+$') { throw 'Invalid ADB serial' }
if ($Mode -eq 'status') {
    $lines = & $Adb -s $Serial shell dumpsys activity activities
    if ($LASTEXITCODE -ne 0) { throw 'Activity service unavailable' }
    $lines | Select-String 'mLockTaskModeState=' | ForEach-Object { $_.Line.Trim() }
    $windows = & $Adb -s $Serial shell dumpsys window displays
    if ($LASTEXITCODE -ne 0) { throw 'Window service unavailable' }
    $focus = @($windows | Select-String '^[ ]*mCurrentFocus=')
    if ($focus.Count -eq 0) {
        $windows = & $Adb -s $Serial shell dumpsys window windows
        if ($LASTEXITCODE -ne 0) { throw 'Window service unavailable' }
        $focus = @($windows | Select-String '^[ ]*mCurrentFocus=')
    }
    if ($focus.Count -ne 1) { Write-Output 'focus=unknown' }
    elseif ($focus[0].Line -match 'u0 com\.naozho\.clock/(?:com\.naozho\.clock\.|\.)MainActivity\}') { Write-Output 'focus=clock' }
    elseif ($focus[0].Line -match 'u0 com\.droiclaw\.launcher3/com\.freeme\.launcher\.FreemeLauncher\}') { Write-Output 'focus=freeme' }
    else { Write-Output 'focus=other_or_none' }
    Write-Output 'Read actual flags/allowlist in the clock policy diagnostics. Verify touch physically.'
    return
}
$fixed = 'su -c "/system/bin/sh /data/adb/modules/naozho_power_trial/trial.sh ' + $Mode + '"'
& $Adb -s $Serial shell $fixed
if ($LASTEXITCODE -ne 0) { throw 'Trial unavailable. Preserve the reported reason; no automatic retry.' }
