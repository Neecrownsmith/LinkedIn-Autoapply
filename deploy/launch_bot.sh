#!/bin/bash
# Wrapper script to execute the LinkedIn Auto-Apply Bot in the correct environment

# Change directory to the repository folder
cd "/home/botuser/LinkedIn-Autoapply"

# Check if the virtual environment exists and activate it
if [ -d ".venv" ]; then
    source .venv/bin/activate
else
    echo "Warning: Virtual environment (.venv) not found. Running with system python."
fi

# Execute the orchestrator python script
python main.py
