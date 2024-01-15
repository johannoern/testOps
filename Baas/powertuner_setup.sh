#!/bin/bash

repo_dir="aws-lambda-power-tuning"

# Check if the directory exists
if [ ! -d "$repo_dir" ]; then
    # Clone the repository if it doesn't exist
    git clone https://github.com/alexcasalboni/aws-lambda-power-tuning.git "$repo_dir"
fi

# Move into the cloned directory
cd "$repo_dir" || exit

# Build the SAM application

sam build -u