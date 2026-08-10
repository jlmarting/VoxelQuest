"""Construye puentes desde la meseta de Carcassonne hacia el resto del mundo.

La muralla está en ±30 (puertas en N(0,-30), S(0,30), E(30,0), O(-30,0)).
El suelo de la meseta está en y=21. El terreno exterior es irregular (y=22-25).
Cada puente: ancho 4, barandillas, desciende gradualmente desde y=21 hasta
conectar con el terreno natural exterior.
"""
from __future__ import annotations
import json
import urllib.request
import sys

AIR = 0
STONE = 3
COBBLE = 8
PLANKS = 9

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

def get_block(x, y, z):
    r = mcp_call("get_block", {"x": x, "y": y, "z": z})
    return r.get("type", 0)

def find_ground(x, z):
    """Busca el suelo natural (no aire/agua) desde y=50 hacia abajo."""
    for y in range(50, 0, -1):
        bt = get_block(x, y, z)
        if bt not in (0, 7):
            return y + 1
    return None

def build_bridge(axis, sign, label):
    """Construye un puente a lo largo de un eje.

    axis: 'x' o 'z'
    sign: +1 o -1 (dirección hacia afuera)
    """
    blocks = []
    # Punto de partida: puerta en la muralla (±30)
    start = 30 if sign > 0 else -30
    # Longitud del puente
    LEN = 24
    # Nivel de la meseta
    MESA_Y = 21
    # Ancho del puente (perpendicular al eje)
    W = 4

    for i in range(1, LEN + 1):
        # Coordenada a lo largo del eje
        coord = start + sign * i
        # Nivel del suelo exterior en este punto
        if axis == 'z':
            gx, gz = 0, coord
        else:
            gx, gz = coord, 0
        ground = find_ground(gx, gz)
        if ground is None:
            ground = MESA_Y
        # Altura del puente: desciende gradualmente desde MESA_Y hasta ground
        # Interpolar: al inicio = MESA_Y, al final = ground
        frac = i / LEN
        bridge_y = MESA_Y + (ground - MESA_Y) * frac
        by = int(round(bridge_y))

        # Tablero del puente (ancho W, perpendicular)
        for w in range(-W // 2, W // 2 + 1):
            if axis == 'z':
                bx, bz = w, coord
            else:
                bx, bz = coord, w
            blocks.append({"x": bx, "y": by, "z": bz, "type": PLANKS})
            # Soportes/pilares cada 4 bloques
            if i % 4 == 0:
                for py in range(by - 1, max(ground - 1, 0), -1):
                    blocks.append({"x": bx, "y": py, "z": bz, "type": COBBLE})

        # Barandillas (a ambos lados)
        for w in [-W // 2 - 1, W // 2 + 1]:
            if axis == 'z':
                bx, bz = w, coord
            else:
                bx, bz = coord, w
            blocks.append({"x": bx, "y": by + 1, "z": bz, "type": STONE})
            blocks.append({"x": bx, "y": by + 2, "z": bz, "type": STONE})

    # Enviar
    print(f"  {label}: {len(blocks)} bloques")
    BATCH = 500
    for i in range(0, len(blocks), BATCH):
        chunk = blocks[i:i + BATCH]
        r = mcp_call("apply_blocks", {"blocks": chunk}, timeout=120)
        if not r.get("success"):
            print(f"    ✗ Error: {r}")
            sys.exit(1)

print("Construyendo puentes desde la meseta de Carcassonne...")
build_bridge('z', -1, "Puente Norte (z negativo)")
build_bridge('z', +1, "Puente Sur (z positivo)")
build_bridge('x', +1, "Puente Este (x positivo)")
build_bridge('x', -1, "Puente Oeste (x negativo)")

print("\n✓ 4 puentes construidos: N, S, E, O")