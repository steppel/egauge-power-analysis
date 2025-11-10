#!/bin/bash

# Script to push eGauge Power Analysis project to GitHub
# Usage: ./push_to_github.sh [username] [repo-name]

USERNAME=${1:-"yourusername"}
REPO_NAME=${2:-"egauge-power-analysis"}

echo "================================================"
echo "   Push eGauge Power Analysis to GitHub"
echo "================================================"
echo ""
echo "This script will help you push your repo to GitHub."
echo "First, make sure you've created a repository on GitHub:"
echo "  https://github.com/new"
echo ""
echo "Repository name should be: $REPO_NAME"
echo ""
read -p "Have you created the GitHub repository? (y/n) " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]
then
    echo "Setting up remote origin..."

    # Check if remote already exists
    if git remote | grep -q "origin"; then
        echo "Remote 'origin' already exists. Updating URL..."
        git remote set-url origin "git@github.com:${USERNAME}/${REPO_NAME}.git"
    else
        echo "Adding remote 'origin'..."
        git remote add origin "git@github.com:${USERNAME}/${REPO_NAME}.git"
    fi

    echo "Pushing to GitHub..."
    git push -u origin main

    echo ""
    echo "✅ Successfully pushed to GitHub!"
    echo "Your repository is now available at:"
    echo "https://github.com/${USERNAME}/${REPO_NAME}"
else
    echo "Please create a GitHub repository first at: https://github.com/new"
    echo "Then run this script again."
fi