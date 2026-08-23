#!/usr/bin/env bash
# CryptoTrada always-on server
# — only one instance can run at a time (lockfile guard)
# — auto-restarts on crash
# — force-kills and restarts if health check stops responding (hung event loop)
# — exits cleanly on Ctrl+C or SIGTERM

HEALTH_URL="http://localhost:8000/api/journal/summary"
STARTUP_WAIT=15     # seconds to let the server boot before health checks begin
HEALTH_INTERVAL=60  # how often to ping the health URL (seconds)
MAX_FAILURES=3      # consecutive failures before force-kill + restart
RESTART_DELAY=10    # seconds to wait between restarts
LOCKFILE="/tmp/cryptotrada.lock"

mkdir -p logs

# ── Single-instance guard ──────────────────────────────────────────────────────
if [ -f "$LOCKFILE" ]; then
    EXISTING_PID=$(cat "$LOCKFILE")
    if kill -0 "$EXISTING_PID" 2>/dev/null; then
        echo "CryptoTrada watchdog already running (PID $EXISTING_PID). Exiting."
        exit 1
    fi
    rm -f "$LOCKFILE"
fi
echo $$ > "$LOCKFILE"
trap "rm -f $LOCKFILE" EXIT INT TERM

log() { echo "[$(date -u '+%Y-%m-%d %H:%M:%S UTC')] $*"; }

while true; do
    log "Starting CryptoTrada server..."
    .venv/bin/python main.py &
    PID=$!
    log "PID=$PID — waiting ${STARTUP_WAIT}s for startup"
    sleep "$STARTUP_WAIT"

    if ! kill -0 "$PID" 2>/dev/null; then
        log "Server failed to start — restarting in ${RESTART_DELAY}s"
        sleep "$RESTART_DELAY"
        continue
    fi

    fails=0
    while kill -0 "$PID" 2>/dev/null; do
        if curl -sf --max-time 5 "$HEALTH_URL" >/dev/null 2>&1; then
            fails=0
        else
            fails=$((fails + 1))
            log "Health check failed ($fails/$MAX_FAILURES)"
            if [ "$fails" -ge "$MAX_FAILURES" ]; then
                log "Server unresponsive — killing PID $PID and restarting"
                kill -9 "$PID" 2>/dev/null
                sleep 3
                break
            fi
        fi
        sleep "$HEALTH_INTERVAL"
    done

    wait "$PID" 2>/dev/null; CODE=$?
    log "Server exited (code $CODE)"

    # 0 = normal, 130 = Ctrl+C (SIGINT), 143 = SIGTERM
    if [[ $CODE -eq 0 || $CODE -eq 130 || $CODE -eq 143 ]]; then
        log "Clean shutdown — done"
        break
    fi

    log "Unexpected exit — restarting in ${RESTART_DELAY}s"
    sleep "$RESTART_DELAY"
done
