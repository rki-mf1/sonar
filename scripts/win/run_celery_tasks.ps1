try {
    docker-compose -f .\docker-compose-dev.yml run --rm dev-django celery -A covsonar_backend worker --loglevel=info --without-gossip --without-mingle --without-heartbeat -Ofair
}
catch {
    Write-Output "Error occurred while running the script - make sure to run the script from the root directory of the project!"
    Write-Host $_.Exception.Message
    exit(1)
}