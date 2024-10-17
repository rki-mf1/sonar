try {
    scripts\win\dev-manage.ps1 dumpdata --indent=4 rest_api django_apscheduler -o dumped-data.json
}
catch {
    Write-Output "Error occurred while running the script - make sure to run the script from the root directory of the project!"
    Write-Host $_.Exception.Message
    exit(1)
}
