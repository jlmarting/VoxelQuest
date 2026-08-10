"""Construye un castillo enorme con ciudadela y guardias que patrullan.

Diseño (base en y=1, terreno aplanado):
- Muralla exterior 60x60, altura 8, con almenas y 4 torres de esquina (h=14)
- Puerta principal al sur con arco
- Patio interior con cuartel y establos
- Ciudadela central: torre 12x12, altura 22, con almenas y torreón
- Muralla interior alrededor de la ciudadela
- Guardias: objetos móviles (kind=box, color armadura) con motion waypoints
  que patrullan las murallas y el patio

Block types: 3=stone, 8=cobblestone, 9=planks, 4=wood, 13=red_brick, 1=grass
"""
from __future__ import annotations
import json
import urllib.request
import sys

STONE = 3
COBBLE = 8
PLANKS = 9
WOOD = 4
BRICK = 13
GRASS = 1

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

blocks = []

# ============================================================
# 1. Aplanar terreno (60x60)
# ============================================================
print("Aplanando terreno...")
mcp_call("fill_area", {"x": 0, "z": 0, "width": 60, "depth": 60, "height": 1, "baseY": 1, "type": GRASS})

# ============================================================
# 2. Muralla exterior (perímetro 60x60, altura 8)
# ============================================================
print("Construyendo muralla exterior...")
WALL_H = 8
# Muros N y S (a lo largo de X)
for x in range(0, 60):
    for y in range(1, WALL_H + 1):
        blocks.append({"x": x, "y": y, "z": 0, "type": COBBLE})
        blocks.append({"x": x, "y": y, "z": 59, "type": COBBLE})
# Muros E y O (a lo largo de Z)
for z in range(0, 60):
    for y in range(1, WALL_H + 1):
        blocks.append({"x": 0, "y": y, "z": z, "type": COBBLE})
        blocks.append({"x": 59, "y": y, "z": z, "type": COBBLE})

# Almenas en la muralla (cada 2 bloques, en la parte superior)
for x in range(0, 60, 2):
    blocks.append({"x": x, "y": WALL_H + 1, "z": 0, "type": COBBLE})
    blocks.append({"x": x, "y": WALL_H + 1, "z": 59, "type": COBBLE})
for z in range(0, 60, 2):
    blocks.append({"x": 0, "y": WALL_H + 1, "z": z, "type": COBBLE})
    blocks.append({"x": 59, "y": WALL_H + 1, "z": z, "type": COBBLE})

# ============================================================
# 3. Puerta principal al sur (z=0, centro x=30)
# ============================================================
print("Construyendo puerta principal...")
# Arco de la puerta (ancho 4, alto 5)
for x in range(28, 32):
    for y in range(1, 6):
        blocks.append({"x": x, "y": y, "z": 0, "type": 0})  # hueco
# Jambas
for x in [27, 32]:
    for y in range(1, 9):
        blocks.append({"x": x, "y": y, "z": 0, "type": STONE})
# Dintel
for x in range(28, 32):
    blocks.append({"x": x, "y": 6, "z": 0, "type": STONE})
# Torreón de la puerta
for x in range(26, 34):
    for y in range(8, 13):
        blocks.append({"x": x, "y": y, "z": 0, "type": STONE})
        blocks.append({"x": x, "y": y, "z": 1, "type": STONE})
# Almenas del torreón
for x in range(26, 34, 2):
    blocks.append({"x": x, "y": 13, "z": 0, "type": STONE})
    blocks.append({"x": x, "y": 13, "z": 1, "type": STONE})

# ============================================================
# 4. Torres de esquina (4 torres, 8x8, altura 14)
# ============================================================
print("Construyendo torres de esquina...")
def torre(cx, cz):
    for x in range(cx, cx + 8):
        for z in range(cz, cz + 8):
            for y in range(1, 15):
                # Solo el perímetro (hueco por dentro)
                if x in (cx, cx + 7) or z in (cz, cz + 7):
                    blocks.append({"x": x, "y": y, "z": z, "type": STONE})
    # Almenas
    for x in range(cx, cx + 8, 2):
        blocks.append({"x": x, "y": 15, "z": cz, "type": STONE})
        blocks.append({"x": x, "y": 15, "z": cz + 7, "type": STONE})
    for z in range(cz, cz + 8, 2):
        blocks.append({"x": cx, "y": 15, "z": z, "type": STONE})
        blocks.append({"x": cx + 7, "y": 15, "z": z, "type": STONE})
    # Suelo interior
    for x in range(cx + 1, cx + 7):
        for z in range(cz + 1, cz + 7):
            blocks.append({"x": x, "y": 1, "z": z, "type": PLANKS})

torre(1, 1)      # NO
torre(51, 1)     # NE
torre(1, 51)     # SO
torre(51, 51)    # SE

# ============================================================
# 5. Patio interior: cuartel y establos
# ============================================================
print("Construyendo cuartel y establos...")
# Cuartel (edificio 10x6, altura 4) en (10, 10)
for x in range(10, 20):
    for z in range(10, 16):
        for y in range(1, 5):
            if x in (10, 19) or z in (10, 15) or y == 4:
                blocks.append({"x": x, "y": y, "z": z, "type": WOOD})
# Puerta del cuartel
for y in range(1, 3):
    blocks.append({"x": 15, "y": y, "z": 10, "type": 0})
# Tejado a dos aguas
for x in range(10, 20):
    blocks.append({"x": x, "y": 5, "z": 10, "type": BRICK})
    blocks.append({"x": x, "y": 5, "z": 15, "type": BRICK})

# Establos (edificio 12x5, altura 3) en (40, 40)
for x in range(40, 52):
    for z in range(40, 45):
        for y in range(1, 4):
            if x in (40, 51) or z in (40, 44) or y == 3:
                blocks.append({"x": x, "y": y, "z": z, "type": PLANKS})
# Puertas de los establos
for x in [43, 46, 49]:
    for y in range(1, 3):
        blocks.append({"x": x, "y": y, "z": 40, "type": 0})

# ============================================================
# 6. Muralla interior alrededor de la ciudadela (28x28)
# ============================================================
print("Construyendo muralla interior...")
INNER = 28
INNER_X0 = 16
INNER_Z0 = 16
INNER_H = 6
for x in range(INNER_X0, INNER_X0 + INNER):
    for y in range(1, INNER_H + 1):
        blocks.append({"x": x, "y": y, "z": INNER_Z0, "type": STONE})
        blocks.append({"x": x, "y": y, "z": INNER_Z0 + INNER - 1, "type": STONE})
for z in range(INNER_Z0, INNER_Z0 + INNER):
    for y in range(1, INNER_H + 1):
        blocks.append({"x": INNER_X0, "y": y, "z": z, "type": STONE})
        blocks.append({"x": INNER_X0 + INNER - 1, "y": y, "z": z, "type": STONE})
# Almenas
for x in range(INNER_X0, INNER_X0 + INNER, 2):
    blocks.append({"x": x, "y": INNER_H + 1, "z": INNER_Z0, "type": STONE})
    blocks.append({"x": x, "y": INNER_H + 1, "z": INNER_Z0 + INNER - 1, "type": STONE})
for z in range(INNER_Z0, INNER_Z0 + INNER, 2):
    blocks.append({"x": INNER_X0, "y": INNER_H + 1, "z": z, "type": STONE})
    blocks.append({"x": INNER_X0 + INNER - 1, "y": INNER_H + 1, "z": z, "type": STONE})
# Puerta de la muralla interior (sur)
for x in range(28, 32):
    for y in range(1, 4):
        blocks.append({"x": x, "y": y, "z": INNER_Z0, "type": 0})

# ============================================================
# 7. Ciudadela central (torre 12x12, altura 22)
# ============================================================
print("Construyendo ciudadela central...")
CIT_X0 = 24
CIT_Z0 = 24
CIT_H = 22
for x in range(CIT_X0, CIT_X0 + 12):
    for z in range(CIT_Z0, CIT_Z0 + 12):
        for y in range(1, CIT_H + 1):
            if x in (CIT_X0, CIT_X0 + 11) or z in (CIT_Z0, CIT_Z0 + 11):
                blocks.append({"x": x, "y": y, "z": z, "type": STONE})
# Suelo interior de la ciudadela
for x in range(CIT_X0 + 1, CIT_X0 + 11):
    for z in range(CIT_Z0 + 1, CIT_Z0 + 11):
        blocks.append({"x": x, "y": 1, "z": z, "type": PLANKS})
# Puerta de la ciudadela (sur)
for y in range(1, 4):
    blocks.append({"x": 30, "y": y, "z": CIT_Z0, "type": 0})
# Ventanas (cada 3 bloques, en cada cara)
for y in range(4, CIT_H, 3):
    for x in [CIT_X0 + 3, CIT_X0 + 8]:
        blocks.append({"x": x, "y": y, "z": CIT_Z0, "type": 0})
        blocks.append({"x": x, "y": y, "z": CIT_Z0 + 11, "type": 0})
    for z in [CIT_Z0 + 3, CIT_Z0 + 8]:
        blocks.append({"x": CIT_X0, "y": y, "z": z, "type": 0})
        blocks.append({"x": CIT_X0 + 11, "y": y, "z": z, "type": 0})
# Almenas de la ciudadela
for x in range(CIT_X0, CIT_X0 + 12, 2):
    blocks.append({"x": x, "y": CIT_H + 1, "z": CIT_Z0, "type": STONE})
    blocks.append({"x": x, "y": CIT_H + 1, "z": CIT_Z0 + 11, "type": STONE})
for z in range(CIT_Z0, CIT_Z0 + 12, 2):
    blocks.append({"x": CIT_X0, "y": CIT_H + 1, "z": z, "type": STONE})
    blocks.append({"x": CIT_X0 + 11, "y": CIT_H + 1, "z": z, "type": STONE})

# Torreón central de la ciudadela (4x4, altura 6 extra)
for x in range(28, 32):
    for z in range(28, 32):
        for y in range(CIT_H + 1, CIT_H + 7):
            if x in (28, 31) or z in (28, 31):
                blocks.append({"x": x, "y": y, "z": z, "type": BRICK})
# Almenas del torreón
for x in range(28, 32, 2):
    blocks.append({"x": x, "y": CIT_H + 7, "z": 28, "type": BRICK})
    blocks.append({"x": x, "y": CIT_H + 7, "z": 31, "type": BRICK})
for z in range(28, 32, 2):
    blocks.append({"x": 28, "y": CIT_H + 7, "z": z, "type": BRICK})
    blocks.append({"x": 31, "y": CIT_H + 7, "z": z, "type": BRICK})

# ============================================================
# 8. Enviar bloques en lotes
# ============================================================
print(f"Enviando {len(blocks)} bloques en lotes de 500...")
BATCH = 500
for i in range(0, len(blocks), BATCH):
    chunk = blocks[i:i + BATCH]
    r = mcp_call("apply_blocks", {"blocks": chunk}, timeout=120)
    if not r.get("success"):
        print(f"  ✗ Error en lote {i//BATCH}: {r}")
        sys.exit(1)
    print(f"  ✓ lote {i//BATCH + 1} ({len(chunk)} bloques)")

print(f"✓ Castillo construido: {len(blocks)} bloques")

# ============================================================
# 9. Guardias que patrullan (objetos móviles con waypoints)
# ============================================================
print("Creando guardias que patrullan...")
GUARD_COLOR = 0x2E5E8C  # azul acero (armadura)

def crear_guardia(name, waypoints, speed=2.0):
    # Crear objeto box (guardia) en el primer waypoint
    r = mcp_call("create_object", {
        "kind": "box",
        "position": waypoints[0],
        "scale": [0.6, 1.8, 0.6],
        "color": GUARD_COLOR,
        "mass": 0.0,  # estático (no cae)
        "anchored": True,
    })
    oid = r.get("object_id")
    if not oid:
        print(f"  ✗ Error creando guardia {name}: {r}")
        return
    # Asignar patrulla con waypoints (loop)
    r2 = mcp_call("move_object", {
        "object_id": oid,
        "motion": {
            "type": "waypoints",
            "points": waypoints,
            "speed": speed,
            "loop": True,
        },
    })
    if r2.get("success"):
        print(f"  ✓ Guardia {name} (id={oid}) patrullando {len(waypoints)} puntos")
    else:
        print(f"  ✗ Error patrulla {name}: {r2}")

# Guardia 1: patrulla la muralla norte (a lo largo de X)
crear_guardia("Guardia Muralla Norte", [
    [5, 9, 1], [15, 9, 1], [25, 9, 1], [35, 9, 1], [45, 9, 1], [55, 9, 1],
    [45, 9, 1], [35, 9, 1], [25, 9, 1], [15, 9, 1],
], speed=3.0)

# Guardia 2: patrulla la muralla sur (a lo largo de X)
crear_guardia("Guardia Muralla Sur", [
    [5, 9, 58], [15, 9, 58], [25, 9, 58], [35, 9, 58], [45, 9, 58], [55, 9, 58],
    [45, 9, 58], [35, 9, 58], [25, 9, 58], [15, 9, 58],
], speed=3.0)

# Guardia 3: patrulla la muralla oeste (a lo largo de Z)
crear_guardia("Guardia Muralla Oeste", [
    [1, 9, 5], [1, 9, 15], [1, 9, 25], [1, 9, 35], [1, 9, 45], [1, 9, 55],
    [1, 9, 45], [1, 9, 35], [1, 9, 25], [1, 9, 15],
], speed=3.0)

# Guardia 4: patrulla la muralla este (a lo largo de Z)
crear_guardia("Guardia Muralla Este", [
    [58, 9, 5], [58, 9, 15], [58, 9, 25], [58, 9, 35], [58, 9, 45], [58, 9, 55],
    [58, 9, 45], [58, 9, 35], [58, 9, 25], [58, 9, 15],
], speed=3.0)

# Guardia 5: patrulla el patio interior (rectángulo)
crear_guardia("Guardia Patio", [
    [8, 2, 20], [8, 2, 40], [20, 2, 40], [20, 2, 20],
], speed=2.0)

# Guardia 6: patrulla alrededor de la ciudadela (muralla interior)
crear_guardia("Guardia Ciudadela", [
    [17, 2, 20], [17, 2, 40], [20, 2, 43], [40, 2, 43], [43, 2, 40], [43, 2, 20],
    [40, 2, 17], [20, 2, 17],
], speed=2.0)

# Guardia 7: patrulla la puerta principal (ida y vuelta)
crear_guardia("Guardia Puerta", [
    [30, 2, 3], [30, 2, 8], [30, 2, 3],
], speed=1.5)

# Guardia 8: patrulla la cima de la ciudadela (torreón)
crear_guardia("Guardia Torreón", [
    [29, 30, 29], [29, 30, 31], [31, 30, 31], [31, 30, 29],
], speed=1.5)

print("\n✓ Castillo completo: murallas, torres, puerta, cuartel, establos, ciudadela y 8 guardias patrullando")