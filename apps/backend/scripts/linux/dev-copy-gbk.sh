#!/usr/bin/env bash

set -euo pipefail

# Check if the correct number of arguments is provided
if [ "$#" -ne 2 ]; then
  echo "Usage: $0 <source_file> <destination_repo>" >&2
  exit 1
fi

SOURCE_FILE="$1"
DEST_REPO="$2"

if [ ! -f "$SOURCE_FILE" ]; then
  echo "Source file does not exist: $SOURCE_FILE" >&2
  exit 1
fi

# Copy the file to the destination repository
mkdir -p "$DEST_REPO"
cp "$SOURCE_FILE" "$DEST_REPO"
