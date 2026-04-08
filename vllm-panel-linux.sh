#!/bin/bash
# vLLM Panel - Linux management script

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PID_FILE="$SCRIPT_DIR/.vllm-panel.pid"
LOG_FILE="$SCRIPT_DIR/server.log"

install() {
    echo "Installing core dependencies..."
    pip3 install --upgrade pip
    pip3 install fastapi uvicorn psutil pydantic huggingface_hub
    echo "Done!"
    read -p "Press Enter..."
}

install_backend() {
    echo "Installing vLLM backend (requires NVIDIA GPU + CUDA)..."
    pip3 install vllm
    echo "Done!"
    read -p "Press Enter..."
}

start() {
    if [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
        echo "Already running (PID: $(cat "$PID_FILE"))"
    else
        echo "Starting vLLM Panel..."
        cd "$SCRIPT_DIR" && nohup python3 main.py > "$LOG_FILE" 2>&1 &
        echo $! > "$PID_FILE"
        sleep 3
        echo "Started!"
        echo "  Panel: http://localhost:8500"
        echo "  vLLM:  http://localhost:8001/v1"
    fi
    read -p "Press Enter..."
}

stop() {
    echo "Stopping Panel..."
    if [ -f "$PID_FILE" ]; then
        kill "$(cat "$PID_FILE")" 2>/dev/null
        rm -f "$PID_FILE"
        echo "Stopped."
    else
        PIDS=$(lsof -ti:8500 2>/dev/null)
        [ -n "$PIDS" ] && echo "$PIDS" | xargs kill -9 && echo "Killed." || echo "Not running."
    fi
    read -p "Press Enter..."
}

status() {
    echo "Panel status:"
    if [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
        echo "  Status: RUNNING (PID: $(cat "$PID_FILE"))"
        curl -s http://localhost:8500/api/info 2>/dev/null | python3 -m json.tool 2>/dev/null
    else
        echo "  Status: NOT RUNNING"
    fi
    read -p "Press Enter..."
}

log() {
    if [ -f "$LOG_FILE" ]; then
        echo "=== Last 50 lines ==="
        tail -50 "$LOG_FILE"
    else
        echo "No log file found."
    fi
    read -p "Press Enter..."
}

while true; do
    clear
    echo "================================================"
    echo "  vLLM Panel - Linux"
    echo "================================================"
    echo "  1. Install dependencies"
    echo "  2. Install vLLM backend"
    echo "  3. Start Panel"
    echo "  4. Stop Panel"
    echo "  5. Status"
    echo "  6. Open browser"
    echo "  7. View log"
    echo "  8. Exit"
    echo "================================================"
    read -p "Choice (1-8): " c
    case $c in
        1) install ;; 2) install_backend ;; 3) start ;; 4) stop ;;
        5) status ;; 6) xdg-open http://localhost:8500 ;; 7) log ;;
        8) echo "Bye!"; exit 0 ;; *) echo "Invalid"; sleep 1 ;;
    esac
done
