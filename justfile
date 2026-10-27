set shell := ["bash", "-cu"]

# install/refresh the project .venv (also used by .envrc)
sync:
    uv sync

# start the hotkey/tray daemon in the background (logs + pid in logs/)
up:
    #!/usr/bin/env bash
    set -euo pipefail
    cd {{justfile_directory()}}
    mkdir -p logs
    if [ -f logs/llmfix.pid ] && kill -0 "$(cat logs/llmfix.pid)" 2>/dev/null; then
      echo "llmfix already running (pid $(cat logs/llmfix.pid))"; exit 0
    fi
    if ! curl -sf -m 2 "${AI_GATEWAY_URL:-http://127.0.0.1:4001/v1}/models" >/dev/null 2>&1; then
      echo "warning: ai-gateway not reachable at ${AI_GATEWAY_URL:-http://127.0.0.1:4001/v1} — start it with: cd ../../ai-gateway && just up"
    fi
    nohup uv run llmfix_linux.py >> logs/llmfix.log 2>&1 &
    echo $! > logs/llmfix.pid
    sleep 1
    if kill -0 "$(cat logs/llmfix.pid)" 2>/dev/null; then
      echo "llmfix running (pid $(cat logs/llmfix.pid)) — hotkey Ctrl+Alt+J. logs: just logs"
    else
      echo "llmfix exited immediately — check: just logs"; exit 1
    fi

# stop the background daemon
down:
    #!/usr/bin/env bash
    cd {{justfile_directory()}}
    if [ -f logs/llmfix.pid ] && kill "$(cat logs/llmfix.pid)" 2>/dev/null; then
      echo "llmfix stopped"
    else
      echo "llmfix: no pidfile/process"
    fi
    rm -f logs/llmfix.pid

# is it running, and is the ai-gateway it depends on reachable
status:
    #!/usr/bin/env bash
    cd {{justfile_directory()}}
    if [ -f logs/llmfix.pid ] && kill -0 "$(cat logs/llmfix.pid)" 2>/dev/null; then
      echo "llmfix: running (pid $(cat logs/llmfix.pid))"
    else
      echo "llmfix: not running"
    fi
    curl -sf -m 2 "${AI_GATEWAY_URL:-http://127.0.0.1:4001/v1}/models" >/dev/null 2>&1 \
      && echo "ai-gateway: up" || echo "ai-gateway: DOWN — cd ../../ai-gateway && just up"

# tail the daemon's log
logs:
    tail -n 60 -f logs/llmfix.log

# run in the foreground with debug logging (Ctrl+C to stop) — for troubleshooting
run:
    uv run llmfix_linux.py --log-level DEBUG

# print the available // commands from commands.toml
list:
    uv run llmfix_linux.py --list
