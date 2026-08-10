"""Destruye todo sobre la faz de la tierra: limpia bloques en un área amplia.

Área: x: -50..70, z: -50..70 (radio ~60 alrededor del centro de actividad).
Pone aire desde y=1 hasta y=60.
"""
from __future__ import annotations
import json
import urllib.request
import sys

AIR = 0

def mcp_call(tool, args, timeout=120):
    body = {"jsonrpc": "2.0", "id": 1, "method": "tools/call",
            "params": {"name": tool, "arguments": args}}
    req = urllib.request.Request("http://localhost:9000/mcp",
        data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        resp = json.loads(r.read().decode())
        if "content" in resp and resp["content"]:
            return json.loads(resp["content"][0].get("text", "{}"))
        return resp

X0, X1 = -50, 70
Z0, Z1 = -50, 70

blocks = []
for x in range(X0, X1 + 1):
    for z in range(Z0, Z1 + 1):
        for y in range(1, 61):
            blocks.append({"x": x, "y": y, "z": z, "type": AIR})

print(f"Limpiando {len(blocks)} bloques en área {X0}..{X1} x {Z0}..{Z1}...")
BATCH = 500
ok = 0
for i in range(0, len(blocks), BATCH):
    chunk = blocks[i:i + BATCH]
    r = mcp_call("apply_blocks", {"blocks": chunk}, timeout=120)
    if r.get("success"):
        ok += len(chunk)
    else:
        print(f"  ✗ Error en lote {i//BATCH}: {r}")
        sys.exit(1)
    if (i // BATCH) % 100 == 0:
        print(f"  ✓ lote {i//BATCH + 1} ({len(chunk)} bloques)")

print(f"\n✓ Destruido: {ok} bloques puestos a aire")