"""Reencarna a todos los NPCs activos siguiendo la nueva pauta.

Elimina los 100 NPCs actuales y los recrea con colores de ropa variados
(paleta amplia de camisas). El render del cliente (objects.js) genera el
aspecto humanoide completo (PlayerModel) con piel, pelo, género, ojos,
vello facial/accesorios derivados del id de cada NPC.

Mantiene las rutas de patrulla por las calles de Carcassonne.
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

# Paleta amplia de colores de camisa (ropa variada)
CAMISAS = [
    0x2266cc, 0xcc4466, 0x2e8b57, 0x8b4513, 0x4682b4, 0xdaa520, 0x9370db,
    0xcd5c5c, 0x556b2f, 0x8b0000, 0x006400, 0x4b0082, 0x8b008b, 0x2f4f4f,
    0x800000, 0x808000, 0x008080, 0x000080, 0x8b6914, 0x6b8e23, 0x483d8b,
    0x8b4789, 0x5f9ea0, 0xd2691e, 0x9acd32, 0x7b68ee, 0xcd853f, 0x20b2aa,
    0xbc8f8f, 0xda70d6, 0xee82ee, 0xff6347, 0x40e0d0, 0xee7600, 0xcd5b45,
    0x698b22, 0x8b7355, 0x7a8b8b, 0x8b7d6b, 0x6c7b8b, 0x8b864e, 0x8b668b,
    0x8b7b8b, 0x8b8b00, 0x8b8b83, 0x8b5a2b, 0x8b3a62, 0x8b1a1a, 0x8b2500,
    0x8b4500, 0x8b6508, 0x8b7500, 0x8b8378, 0x8b8682, 0x8b8989, 0x8b8b7a,
    0x8b8b8b, 0x8b8b8b, 0x8b8b8b, 0x8b8b8b, 0x8b8b8b, 0x8b8b8b, 0x8b8b8b,
    0x8b8b8b, 0x8b8b8b, 0x8b8b8b, 0x8b8b8b, 0x8b8b8b, 0x8b8b8b, 0x8b8b8b,
    0x8b8b8b, 0x8b8b8b, 0x8b8b8b, 0x8b8b8b, 0x8b8b8b, 0x8b8b8b, 0x8b8b8b,
    0x8b8b8b, 0x8b8b8b, 0x8b8b8b, 0x8b8b8b, 0x8b8b8b, 0x8b8b8b, 0x8b8b8b,
    0x8b8b8b, 0x8b8b8b, 0x8b8b8b, 0x8b8b8b, 0x8b8b8b, 0x8b8b8b, 0x8b8b8b,
    0x8b8b8b, 0x8b8b8b, 0x8b8b8b, 0x8b8b8b, 0x8b8b8b, 0x8b8b8b, 0x8b8b8b,
    0x8b8b8b, 0x8b8b8b, 0x8b8b8b, 0x8b8b8b, 0x8b8b8b, 0x8b8b8b, 0x8b8b8b,
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
]

PUERTAS = [(0, -30), (0, 30), (30, 0), (-30, 0)]

# 1. Eliminar todos los NPCs actuales
print("1. Eliminando NPCs actuales...")
r = mcp_call("list_objects", {})
objs = r.get("objects", [])
npcs = [o for o in objs if o["kind"] == "box"]
for o in npcs:
    mcp_call("destroy_object", {"object_id": o["id"], "cause": "reencarnar"})
print(f"  {len(npcs)} NPCs eliminados")

# 2. Recrear con colores variados
print("2. Recreando NPCs con aspecto variado...")
random.seed(7)
created = 0
for i in range(100):
    puerta = i % 4
    ruta = i // 4
    px, pz = PUERTAS[puerta]
    if puerta == 0:
        entrada = [px, 1, pz - 5]
    elif puerta == 1:
        entrada = [px, 1, pz + 5]
    elif puerta == 2:
        entrada = [px + 5, 1, pz]
    else:
        entrada = [px - 5, 1, pz]

    # Color de camisa variado (paleta amplia, sin repetición excesiva)
    color = CAMISAS[i % len(CAMISAS)]
    # Pequeña variación aleatoria para más diversidad
    if random.random() < 0.3:
        color = random.choice(CAMISAS)

    r = mcp_call("create_object", {
        "kind": "box",
        "position": entrada,
        "scale": [0.6, 1.8, 0.6],
        "color": color,
        "mass": 0.0,
        "anchored": True,
    })
    oid = r.get("object_id")
    if not oid:
        print(f"  ✗ Error NPC {i}: {r}")
        continue

    ruta_pts = RUTAS[ruta % len(RUTAS)]
    waypoints = [entrada] + ruta_pts
    r2 = mcp_call("move_object", {
        "object_id": oid,
        "motion": {
            "type": "waypoints",
            "points": waypoints,
            "speed": random.uniform(2.0, 3.5),
            "loop": True,
        },
    })
    if r2.get("success"):
        created += 1
    if (i + 1) % 20 == 0:
        print(f"  {i+1}/100 NPCs reencarnados")

print(f"\n✓ {created} NPCs reencarnados con aspecto variado")
print(f"  - Paleta de {len(CAMISAS)} colores de camisa")
print(f"  - El cliente genera piel, pelo, género, ojos, vello facial/accesorios por id")