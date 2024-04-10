try {
scripts\win\dev-manage.ps1 shell -c "import permission_model.permission_model as p; p.main()"
}
catch {
    Write-Output "Error occurred while running the script - make sure to run the script from the root directory of the project!"
    Write-Host $_.Exception.Message
    exit(1)
}