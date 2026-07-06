#!/bin/bash
# Wrapper script to execute the LinkedIn Auto-Apply Bot in the correct environment

# Change directory to the repository folder
cd "/home/botuser/LinkedIn-Autoapply"

# Check if the virtual environment exists and activate it
if [ -d ".venv" ]; then
    source .venv/bin/activate
    python main.py
else
    echo "Warning: Virtual environment (.venv) not found. Running with system python3."
    python3 main.py
fi
