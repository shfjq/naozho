# Requires Windows PowerShell 5.1+ and Android platform-tools (adb on PATH).
# Reads OS policy as shell. Only the diagnostic receipt in the debug app's files is written.
[CmdletBinding()]
param([string]$Serial)

$ErrorActionPreference = 'Stop'
$deviceArgs = @()
if ($Serial) { $deviceArgs = @('-s', $Serial) }
$clock = 'com.naozho.clock'
$native = 'com.droiclaw.launcher3/com.freeme.launcher.FreemeLauncher'

function Invoke-Device([string[]]$AdbArgs) {
    $output = & adb @deviceArgs @AdbArgs
    if ($LASTEXITCODE -ne 0) { throw "adb failed ($LASTEXITCODE): $($AdbArgs -join ' ')" }
    return ($output -join [Environment]::NewLine).Trim()
}

if ((Invoke-Device @('get-state')) -ne 'device') { throw 'Connect one authorized CPDAY10, or specify -Serial.' }
if ((Invoke-Device @('shell','am get-current-user')) -ne '0') { throw 'Expected foreground user 0.' }
if ((Invoke-Device @('shell','getprop ro.build.version.sdk')) -ne '36') { throw 'Expected Android API 36.' }
$paths = (Invoke-Device @('shell',"pm path --user 0 $clock")) -split '\r?\n'
$base = @($paths | Where-Object { $_ -cmatch '^package:(/data/app/[-a-zA-Z0-9_+=~./]+/base\.apk)$' })
if ($base.Count -ne 1) { throw 'Could not identify the installed base APK.' }
$apk = $base[0].Substring(8)
$nonce = Invoke-Device @('shell',"run-as $clock cat files/home-policy-challenge")
if ($nonce -cnotmatch '^[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}$') { throw 'Prepare a new audit number in the recovery screen.' }

$idle = Invoke-Device @('shell','am wait-for-broadcast-idle --flush-broadcast-loopers')
if ($idle -match '(?i)unknown|error|exception|timeout|timed out') {
    throw "Broadcast drain was not confirmed: $idle"
}
$raw = Invoke-Device @('shell',"CLASSPATH=$apk app_process /system/bin com.naozho.clock.tools.HomePolicyReader $native $nonce")
if ($raw -cnotmatch '^[A-Za-z0-9+/]+={0,2}$') { throw 'The device did not return an unambiguous policy snapshot.' }
$receipt = [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($raw)) | ConvertFrom-Json
if ($receipt.nonce -cne $nonce -or $receipt.user -ne 0 -or $receipt.native -cne $native) {
    throw 'The snapshot does not match this request.'
}
$raw | & adb @deviceArgs shell "run-as $clock tee files/home-policy-audit.txt" | Out-Null
if ($LASTEXITCODE -ne 0 -or (Invoke-Device @('shell',"run-as $clock cat files/home-policy-audit.txt")) -cne $raw) {
    throw 'Could not verify the receipt in the debug application.'
}
$previous = if ($receipt.previous) { $receipt.previous } else { '(no managed HOME preference)' }
Write-Output "Audited user 0. Previous managed HOME: $previous"
Write-Output 'Return to the recovery screen and import the snapshot within five minutes.'
