#!/bin/bash
read -p "Which do you want to use? (shyft/dexscreener): " choice
if [[ "$choice" == "shyft" ]]; then
    python3 token_monitoring.py
elif [[ "$choice" == "dexscreener" ]]; then
    python3 project.py
else
    echo "Invalid choice."
fi
