try {
    scripts\win\dc-dev.ps1 run --rm sonar-django-backend "poetry run python ./manage.py $args"
}
catch {
    Write-Output "Error occurred while running the script - make sure to run the script from the root directory of the project!"
    Write-Host $_.Exception.Message
    exit(1)
}
