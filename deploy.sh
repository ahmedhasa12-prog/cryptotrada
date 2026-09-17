#!/bin/bash
# CryptoTrada Railway Deploy — Run: bash deploy.sh
set -e
cd /Users/ahmedabdelwahid/projects/cryptotrada
echo "Installing Railway CLI..."
NPM_CONFIG_CACHE=/tmp/npm-cache npx @railway/cli login
NPM_CONFIG_CACHE=/tmp/npm-cache npx @railway/cli init
NPM_CONFIG_CACHE=/tmp/npm-cache npx @railway/cli up --deploy
echo "Done! Visit the Railway URL."
