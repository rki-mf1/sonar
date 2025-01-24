# dev-copy-gbk.ps1
param (
    [string]$SourceFile,
    [string]$DestinationRepo
)

# Check if the correct number of arguments is provided
if (-not $SourceFile -or -not $DestinationRepo) {
    Write-Output "Usage: dev-copy-gbk.ps1 -SourceFile <source_file> -DestinationRepo <destination_repo>"
    exit 1
}

if (-not (Test-Path -Path $DestinationRepo)) {
    New-Item -ItemType Directory -Path $DestinationRepo -Force | Out-Null
}

try {
    Copy-Item -Path $SourceFile -Destination $DestinationRepo -Force
    # Write-Output "File successfully copied to $DestinationRepo"
} catch {
    Write-Output "Failed to copy file to $DestinationRepo"
    exit 1
}