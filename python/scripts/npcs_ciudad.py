"""Crea 30 NPCs que deambulan por Carcassonne.

Cada NPC es un objeto box con proporciones humanas (0.6x1.8x0.6) y color de
ropa variado. El cliente (objects.js) los renderiza con PlayerModel (aspecto
humanoide completo: piel, pelo, género, ojos, vello facial/accesorios).

Patrullan las calles de la ciudad con waypoints en loop.
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

# Paleta amplia de colores de camisa
CAMISAS = [
    0x2266cc, 0xcc4466, 0x2e8b57, 0x8b4513, 0x4682b4, 0xdaa520, 0x9370db,
    0xcd5c5c, 0x556b2f, 0x8b0000, 0x006400, 0x4b0082, 0x8b008b, 0x2f4f4f,
    0x800000, 0x808000, 0x008080, 0x000080, 0x8b6914, 0x6b8e23, 0x483d8b,
    0x8b4789, 0x5f9ea0, 0xd2691e, 0x9acd32, 0x7b68ee, 0xcd853f, 0x20b2aa,
    0xbc8f8f, 0xda70d6, 0xee82ee, 0xff6347, 0x40e0d0, 0xee7600, 0xcd5b45,
]

# Rutas de patrulla dentro de la ciudad (calles)
RUTAS = [
    [[0, 1, -25], [0, 1, -15], [0, 1, -5], [0, 1, 5], [0, 1, 15], [0, 1, 25],
     [0, 1, 15], [0, 1, 5], [0, 1, -5], [0, 1, -15]],
    [[-25, 1, 0], [-15, 1, 0], [-5, 1, 0], [5, 1, 0], [15, 1, 0], [25, 1, 0],
     [15, 1, 0], [5, 1, 0], [-5, 1, 0], [-15, 1, 0]],
    [[-12, 1, -25], [-12, 1, -15], [-12, 1, -5], [-12, 1, 5], [-12, 1, 15], [-12, 1, 25],
     [-12, 1, 15], [-12, 1, 5], [-12, 1, -5], [-12, 1, -15]],
    [[12, 1, -25], [12, 1, -15], [12, 1, -5], [12, 1, 5], [12, 1, 15], [12, 1, 25],
     [12, 1, 15], [12, 1, 5], [12, 1, -5], [12, 1, -15]],
    [[-25, 1, -12], [-15, 1, -12], [-5, 1, -12], [5, 1, -12], [15, 1, -12], [25, 1, -12],
     [15, 1, -12], [5, 1, -12], [-5, 1, -12], [-15, 1, -12]],
    [[-25, 1, 12], [-15, 1, 12], [-5, 1, 12], [5, 1, 12], [15, 1, 12], [25, 1, 12],
     [15, 1, 12], [5, 1, 12], [-5, 1, 12], [-15, 1, 12]],
    [[-4, 1, -4], [4, 1, -4], [4, 1, 4], [-4, 1, 4]],
    [[-8, 1, -8], [-2, 1, -8], [-2, 1, -2], [-8, 1, -2]],
    [[-20, 1, -20], [-10, 1, -20], [-10, 1, -10], [-20, 1, -10]],
    [[20, 1, 20], [10, 1, 20], [10, 1, 10], [20, 1, 10]],
]

print(f"Creando 30 NPCs que deambulan por Carcassonne...")
random.seed(11)
created = 0
for i in range(30):
    ruta = RUTAS[i % len(RUTAS)]
    color = CAMISAS[i % len(CAMISAS)]
    if random.random() < 0.3:
        color = random.choice(CAMISAS)

    r = mcp_call("create_object", {
        "kind": "box",
        "position": ruta[0],
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
            "points": ruta,
            "speed": random.uniform(1.5, 3.0),
            "loop": True,
        },
    })
    if r2.get("success"):
        created += 1
    if (i + 1) % 10 == 0:
        print(f"  {i+1}/30 NPCs creados")

print(f"\n✓ {created} NPCs creados deambulando por las calles de Carcassonne")