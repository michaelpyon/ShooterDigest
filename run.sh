#!/bin/bash
# Shooter Digest - One-click runner
# Just double-click this file or run: ./run.sh

cd "$(dirname "$0")"

# Set up Python environment if needed
if [ ! -d "venv" ]; then
    echo "First-time setup: installing dependencies..."
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt --quiet
    echo "Setup complete!"
    echo ""
else
    source venv/bin/activate
fi

python main.py

# Open the generated digest
LATEST=$(ls -t output/digest_*.md 2>/dev/null | head -1)
if [ -n "$LATEST" ]; then
    echo ""
    echo "Opening digest..."
    open "$LATEST"
fi
