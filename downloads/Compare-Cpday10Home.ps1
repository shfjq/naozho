# Read-only. Run after launching the standalone probe once in user 0.
[CmdletBinding()]
param([string]$Serial)
$ErrorActionPreference = 'Stop'
$device = @()
if ($Serial) { $device = @('-s', $Serial) }
function Read-Device([string]$command) {
    $lines = & adb @device shell $command
    if ($LASTEXITCODE -ne 0 -or ($lines -match '^(Error:|Exception occurred|Unknown command)')) {
        throw "adb failed: $command -- $($lines -join ' ')"
    }
    $lines
}

$clock = 'com.naozho.clock'
$probe = 'com.naozho.homeprobe'
Write-Output ("Sample " + (Get-Date -Format o))
if (((Read-Device 'am get-current-user') -join '').Trim() -ne '0') { throw 'Expected foreground user 0.' }
$sdk = [int]((Read-Device 'getprop ro.build.version.sdk') -join '')
Read-Device 'am get-started-user-state 0'
Read-Device 'getprop ro.build.fingerprint'
foreach ($pkg in @($clock,$probe)) {
    if (!((Read-Device "pm path --user 0 $pkg") -match '^package:')) { throw "Package unavailable: $pkg" }
    Write-Output "=== $pkg ==="
    Read-Device "dumpsys package $pkg" | Select-String 'versionName=|versionCode=|User 0:|android.intent.category.HOME|MainActivity' |
        ForEach-Object { $_.Line }
}
$baseIntent = '-a android.intent.action.MAIN -c android.intent.category.HOME'
$defaultCategory = ' -c android.intent.category.DEFAULT'
$cases = @(@{Flags=0; Extra=''}, @{Flags=65536; Extra=$defaultCategory}, @{Flags=786432; Extra=''})
if ($sdk -lt 36) {
    Write-Output 'Compatibility run: using shell default query flags. Exact CPDAY10 matrix requires API 36.'
    $cases = @(@{Extra=''}, @{Extra=$defaultCategory})
}
foreach ($case in $cases) {
    $flags = if ($sdk -ge 36) { "--query-flags $($case.Flags)" } else { '' }
    foreach ($scope in @(''," -p $clock"," -p $probe")) {
        $cmd = "cmd package query-activities --components --user 0 $flags $baseIntent$($case.Extra)$scope"
        Write-Output $cmd
        Read-Device $cmd
    }
}
$mainFlag = if ($sdk -ge 36) { '--query-flags 0' } else { '' }
$main = Read-Device "cmd package query-activities --components --user 0 $mainFlag -a android.intent.action.MAIN"
foreach ($pkg in @($clock,$probe)) {
    Write-Output "Unscoped MAIN entries from $pkg (without HOME category):"
    $main |
        Where-Object { $_.Trim().StartsWith("$pkg/") }
}
Write-Output 'Resolved system HOME, then DEFAULT-category HOME:'
$launchFlags = if ($sdk -ge 36) { '--query-flags 66560' } else { '' }
$settingsFlags = if ($sdk -ge 36) { '--query-flags 65536' } else { '' }
Read-Device "cmd package resolve-activity --brief --user 0 $launchFlags $baseIntent"
Read-Device "cmd package resolve-activity --brief --user 0 $settingsFlags $baseIntent$defaultCategory"
Write-Output 'Independent app caller, most recent sample (check its timestamp):'
Read-Device 'logcat -d -s NaozhoHomeProbe:I' | Select-Object -Last 12
