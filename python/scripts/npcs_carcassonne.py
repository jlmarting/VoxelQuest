"""Crea 10 NPCs que deambulan por Carcassonne.

Los NPCs son objetos box con proporciones humanas (0.6x1.8x0.6) y colores
de ropa variados. Cada uno patrulla una ruta de waypoints dentro de la
muralla (x:-30..30, z:-30..30) con motion waypoints en loop.

Estilos variados: colores de camisa/pantalón distintos por NPC.
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

# Estilos de NPC (color de ropa, nombre)
ESTILOS = [
    ("Aldeano", 0x8B4513),      # marrón
    ("Mercader", 0x2E8B57),     # verde
    ("Caballero", 0x4682B4),    # azul acero
    ("Campesina", 0xCD5C5C),    # rojo indio
    ("Monje", 0x6B4226),        # marrón oscuro
    ("Artesano", 0xDAA520),     # dorado
    ("Peregrina", 0x9370DB),    # púrpura medio
    ("Herrero", 0x696969),      # gris
    ("Juglar", 0xFF6347),       # tomate
    ("Panadera", 0xFFDAB9),     # melocotón
]

# Rutas de deambulación dentro de Carcassonne (calles)
RUTAS = [
    # Ruta 1: calle central N-S
    [[0, 1, -25], [0, 1, -15], [0, 1, -5], [0, 1, 5], [0, 1, 15], [0, 1, 25],
     [0, 1, 15], [0, 1, 5], [0, 1, -5], [0, 1, -15]],
    # Ruta 2: calle central E-O
    [[-25, 1, 0], [-15, 1, 0], [-5, 1, 0], [5, 1, 0], [15, 1, 0], [25, 1, 0],
     [15, 1, 0], [5, 1, 0], [-5, 1, 0], [-15, 1, 0]],
    # Ruta 3: calle x=-12
    [[-12, 1, -25], [-12, 1, -15], [-12, 1, -5], [-12, 1, 5], [-12, 1, 15], [-12, 1, 25],
     [-12, 1, 15], [-12, 1, 5], [-12, 1, -5], [-12, 1, -15]],
    # Ruta 4: calle x=12
    [[12, 1, -25], [12, 1, -15], [12, 1, -5], [12, 1, 5], [12, 1, 15], [12, 1, 25],
     [12, 1, 15], [12, 1, 5], [12, 1, -5], [12, 1, -15]],
    # Ruta 5: calle z=-12
    [[-25, 1, -12], [-15, 1, -12], [-5, 1, -12], [5, 1, -12], [15, 1, -12], [25, 1, -12],
     [15, 1, -12], [5, 1, -12], [-5, 1, -12], [-15, 1, -12]],
    # Ruta 6: calle z=12
    [[-25, 1, 12], [-15, 1, 12], [-5, 1, 12], [5, 1, 12], [15, 1, 12], [25, 1, 12],
     [15, 1, 12], [5, 1, 12], [-5, 1, 12], [-15, 1, 12]],
    # Ruta 7: alrededor de la plaza central
    [[-4, 1, -4], [4, 1, -4], [4, 1, 4], [-4, 1, 4]],
    # Ruta 8: alrededor de la catedral
    [[-8, 1, -8], [-2, 1, -8], [-2, 1, -2], [-8, 1, -2]],
    # Ruta 9: calle secundaria aleatoria
    [[-20, 1, -20], [-10, 1, -20], [-10, 1, -10], [-20, 1, -10]],
    # Ruta 10: calle secundaria aleatoria
    [[20, 1, 20], [10, 1, 20], [10, 1, 10], [20, 1, 10]],
]

def crear_npc(nombre, color, ruta, speed):
    # Crear objeto box con proporciones humanas
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
        print(f"  ✗ Error creando NPC {nombre}: {r}")
        return
    # Asignar ruta de deambulación (waypoints loop)
    r2 = mcp_call("move_object", {
        "object_id": oid,
        "motion": {
            "type": "waypoints",
            "points": ruta,
            "speed": speed,
            "loop": True,
        },
    })
    if r2.get("success"):
        print(f"  ✓ NPC {nombre} (id={oid}) deambulando por {len(ruta)} puntos")
    else:
        print(f"  ✗ Error ruta {nombre}: {r2}")

print(f"Creando {len(ESTILOS)} NPCs que deambulan por Carcassonne...")
random.seed()
for i, (nombre, color) in enumerate(ESTILOS):
    speed = random.uniform(1.5, 3.0)
    crear_npc(nombre, color, RUTAS[i], speed)

print("\n✓ 10 NPCs creados deambulando por las calles de Carcassonne")