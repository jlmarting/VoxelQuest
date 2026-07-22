#!/usr/bin/env bash
# Arranca el servidor VoxelQuest Python y sirve el cliente web.
set -euo pipefail

PORT="${PORT:-9001}"
CLIENT_PORT="${CLIENT_PORT:-8080}"
HOST="${HOST:-127.0.0.1}"

echo "[run] Iniciando VoxelQuest con uv..."

# 1. Arrancar servidor Python en segundo plano
uv run python -m server.main --host "$HOST" --port "$PORT" &
SERVER_PID=$!

# 2. Esperar a que el servidor responda
for i in {1..30}; do
    if curl -sf "http://$HOST:$PORT/health" >/dev/null 2>&1; then
        break
    fi
    sleep 0.2
done

# 3. Abrir navegador (solo si hay display disponible)
if command -v xdg-open >/dev/null 2>&1 && [ -n "${DISPLAY:-}" ]; then
    xdg-open "http://$HOST:$CLIENT_PORT" &
fi

# 4. Servir cliente estático (desde raíz del proyecto)
uv run python -m http.server "$CLIENT_PORT" --directory . --bind "$HOST" &
CLIENT_PID=$!

echo "[run] Servidor Python: http://$HOST:$PORT"
echo "[run] Cliente web:   http://$HOST:$CLIENT_PORT"
echo "[run] Pulsa Ctrl+C para detener todo."

# 5. Gestionar señales de cierre
cleanup() {
    echo "[run] Deteniendo servicios..."
    kill "$SERVER_PID" "$CLIENT_PID" 2>/dev/null || true
    wait 2>/dev/null || true
    exit 0
}
trap cleanup INT TERM

wait "$SERVER_PID"
