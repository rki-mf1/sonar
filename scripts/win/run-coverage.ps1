try {
    docker-compose -f docker-compose-dev.yml exec -T dev-django pip install --no-cache-dir --disable-pip-version-check -r requirements-testing.txt
    docker-compose -f docker-compose-dev.yml exec -T dev-django coverage run ./manage.py test --no-input $args
}
catch {
    Write-Output "Error occurred while running the script - make sure to run the script from the root directory of the project!"
    Write-Host $_.Exception.Message
    exit(1)
}