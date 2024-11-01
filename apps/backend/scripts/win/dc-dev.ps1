try {
    docker-compose -f compose.yml -f compose-dev.yml --env-file conf\docker\common.env --env-file conf\docker\dev.env --env-file conf\docker\dev-secrets.env $args
}
catch {
    Write-Output "Error occurred while running the script - make sure to run the script from the root directory of the project!"
    Write-Host $_.Exception.Message
    exit(1)
}
