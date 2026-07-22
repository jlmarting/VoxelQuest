#!/bin/bash
PORT=${1:-9000}
kill $(lsof -ti :$PORT) 2>/dev/null && echo "Puerto $PORT liberado" || echo "Puerto $PORT libre"
