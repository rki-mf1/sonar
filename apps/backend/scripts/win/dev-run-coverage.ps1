try {
    scripts\win\dc-dev.ps1 exec -T sonar-django-backend pip install --no-cache-dir --disable-pip-version-check -r requirements-testing.txt
    scripts\win\dc-dev.ps1 exec -T sonar-django-backend coverage run ./manage.py test --no-input $args
}
catch {
    Write-Output "Error occurred while running the script - make sure to run the script from the root directory of the project!"
    Write-Host $_.Exception.Message
    exit(1)
}
