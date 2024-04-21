try {
    docker-compose -f .\docker-compose-dev.yml run --rm dev-django poetry run python ./manage.py $args
}
catch {
    Write-Output "Error occurred while running the script - make sure to run the script from the root directory of the project!"
    Write-Host $_.Exception.Message
    exit(1)
}