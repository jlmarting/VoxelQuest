"""
Crea una estatua GIGANTE del Discobolo (lanzador de disco) usando bloques estandar.
Altura: ~55 bloques. Usa apply_blocks para construir directamente en el mundo.
"""
import json, urllib.request, time, sys

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

def add_box(blocks, x1, y1, z1, x2, y2, z2, btype):
    """Añade todos los bloques de una caja [x1,x2] x [y1,y2] x [z1,z2]."""
    for x in range(min(x1, x2), max(x1, x2) + 1):
        for y in range(min(y1, y2), max(y1, y2) + 1):
            for z in range(min(z1, z2), max(z1, z2) + 1):
                blocks.append({"x": x, "y": y, "z": z, "type": btype})

def detect_ground(wx, wz):
    for y in range(80, 0, -1):
        res = mcp("get_block", {"x": wx, "y": y, "z": wz})
        bt = res.get("type", 0) if isinstance(res, dict) else 0
        if bt != AIR and bt != WATER:
            return y + 1
    return 30

def build_discobolo_gigante(base_x, base_y, base_z):
    """
    Construye un Discobolo gigante centrado en (base_x, base_y, base_z).
    Orientacion: mira hacia +Z (lanzando hacia el norte).
    """
    b = []

    # ============================================================
    # 1. PEDESTAL (base solida, 14x10x6)
    # ============================================================
    add_box(b, base_x - 6, base_y,     base_z - 4, base_x + 6, base_y + 1, base_z + 4, STONE)
    add_box(b, base_x - 5, base_y + 2, base_z - 3, base_x + 5, base_y + 3, base_z + 3, COBBLESTONE)
    add_box(b, base_x - 4, base_y + 4, base_z - 2, base_x + 4, base_y + 5, base_z + 2, STONE)

    by = base_y + 6  # altura desde donde empieza la estatua

    # ============================================================
    # 2. PIERNA DERECHA (apoyo, recta, gruesa)
    # ============================================================
    # Pie
    add_box(b, base_x - 2, by,     base_z - 2, base_x + 1, by + 1, base_z + 2, COBBLESTONE)
    # Pantorrilla
    add_box(b, base_x - 2, by + 2, base_z - 2, base_x + 1, by + 7, base_z + 2, COBBLESTONE)
    # Muslo
    add_box(b, base_x - 2, by + 8, base_z - 2, base_x + 1, by + 14, base_z + 2, COBBLESTONE)

    # ============================================================
    # 3. PIERNA IZQUIERDA (flexionada, adelantada)
    # ============================================================
    # Pie izquierdo (adelante y un poco levantado)
    add_box(b, base_x + 3, by,     base_z - 1, base_x + 6, by + 1, base_z + 2, COBBLESTONE)
    # Pantorrilla izquierda (inclinada hacia arriba/adelante)
    add_box(b, base_x + 3, by + 2, base_z - 1, base_x + 6, by + 6, base_z + 2, COBBLESTONE)
    # Muslo izquierdo (subiendo hacia la cadera)
    add_box(b, base_x + 2, by + 7, base_z - 1, base_x + 5, by + 12, base_z + 2, COBBLESTONE)

    # ============================================================
    # 4. CADERA / PELVIS
    # ============================================================
    add_box(b, base_x - 3, by + 13, base_z - 3, base_x + 5, by + 16, base_z + 3, STONE)

    # ============================================================
    # 5. TORSO (inclinado hacia +Z, direccion del lanzamiento)
    # ============================================================
    # Abdomen
    add_box(b, base_x - 3, by + 17, base_z - 3, base_x + 3, by + 20, base_z + 3, COBBLESTONE)
    # Torso medio (se inclina hacia adelante)
    add_box(b, base_x - 3, by + 21, base_z - 2, base_x + 3, by + 26, base_z + 4, COBBLESTONE)
    # Torso superior (pecho, hombros mas anchos)
    add_box(b, base_x - 4, by + 27, base_z - 2, base_x + 4, by + 32, base_z + 4, COBBLESTONE)

    # ============================================================
    # 6. BRAZO IZQUIERDO (atras, contrapeso)
    # ============================================================
    # Hombro izquierdo
    add_box(b, base_x - 7, by + 28, base_z - 2, base_x - 4, by + 31, base_z + 2, STONE)
    # Brazo extendido hacia atras
    add_box(b, base_x - 12, by + 29, base_z - 1, base_x - 7, by + 30, base_z + 1, STONE)

    # ============================================================
    # 7. BRAZO DERECHO (extendido hacia +Z con el disco)
    # ============================================================
    # Hombro derecho
    add_box(b, base_x + 4, by + 28, base_z - 2, base_x + 7, by + 31, base_z + 2, STONE)
    # Brazo extendido hacia adelante (+Z)
    add_box(b, base_x + 4, by + 29, base_z + 3, base_x + 6, by + 31, base_z + 12, STONE)

    # ============================================================
    # 8. DISCO (placa circular/gruesa en la mano derecha)
    # ============================================================
    # Centro del disco
    add_box(b, base_x + 3, by + 30, base_z + 12, base_x + 7, by + 31, base_z + 18, PLANKS)
    # Borde del disco
    add_box(b, base_x + 2, by + 30, base_z + 13, base_x + 2, by + 31, base_z + 17, PLANKS)
    add_box(b, base_x + 8, by + 30, base_z + 13, base_x + 8, by + 31, base_z + 17, PLANKS)

    # ============================================================
    # 9. CUELLO
    # ============================================================
    add_box(b, base_x - 1, by + 33, base_z - 1, base_x + 1, by + 35, base_z + 1, COBBLESTONE)

    # ============================================================
    # 10. CABEZA (girada hacia +Z, mirando el lanzamiento)
    # ============================================================
    add_box(b, base_x - 2, by + 36, base_z - 2, base_x + 2, by + 42, base_z + 3, STONE)
    # Frente/mirada
    add_box(b, base_x - 1, by + 37, base_z + 3, base_x + 1, by + 40, base_z + 4, COBBLESTONE)  # cara
    # Pelo
    add_box(b, base_x - 2, by + 40, base_z - 2, base_x + 2, by + 42, base_z + 2, WOOD)

    # ============================================================
    # 11. DETALLES: OJOS, NARIZ, BOCA
    # ============================================================
    # Ojos (huecos/air para simular ojos)
    # Nariz (protuberancia)
    add_box(b, base_x, by + 38, base_z + 4, base_x, by + 39, base_z + 5, COBBLESTONE)

    return b


if __name__ == "__main__":
    # Obtener posicion del jugador
    players = mcp("list_players", {})
    p = players.get("players", [{}])[0] if isinstance(players, dict) else {}
    px, pz = int(p.get("x", 0)), int(p.get("z", 0))
    print(f"Jugador en ({px}, {pz})")

    base_y = detect_ground(px, pz)
    print(f"Suelo en y={base_y}")

    # Colocar la estatua 15 bloques al sur del jugador (para que lo vea de frente)
    base_x = px
    base_z = pz + 20

    print(f"Construyendo Discobolo gigante en ({base_x}, {base_y}, {base_z})...")
    blocks = build_discobolo_gigante(base_x, base_y, base_z)
    print(f"Total bloques: {len(blocks)}")

    BATCH = 400
    ok_total = 0
    for i in range(0, len(blocks), BATCH):
        batch = blocks[i:i + BATCH]
        ok = send_batch(batch)
        ok_total += ok
        time.sleep(0.05)

    print(f"\n✓ Discobolo gigante construido!")
    print(f"{ok_total}/{len(blocks)} bloques colocados")
    print(f"Altura total: ~55 bloques | Mira hacia el norte (+Z)")
