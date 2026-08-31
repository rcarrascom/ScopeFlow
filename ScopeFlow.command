#!/bin/bash

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

echo "=================================================="
echo "Starting ScopeFlow (mock data, port 8004)..."
echo "=================================================="

if [ ! -d "venv" ]; then
    python3 -m venv venv
fi

source venv/bin/activate
pip3 install -q fastapi uvicorn jinja2 pydantic

lsof -ti:8004 | xargs kill -9 2>/dev/null

echo "Booting up the local web server (port 8004)..."
nohup venv/bin/python -m uvicorn main:app --host 127.0.0.1 --port 8004 --log-level warning > /dev/null 2>&1 &

sleep 2
open http://127.0.0.1:8004/ScopeFlow

nohup osascript -e 'tell application "Terminal" to close front window' > /dev/null 2>&1 &
exit 0
