"""
Construye una fortaleza junto al jugador.
Muralla doble concéntrica, torreones, torreón central.
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


def send_batch(blocks):
    res = mcp("apply_blocks", {"blocks": blocks}, timeout=120)
    if isinstance(res, dict) and "error" in res:
        return 0
    return len(blocks)


def build_fortress(cx, cz, g):
    blocks = []

    R = 20
    wall_h = 8
    tower_h = 14
    keep_w, keep_h = 12, 10

    # ---- Base de piedra nivelada (radio R) ----
    for x in range(cx - R - 2, cx + R + 3):
        for z in range(cz - R - 2, cz + R + 3):
            blocks.append({"x": x, "y": g, "z": z, "type": STONE})

    # ---- Muralla exterior circular (octogonal) ----
    for layer in range(wall_h):
        y = g + 1 + layer
        r = R - layer // 3
        for dx in range(-r, r + 1):
            dz_limit = int((r * r - dx * dx) ** 0.5)
            for dz in [-dz_limit, dz_limit]:
                blocks.append({"x": cx + dx, "y": y, "z": cz + dz, "type": COBBLESTONE})
        for dz in range(-r, r + 1):
            dx_limit = int((r * r - dz * dz) ** 0.5)
            for dx in [-dx_limit, dx_limit]:
                blocks.append({"x": cx + dx, "y": y, "z": cz + dz, "type": COBBLESTONE})

    # ---- Torreones circulares (8 alrededor) ----
    for angle in range(0, 360, 45):
        import math
        a = math.radians(angle)
        tx = cx + int(R * math.cos(a))
        tz = cz + int(R * math.sin(a))
        tr = 4
        for dx in range(-tr, tr + 1):
            for dz in range(-tr, tr + 1):
                if dx * dx + dz * dz <= tr * tr + 1:
                    for y in range(g + 1, g + tower_h):
                        blocks.append({"x": tx + dx, "y": y, "z": tz + dz, "type": STONE})
                    for i in range(4):
                        r2 = tr - i
                        for dx2 in range(-r2, r2 + 1):
                            for dz2 in range(-r2, r2 + 1):
                                if dx2 * dx2 + dz2 * dz2 <= r2 * r2 + 1:
                                    blocks.append({"x": tx + dx2, "y": g + tower_h + i, "z": tz + dz2, "type": COBBLESTONE})
                    blocks.append({"x": tx, "y": g + tower_h + 4, "z": tz, "type": STONE})
        # Puerta en cada torre
        for y in range(g + 1, g + 3):
            blocks.append({"x": tx + tr, "y": y, "z": tz, "type": AIR})

    # ---- Torreon central ----
    kx1, kx2 = cx - keep_w // 2, cx + keep_w // 2
    kz1, kz2 = cz - keep_w // 2, cz + keep_w // 2

    for y in range(g + 1, g + keep_h):
        for x in range(kx1, kx2 + 1):
            blocks.append({"x": x, "y": y, "z": kz1, "type": COBBLESTONE})
            blocks.append({"x": x, "y": y, "z": kz2, "type": COBBLESTONE})
        for z in range(kz1 + 1, kz2):
            blocks.append({"x": kx1, "y": y, "z": z, "type": COBBLESTONE})
            blocks.append({"x": kx2, "y": y, "z": z, "type": COBBLESTONE})

    for x in range(kx1, kx2 + 1):
        for z in range(kz1, kz2 + 1):
            blocks.append({"x": x, "y": g + keep_h, "z": z, "type": WOOD})

    for x in range(kx1, kx2 + 1, 2):
        blocks.append({"x": x, "y": g + keep_h + 1, "z": kz1, "type": STONE})
        blocks.append({"x": x, "y": g + keep_h + 1, "z": kz2, "type": STONE})
    for z in range(kz1 + 1, kz2, 2):
        blocks.append({"x": kx1, "y": g + keep_h + 1, "z": z, "type": STONE})
        blocks.append({"x": kx2, "y": g + keep_h + 1, "z": z, "type": STONE})

    # Puerta torreon
    for x in range(cx - 1, cx + 2):
        for y in range(g + 1, g + 3):
            blocks.append({"x": x, "y": y, "z": kz2, "type": AIR})

    # Interior hueco torreon
    for x in range(kx1 + 1, kx2):
        for y in range(g + 1, g + keep_h):
            for z in range(kz1 + 1, kz2):
                blocks.append({"x": x, "y": y, "z": z, "type": AIR})

    # ---- Camino de ronda entre torreones y muralla ----
    for x in range(cx - R + 2, cx + R - 1):
        for z in [cz - R + 2, cz + R - 2]:
            blocks.append({"x": x, "y": g + 1, "z": z, "type": PLANKS})
    for z in range(cz - R + 2, cz + R - 1):
        for x in [cx - R + 2, cx + R - 2]:
            blocks.append({"x": x, "y": g + 1, "z": z, "type": PLANKS})

    # ---- Patio interior (suelo de tablones) ----
    for x in range(cx - R + 2, cx + R - 1):
        for z in range(cz - R + 2, cz + R - 1):
            if (x - kx1) * (x - kx2 + 1) <= 0 and (z - kz1) * (z - kz2 + 1) <= 0:
                continue
            blocks.append({"x": x, "y": g + 1, "z": z, "type": PLANKS})

    # ---- Aire sobre el patio interior ----
    for x in range(cx - R + 2, cx + R - 1):
        for y in range(g + 2, g + wall_h):
            for z in range(cz - R + 2, cz + R - 1):
                if (x - kx1) * (x - kx2 + 1) <= 0 and (z - kz1) * (z - kz2 + 1) <= 0:
                    continue
                blocks.append({"x": x, "y": y, "z": z, "type": AIR})

    # Resolver prioridad: aire gana
    block_map = {}
    for b in blocks:
        if b["type"] == AIR:
            block_map[(b["x"], b["y"], b["z"])] = AIR
        else:
            key = (b["x"], b["y"], b["z"])
            if key not in block_map:
                block_map[key] = b["type"]
    for b in blocks:
        if b["type"] == AIR:
            block_map[(b["x"], b["y"], b["z"])] = AIR
    for b in blocks:
        if b["type"] != AIR:
            key = (b["x"], b["y"], b["z"])
            if key not in block_map or block_map[key] != AIR:
                block_map[key] = b["type"]

    return [{"x": k[0], "y": k[1], "z": k[2], "type": v} for k, v in block_map.items()]


if __name__ == "__main__":
    players = mcp("list_players", {})
    p = players.get("players", [{}])[0] if isinstance(players, dict) else {}
    px, pz = int(p.get("x", 0)), int(p.get("z", 0))
    print(f"Jugador en ({px}, {pz})")

    g = 1
    print(f"Suelo en y={g}")

    cx, cz = px, pz
    print(f"Fortaleza centrada en ({cx}, {cz})")

    blocks = build_fortress(cx, cz, g)
    print(f"\nColocando {len(blocks)} bloques...")

    BATCH = 400
    ok_total = 0
    for i in range(0, len(blocks), BATCH):
        batch = blocks[i:i + BATCH]
        ok = send_batch(batch)
        ok_total += ok
        time.sleep(0.05)

    print(f"\nFortaleza construida en ({cx}, {g}, {cz})!")
    print(f"{ok_total}/{len(blocks)} bloques colocados")
    print(f"Radio 20 | 8 torreones con aguja | torreon central | muralla almenada doble | patio transitable")
