try {
    scripts\win\dc-dev.ps1 logs --tail 50 -f sonar-django-backend
}
catch {
    Write-Output "Error occurred while running the script - make sure to run the script from the root directory of the project!"
    Write-Host $_.Exception.Message
    exit(1)
}
