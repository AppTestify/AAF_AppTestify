#!/usr/bin/env bash
# Run API (port 8000) and PM UI (port 5173). Requires two terminals or tmux; this starts API in background.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
if [[ ! -d .venv ]] && [[ ! -d .venv311 ]]; then
  echo "Create a venv first: python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt"
  exit 1
fi
# shellcheck disable=SC1091
if [[ -f .venv311/bin/activate ]]; then source .venv311/bin/activate; elif [[ -f .venv/bin/activate ]]; then source .venv/bin/activate; fi
export PYTHONPATH="$ROOT"
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 &
API_PID=$!
trap 'kill $API_PID 2>/dev/null || true' EXIT
cd "$ROOT/frontend"
npm run dev
