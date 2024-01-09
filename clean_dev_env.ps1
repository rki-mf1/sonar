Param(
    [switch]$NoTestData = $false,
    [switch]$NoRebuild = $false
)
.\dc-dev.ps1 down
if ($LASTEXITCODE -ne 0) {
    exit($LASTEXITCODE)
}

if ($NoRebuild) {
    echo "######### Skip rebuilding the docker image ###########"
}
else{
    .\build_docker_dev.ps1
    if ($LASTEXITCODE -ne 0) {
        exit($LASTEXITCODE)
    }
}
.\dc-dev.ps1 up -d
if ($LASTEXITCODE -ne 0) {
    exit($LASTEXITCODE)
}
.\dev-manage.ps1 migrate
if ($LASTEXITCODE -ne 0) {
    exit($LASTEXITCODE)
}
if ($NoTestData) {
    echo "######### loading fixtures without test data #########"
    .\dev-manage.ps1 loaddata initial_data initial_auth
}
else {
    echo "######### loading fixtures with test data ############"    
    .\dev-manage.ps1 loaddata test_data
}
if ($LASTEXITCODE -ne 0) {
    exit($LASTEXITCODE)
}