#!/usr/bin/env bash
cd "$(dirname "$0")/backend" && . .venv/bin/activate && uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
