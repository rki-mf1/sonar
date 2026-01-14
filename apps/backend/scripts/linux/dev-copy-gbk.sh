#!/usr/bin/env bash

# Check if the correct number of arguments is provided
if [ "$#" -ne 2 ]; then
  echo "Usage: $0 <source_file> <destination_repo>"
  exit 1
fi

SOURCE_FILE="$1"
DEST_REPO="$2"

# Copy the file to the destination repository
mkdir -p "$DEST_REPO"
cp "$SOURCE_FILE" "$DEST_REPO"

# Check if the copy was successful
if ! [ $? -eq 0 ]; then
  echo "Failed to copy file to $DEST_REPO"
fi
