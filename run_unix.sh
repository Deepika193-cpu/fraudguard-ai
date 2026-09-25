#!/usr/bin/env bash
set -euo pipefail

if [[ ! -x ".venv/bin/python" ]]; then
  echo "Creating Python virtual environment..."
  python3 -m venv .venv
fi

source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt

if [[ ! -f ".env" ]]; then
  cp .env.example .env
fi

echo "Starting FraudGuard AI at http://127.0.0.1:5000"
python app.py
