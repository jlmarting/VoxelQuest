"""
Construye un castillo medieval detallado cerca del jugador.
Usa MCP JSON-RPC contra el servidor Python.

Elementos incluidos:
- Murallas perimetrales con almenas (merlones y almenas)
- 4 torres de esquina con matacanes y almenas
- Torre del homenaje central con torreones
- Puerta principal con arco y torreon defensivo
- Patio interior transitable con empedrado
- Postigo trasero
- Foso perimetral
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


def detect_ground(wx, wz):
    for y in range(50, 0, -1):
        res = mcp("get_block", {"x": wx, "y": y, "z": wz})
        bt = res.get("type", 0) if isinstance(res, dict) else 0
        if bt != AIR and bt != WATER:
            return y + 1
    return 23


def send_batch(blocks):
    res = mcp("apply_blocks", {"blocks": blocks}, timeout=120)
    if isinstance(res, dict) and "error" in res:
        return 0
    return len(blocks)


def ring(x, y, z, r):
    """Círculo de voxeles de radio r (espesor 1)."""
    out = set()
    for dx in range(-r, r + 1):
        for dz in range(-r, r + 1):
            d = math.sqrt(dx * dx + dz * dz)
            if d <= r + 0.5 and d > r - 1.5:
                out.add((x + dx, y, z + dz))
    return out


def fill_rect(x1, x2, z1, z2):
    out = set()
    for x in range(x1, x2 + 1):
        for z in range(z1, z2 + 1):
            out.add((x, z))
    return out


def build_castle(base_x, base_z, base_y):
    # ============================================================
    # Dimensiones del castillo (61x61 exterior, muros grosor 2)
    # ============================================================
    M = 61          # lado exterior
    WALL_H = 12     # altura de la muralla
    TOWER_W = 9     # torres de esquina 9x9
    TOWER_H = 28    # altura torres
    KEEP_W = 15     # torre del homenaje 15x15
    KEEP_H = 20
    # Coordenadas
    x0, z0 = base_x, base_z          # esquina inferior izquierda (patio empieza en +2)
    x1, x2 = base_x, base_x + M - 1  # muros X
    z1, z2 = base_z, base_z + M - 1  # muros Z
    patio_x1, patio_x2 = base_x + 2, base_x + M - 3
    patio_z1, patio_z2 = base_z + 2, base_z + M - 3

    blocks = []
    air = []

    # ============================================================
    # 1. SOLERA / PATIO empedrado
    # ============================================================
    for x in range(patio_x1, patio_x2 + 1):
        for z in range(patio_z1, patio_z2 + 1):
            blocks.append({"x": x, "y": base_y, "z": z, "type": COBBLESTONE})

    # ============================================================
    # 2. MURALLAS PERIMETRALES (grosor 2) + ALMENAS
    # ============================================================
    def add_wall(x_from, x_to, z_from, z_to):
        for x in range(x_from, x_to + 1):
            for z in range(z_from, z_to + 1):
                for dy in range(1, WALL_H):
                    blocks.append({"x": x, "y": base_y + dy, "z": z, "type": STONE})

    add_wall(x1, x2, z1, z1 + 1)
    add_wall(x1, x2, z2 - 1, z2)
    add_wall(x1, x1 + 1, z1, z2)
    add_wall(x2 - 1, x2, z1, z2)

    # Almenas (merlones a lo largo de la coronacion)
    def crenellations(x_from, x_to, z_from, z_to, axis):
        # axis: 'x' = la muralla corre en X, 'z' = corre en Z
        positions = range(x_from, x_to + 1) if axis == 'x' else range(z_from, z_to + 1)
        for i, p in enumerate(positions):
            if axis == 'x':
                bx, bz = p, z_from
            else:
                bx, bz = x_from, p
            # Merlon (solido) en posiciones pares, almena (hueco) en impares
            if i % 2 == 0:
                blocks.append({"x": bx, "y": base_y + WALL_H, "z": bz, "type": COBBLESTONE})
            else:
                air.append({"x": bx, "y": base_y + WALL_H, "z": bz, "type": AIR})
            # Merlon de la fila interior (grosor 2)
            if axis == 'x':
                bx2, bz2 = p, z_from + 1
            else:
                bx2, bz2 = x_from + 1, p
            if i % 2 == 0:
                blocks.append({"x": bx2, "y": base_y + WALL_H, "z": bz2, "type": COBBLESTONE})
            else:
                air.append({"x": bx2, "y": base_y + WALL_H, "z": bz2, "type": AIR})

    # Almenas en los 4 tramos (excluyendo las torres de esquina y la puerta)
    tw = TOWER_W  # las torres de esquina ocupan [x0..x0+8] y [x2-8..x2]
    crenellations(x1 + tw, x2 - tw, z1, z1, 'x')   # muralla frontal
    crenellations(x1 + tw, x2 - tw, z2, z2, 'x')   # muralla trasera
    crenellations(x1, x1, z1 + tw, z2 - tw, 'z')   # muralla izquierda
    crenellations(x2, x2, z1 + tw, z2 - tw, 'z')   # muralla derecha

    # ============================================================
    # 3. TORRES DE ESQUINA (9x9) con matacanes + almenas
    # ============================================================
    corners = [
        (x1, z1), (x2 - TOWER_W + 1, z1),
        (x1, z2 - TOWER_W + 1), (x2 - TOWER_W + 1, z2 - TOWER_W + 1),
    ]
    for cx, cz in corners:
        for dx in range(TOWER_W):
            for dz in range(TOWER_W):
                for dy in range(1, TOWER_H):
                    blocks.append({"x": cx + dx, "y": base_y + dy, "z": cz + dz, "type": STONE})
        # Interior hueco de la torre (habitacion abajo)
        for dx in range(2, TOWER_W - 2):
            for dz in range(2, TOWER_W - 2):
                for dy in range(1, WALL_H - 1):
                    air.append({"x": cx + dx, "y": base_y + dy, "z": cz + dz, "type": AIR})
        # Matacanes (voladizo defensivo)
        for dx in range(-1, TOWER_W + 1):
            for dz in range(-1, TOWER_W + 1):
                if dx in (-1, TOWER_W) or dz in (-1, TOWER_W):
                    blocks.append({"x": cx + dx, "y": base_y + TOWER_H - 1, "z": cz + dz, "type": COBBLESTONE})
        # Almenas superiores de la torre
        for i in range(TOWER_W):
            for edge in [(cx + i, cz), (cx + i, cz + TOWER_W - 1), (cx, cz + i), (cx + TOWER_W - 1, cz + i)]:
                ex, ez = edge
                if (ex + ez) % 2 == 0:
                    blocks.append({"x": ex, "y": base_y + TOWER_H, "z": ez, "type": COBBLESTONE})
                else:
                    air.append({"x": ex, "y": base_y + TOWER_H, "z": ez, "type": AIR})

    # ============================================================
    # 4. TORRE DEL HOMENAJE central (15x15) + torreones
    # ============================================================
    keep_cx = base_x + M // 2
    keep_cz = base_z + M // 2
    kx1 = keep_cx - KEEP_W // 2
    kz1 = keep_cz - KEEP_W // 2
    for dx in range(KEEP_W):
        for dz in range(KEEP_W):
            for dy in range(1, KEEP_H):
                blocks.append({"x": kx1 + dx, "y": base_y + dy, "z": kz1 + dz, "type": STONE})
    # Interior de la torre del homenaje
    for dx in range(2, KEEP_W - 2):
        for dz in range(2, KEEP_W - 2):
            for dy in range(1, KEEP_H - 2):
                air.append({"x": kx1 + dx, "y": base_y + dy, "z": kz1 + dz, "type": AIR})
    # Almenas superiores
    for dx in range(KEEP_W):
        for dz in range(KEEP_W):
            if dx in (0, KEEP_W - 1) or dz in (0, KEEP_W - 1):
                if (dx + dz) % 2 == 0:
                    blocks.append({"x": kx1 + dx, "y": base_y + KEEP_H, "z": kz1 + dz, "type": COBBLESTONE})
    # Torreones en las 4 esquinas del homenaje
    for ox, oz in [(0, 0), (KEEP_W - 1, 0), (0, KEEP_W - 1), (KEEP_W - 1, KEEP_W - 1)]:
        for dx in range(-1, 2):
            for dz in range(-1, 2):
                if (dx, dz) != (0, 0) or True:
                    blocks.append({"x": kx1 + ox + dx, "y": base_y + KEEP_H + 1, "z": kz1 + oz + dz, "type": COBBLESTONE})
        for i in range(2, 5):
            blocks.append({"x": kx1 + ox, "y": base_y + KEEP_H + i, "z": kz1 + oz, "type": STONE})

    # ============================================================
    # 5. PUERTA PRINCIPAL (arco + torreon) en la muralla frontal
    # ============================================================
    gate_x = keep_cx
    gate_y = base_y
    # Hueco de la puerta (3 de ancho, 5 de alto) en la muralla frontal
    for dx in range(-1, 2):
        for dy in range(1, 6):
            air.append({"x": gate_x + dx, "y": gate_y + dy, "z": z1, "type": AIR})
            air.append({"x": gate_x + dx, "y": gate_y + dy, "z": z1 + 1, "type": AIR})
    # Arco de la puerta
    for i in range(5):
        angle = math.pi * (i / 4.0)
        arc_x = gate_x + int(math.cos(angle) * 2)
        arc_y = 5 + int(math.sin(angle) * 3)
        blocks.append({"x": arc_x, "y": gate_y + arc_y, "z": z1, "type": COBBLESTONE})
        blocks.append({"x": arc_x, "y": gate_y + arc_y, "z": z1 + 1, "type": COBBLESTONE})
    # Torreon sobre la puerta
    tg_w = 9
    tg_x = gate_x - tg_w // 2
    for dx in range(tg_w):
        for dz in range(2):
            for dy in range(6, 14):
                blocks.append({"x": tg_x + dx, "y": gate_y + dy, "z": z1 + dz, "type": STONE})
    # Almenas del torreon de la puerta
    for i in range(tg_w):
        if i % 2 == 0:
            blocks.append({"x": tg_x + i, "y": gate_y + 14, "z": z1, "type": COBBLESTONE})
        else:
            air.append({"x": tg_x + i, "y": gate_y + 14, "z": z1, "type": AIR})
    # Interior del torreon (piso de guardia)
    for dx in range(2, tg_w - 2):
        for dz in range(1, 2):
            for dy in range(7, 13):
                air.append({"x": tg_x + dx, "y": gate_y + dy, "z": z1 + dz, "type": AIR})
    # Escalinata exterior
    for step in range(3):
        for dx in range(-2, 3):
            blocks.append({"x": gate_x + dx, "y": gate_y - 1 - step, "z": z1 - 1 - step, "type": COBBLESTONE})

    # ============================================================
    # 6. POSTIGO trasero (paso 1x2 en muralla trasera)
    # ============================================================
    post_x = keep_cx
    for dy in range(1, 3):
        air.append({"x": post_x, "y": gate_y + dy, "z": z2, "type": AIR})

    # ============================================================
    # 7. FOSO perimetral (zona de agua alrededor)
    # ============================================================
    for dx in range(-3, M + 3):
        for dz in range(-3, M + 3):
            # Solo la franja exterior al castillo
            if (x1 - 3 <= base_x + dx <= x1 - 1 or x2 + 1 <= base_x + dx <= x2 + 3 or
                z1 - 3 <= base_z + dz <= z1 - 1 or z2 + 1 <= base_z + dz <= z2 + 3):
                blocks.append({"x": base_x + dx, "y": base_y - 1, "z": base_z + dz, "type": WATER})
            # Camino seco en la puerta
    for dx in range(-2, 3):
        for dz in range(-2, 0):
            blocks.append({"x": gate_x + dx, "y": base_y - 1, "z": z1 + dz, "type": COBBLESTONE})

    # ============================================================
    # RESOLVER: aire gana sobre bloques solidos
    # ============================================================
    block_map = {}
    for b in blocks:
        block_map[(b["x"], b["y"], b["z"])] = b["type"]
    for b in air:
        block_map[(b["x"], b["y"], b["z"])] = AIR

    return [{"x": k[0], "y": k[1], "z": k[2], "type": v} for k, v in block_map.items()]


if __name__ == "__main__":
    if len(sys.argv) >= 4:
        base_x = int(sys.argv[1])
        base_z = int(sys.argv[2])
        base_y = int(sys.argv[3])
        print(f"Usando coordenadas manuales: ({base_x}, {base_z}), y={base_y}")
    else:
        players = mcp("list_players", {})
        p = players.get("players", [{}])[0] if isinstance(players, dict) else {}
        px, pz = int(p.get("x", 0)), int(p.get("z", 0))
        print(f"Jugador en ({px}, {pz})")

        base_y = detect_ground(px, pz)
        print(f"Suelo en y={base_y}")

        base_x = px - 30
        base_z = pz - 30
        print(f"Castillo desde ({base_x}, {base_z}), y={base_y}")

    blocks = build_castle(base_x, base_z, base_y)
    print(f"\nColocando {len(blocks)} bloques...")

    BATCH = 400
    ok_total = 0
    for i in range(0, len(blocks), BATCH):
        batch = blocks[i:i + BATCH]
        ok = send_batch(batch)
        ok_total += ok
        time.sleep(0.05)

    print(f"\nCastillo medieval construido en ({base_x}, {base_y}, {base_z})!")
    print(f"{ok_total}/{len(blocks)} bloques colocados")
    print("61x61 de base | murallas 12 bloques | torres de esquina 28 | homenaje central 20 | foso perimetral")
