try {
    scripts\win\dc-dev.ps1 exec -T sonar-django-backend coverage report $args
    scripts\win\dc-dev.ps1 exec -T soanr-django-backend coverage html $args
    Invoke-Item htmlcov/index.html
}
catch {
    Write-Output "Error occurred while running the script - make sure to run the script from the root directory of the project!"
    Write-Host $_.Exception.Message
    exit(1)
}
