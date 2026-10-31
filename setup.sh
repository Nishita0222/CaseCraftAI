#!/usr/bin/env bash
set -e
(cd backend && python3 -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt)
(cd frontend && npm install)
echo "Done. Run ./run_backend.sh and ./run_frontend.sh in two terminals."
