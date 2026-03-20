# Chrome Profile Cleanup Script
# WARNING: Close Chrome completely before running this!

$chromeUserDataPath = "$env:LOCALAPPDATA\Google\Chrome\User Data"

Write-Host "Chrome User Data Path: $chromeUserDataPath" -ForegroundColor Cyan
Write-Host ""

if (Test-Path $chromeUserDataPath) {
    # Get all profile directories
    $profiles = Get-ChildItem -Path $chromeUserDataPath -Directory |
                Where-Object { $_.Name -match "profile" -or $_.Name -match "Profile" }

    Write-Host "Found the following profiles:" -ForegroundColor Yellow
    $profiles | ForEach-Object { Write-Host "  - $($_.Name)" }
    Write-Host ""

    # Filter test profiles
    $testProfiles = $profiles | Where-Object {
        $_.Name -match "smoke_|postfix_|allcheck_|apitest_"
    }

    if ($testProfiles.Count -gt 0) {
        Write-Host "Test profiles to delete:" -ForegroundColor Red
        $testProfiles | ForEach-Object { Write-Host "  - $($_.Name)" -ForegroundColor Red }
        Write-Host ""

        $confirm = Read-Host "Do you want to delete these test profiles? (yes/no)"

        if ($confirm -eq "yes") {
            foreach ($profile in $testProfiles) {
                Write-Host "Deleting: $($profile.FullName)" -ForegroundColor Red
                Remove-Item -Path $profile.FullName -Recurse -Force -ErrorAction SilentlyContinue
            }
            Write-Host ""
            Write-Host "Cleanup complete!" -ForegroundColor Green
        } else {
            Write-Host "Cleanup cancelled." -ForegroundColor Yellow
        }
    } else {
        Write-Host "No test profiles found with names matching smoke_, postfix_, allcheck_, or apitest_" -ForegroundColor Yellow
    }
} else {
    Write-Host "Chrome User Data directory not found at: $chromeUserDataPath" -ForegroundColor Red
}
