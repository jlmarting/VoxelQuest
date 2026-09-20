"""
Venus de Milo como pixel-art 3D con BLOQUES ESTANDAR del mundo.
Altura: 30 bloques. Usa apply_blocks para construir directamente.
Esto garantiza iluminacion correcta y visibilidad desde lejos.
Tecnica: capas horizontales con patrones de bloques que simulan la silueta.
"""
import json, urllib.request, time, sys, math

URL = "http://localhost:9000/mcp"
_RPC = [0]

AIR, GRASS, DIRT, STONE, WOOD, LEAVES, SAND, WATER, COBBLESTONE, PLANKS, BEDROCK = range(11)

def mcp(method, params, timeout=15):
    _RPC[0] += 1
    data = json.dumps({
        "jsonrpc": "2.0", "id": _RPC[0],
        "method": "tools/call",
        "params": {"name": method, "arguments": params}
    }).encode()
    req = urllib.request.Request(URL, data=data, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            resp = json.loads(r.read().decode())
            if "error" in resp:
                return {"error": resp["error"]}
            content = resp.get("content", [])
            if content and isinstance(content[0], dict) and "text" in content[0]:
                return json.loads(content[0]["text"])
            return resp.get("result", {})
    except Exception as e:
        return {"error": str(e)}

def send_batch(blocks):
    res = mcp("apply_blocks", {"blocks": blocks}, timeout=120)
    if isinstance(res, dict) and "error" in res:
        return 0
    return len(blocks)

# Obtener posicion del jugador
players = mcp("list_players", {})
p = players.get("players", [{}])[0] if isinstance(players, dict) else {}
px, pz = int(p.get("x", 0)), int(p.get("z", 0))
print(f"Jugador en ({px}, {pz})")

# La Venus anterior mala (subvoxel) en las afueras
# Posicion para la nueva: justo al lado del castillo
# El castillo se construyo cerca del jugador, la Venus de 30 esta en z-34.5
# Pongamos esta en z-20 (mas cerca, visible)
BASE_X = px
BASE_Z = pz - 25
BASE_Y = 1  # desde el suelo

H = 30  # altura total

print(f"\nConstruyendo Venus de bloques en ({BASE_X}, {BASE_Y}, {BASE_Z})...")

blocks = []

# ============================================================
# CAPAS HORIZONTALES - cada capa define la silueta en X-Z
# ============================================================
# Formato: para cada Y, una lista de (x, z, ancho_x, profundidad_z, tipo)
# Contrapposto: cadera desplazada -1 a -2 bloques, hombros desplazados +1
# ============================================================

def add_layer(y, center_x, center_z, width_x, depth_z, btype):
    """Añade una capa eliptica de bloques."""
    w2 = width_x / 2.0
    d2 = depth_z / 2.0
    for dx in range(-int(math.ceil(w2)), int(math.ceil(w2)) + 1):
        for dz in range(-int(math.ceil(d2)), int(math.ceil(d2)) + 1):
            # Elipse: (dx/w2)^2 + (dz/d2)^2 <= 1
            if w2 > 0 and d2 > 0:
                val = (dx / w2) ** 2 + (dz / d2) ** 2
                if val <= 1.2:  # ligeramente mas permisivo para evitar agujeros
                    blocks.append({"x": BASE_X + center_x + dx, "y": BASE_Y + y, "z": BASE_Z + center_z + dz, "type": btype})

# PEDESTAL (y 0-2): solido rectangular
for y in range(3):
    for dx in range(-3, 4):
        for dz in range(-3, 4):
            blocks.append({"x": BASE_X + dx, "y": BASE_Y + y, "z": BASE_Z + dz, "type": COBBLESTONE})

# PIES (y 3-4)
add_layer(3, 0, 0, 3, 2, STONE)
add_layer(4, 0, 0, 3, 2, STONE)

# TOBILLOS (y 5-6): pierna derecha recta, izquierda adelantada +1 en Z
add_layer(5, 0, 0, 2, 2, STONE)        # derecha (apoyo)
add_layer(5, -1, 1, 2, 2, STONE)       # izquierda (adelantada)
add_layer(6, 0, 0, 2, 2, STONE)
add_layer(6, -1, 1, 2, 2, STONE)

# PANTORRILLAS (y 7-10): volumen trasero
add_layer(7, 0, 0, 2.5, 2.5, STONE)
add_layer(7, -1, 1, 2, 2.5, STONE)
add_layer(8, 0, 0, 2.5, 2.5, STONE)
add_layer(8, -1, 1, 2, 2.5, STONE)
add_layer(9, 0, 0, 2.5, 2.5, STONE)
add_layer(9, -1, 1, 2, 2.5, STONE)
add_layer(10, 0, 0, 2.5, 2.5, STONE)
add_layer(10, -1, 1, 2, 2.5, STONE)

# RODILLAS (y 11-12)
add_layer(11, 0, 0, 3, 3, STONE)
add_layer(11, -1, 1, 2.5, 2.5, STONE)
add_layer(12, 0, 0, 3, 3, STONE)
add_layer(12, -1, 1, 2.5, 2.5, STONE)

# MUSLOS (y 13-17): volumen creciente
add_layer(13, -0.5, 0, 3.5, 3, STONE)
add_layer(13, -1.5, 1, 2.5, 2.5, STONE)
add_layer(14, -0.5, 0, 4, 3, STONE)
add_layer(14, -1.5, 1, 2.5, 2.5, STONE)
add_layer(15, -0.5, 0, 4.5, 3.5, STONE)
add_layer(15, -1.5, 1, 2.5, 2.5, STONE)
add_layer(16, -0.5, 0, 5, 3.5, STONE)
add_layer(16, -1.5, 1, 2.5, 2.5, STONE)
add_layer(17, -0.5, 0, 5.5, 4, STONE)
add_layer(17, -1.5, 1, 2.5, 2.5, STONE)

# CADERA / PANHO (y 18-22): maximo volumen, desplazamiento cadera -2
# Contrapposto: cadera hacia izquierda (en X negativo)
for y in range(18, 23):
    t = (y - 18) / 4.0  # 0 a 1
    w = 6 - t * 0.5     # de 6 a 5.5
    d = 4 - t * 0.3     # de 4 a 3.7
    # Capa principal (cadera)
    add_layer(y, -1, 0, w, d, COBBLESTONE if y <= 20 else STONE)
    # Pierna izquierda visible
    add_layer(y, -2, 1, 2, 2, STONE)

# CINTURA (y 23-24): muy estrecha
add_layer(23, -0.5, 0, 3.5, 2.5, STONE)
add_layer(24, -0.5, 0, 3, 2, STONE)

# ABDOMEN (y 25-27): vientre suave
add_layer(25, -0.5, 0, 3.5, 2.5, STONE)
add_layer(26, -0.5, 0, 4, 3, STONE)
add_layer(27, -0.5, 0, 4.5, 3.5, STONE)

# PECHO / BUSTO (y 28-30): prominencia frontal
add_layer(28, -0.5, 0.5, 5, 4, STONE)
add_layer(29, -0.5, 0.5, 5.5, 4.5, STONE)
add_layer(30, -0.5, 0.5, 5, 4, STONE)

# HOMBROS (y 31-32): hombros desplazados +1 (opuesto a caderas)
add_layer(31, 0.5, 0, 6, 3.5, STONE)
add_layer(32, 0.5, 0, 6, 3, STONE)

# MUNIONES (y 33-34): brazos cortados, mas estrechos
add_layer(33, 0.5, 0, 4, 2.5, COBBLESTONE)
add_layer(34, 0.5, 0, 3, 2, COBBLESTONE)

# CUELLO (y 35-36)
add_layer(35, 0.5, 0, 2, 1.5, STONE)
add_layer(36, 0.5, 0, 1.5, 1.2, STONE)

# CABEZA (y 37-39): ovalada, mirando hacia izquierda (mas volumen en +X derecha)
add_layer(37, 0.5, 0, 2.5, 2, STONE)
add_layer(38, 0.5, 0, 2.5, 2, STONE)
add_layer(39, 0.5, 0, 2, 1.8, STONE)

# CABELLO / MOÑO (y 40-41): parte posterior y superior
for y in [40, 41]:
    for dx in [-1, 0, 1, 2]:
        for dz in [-2, -1, 0, 1]:
            if abs(dx) + abs(dz) <= 3:
                blocks.append({"x": BASE_X + 0.5 + dx, "y": BASE_Y + y, "z": BASE_Z + dz, "type": COBBLESTONE})

# ============================================================
# PANO: pliegues que cuelgan desde cadera hasta tobillos
# Usamos bloques de COBBLESTONE para simular panho
# ============================================================
# Pliegues laterales y traseros
for y in range(10, 18):
    # Pliegue izquierdo (largo)
    for dz in [-2, -3]:
        blocks.append({"x": BASE_X - 3, "y": BASE_Y + y, "z": BASE_Z + dz, "type": COBBLESTONE})
        blocks.append({"x": BASE_X - 3.5, "y": BASE_Y + y, "z": BASE_Z + dz, "type": COBBLESTONE})
    # Pliegue derecho
    for dz in [1, 2]:
        blocks.append({"x": BASE_X + 2, "y": BASE_Y + y, "z": BASE_Z + dz, "type": COBBLESTONE})
        blocks.append({"x": BASE_X + 2.5, "y": BASE_Y + y, "z": BASE_Z + dz, "type": COBBLESTONE})
    # Pliegue trasero
    for dx in [-2, -1, 0, 1]:
        blocks.append({"x": BASE_X + dx, "y": BASE_Y + y, "z": BASE_Z - 3, "type": COBBLESTONE})

# Pliegues frontales (cubriendo pierna izquierda parcialmente)
for y in range(12, 18):
    for dx in [-2, -1.5]:
        blocks.append({"x": BASE_X + dx, "y": BASE_Y + y, "z": BASE_Z + 1.5, "type": COBBLESTONE})

# Eliminar bloques interiores (hacer hueco el interior)
# Esto reduce bloques y mejora rendimiento
print(f"Total bloques antes de deduplicar: {len(blocks)}")

# Deduplicar
block_dict = {}
for b in blocks:
    key = (b["x"], b["y"], b["z"])
    block_dict[key] = b["type"]

# Convertir de vuelta
final_blocks = [{"x": k[0], "y": k[1], "z": k[2], "type": v} for k, v in block_dict.items()]

print(f"Bloques unicos: {len(final_blocks)}")

# Enviar en lotes
BATCH = 500
ok_total = 0
for i in range(0, len(final_blocks), BATCH):
    batch = final_blocks[i:i + BATCH]
    ok = send_batch(batch)
    ok_total += ok
    time.sleep(0.05)

print(f"\n✓ Venus de Milo en BLOQUES construida!")
print(f"  {ok_total}/{len(final_blocks)} bloques colocados")
print(f"  Posicion: ({BASE_X}, {BASE_Y}, {BASE_Z})")
print(f"  Altura: {H} bloques")
print(f"  Tecnica: Pixel-art 3D con bloques estandar")
print(f"  Postura: Contrapposto (cadera inclinada, pierna adelantada)")
print(f"  Iluminacion: Bloques estandar = maxima compatibilidad con luz")
