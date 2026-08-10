"""
Construye un pueblo con 5 casas cerca del jugador.
Usa MCP JSON-RPC contra el servidor Python.
Detecta dinamicamente la altura del suelo.
"""

import json, os, urllib.request, time, sys

URL = "http://localhost:9000/mcp"
API_KEY = os.environ.get("MCP_API_KEY", "")
_RPC = [0]

AIR, GRASS, DIRT, STONE, WOOD, LEAVES, SAND, WATER, COBBLESTONE, PLANKS, BEDROCK = range(11)

def mcp(method, params, timeout=15):
    _RPC[0] += 1
    data = json.dumps({
        "jsonrpc": "2.0", "id": _RPC[0],
        "method": "tools/call",
        "params": {"name": method, "arguments": params}
    }).encode()
    headers = {"Content-Type": "application/json"}
    if API_KEY:
        headers["X-API-Key"] = API_KEY
    req = urllib.request.Request(URL, data=data, headers=headers)
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


def break_batch(blocks):
    air = [{"x": b["x"], "y": b["y"], "z": b["z"], "type": AIR} for b in blocks]
    res = mcp("apply_blocks", {"blocks": air}, timeout=120)
    if isinstance(res, dict) and "error" in res:
        return 0
    return len(air)


def build_house(cx, cz, ground):
    hw, hd = 3, 3
    x1, x2 = cx - hw, cx + hw
    z1, z2 = cz - hd, cz + hd
    wall_low = ground + 1
    wall_high = ground + 2
    roof_y = ground + 3

    blocks, air = [], []

    for x in range(x1, x2 + 1):
        for z in range(z1, z2 + 1):
            blocks.append({"x": x, "y": ground, "z": z, "type": PLANKS})

    for y in range(wall_low, wall_high + 1):
        for x in range(x1, x2 + 1):
            for z in range(z1, z2 + 1):
                if x1 < x < x2 and z1 < z < z2:
                    continue
                if z == z1 and x == cx:
                    continue
                if z in (z1, z2) and y == wall_high and x in (cx - 1, cx + 1):
                    continue
                if x in (x1, x2) and y == wall_high and z in (cz - 1, cz + 1):
                    continue
                blocks.append({"x": x, "y": y, "z": z, "type": COBBLESTONE})

    overhang = 1
    for x in range(x1 - overhang, x2 + overhang + 1):
        for z in range(z1 - overhang, z2 + overhang + 1):
            blocks.append({"x": x, "y": roof_y, "z": z, "type": WOOD})

    for x in range(x1 + 1, x2):
        for z in range(z1 + 1, z2):
            for y in range(wall_low, roof_y):
                air.append({"x": x, "y": y, "z": z, "type": AIR})
    air.append({"x": cx, "y": wall_low, "z": z1, "type": AIR})
    air.append({"x": cx, "y": wall_high, "z": z1, "type": AIR})

    blocks.append({"x": cx, "y": ground, "z": z1 - 1, "type": PLANKS})

    block_map = {}
    for b in blocks:
        block_map[(b["x"], b["y"], b["z"])] = b["type"]
    for b in air:
        block_map[(b["x"], b["y"], b["z"])] = AIR

    return [{"x": k[0], "y": k[1], "z": k[2], "type": v} for k, v in block_map.items()]


def build_path_corner(ax, az, bx, bz, ground):
    """Camino en L desde (ax,az) hasta (bx,bz) con 3 de ancho."""
    path = []
    corners = []
    mx = ax
    for step in range(2):
        if step == 0:
            tx, tz = mx, bz
        else:
            tx, tz = bx, bz
        x, z = ax, az
        dx = 1 if tx >= ax else -1
        while x != tx:
            for w in range(-1, 2):
                corners.append((x + w, z))
            x += dx
        dz = 1 if tz >= az else -1
        while z != tz:
            for w in range(-1, 2):
                corners.append((x + w, z))
            z += dz
        corners.append((x, z))
    for (x, z) in set(corners):
        path.append({"x": x, "y": ground, "z": z, "type": PLANKS})
    return path


def clear_site(cx, cz, ground):
    r = 5
    air_blocks = []
    for x in range(cx - r, cx + r + 1):
        for z in range(cz - r, cz + r + 1):
            for y in range(ground - 1, ground + 5):
                air_blocks.append({"x": x, "y": y, "z": z})
    break_batch(air_blocks)


def build_plaza(cx, cz, ground):
    blocks = []
    r = 3
    for x in range(cx - r, cx + r + 1):
        for z in range(cz - r, cz + r + 1):
            blocks.append({"x": x, "y": ground, "z": z, "type": STONE})
    return blocks


def build_lamp(cx, cz, ground):
    blocks = []
    for h in range(1, 5):
        blocks.append({"x": cx, "y": ground + h, "z": cz, "type": WOOD})
    blocks.append({"x": cx, "y": ground + 4, "z": cz, "type": STONE})
    return blocks


if __name__ == "__main__":
    # Detectar posicion del jugador
    players = mcp("list_players", {})
    p = players.get("players", [{}])[0] if isinstance(players, dict) else {}
    px, pz = int(p.get("x", 0)), int(p.get("z", 0))
    print(f"Jugador en ({px}, {pz})")

    ground = detect_ground(px, pz)
    print(f"Suelo en y={ground}")

    CX, CZ = px, pz
    OFFSET = 16

    HOUSES = [
        (CX, CZ - OFFSET),   # Norte
        (CX + OFFSET, CZ),   # Este
        (CX, CZ + OFFSET),   # Sur
        (CX - OFFSET, CZ),   # Oeste
    ]

    if "--clear" in sys.argv:
        print("\nLimpiando solares...")
        for i, (cx, cz) in enumerate(HOUSES):
            print(f"  Solar {i+1} ({cx},{cz})...")
            clear_site(cx, cz, ground)
        clear_site(CX, CZ, ground)
        time.sleep(0.2)

    print("\nConstruyendo 4 casas...")
    all_blocks = []
    for i, (cx, cz) in enumerate(HOUSES):
        house = build_house(cx, cz, ground)
        all_blocks.extend(house)
        print(f"  Casa {i+1} ({cx},{cz}): {len(house)} bloques")

    print("\nConstruyendo caminos...")
    for i, (cx, cz) in enumerate(HOUSES):
        path = build_path_corner(cx, cz, CX, CZ, ground)
        all_blocks.extend(path)
        print(f"  Camino {i+1}: {len(path)} bloques")

    print("\nConstruyendo plaza central...")
    plaza = build_plaza(CX, CZ, ground)
    all_blocks.extend(plaza)
    print(f"  Plaza: {len(plaza)} bloques")

    print("\nColocando faroles...")
    faroles = []
    for dx, dz in [(-2, 2), (2, 2), (-2, -2), (2, -2)]:
        faroles.extend(build_lamp(CX + dx, CZ + dz, ground))
    all_blocks.extend(faroles)
    print(f"  Faroles: {len(faroles)} bloques")

    print(f"\nColocando {len(all_blocks)} bloques...")
    BATCH = 400
    ok_total = 0
    for i in range(0, len(all_blocks), BATCH):
        batch = all_blocks[i:i + BATCH]
        ok = send_batch(batch)
        ok_total += ok
        time.sleep(0.05)

    print(f"\nPueblo construido en ({CX}, {CZ})!")
    print(f"{ok_total}/{len(all_blocks)} bloques colocados")
    print(f"4 casas | plaza | caminos | faroles")
