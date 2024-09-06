Param(
    [switch]$NoTestData = $false,
    [switch]$NoRebuild = $false
)
try {
    scripts\win\dc-dev.ps1 down
    if ($LASTEXITCODE -ne 0) {
        exit($LASTEXITCODE)
    }

    if ($NoRebuild) {
        Write-Output "######### Skip rebuilding the docker image ###########"
    }
    else {
        scripts\win\build_docker_dev.ps1
        if ($LASTEXITCODE -ne 0) {
            exit($LASTEXITCODE)
        }
    }
    scripts\win\dc-dev.ps1 up -d
    if ($LASTEXITCODE -ne 0) {
        exit($LASTEXITCODE)
    }
    scripts\win\dev-manage.ps1 migrate
    if ($LASTEXITCODE -ne 0) {
        exit($LASTEXITCODE)
    }
    if ($NoTestData) {
        Write-Output "######### loading fixtures without test data #########"
        scripts\win\dev-manage.ps1 loaddata initial_auth
    }
    else {
        Write-Output "######### loading fixtures with test data ############"    
        scripts\win\dev-manage.ps1 loaddata initial_auth test_data_sm
        scripts\win\dev-manage.ps1 import_lineage
    }
    if ($LASTEXITCODE -ne 0) {
        exit($LASTEXITCODE)
    }
}
catch {
    Write-Output "Error occurred while running the script - make sure to run the script from the root directory of the project!"
    Write-Host $_.Exception.Message
    exit(1)
}