"""
Construye un castillo con murallas, torres y torreon.
"""

import json, urllib.request, time, sys

URL = "http://localhost:9000/mcp"
_RPC = [0]

AIR, GRASS, DIRT, STONE, WOOD, LEAVES, SAND, WATER, COBBLESTONE, PLANKS, BEDROCK = range(11)
GLOWSTONE = 11


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
    return 1


def send_batch(blocks):
    res = mcp("apply_blocks", {"blocks": blocks}, timeout=120)
    if isinstance(res, dict) and "error" in res:
        return 0
    return len(blocks)


def build_castle(cx, cz, g):
    blocks = []

    # Dimensiones
    wall_w, wall_d = 30, 20
    wall_h = 6
    tower_h = 10
    keep_w, keep_d, keep_h = 10, 8, 8

    x1, x2 = cx - wall_w // 2, cx + wall_w // 2
    z1, z2 = cz - wall_d // 2, cz + wall_d // 2

    # ---- Suelo del patio interior ----
    for x in range(x1 + 1, x2):
        for z in range(z1 + 1, z2):
            blocks.append({"x": x, "y": g, "z": z, "type": PLANKS})

    # ---- Murallas exteriores con almenas ----
    for y in range(g + 1, g + wall_h):
        for x in range(x1, x2 + 1):
            blocks.append({"x": x, "y": y, "z": z1, "type": STONE})
            blocks.append({"x": x, "y": y, "z": z2, "type": STONE})
    for y in range(g + 1, g + wall_h):
        for z in range(z1 + 1, z2):
            blocks.append({"x": x1, "y": y, "z": z, "type": STONE})
            blocks.append({"x": x2, "y": y, "z": z, "type": STONE})

    # Almenas (piedra alternada en la cima)
    for x in range(x1, x2 + 1, 2):
        blocks.append({"x": x, "y": g + wall_h, "z": z1, "type": STONE})
        blocks.append({"x": x, "y": g + wall_h, "z": z2, "type": STONE})
    for z in range(z1 + 1, z2, 2):
        blocks.append({"x": x1, "y": g + wall_h, "z": z, "type": STONE})
        blocks.append({"x": x2, "y": g + wall_h, "z": z, "type": STONE})

    # ---- Puerta de entrada (sur, lado z2) ----
    gate_x1, gate_x2 = cx - 2, cx + 2
    for x in range(gate_x1, gate_x2 + 1):
        for y in range(g + 1, g + 4):
            blocks.append({"x": x, "y": y, "z": z2, "type": AIR})
    # Arco sobre la puerta
    for x in range(gate_x1 - 1, gate_x2 + 2):
        blocks.append({"x": x, "y": g + 4, "z": z2, "type": COBBLESTONE})
    blocks.append({"x": gate_x1 - 1, "y": g + 3, "z": z2, "type": COBBLESTONE})
    blocks.append({"x": gate_x2 + 1, "y": g + 3, "z": z2, "type": COBBLESTONE})

    # ---- Torres esquineras (circulares cuadradas) ----
    tower_pos = [(x1, z1), (x2, z1), (x1, z2), (x2, z2)]
    for tx, tz in tower_pos:
        tr = 3
        for dx in range(-tr, tr + 1):
            for dz in range(-tr, tr + 1):
                if dx * dx + dz * dz <= tr * tr + 1:
                    for y in range(g + 1, g + tower_h):
                        blocks.append({"x": tx + dx, "y": y, "z": tz + dz, "type": STONE})
                    # Techo conico
                    for i in range(3):
                        r = tr - i
                        for dx2 in range(-r, r + 1):
                            for dz2 in range(-r, r + 1):
                                if dx2 * dx2 + dz2 * dz2 <= r * r + 1:
                                    blocks.append({"x": tx + dx2, "y": g + tower_h + i, "z": tz + dz2, "type": COBBLESTONE})
                    # Punta
                    blocks.append({"x": tx, "y": g + tower_h + 3, "z": tz, "type": STONE})

    # ---- Torreon central (keep) ----
    kx1, kx2 = cx - keep_w // 2, cx + keep_w // 2
    kz1, kz2 = cz - keep_d // 2, cz + keep_d // 2

    # Suelo del torreon
    for x in range(kx1, kx2 + 1):
        for z in range(kz1, kz2 + 1):
            blocks.append({"x": x, "y": g, "z": z, "type": PLANKS})

    # Paredes
    for y in range(g + 1, g + keep_h):
        for x in range(kx1, kx2 + 1):
            blocks.append({"x": x, "y": y, "z": kz1, "type": COBBLESTONE})
            blocks.append({"x": x, "y": y, "z": kz2, "type": COBBLESTONE})
        for z in range(kz1 + 1, kz2):
            blocks.append({"x": kx1, "y": y, "z": z, "type": COBBLESTONE})
            blocks.append({"x": kx2, "y": y, "z": z, "type": COBBLESTONE})

    # Techo del torreon
    for x in range(kx1, kx2 + 1):
        for z in range(kz1, kz2 + 1):
            blocks.append({"x": x, "y": g + keep_h, "z": z, "type": WOOD})

    # Almenas del torreon
    for x in range(kx1, kx2 + 1, 2):
        blocks.append({"x": x, "y": g + keep_h + 1, "z": kz1, "type": STONE})
        blocks.append({"x": x, "y": g + keep_h + 1, "z": kz2, "type": STONE})
    for z in range(kz1 + 1, kz2, 2):
        blocks.append({"x": kx1, "y": g + keep_h + 1, "z": z, "type": STONE})
        blocks.append({"x": kx2, "y": g + keep_h + 1, "z": z, "type": STONE})

    # Puerta del torreon (sur)
    for x in range(cx - 1, cx + 2):
        for y in range(g + 1, g + 3):
            blocks.append({"x": x, "y": y, "z": kz2, "type": AIR})

    # Interior hueco del torreon
    for x in range(kx1 + 1, kx2):
        for y in range(g + 1, g + keep_h):
            for z in range(kz1 + 1, kz2):
                blocks.append({"x": x, "y": y, "z": z, "type": AIR})

    # ---- Interior hueco del patio (aire sobre el suelo) ----
    for x in range(x1 + 1, x2):
        for y in range(g + 1, g + wall_h):
            for z in range(z1 + 1, z2):
                blocks.append({"x": x, "y": y, "z": z, "type": AIR})

    # Apertura en torres (puertas)
    for tx, tz in tower_pos:
        for y in range(g + 1, g + 3):
            blocks.append({"x": tx, "y": y, "z": tz, "type": AIR})

    # Resolver prioridad: aire gana
    block_map = {}
    for b in blocks:
        block_map[(b["x"], b["y"], b["z"])] = b["type"]
    for b in [b for b in blocks if b["type"] == AIR]:
        block_map[(b["x"], b["y"], b["z"])] = AIR

    return [{"x": k[0], "y": k[1], "z": k[2], "type": v} for k, v in block_map.items()]


if __name__ == "__main__":
    players = mcp("list_players", {})
    p = players.get("players", [{}])[0] if isinstance(players, dict) else {}
    px, pz = int(p.get("x", 0)), int(p.get("z", 0))
    print(f"Jugador en ({px}, {pz})")

    g = detect_ground(px, pz)
    print(f"Suelo en y={g}")

    cx, cz = px + 25, pz
    print(f"Castillo centrado en ({cx}, {cz})")

    blocks = build_castle(cx, cz, g)
    print(f"\nColocando {len(blocks)} bloques...")

    BATCH = 400
    ok_total = 0
    for i in range(0, len(blocks), BATCH):
        batch = blocks[i:i + BATCH]
        ok = send_batch(batch)
        ok_total += ok
        time.sleep(0.05)

    print(f"\nCastillo construido en ({cx}, {g}, {cz})!")
    print(f"{ok_total}/{len(blocks)} bloques colocados")
    print(f"Murallas 30x20 | 4 torres con techo conico | torreon central | patio interior")
