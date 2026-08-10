"""Destruye todo lo construido: castillos, catedral, terreno aplanado.

Áreas a limpiar (poner aire):
- Castillo medieval en (25,25,0): murallas 30x20, torres, torreón → área 40x30
- Castillo anterior en (35,24,4): 30x20 → área 40x30
- Terreno preparado catedral: x:50-99, z:0-49 (50x50)
- Catedral en (62,21,2): 45x25 → dentro del área 50x50

Se limpia desde y=1 hasta y=60 en cada área.
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

# Áreas a limpiar: (x0, x1, z0, z1)
AREAS = [
    (5, 45, -15, 15),    # castillo medieval (25,25,0) + margen
    (15, 55, -6, 14),    # castillo anterior (35,24,4) + margen
    (50, 99, 0, 49),     # terreno catedral 50x50
]

blocks = []
for (x0, x1, z0, z1) in AREAS:
    for x in range(x0, x1 + 1):
        for z in range(z0, z1 + 1):
            for y in range(1, 61):
                blocks.append({"x": x, "y": y, "z": z, "type": AIR})

print(f"Total: {len(blocks)} bloques a aire")

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
    if (i // BATCH) % 50 == 0:
        print(f"  ✓ lote {i//BATCH + 1} ({len(chunk)} bloques)")

print(f"\n✓ Destruido: {ok} bloques puestos a aire en {len(AREAS)} áreas")