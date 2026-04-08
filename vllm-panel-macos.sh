#!/bin/bash
# vLLM Panel v4.0 - Management Console (macOS)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PID_FILE="$SCRIPT_DIR/.vllm-panel.pid"
LOG_FILE="$SCRIPT_DIR/server.log"

install() { pip3 install fastapi uvicorn psutil pydantic huggingface_hub; echo "Done!"; read -p "Enter..."; }
install_mlx() { pip3 install mlx-lm; echo "Done!"; read -p "Enter..."; }
install_vllm() { pip3 install vllm; echo "Done!"; read -p "Enter..."; }

start() {
    if [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
        echo "Already running (PID: $(cat "$PID_FILE"))"
    else
        cd "$SCRIPT_DIR" && nohup python3 main.py > "$LOG_FILE" 2>&1 &
        echo $! > "$PID_FILE"
        sleep 3
        echo "Started! Panel: http://localhost:8500"
    fi
    read -p "Enter..."
}

stop() {
    if [ -f "$PID_FILE" ]; then
        kill "$(cat "$PID_FILE")" 2>/dev/null; rm -f "$PID_FILE"
        echo "Stopped."
    fi
    read -p "Enter..."
}

status() {
    if [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
        echo "RUNNING (PID: $(cat "$PID_FILE"))"
        curl -s http://localhost:8500/api/info 2>/dev/null | python3 -m json.tool 2>/dev/null
    else
        echo "NOT RUNNING"
    fi
    read -p "Enter..."
}

log() { [ -f "$LOG_FILE" ] && tail -50 "$LOG_FILE" || echo "No log."; read -p "Enter..."; }

while true; do
    clear
    echo "================================================"
    echo "  vLLM Panel v4.0 - macOS"
    echo "================================================"
    echo "  1. Install dependencies"
    echo "  2. Install MLX-LM (Apple Silicon)"
    echo "  3. Install vLLM (optional)"
    echo "  4. Start Panel"
    echo "  5. Stop Panel"
    echo "  6. Status"
    echo "  7. Open browser"
    echo "  8. View log"
    echo "  9. Exit"
    echo "================================================"
    read -p "Choice (1-9): " c
    case $c in
        1) install ;; 2) install_mlx ;; 3) install_vllm ;; 4) start ;;
        5) stop ;; 6) status ;; 7) open http://localhost:8500 ;; 8) log ;;
        9) echo "Bye!"; exit 0 ;; *) echo "Invalid"; sleep 1 ;;
    esac
done
