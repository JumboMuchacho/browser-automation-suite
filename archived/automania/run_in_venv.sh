#!/usr/bin/env bash
# Universal venv launcher for Chip In project

# Activate venv (Linux/macOS)
if [ -d ".venv" ]; then
    if [ -f ".venv/bin/activate" ]; then
        source .venv/bin/activate
    elif [ -f ".venv/Scripts/activate" ]; then
        # Windows Git Bash
        source .venv/Scripts/activate
    fi
else
    echo "No .venv directory found. Please create it with 'python3 -m venv .venv' and install requirements."
    exit 1
fi

python run.py
