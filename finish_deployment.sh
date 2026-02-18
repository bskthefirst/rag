#!/bin/bash
if [ -z "$1" ]; then
    echo "Error: Please provide your GitHub Personal Access Token."
    echo "Usage: ./finish_deployment.sh <YOUR_TOKEN>"
    exit 1
fi

TOKEN=$1
REPO="https://bskthefirst:${TOKEN}@github.com/bskthefirst/rag.git"

echo "Setting remote URL with token..."
git remote set-url origin $REPO

echo "Pushing code..."
git push -u origin main

if [ $? -eq 0 ]; then
    echo "✅ Success! Deployment complete."
else
    echo "❌ Push failed. Please check your token permissions (ensure 'workflow' is checked)."
fi
