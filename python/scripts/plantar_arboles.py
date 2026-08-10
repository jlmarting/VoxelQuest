"""Planta árboles alrededor del fuego en (10,24,10) para que el fuego se propague.

Crea 8 árboles (tronco WOOD + copa LEAVES) en un radio de 4-8 bloques
alrededor del fuego central.
"""
from __future__ import annotations
import json
import urllib.request
import sys

WOOD = 4
LEAVES = 5
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

# Posiciones de árboles alrededor del fuego (10,24,10), suelo en y=24
TREE_POS = [
    (4, 10), (16, 10), (10, 4), (10, 16),
    (3, 3), (17, 17), (3, 17), (17, 3),
    (5, 14), (15, 6), (6, 15), (14, 5),
]

blocks = []
for (tx, tz) in TREE_POS:
    # Tronco (altura 4-6)
    h = 5
    for i in range(h):
        blocks.append({"x": tx, "y": 24 + i, "z": tz, "type": WOOD})
    # Copa (cubo de hojas)
    top = 24 + h
    for dx in range(-2, 3):
        for dz in range(-2, 3):
            for dy in range(-1, 2):
                if abs(dx) + abs(dz) + abs(dy) < 4:
                    blocks.append({"x": tx + dx, "y": top + dy, "z": tz + dz, "type": LEAVES})

print(f"Plantando {len(TREE_POS)} árboles ({len(blocks)} bloques)...")
BATCH = 500
ok = 0
for i in range(0, len(blocks), BATCH):
    chunk = blocks[i:i + BATCH]
    r = mcp_call("apply_blocks", {"blocks": chunk}, timeout=120)
    if r.get("success"):
        ok += len(chunk)
    else:
        print(f"  ✗ Error: {r}")
        sys.exit(1)

print(f"✓ {ok} bloques de árboles plantados alrededor del fuego")