#!/usr/bin/env python3
"""Adaptador stdio MCP para servidor Python.
Lee JSON-RPC 2.0 de stdin, lo reenvía por HTTP a server.main, escribe respuesta a stdout.
"""
import json
import sys
import urllib.request
import urllib.error

SERVER_URL = "http://127.0.0.1:9000/mcp"


def send_rpc(request: dict) -> dict | None:
    data = json.dumps(request).encode()
    req = urllib.request.Request(SERVER_URL, data=data, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return {"jsonrpc": "2.0", "id": request.get("id"), "error": {"code": e.code, "message": str(e)}}
    except Exception as e:
        return {"jsonrpc": "2.0", "id": request.get("id"), "error": {"code": -32603, "message": str(e)}}


# Handshake: MCP protocol expects initialize response
for line in sys.stdin:
    line = line.strip()
    if not line:
        continue
    try:
        req = json.loads(line)
    except json.JSONDecodeError:
        continue

    resp = send_rpc(req)
    if resp is not None:
        sys.stdout.write(json.dumps(resp) + "\n")
        sys.stdout.flush()

    # Salir si es una notificación de cierre
    if req.get("method") == "notifications/exit" or req.get("method") == "exit":
        break
