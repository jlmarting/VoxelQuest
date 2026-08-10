"""Prepara el terreno para la catedral al este del castillo.

Área 50x50: x=50..99, z=0..49 (al este del castillo en (25,25,0)).
1. Elimina todo lo que esté por encima del suelo (y=22..60) → aire.
2. Aplana el suelo a y=21 con tierra (DIRT=2) en toda el área.
"""
from __future__ import annotations
import json
import urllib.request
import sys

AIR = 0
DIRT = 2

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

X0, X1 = 50, 99
Z0, Z1 = 0, 49
GROUND_Y = 21  # nivel uniforme del suelo

blocks = []

# 1. Limpiar todo por encima del suelo (y=22..60) → aire
print("Eliminando todo por encima del suelo...")
for x in range(X0, X1 + 1):
    for z in range(Z0, Z1 + 1):
        for y in range(22, 61):
            blocks.append({"x": x, "y": y, "z": z, "type": AIR})

# 2. Suelo de tierra a nivel uniforme y=21
print("Aplanando suelo de tierra a y=21...")
for x in range(X0, X1 + 1):
    for z in range(Z0, Z1 + 1):
        blocks.append({"x": x, "y": GROUND_Y, "z": z, "type": DIRT})

print(f"Total: {len(blocks)} bloques (aire + tierra)")

# Enviar en lotes
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
    print(f"  ✓ lote {i//BATCH + 1} ({len(chunk)} bloques)")

print(f"\n✓ Terreno preparado: {ok} bloques. Área 50x50 plana con suelo de tierra en y=21.")