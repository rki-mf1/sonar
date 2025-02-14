try {
    scripts\win\dev-manage.ps1 flush --noinput
    scripts\win\dev-manage.ps1 loaddata initial_auth test_data_1000
    scripts\win\dev-copy-gbk.ps1 -SourceFile "..\..\..\test-data\covid19\MN908947.nextclade.gb" -DestinationRepo ".\work\sonar\data\import\gbks\"
}
catch {
    Write-Output "Error occurred while running the script - make sure to run the script from the root directory of the project!"
    Write-Host $_.Exception.Message
    exit(1)
}
