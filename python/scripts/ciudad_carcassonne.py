"""Construye una ciudad aleatoria estilo Carcassonne en la zona libre.

Carcassonne: ciudad medieval fortificada con murallas dobles y torres,
calles estrechas, casas con tejados, catedral central, plaza de mercado
y castillo (Château Comtal).

Plan:
1. Suelo de tierra en y=21 (área 80x80).
2. Muralla exterior con torres (perímetro).
3. Calles (suelo de piedra) en cuadrícula irregular.
4. Casas con tejados a dos aguas en las manzanas.
5. Catedral central con torres.
6. Plaza de mercado.
7. Castillo (Château Comtal) en una esquina.
"""
from __future__ import annotations
import json
import urllib.request
import sys
import random

AIR = 0
GRASS = 1
DIRT = 2
STONE = 3
WOOD = 4
LEAVES = 5
SAND = 6
WATER = 7
COBBLE = 8
PLANKS = 9
BRICK = 13

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

random.seed(42)

# ============================================================
# 1. Suelo de tierra (área 80x80, y=21)
# ============================================================
print("1. Creando suelo de tierra...")
X0, X1 = -40, 40
Z0, Z1 = -40, 40
GROUND = 21
blocks = []
for x in range(X0, X1 + 1):
    for z in range(Z0, Z1 + 1):
        blocks.append({"x": x, "y": GROUND, "z": z, "type": DIRT})
send(blocks, "suelo")

# ============================================================
# 2. Muralla exterior con torres (perímetro 60x60)
# ============================================================
print("2. Muralla exterior con torres...")
W = 60
WX0, WZ0 = -30, -30
WALL_H = 7
blocks = []
# Muros
for x in range(WX0, WX0 + W):
    for y in range(1, WALL_H + 1):
        blocks.append({"x": x, "y": GROUND + y, "z": WZ0, "type": COBBLE})
        blocks.append({"x": x, "y": GROUND + y, "z": WZ0 + W - 1, "type": COBBLE})
for z in range(WZ0, WZ0 + W):
    for y in range(1, WALL_H + 1):
        blocks.append({"x": WX0, "y": GROUND + y, "z": z, "type": COBBLE})
        blocks.append({"x": WX0 + W - 1, "y": GROUND + y, "z": z, "type": COBBLE})
# Almenas
for x in range(WX0, WX0 + W, 2):
    blocks.append({"x": x, "y": GROUND + WALL_H + 1, "z": WZ0, "type": COBBLE})
    blocks.append({"x": x, "y": GROUND + WALL_H + 1, "z": WZ0 + W - 1, "type": COBBLE})
for z in range(WZ0, WZ0 + W, 2):
    blocks.append({"x": WX0, "y": GROUND + WALL_H + 1, "z": z, "type": COBBLE})
    blocks.append({"x": WX0 + W - 1, "y": GROUND + WALL_H + 1, "z": z, "type": COBBLE})
# Torres de esquina (8x8, altura 12)
for (tx, tz) in [(WX0, WZ0), (WX0 + W - 8, WZ0), (WX0, WZ0 + W - 8), (WX0 + W - 8, WZ0 + W - 8)]:
    for x in range(tx, tx + 8):
        for z in range(tz, tz + 8):
            for y in range(1, 13):
                if x in (tx, tx + 7) or z in (tz, tz + 7):
                    blocks.append({"x": x, "y": GROUND + y, "z": z, "type": STONE})
    # Techo cónico
    for i in range(3):
        r = 3 - i
        for dx in range(-r, r + 1):
            for dz in range(-r, r + 1):
                if dx * dx + dz * dz <= r * r + 1:
                    blocks.append({"x": tx + 4 + dx, "y": GROUND + 12 + i, "z": tz + 4 + dz, "type": BRICK})
    blocks.append({"x": tx + 4, "y": GROUND + 15, "z": tz + 4, "type": STONE})
# Puertas (N, S, E, O)
for (gx, gz) in [(0, WZ0), (0, WZ0 + W - 1), (WX0, 0), (WX0 + W - 1, 0)]:
    for y in range(1, 5):
        blocks.append({"x": gx, "y": GROUND + y, "z": gz, "type": AIR})
    # Arco
    for dx in range(-1, 2):
        blocks.append({"x": gx + dx, "y": GROUND + 5, "z": gz, "type": STONE})
send(blocks, "muralla")

# ============================================================
# 3. Calles (suelo de piedra) en cuadrícula irregular
# ============================================================
print("3. Calles de piedra...")
blocks = []
# Calles principales (cada 12 bloques, con variación aleatoria)
calles_x = [-24, -12, 0, 12, 24]
calles_z = [-24, -12, 0, 12, 24]
for cx in calles_x:
    for z in range(WZ0 + 1, WZ0 + W - 1):
        blocks.append({"x": cx, "y": GROUND, "z": z, "type": COBBLE})
        blocks.append({"x": cx + 1, "y": GROUND, "z": z, "type": COBBLE})
for cz in calles_z:
    for x in range(WX0 + 1, WX0 + W - 1):
        blocks.append({"x": x, "y": GROUND, "z": cz, "type": COBBLE})
        blocks.append({"x": x, "y": GROUND, "z": cz + 1, "type": COBBLE})
# Calles secundarias aleatorias
for _ in range(8):
    sx = random.randint(WX0 + 4, WX0 + W - 6)
    sz = random.randint(WZ0 + 4, WZ0 + W - 6)
    if random.random() < 0.5:
        for z in range(sz - 4, sz + 5):
            blocks.append({"x": sx, "y": GROUND, "z": z, "type": COBBLE})
    else:
        for x in range(sx - 4, sx + 5):
            blocks.append({"x": x, "y": GROUND, "z": sz, "type": COBBLE})
send(blocks, "calles")

# ============================================================
# 4. Casas con tejados a dos aguas (en las manzanas)
# ============================================================
print("4. Casas con tejados...")
blocks = []
# Manzanas entre calles: generar casas en posiciones aleatorias
for _ in range(40):
    # Posición dentro de la muralla, evitando calles
    hx = random.randint(WX0 + 3, WX0 + W - 5)
    hz = random.randint(WZ0 + 3, WZ0 + W - 5)
    # Evitar calles principales
    if any(abs(hx - cx) < 3 for cx in calles_x) or any(abs(hz - cz) < 3 for cz in calles_z):
        continue
    # Tamaño de la casa
    w = random.randint(3, 5)
    d = random.randint(3, 5)
    h = random.randint(3, 5)
    # Paredes
    for x in range(hx, hx + w):
        for z in range(hz, hz + d):
            for y in range(1, h):
                if x in (hx, hx + w - 1) or z in (hz, hz + d - 1):
                    blocks.append({"x": x, "y": GROUND + y, "z": z, "type": WOOD})
    # Tejado a dos aguas (ladrillo)
    for x in range(hx, hx + w):
        for z in range(hz, hz + d):
            blocks.append({"x": x, "y": GROUND + h, "z": z, "type": BRICK})
    # Cumbrera
    for x in range(hx, hx + w):
        blocks.append({"x": x, "y": GROUND + h + 1, "z": hz + d // 2, "type": BRICK})
    # Puerta
    blocks.append({"x": hx + w // 2, "y": GROUND + 1, "z": hz, "type": AIR})
    blocks.append({"x": hx + w // 2, "y": GROUND + 2, "z": hz, "type": AIR})
send(blocks, "casas")

# ============================================================
# 5. Catedral central con torres
# ============================================================
print("5. Catedral central...")
blocks = []
CAT_X, CAT_Z = -6, -6
CAT_W, CAT_D, CAT_H = 12, 12, 10
# Paredes
for x in range(CAT_X, CAT_X + CAT_W):
    for z in range(CAT_Z, CAT_Z + CAT_D):
        for y in range(1, CAT_H):
            if x in (CAT_X, CAT_X + CAT_W - 1) or z in (CAT_Z, CAT_Z + CAT_D - 1):
                blocks.append({"x": x, "y": GROUND + y, "z": z, "type": STONE})
# Techo
for x in range(CAT_X, CAT_X + CAT_W):
    for z in range(CAT_Z, CAT_Z + CAT_D):
        blocks.append({"x": x, "y": GROUND + CAT_H, "z": z, "type": BRICK})
# Torres frontales (2 torres con agujas)
for (tx, tz) in [(CAT_X, CAT_Z), (CAT_X + CAT_W - 4, CAT_Z)]:
    for x in range(tx, tx + 4):
        for z in range(tz, tz + 4):
            for y in range(1, 18):
                if x in (tx, tx + 3) or z in (tz, tz + 3):
                    blocks.append({"x": x, "y": GROUND + y, "z": z, "type": STONE})
    # Aguja
    for i in range(5):
        r = 2 - i // 2
        for dx in range(-r, r + 1):
            for dz in range(-r, r + 1):
                if dx * dx + dz * dz <= r * r + 1:
                    blocks.append({"x": tx + 2 + dx, "y": GROUND + 18 + i, "z": tz + 2 + dz, "type": BRICK})
    blocks.append({"x": tx + 2, "y": GROUND + 23, "z": tz + 2, "type": STONE})
# Portal
for y in range(1, 5):
    blocks.append({"x": CAT_X + CAT_W // 2, "y": GROUND + y, "z": CAT_Z, "type": AIR})
# Interior hueco
for x in range(CAT_X + 1, CAT_X + CAT_W - 1):
    for y in range(1, CAT_H):
        for z in range(CAT_Z + 1, CAT_Z + CAT_D - 1):
            blocks.append({"x": x, "y": GROUND + y, "z": z, "type": AIR})
send(blocks, "catedral")

# ============================================================
# 6. Plaza de mercado (centro)
# ============================================================
print("6. Plaza de mercado...")
blocks = []
# Suelo de la plaza
for x in range(-4, 5):
    for z in range(-4, 5):
        blocks.append({"x": x, "y": GROUND, "z": z, "type": PLANKS})
# Puestos de mercado (4 puestos con toldo)
for (px, pz) in [(-3, -3), (3, -3), (-3, 3), (3, 3)]:
    for x in range(px, px + 2):
        for z in range(pz, pz + 2):
            blocks.append({"x": x, "y": GROUND + 1, "z": z, "type": WOOD})
            blocks.append({"x": x, "y": GROUND + 2, "z": z, "type": WOOD})
    # Toldo
    for x in range(px - 1, px + 3):
        for z in range(pz - 1, pz + 3):
            blocks.append({"x": x, "y": GROUND + 3, "z": z, "type": LEAVES})
# Fuente central
for x in range(-1, 2):
    for z in range(-1, 2):
        blocks.append({"x": x, "y": GROUND + 1, "z": z, "type": STONE})
blocks.append({"x": 0, "y": GROUND + 2, "z": 0, "type": WATER})
send(blocks, "plaza")

# ============================================================
# 7. Castillo (Château Comtal) en una esquina
# ============================================================
print("7. Castillo (Château Comtal)...")
blocks = []
CH_X, CH_Z = 20, 20
CH_W, CH_D, CH_H = 10, 10, 12
# Paredes
for x in range(CH_X, CH_X + CH_W):
    for z in range(CH_Z, CH_Z + CH_D):
        for y in range(1, CH_H):
            if x in (CH_X, CH_X + CH_W - 1) or z in (CH_Z, CH_Z + CH_D - 1):
                blocks.append({"x": x, "y": GROUND + y, "z": z, "type": STONE})
# Techo
for x in range(CH_X, CH_X + CH_W):
    for z in range(CH_Z, CH_Z + CH_D):
        blocks.append({"x": x, "y": GROUND + CH_H, "z": z, "type": BRICK})
# Torreón central
for x in range(CH_X + 3, CH_X + 7):
    for z in range(CH_Z + 3, CH_Z + 7):
        for y in range(1, 18):
            if x in (CH_X + 3, CH_X + 6) or z in (CH_Z + 3, CH_Z + 6):
                blocks.append({"x": x, "y": GROUND + y, "z": z, "type": STONE})
# Almenas del torreón
for x in range(CH_X + 3, CH_X + 7, 2):
    blocks.append({"x": x, "y": GROUND + 18, "z": CH_Z + 3, "type": STONE})
    blocks.append({"x": x, "y": GROUND + 18, "z": CH_Z + 6, "type": STONE})
for z in range(CH_Z + 3, CH_Z + 7, 2):
    blocks.append({"x": CH_X + 3, "y": GROUND + 18, "z": z, "type": STONE})
    blocks.append({"x": CH_X + 6, "y": GROUND + 18, "z": z, "type": STONE})
# Puerta
for y in range(1, 4):
    blocks.append({"x": CH_X + CH_W // 2, "y": GROUND + y, "z": CH_Z, "type": AIR})
# Interior hueco
for x in range(CH_X + 1, CH_X + CH_W - 1):
    for y in range(1, CH_H):
        for z in range(CH_Z + 1, CH_Z + CH_D - 1):
            blocks.append({"x": x, "y": GROUND + y, "z": z, "type": AIR})
send(blocks, "castillo")

print("\n✓ Ciudad estilo Carcassonne construida:")
print("  - Muralla 60x60 con 4 torres y 4 puertas")
print("  - Calles de piedra en cuadrícula irregular")
print("  - 40 casas con tejados a dos aguas")
print("  - Catedral central con 2 torres y agujas")
print("  - Plaza de mercado con puestos y fuente")
print("  - Castillo (Château Comtal) con torreón")