"""
Construye una catedral gotica DETALLADA cerca del jugador.
Usa MCP JSON-RPC contra el servidor Python.

Detalles arquitectonicos incluidos:
- Portada con arcos, columnas y escalinata
- Roseton circular en fachada
- Contrafuertes con pinaculos
- Arcbotantes (arcos exteriores de soporte)
- Torre central (cimborrio) sobre el crucero
- Capillas radiantes en el abside
- Ventanas con arco apuntado (clerestorio)
- Suelos interiores con patrones
- Altar elevado con retablo
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


def clear_zone(base_x, base_z, base_y, long, wide, height):
    air_blocks = []
    for dx in range(-3, wide + 3):
        for dz in range(-3, long + 3):
            for dy in range(-2, height + 8):
                air_blocks.append({"x": base_x + dx, "y": base_y + dy, "z": base_z + dz, "type": AIR})
    BATCH = 1000
    total = 0
    for i in range(0, len(air_blocks), BATCH):
        batch = air_blocks[i:i + BATCH]
        ok = send_batch(batch)
        total += ok
        time.sleep(0.02)
    return total


def dist(x1, z1, x2, z2):
    return math.sqrt((x1 - x2) ** 2 + (z1 - z2) ** 2)


def build_cathedral_detailed(base_x, base_z, base_y):
    long = 55
    wide = 31
    nave_h = 26
    aisle_h = 14
    
    # ============================================================
    # 1. SUELO EXTERIOR - base de la catedral (explanada)
    # ============================================================
    blocks = []
    for dx in range(-2, wide + 2):
        for dz in range(-4, long + 4):
            blocks.append({"x": base_x + dx, "y": base_y - 1, "z": base_z + dz, "type": COBBLESTONE})
    
    # ============================================================
    # 2. ESCALINATA DE ENTRADA (fachada principal, z=0)
    # ============================================================
    for step in range(4):
        z_out = base_z - 1 - step
        y_step = base_y - 1 - step
        for dx in range(6, wide - 6):
            blocks.append({"x": base_x + dx, "y": y_step, "z": z_out, "type": STONE})
            blocks.append({"x": base_x + dx, "y": y_step - 1, "z": z_out, "type": COBBLESTONE})
    
    # ============================================================
    # 3. SUELO INTERIOR (patron de pasillos)
    # ============================================================
    for dx in range(wide):
        for dz in range(long):
            # Pasillo central = PLANKS, naves laterales = STONE alternado
            if 10 <= dx < wide - 10:
                if (dx + dz) % 4 == 0:
                    blocks.append({"x": base_x + dx, "y": base_y, "z": base_z + dz, "type": COBBLESTONE})
                else:
                    blocks.append({"x": base_x + dx, "y": base_y, "z": base_z + dz, "type": PLANKS})
            else:
                blocks.append({"x": base_x + dx, "y": base_y, "z": base_z + dz, "type": STONE})
    
    # ============================================================
    # 4. MUROS EXTERIORES PRINCIPALES
    # ============================================================
    # Muros frontales y traseros
    for dx in range(wide):
        for dz in [0, long - 1]:
            for dy in range(1, aisle_h):
                blocks.append({"x": base_x + dx, "y": base_y + dy, "z": base_z + dz, "type": STONE})
    # Muros laterales
    for dz in range(long):
        for dx in [0, wide - 1]:
            for dy in range(1, aisle_h):
                blocks.append({"x": base_x + dx, "y": base_y + dy, "z": base_z + dz, "type": STONE})
    
    # ============================================================
    # 5. NAVES LATERALES - arcadas interiores (pilares)
    # ============================================================
    left_aisle_x = 9
    right_aisle_x = wide - 10
    for dz in range(1, long - 1):
        for dy in range(1, aisle_h):
            blocks.append({"x": base_x + left_aisle_x, "y": base_y + dy, "z": base_z + dz, "type": STONE})
            blocks.append({"x": base_x + right_aisle_x, "y": base_y + dy, "z": base_z + dz, "type": STONE})
    
    # ============================================================
    # 6. COLUMNAS CENTRALES (arbotantes interiores)
    # ============================================================
    col_dz = [10, 18, 26, 34, 42]
    col_dx = [left_aisle_x + 2, right_aisle_x - 2]
    for dz in col_dz:
        for dx in col_dx:
            for dy in range(1, nave_h):
                blocks.append({"x": base_x + dx, "y": base_y + dy, "z": base_z + dz, "type": COBBLESTONE})
            # Capiteles decorados
            for ox, oz in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                blocks.append({"x": base_x + dx + ox, "y": base_y + nave_h - 1, "z": base_z + dz + oz, "type": COBBLESTONE})
    
    # ============================================================
    # 7. CONTRAFUERTES EXTERIORES (elemento gotico clave)
    # ============================================================
    for dz in range(3, long - 3, 6):
        # Contrafuertes laterales izquierdos
        for dx_off in range(1, 3):
            for dy in range(1, nave_h + 4):
                blocks.append({"x": base_x - dx_off, "y": base_y + dy, "z": base_z + dz, "type": COBBLESTONE})
            for dy in range(nave_h + 4, nave_h + 8):
                blocks.append({"x": base_x - 1, "y": base_y + dy, "z": base_z + dz, "type": COBBLESTONE})
        # Pinaculo izquierdo
        for dy in range(nave_h + 8, nave_h + 13):
            blocks.append({"x": base_x - 1, "y": base_y + dy, "z": base_z + dz, "type": STONE})
        
        # Contrafuertes laterales derechos
        for dx_off in range(1, 3):
            for dy in range(1, nave_h + 4):
                blocks.append({"x": base_x + wide - 1 + dx_off, "y": base_y + dy, "z": base_z + dz, "type": COBBLESTONE})
            for dy in range(nave_h + 4, nave_h + 8):
                blocks.append({"x": base_x + wide, "y": base_y + dy, "z": base_z + dz, "type": COBBLESTONE})
        # Pinaculo derecho
        for dy in range(nave_h + 8, nave_h + 13):
            blocks.append({"x": base_x + wide, "y": base_y + dy, "z": base_z + dz, "type": STONE})
    
    # ============================================================
    # 8. ARCBOTANTES (arcos exteriores de soporte gotico)
    # ============================================================
    for dz in range(6, long - 6, 6):
        # Arcbotante izquierdo
        apex_x = base_x - 3
        start_x = base_x
        for t in range(0, 10):
            progress = t / 9.0
            x = int(start_x + (apex_x - start_x) * progress)
            y = int(base_y + nave_h - 2 + math.sin(progress * math.pi) * 5)
            blocks.append({"x": x, "y": y, "z": base_z + dz, "type": COBBLESTONE})
            blocks.append({"x": x, "y": y, "z": base_z + dz + 1, "type": COBBLESTONE})
        
        # Arcbotante derecho
        apex_x = base_x + wide + 2
        start_x = base_x + wide - 1
        for t in range(0, 10):
            progress = t / 9.0
            x = int(start_x + (apex_x - start_x) * progress)
            y = int(base_y + nave_h - 2 + math.sin(progress * math.pi) * 5)
            blocks.append({"x": x, "y": y, "z": base_z + dz, "type": COBBLESTONE})
            blocks.append({"x": x, "y": y, "z": base_z + dz + 1, "type": COBBLESTONE})
    
    # ============================================================
    # 9. TEJADOS NAVES LATERALES (inclinados con hojas + cobblestone)
    # ============================================================
    for dz in range(1, long - 1):
        for i, dx in enumerate(range(left_aisle_x)):
            y = aisle_h + i
            mat = COBBLESTONE if i == 0 or i == left_aisle_x - 1 else LEAVES
            blocks.append({"x": base_x + dx, "y": base_y + y, "z": base_z + dz, "type": mat})
            blocks.append({"x": base_x + (wide - 1 - dx), "y": base_y + y, "z": base_z + dz, "type": mat})
    
    # ============================================================
    # 10. CUBIERTA NAVE CENTRAL (boveda ojival)
    # ============================================================
    center_start = left_aisle_x + 1
    center_end = right_aisle_x
    center_w = center_end - center_start
    mid = center_w // 2
    for dz in range(1, long - 1):
        for i in range(mid + 1):
            y = nave_h + i
            mat = COBBLESTONE if i == mid else LEAVES
            blocks.append({"x": base_x + center_start + i, "y": base_y + y, "z": base_z + dz, "type": mat})
            blocks.append({"x": base_x + center_end - 1 - i, "y": base_y + y, "z": base_z + dz, "type": mat})
    
    # ============================================================
    # 11. TORRES FRONTALES CON AGUJAS DETALLADAS
    # ============================================================
    tower_w = 7
    tower_h = 36
    for tower in [0, wide - tower_w]:
        for dx in range(tower_w):
            for dz in range(tower_w):
                for dy in range(1, tower_h):
                    blocks.append({"x": base_x + tower + dx, "y": base_y + dy, "z": base_z + dz, "type": STONE})
        
        # Cornisa decorativa
        for dx in range(-1, tower_w + 1):
            for dz in range(-1, tower_w + 1):
                if dx == -1 or dx == tower_w or dz == -1 or dz == tower_w:
                    blocks.append({"x": base_x + tower + dx, "y": base_y + tower_h, "z": base_z + dz, "type": COBBLESTONE})
        
        # Agujas con base mas ancha
        for i in range(12):
            cx = base_x + tower + tower_w // 2
            cz = base_z + tower_w // 2
            blocks.append({"x": cx, "y": base_y + tower_h + 1 + i, "z": cz, "type": COBBLESTONE})
            if i < 5:
                for ox, oz in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
                    blocks.append({"x": cx + ox, "y": base_y + tower_h + 1 + i, "z": cz + oz, "type": STONE})
            if i < 2:
                for ox, oz in [(1, 1), (-1, -1), (1, -1), (-1, 1)]:
                    blocks.append({"x": cx + ox, "y": base_y + tower_h + 1 + i, "z": cz + oz, "type": STONE})
    
    # ============================================================
    # 12. TORRE CENTRAL / CIMBORRIO sobre el crucero
    # ============================================================
    cimborio_x = wide // 2 - 3
    cimborio_z = long // 2 - 3
    cimborio_w = 7
    cimborio_h = nave_h + 12
    
    for dx in range(cimborio_w):
        for dz in range(cimborio_w):
            for dy in range(nave_h, cimborio_h):
                blocks.append({"x": base_x + cimborio_x + dx, "y": base_y + dy, "z": base_z + cimborio_z + dz, "type": COBBLESTONE})
    
    # Agujas del cimborrio
    for i in range(8):
        cx = base_x + cimborio_x + cimborio_w // 2
        cz = base_z + cimborio_z + cimborio_w // 2
        blocks.append({"x": cx, "y": base_y + cimborio_h + i, "z": cz, "type": STONE})
        if i < 3:
            for ox, oz in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
                blocks.append({"x": cx + ox, "y": base_y + cimborio_h + i, "z": cz + oz, "type": COBBLESTONE})
    
    # ============================================================
    # 13. CRUCERO (tejado elevado del transepto)
    # ============================================================
    transept_z = long // 2
    transept_w = 16
    half = transept_w // 2
    center_x_mid = wide // 2
    for dx in range(center_x_mid - half, center_x_mid + half + 1):
        for dz in range(transept_z - 8, transept_z + 9):
            h = nave_h if center_start <= dx < center_end else aisle_h
            for i in range(4):
                mat = COBBLESTONE if i == 3 else LEAVES
                blocks.append({"x": base_x + dx, "y": base_y + h + i, "z": base_z + dz, "type": mat})
    
    # ============================================================
    # 14. CAPILLAS RADIANTES (abside trasero)
    # ============================================================
    for cap in range(3):
        cap_z = long - 2 + cap * 4
        cap_rad = 3 - cap
        cap_cx = wide // 2
        for dx in range(cap_cx - cap_rad - 2, cap_cx + cap_rad + 3):
            for dz in range(3):
                if dist(dx, dz, cap_cx, 0) <= cap_rad + 2:
                    for dy in range(1, aisle_h - 2):
                        blocks.append({"x": base_x + dx, "y": base_y + dy, "z": base_z + cap_z + dz, "type": STONE})
                    # Techos de capillas
                    for i in range(2):
                        y = aisle_h - 2 + i
                        if dist(dx, dz, cap_cx, 0) <= cap_rad + 2 - i:
                            blocks.append({"x": base_x + dx, "y": base_y + y, "z": base_z + cap_z + dz, "type": LEAVES})
    
    # ============================================================
    # 15. ALTAR ELEVADO CON RETABLO
    # ============================================================
    altar_z_start = long - 8
    for dx in range(10, wide - 10):
        for dz in range(altar_z_start, long - 2):
            # Plataforma
            for dy in range(1, 4):
                blocks.append({"x": base_x + dx, "y": base_y + dy, "z": base_z + dz, "type": PLANKS})
    
    # Retablo (muro trasero del altar)
    for dx in range(10, wide - 10):
        for dy in range(4, 10):
            blocks.append({"x": base_x + dx, "y": base_y + dy, "z": base_z + long - 3, "type": COBBLESTONE})
    
    # ============================================================
    # 16. PORTADA PRINCIPAL (fachada detallada)
    # ============================================================
    # Marcos de la portada
    for dx in range(7, wide - 7):
        for dy in range(1, 14):
            blocks.append({"x": base_x + dx, "y": base_y + dy, "z": base_z, "type": COBBLESTONE})
    
    # Arcos de la portada (tres arcos: central grande + dos laterales)
    # Arco central
    for i in range(8):
        angle = math.pi * (i / 7.0)
        arc_x = wide // 2 + int(math.cos(angle) * 5)
        arc_y = 4 + int(math.sin(angle) * 6)
        blocks.append({"x": base_x + arc_x, "y": base_y + arc_y, "z": base_z, "type": COBBLESTONE})
        blocks.append({"x": base_x + arc_x + 1, "y": base_y + arc_y, "z": base_z, "type": COBBLESTONE})
    
    # Arcos laterales
    for side in [-1, 1]:
        center_arc_x = wide // 2 + side * 9
        for i in range(6):
            angle = math.pi * (i / 5.0)
            arc_x = center_arc_x + int(math.cos(angle) * 3)
            arc_y = 3 + int(math.sin(angle) * 4)
            blocks.append({"x": base_x + arc_x, "y": base_y + arc_y, "z": base_z, "type": COBBLESTONE})
    
    # ============================================================
    # 17. ROSETON CIRCULAR en fachada principal
    # ============================================================
    roseton_cx = wide // 2
    roseton_cy = 10
    roseton_r = 5
    roseton_z = base_z
    for dx in range(-roseton_r, roseton_r + 1):
        for dy in range(-roseton_r, roseton_r + 1):
            d = math.sqrt(dx ** 2 + dy ** 2)
            if d <= roseton_r:
                # Marco del roseton = COBBLESTONE, interior = AIR (hueco)
                if d > roseton_r - 1.5:
                    blocks.append({"x": base_x + roseton_cx + dx, "y": base_y + roseton_cy + dy, "z": roseton_z, "type": COBBLESTONE})
    
    # ============================================================
    # 18. VENTANAS CON ARCO APUNTADO (clerestorio y laterales)
    # ============================================================
    air = []
    
    # Ventanas altas nave central (clerestorio) - arco apuntado
    for dz in range(6, long - 6, 7):
        for dx in [left_aisle_x + 1, right_aisle_x - 1]:
            # Hueco base
            for dy in range(aisle_h + 2, nave_h):
                air.append({"x": base_x + dx, "y": base_y + dy, "z": base_z + dz, "type": AIR})
            # Añadir arco apuntado (triangular superior)
            for i in range(3):
                air.append({"x": base_x + dx, "y": base_y + nave_h + i, "z": base_z + dz, "type": AIR})
                air.append({"x": base_x + dx - 1, "y": base_y + nave_h + i, "z": base_z + dz, "type": AIR})
                air.append({"x": base_x + dx + 1, "y": base_y + nave_h + i, "z": base_z + dz, "type": AIR})
    
    # Ventanas naves laterales (arco de medio punto)
    for dz in range(5, long - 5, 6):
        for side in [0, wide - 1]:
            for dy in range(3, aisle_h - 1):
                air.append({"x": base_x + side, "y": base_y + dy, "z": base_z + dz, "type": AIR})
            # Arco superior
            for i in range(3):
                air.append({"x": base_x + side, "y": base_y + aisle_h - 1 + i, "z": base_z + dz, "type": AIR})
                air.append({"x": base_x + side, "y": base_y + aisle_h - 1 + i, "z": base_z + dz - 1, "type": AIR})
                air.append({"x": base_x + side, "y": base_y + aisle_h - 1 + i, "z": base_z + dz + 1, "type": AIR})
    
    # Gran portal (entrada principal)
    for dx in range(8, wide - 8):
        for dy in range(3, 14):
            air.append({"x": base_x + dx, "y": base_y + dy, "z": base_z, "type": AIR})
            air.append({"x": base_x + dx, "y": base_y + dy, "z": base_z + 1, "type": AIR})
    
    # Roseton (interior circular)
    for dx in range(-roseton_r + 1, roseton_r):
        for dy in range(-roseton_r + 1, roseton_r):
            if math.sqrt(dx ** 2 + dy ** 2) < roseton_r - 1.5:
                air.append({"x": base_x + roseton_cx + dx, "y": base_y + roseton_cy + dy, "z": roseton_z, "type": AIR})
    
    # Interior transitable (nave central y laterales)
    for dx in range(1, wide - 1):
        for dz in range(1, long - 1):
            for dy in range(1, aisle_h):
                if dx not in [left_aisle_x, right_aisle_x] and dz not in col_dz:
                    air.append({"x": base_x + dx, "y": base_y + dy, "z": base_z + dz, "type": AIR})
            if center_start <= dx < center_end:
                for dy in range(aisle_h, nave_h):
                    air.append({"x": base_x + dx, "y": base_y + dy, "z": base_z + dz, "type": AIR})
    
    # Hueco para el cimborrio (interior)
    for dx in range(cimborio_w - 2):
        for dz in range(cimborio_w - 2):
            for dy in range(nave_h, cimborio_h - 2):
                air.append({"x": base_x + cimborio_x + 1 + dx, "y": base_y + dy, "z": base_z + cimborio_z + 1 + dz, "type": AIR})
    
    # Interior de capillas radiantes
    for cap in range(3):
        cap_z = long - 2 + cap * 4
        cap_rad = 3 - cap
        cap_cx = wide // 2
        for dx in range(cap_cx - cap_rad, cap_cx + cap_rad + 1):
            for dz in range(2):
                if dist(dx, dz, cap_cx, 0) < cap_rad:
                    for dy in range(1, aisle_h - 3):
                        air.append({"x": base_x + dx, "y": base_y + dy, "z": base_z + cap_z + dz, "type": AIR})
    
    # ============================================================
    # 19. GARgOLAS (salientes decorativos en los contrafuertes)
    # ============================================================
    for dz in [15, 30, 40]:
        # Gargola izquierda
        blocks.append({"x": base_x - 3, "y": base_y + nave_h - 1, "z": base_z + dz, "type": COBBLESTONE})
        blocks.append({"x": base_x - 4, "y": base_y + nave_h - 2, "z": base_z + dz, "type": COBBLESTONE})
        blocks.append({"x": base_x - 4, "y": base_y + nave_h - 3, "z": base_z + dz, "type": COBBLESTONE})
        
        # Gargola derecha
        blocks.append({"x": base_x + wide + 2, "y": base_y + nave_h - 1, "z": base_z + dz, "type": COBBLESTONE})
        blocks.append({"x": base_x + wide + 3, "y": base_y + nave_h - 2, "z": base_z + dz, "type": COBBLESTONE})
        blocks.append({"x": base_x + wide + 3, "y": base_y + nave_h - 3, "z": base_z + dz, "type": COBBLESTONE})
    
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
    # Permitir coordenadas manual: python build_gothic_cathedral.py 80 -49 30
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
        
        # Centrar la catedral cerca del jugador
        base_x = px - 15  # centrar los 31 de ancho
        base_z = pz - 5   # un poco al sur para ver la fachada
        print(f"Catedral desde ({base_x}, {base_z}), y={base_y}")
    
    blocks = build_cathedral_detailed(base_x, base_z, base_y)
    print(f"\nColocando {len(blocks)} bloques...")
    
    BATCH = 400
    ok_total = 0
    for i in range(0, len(blocks), BATCH):
        batch = blocks[i:i + BATCH]
        ok = send_batch(batch)
        ok_total += ok
        time.sleep(0.05)
    
    print(f"\nCatedral gotica DETALLADA construida en ({base_x}, {base_y}, {base_z})!")
    print(f"{ok_total}/{len(blocks)} bloques colocados")
    print(f"55x31 de base | 48 bloques de alto en torres | con contrafuertes, arcbotantes, cimborrio y capillas radiantes")
