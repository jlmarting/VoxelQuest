"""Crea 10 NPCs con los pies sobre la superficie de Carcassonne.

Detecta el suelo (bloque sólido) en cada waypoint y coloca el NPC con
y = suelo (los pies del PlayerModel quedan sobre la superficie).

El cliente renderiza los NPCs con PlayerModel: el grupo se posiciona en
(x, y, z) del objeto y los pies del modelo están en y=0 del grupo, así que
con y = altura del suelo los pies quedan exactamente sobre la superficie.
"""
from __future__ import annotations
import json
import urllib.request
import sys
import random

def mcp_call(tool, args, timeout=60):
    body = {"jsonrpc": "2.0", "id": 1, "method": "tools/call",
            "params": {"name": tool, "arguments": args}}
    req = urllib.request.Request("http://localhost:9000/mcp",
        data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        resp = json.loads(r.read().decode())
        if "content" in resp and resp["content"]:
            return json.loads(resp["content"][0].get("text", "{}"))
        return resp

def get_block(x, y, z):
    r = mcp_call("get_block", {"x": x, "y": y, "z": z})
    return r.get("type", 0)

def find_ground(x, z):
    """Busca el suelo sólido (no aire/agua) desde y=30 hacia abajo."""
    for y in range(30, 0, -1):
        bt = get_block(x, y, z)
        if bt not in (0, 7):
            return y + 1  # techo del bloque = superficie
    return 22  # fallback

# Paleta de camisas
CAMISAS = [
    0x2266cc, 0xcc4466, 0x2e8b57, 0x8b4513, 0x4682b4, 0xdaa520, 0x9370db,
    0xcd5c5c, 0x556b2f, 0x8b0000, 0x006400, 0x4b0082, 0x8b008b, 0x2f4f4f,
    0x800000, 0x808000, 0x008080, 0x000080, 0x8b6914, 0x6b8e23, 0x483d8b,
]

# Rutas de patrulla (x, z) — la Y se detecta por suelo
RUTAS = [
    [[0, -25], [0, -15], [0, -5], [0, 5], [0, 15], [0, 25], [0, 15], [0, 5], [0, -5], [0, -15]],
    [[-25, 0], [-15, 0], [-5, 0], [5, 0], [15, 0], [25, 0], [15, 0], [5, 0], [-5, 0], [-15, 0]],
    [[-12, -25], [-12, -15], [-12, -5], [-12, 5], [-12, 15], [-12, 25], [-12, 15], [-12, 5], [-12, -5], [-12, -15]],
    [[12, -25], [12, -15], [12, -5], [12, 5], [12, 15], [12, 25], [12, 15], [12, 5], [12, -5], [12, -15]],
    [[-25, -12], [-15, -12], [-5, -12], [5, -12], [15, -12], [25, -12], [15, -12], [5, -12], [-5, -12], [-15, -12]],
    [[-25, 12], [-15, 12], [-5, 12], [5, 12], [15, 12], [25, 12], [15, 12], [5, 12], [-5, 12], [-15, 12]],
    [[-4, -4], [4, -4], [4, 4], [-4, 4]],
    [[-8, -8], [-2, -8], [-2, -2], [-8, -2]],
    [[-20, -20], [-10, -20], [-10, -10], [-20, -10]],
    [[20, 20], [10, 20], [10, 10], [20, 10]],
]

print("Creando 10 NPCs con los pies sobre la superficie...")
random.seed(21)
created = 0
for i in range(10):
    ruta_xz = RUTAS[i % len(RUTAS)]
    # Detectar suelo en cada waypoint
    waypoints = []
    for (wx, wz) in ruta_xz:
        gy = find_ground(wx, wz)
        waypoints.append([wx, gy, wz])

    color = CAMISAS[i % len(CAMISAS)]
    r = mcp_call("create_object", {
        "kind": "box",
        "position": waypoints[0],
        "scale": [0.6, 1.8, 0.6],
        "color": color,
        "mass": 0.0,
        "anchored": True,
    })
    oid = r.get("object_id")
    if not oid:
        print(f"  ✗ Error NPC {i}: {r}")
        continue

    r2 = mcp_call("move_object", {
        "object_id": oid,
        "motion": {
            "type": "waypoints",
            "points": waypoints,
            "speed": random.uniform(1.5, 3.0),
            "loop": True,
        },
    })
    if r2.get("success"):
        created += 1
        print(f"  ✓ NPC {i+1} (id={oid}) en y={waypoints[0][1]} (suelo)")

print(f"\n✓ {created} NPCs creados con los pies sobre la superficie")