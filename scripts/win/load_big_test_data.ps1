try {
    scripts\win\dev-manage.ps1 flush --noinput
    scripts\win\dev-manage.ps1 loaddata initial_auth test_data_big
}
catch {
    Write-Output "Error occurred while running the script - make sure to run the script from the root directory of the project!"
    Write-Host $_.Exception.Message
    exit(1)
}