#!/usr/bin/env bash
# Mac/Linux:  ./run.sh   (local testing)
set -e
cd "$(dirname "$0")"
[ -d .venv ] || python3 -m venv .venv
source .venv/bin/activate
pip install -q -r requirements.txt
# --host 0.0.0.0 lets an iPhone on the same Wi-Fi reach this computer
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
