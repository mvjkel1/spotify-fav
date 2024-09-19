#!/bin/bash 
echo "Running pre-commit formatting script..."

ruff format src/server/app --line-length 100
ruff format src/server/tests --line-length 100