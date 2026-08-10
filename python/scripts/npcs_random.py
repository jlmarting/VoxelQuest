"""Crea 5 NPCs aleatorios que deambulan por la zona.

Cada NPC: posición y ruta aleatorias, color de camisa aleatorio, Y constante
sobre el suelo detectado. El cliente los renderiza con PlayerModel.
"""
from __future__ import annotations
import json
import urllib.request
import sys
import random
import math

math_cos = math.cos
math_sin = math.sin

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
    for y in range(30, 0, -1):
        bt = get_block(x, y, z)
        if bt not in (0, 7):
            return y + 1
    return 22

CAMISAS = [
    0x2266cc, 0xcc4466, 0x2e8b57, 0x8b4513, 0x4682b4, 0xdaa520, 0x9370db,
    0xcd5c5c, 0x556b2f, 0x8b0000, 0x006400, 0x4b0082, 0x8b008b, 0x2f4f4f,
    0x800000, 0x808000, 0x008080, 0x000080, 0x8b6914, 0x6b8e23, 0x483d8b,
]

print("Creando 5 NPCs aleatorios...")
random.seed()
created = 0
for i in range(5):
    # Centro aleatorio en la zona
    cx = random.randint(-20, 20)
    cz = random.randint(-20, 20)
    # Ruta aleatoria: 4-6 puntos alrededor del centro
    n_pts = random.randint(4, 6)
    ruta_xz = []
    for j in range(n_pts):
        ang = j * (2 * 3.14159 / n_pts) + random.uniform(-0.3, 0.3)
        dist = random.uniform(3, 8)
        ruta_xz.append([cx + int(math_cos(ang) * dist), cz + int(math_sin(ang) * dist)])

    # Y constante sobre el suelo del primer punto
    base_y = find_ground(ruta_xz[0][0], ruta_xz[0][1])
    waypoints = [[wx, base_y, wz] for (wx, wz) in ruta_xz]

    color = random.choice(CAMISAS)
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
        print(f"  ✓ NPC {i+1} (id={oid}) en ({waypoints[0][0]},{waypoints[0][1]},{waypoints[0][2]}) color={hex(color)}")

print(f"\n✓ {created} NPCs aleatorios creados")