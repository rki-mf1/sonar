try {
    docker-compose -f docker-compose-dev.yml exec -T dev-django coverage report $args
    docker-compose -f docker-compose-dev.yml exec -T dev-django coverage html $args
    Invoke-Item htmlcov/index.html
}
catch {
    Write-Output "Error occurred while running the script - make sure to run the script from the root directory of the project!"
    Write-Host $_.Exception.Message
    exit(1)
}