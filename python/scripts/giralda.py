"""Construye La Giralda de Sevilla en la posición del jugador 1.

La Giralda: torre campanario almohade (base cuadrada con ventanas geminadas)
con remate renacentista (cuerpo de campanas con arcos, cúpula y Giraldillo).

Centrada en (-404, -61), suelo en y=24.
"""
from __future__ import annotations
import json
import urllib.request
import sys

AIR = 0
STONE = 3
WOOD = 4
COBBLE = 8
PLANKS = 9
BRICK = 13
SAND = 6

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

def send(blocks, label):
    print(f"  {label}: {len(blocks)} bloques")
    BATCH = 500
    for i in range(0, len(blocks), BATCH):
        chunk = blocks[i:i + BATCH]
        r = mcp_call("apply_blocks", {"blocks": chunk}, timeout=120)
        if not r.get("success"):
            print(f"    ✗ Error: {r}")
            sys.exit(1)

CX, CZ = -404, -61
G = 24  # suelo

blocks = []

# ============================================================
# 1. Base / zócalo (13x13, altura 3)
# ============================================================
print("1. Zócalo...")
for x in range(CX - 6, CX + 7):
    for z in range(CZ - 6, CZ + 7):
        for y in range(0, 3):
            blocks.append({"x": x, "y": G + y, "z": z, "type": COBBLE})

# ============================================================
# 2. Cuerpo almohade inferior (11x11, altura 12)
# ============================================================
print("2. Cuerpo almohade inferior...")
for x in range(CX - 5, CX + 6):
    for z in range(CZ - 5, CZ + 6):
        for y in range(3, 15):
            if x in (CX - 5, CX + 5) or z in (CZ - 5, CZ + 5):
                blocks.append({"x": x, "y": G + y, "z": z, "type": STONE})
# Ventanas geminadas (arcos de herradura) en cada cara
for y in [5, 8, 11]:
    # Cara N (z = CZ-5)
    for dx in [-3, 0, 3]:
        blocks.append({"x": CX + dx, "y": G + y, "z": CZ - 5, "type": AIR})
        blocks.append({"x": CX + dx, "y": G + y + 1, "z": CZ - 5, "type": AIR})
        blocks.append({"x": CX + dx, "y": G + y + 2, "z": CZ - 5, "type": AIR})
    # Cara S (z = CZ+5)
    for dx in [-3, 0, 3]:
        blocks.append({"x": CX + dx, "y": G + y, "z": CZ + 5, "type": AIR})
        blocks.append({"x": CX + dx, "y": G + y + 1, "z": CZ + 5, "type": AIR})
        blocks.append({"x": CX + dx, "y": G + y + 2, "z": CZ + 5, "type": AIR})
    # Cara E (x = CX+5)
    for dz in [-3, 0, 3]:
        blocks.append({"x": CX + 5, "y": G + y, "z": CZ + dz, "type": AIR})
        blocks.append({"x": CX + 5, "y": G + y + 1, "z": CZ + dz, "type": AIR})
        blocks.append({"x": CX + 5, "y": G + y + 2, "z": CZ + dz, "type": AIR})
    # Cara O (x = CX-5)
    for dz in [-3, 0, 3]:
        blocks.append({"x": CX - 5, "y": G + y, "z": CZ + dz, "type": AIR})
        blocks.append({"x": CX - 5, "y": G + y + 1, "z": CZ + dz, "type": AIR})
        blocks.append({"x": CX - 5, "y": G + y + 2, "z": CZ + dz, "type": AIR})

# ============================================================
# 3. Cuerpo almohade superior (9x9, altura 10)
# ============================================================
print("3. Cuerpo almohade superior...")
for x in range(CX - 4, CX + 5):
    for z in range(CZ - 4, CZ + 5):
        for y in range(15, 25):
            if x in (CX - 4, CX + 4) or z in (CZ - 4, CZ + 4):
                blocks.append({"x": x, "y": G + y, "z": z, "type": STONE})
# Ventanas
for y in [17, 20]:
    for dx in [-2, 0, 2]:
        blocks.append({"x": CX + dx, "y": G + y, "z": CZ - 4, "type": AIR})
        blocks.append({"x": CX + dx, "y": G + y + 1, "z": CZ - 4, "type": AIR})
        blocks.append({"x": CX + dx, "y": G + y, "z": CZ + 4, "type": AIR})
        blocks.append({"x": CX + dx, "y": G + y + 1, "z": CZ + 4, "type": AIR})
    for dz in [-2, 0, 2]:
        blocks.append({"x": CX - 4, "y": G + y, "z": CZ + dz, "type": AIR})
        blocks.append({"x": CX - 4, "y": G + y + 1, "z": CZ + dz, "type": AIR})
        blocks.append({"x": CX + 4, "y": G + y, "z": CZ + dz, "type": AIR})
        blocks.append({"x": CX + 4, "y": G + y + 1, "z": CZ + dz, "type": AIR})

# ============================================================
# 4. Cuerpo de campanas (7x7, altura 8) con arcos
# ============================================================
print("4. Cuerpo de campanas...")
for x in range(CX - 3, CX + 4):
    for z in range(CZ - 3, CZ + 4):
        for y in range(25, 33):
            if x in (CX - 3, CX + 3) or z in (CZ - 3, CZ + 3):
                blocks.append({"x": x, "y": G + y, "z": z, "type": BRICK})
# Arcos de campanas (grandes aberturas)
for y in [26, 27, 28, 29]:
    # Cara N
    for dx in [-1, 0, 1]:
        blocks.append({"x": CX + dx, "y": G + y, "z": CZ - 3, "type": AIR})
    # Cara S
    for dx in [-1, 0, 1]:
        blocks.append({"x": CX + dx, "y": G + y, "z": CZ + 3, "type": AIR})
    # Cara E
    for dz in [-1, 0, 1]:
        blocks.append({"x": CX + 3, "y": G + y, "z": CZ + dz, "type": AIR})
    # Cara O
    for dz in [-1, 0, 1]:
        blocks.append({"x": CX - 3, "y": G + y, "z": CZ + dz, "type": AIR})

# ============================================================
# 5. Remate renacentista (cúpula + Giraldillo)
# ============================================================
print("5. Remate renacentista...")
# Cuerpo superior (5x5)
for x in range(CX - 2, CX + 3):
    for z in range(CZ - 2, CZ + 3):
        for y in range(33, 36):
            if x in (CX - 2, CX + 2) or z in (CZ - 2, CZ + 2):
                blocks.append({"x": x, "y": G + y, "z": z, "type": BRICK})
# Cúpula (escalonada)
for i, r in enumerate([2, 1, 1, 0]):
    for dx in range(-r, r + 1):
        for dz in range(-r, r + 1):
            if dx * dx + dz * dz <= r * r + 1:
                blocks.append({"x": CX + dx, "y": G + 36 + i, "z": CZ + dz, "type": BRICK})
# Giraldillo (estatua en la cima)
for y in range(40, 43):
    blocks.append({"x": CX, "y": G + y, "z": CZ, "type": SAND})
blocks.append({"x": CX, "y": G + 43, "z": CZ, "type": SAND})

# ============================================================
# 6. Interior hueco (escalera de caracol simplificada)
# ============================================================
print("6. Interior hueco...")
for x in range(CX - 4, CX + 5):
    for y in range(3, 25):
        for z in range(CZ - 4, CZ + 5):
            if not (x in (CX - 4, CX + 4) or z in (CZ - 4, CZ + 4)):
                blocks.append({"x": x, "y": G + y, "z": z, "type": AIR})
# Puerta de entrada (cara S)
for y in range(0, 4):
    blocks.append({"x": CX, "y": G + y, "z": CZ + 6, "type": AIR})

send(blocks, "Giralda")

print("\n✓ La Giralda construida en", (CX, G, CZ))
print("  - Zócalo 13x13")
print("  - Cuerpo almohade inferior 11x11 con ventanas geminadas")
print("  - Cuerpo almohade superior 9x9")
print("  - Cuerpo de campanas 7x7 con arcos")
print("  - Remate renacentista con cúpula y Giraldillo")
print("  - Altura total ~43 bloques")