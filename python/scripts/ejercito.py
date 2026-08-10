"""Genera un ejército de 100 soldados que entran en Carcassonne y patrullan.

Cada soldado es un objeto box con proporciones humanas y color de armadura.
Entran por las 4 puertas (N/S/E/O) y patrullan las calles de la ciudad
con waypoints en loop.

Distribución: 25 soldados por puerta.
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

# Colores de armadura (variados)
ARMADURAS = [0x808080, 0x696969, 0xA9A9A9, 0x778899, 0x8B7D6B, 0x6B8E23, 0x556B2F, 0x8B4513]

# Rutas de patrulla dentro de la ciudad (calles)
RUTAS = [
    # Calle central N-S
    [[0, 1, -25], [0, 1, -15], [0, 1, -5], [0, 1, 5], [0, 1, 15], [0, 1, 25],
     [0, 1, 15], [0, 1, 5], [0, 1, -5], [0, 1, -15]],
    # Calle central E-O
    [[-25, 1, 0], [-15, 1, 0], [-5, 1, 0], [5, 1, 0], [15, 1, 0], [25, 1, 0],
     [15, 1, 0], [5, 1, 0], [-5, 1, 0], [-15, 1, 0]],
    # Calle x=-12
    [[-12, 1, -25], [-12, 1, -15], [-12, 1, -5], [-12, 1, 5], [-12, 1, 15], [-12, 1, 25],
     [-12, 1, 15], [-12, 1, 5], [-12, 1, -5], [-12, 1, -15]],
    # Calle x=12
    [[12, 1, -25], [12, 1, -15], [12, 1, -5], [12, 1, 5], [12, 1, 15], [12, 1, 25],
     [12, 1, 15], [12, 1, 5], [12, 1, -5], [12, 1, -15]],
    # Calle z=-12
    [[-25, 1, -12], [-15, 1, -12], [-5, 1, -12], [5, 1, -12], [15, 1, -12], [25, 1, -12],
     [15, 1, -12], [5, 1, -12], [-5, 1, -12], [-15, 1, -12]],
    # Calle z=12
    [[-25, 1, 12], [-15, 1, 12], [-5, 1, 12], [5, 1, 12], [15, 1, 12], [25, 1, 12],
     [15, 1, 12], [5, 1, 12], [-5, 1, 12], [-15, 1, 12]],
    # Plaza central
    [[-4, 1, -4], [4, 1, -4], [4, 1, 4], [-4, 1, 4]],
    # Alrededor de la catedral
    [[-8, 1, -8], [-2, 1, -8], [-2, 1, -2], [-8, 1, -2]],
]

# Puntos de entrada (puertas)
PUERTAS = [
    (0, -30),  # Norte
    (0, 30),   # Sur
    (30, 0),   # Este
    (-30, 0),  # Oeste
]

def crear_soldado(idx, puerta_idx, ruta_idx):
    """Crea un soldado que entra por una puerta y patrulla una ruta."""
    px, pz = PUERTAS[puerta_idx]
    # Punto de entrada (fuera de la muralla)
    if puerta_idx == 0:   # Norte
        entrada = [px, 1, pz - 5]
    elif puerta_idx == 1: # Sur
        entrada = [px, 1, pz + 5]
    elif puerta_idx == 2: # Este
        entrada = [px + 5, 1, pz]
    else:                 # Oeste
        entrada = [px - 5, 1, pz]

    color = ARMADURAS[idx % len(ARMADURAS)]
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
        print(f"  ✗ Error soldado {idx}: {r}")
        return None

    # Ruta: entrar por la puerta y luego patrullar la calle
    ruta = RUTAS[ruta_idx % len(RUTAS)]
    # Prefijo: desde la entrada hasta el primer punto de la ruta
    waypoints = [entrada] + ruta
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
        return oid
    print(f"  ✗ Error ruta soldado {idx}: {r2}")
    return None

print(f"Generando ejército de 100 soldados...")
random.seed()
created = 0
for i in range(100):
    puerta = i % 4
    ruta = i // 4
    oid = crear_soldado(i, puerta, ruta)
    if oid:
        created += 1
    if (i + 1) % 10 == 0:
        print(f"  {i+1}/100 soldados creados")

print(f"\n✓ Ejército de {created} soldados creado")
print(f"  - 25 soldados por puerta (N/S/E/O)")
print(f"  - Patrullan las calles de Carcassonne")
print(f"  - Colores de armadura variados")