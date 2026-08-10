"""Reposiciona los NPCs sobre el suelo de la ciudad y reasigna la patrulla.

La física del servidor no reposa bien los NPCs (cayeron al fondo y=0.9).
Solución: detectar el suelo sólido en cada waypoint y colocar el NPC con
y = techo del bloque (pies sobre la superficie). Luego reasignar el motion
de patrulla con las posiciones corregidas.
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
    return 22

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

# 1. Obtener NPCs actuales
r = mcp_call("list_objects", {})
objs = r.get("objects", [])
npcs = [o for o in objs if o["kind"] == "box"]
print(f"NPCs encontrados: {len(npcs)}")

# 2. Para cada NPC: reposicionar sobre el suelo y reasignar patrulla
random.seed(21)
for i, o in enumerate(npcs):
    oid = o["id"]
    ruta_xz = RUTAS[i % len(RUTAS)]
    # Detectar suelo en cada waypoint
    waypoints = []
    for (wx, wz) in ruta_xz:
        gy = find_ground(wx, wz)
        waypoints.append([wx, gy, wz])

    # Reposicionar sobre el suelo (pies sobre la superficie)
    mcp_call("update_object", {"object_id": oid, "patch": {"position": waypoints[0]}})
    # Reasignar patrulla
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
        print(f"  ✓ NPC {oid} reposicionado en y={waypoints[0][1]} (suelo)")

print("\n✓ NPCs reposicionados sobre el suelo de la ciudad")