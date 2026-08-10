"""
Construye una casa habitable cerca del spawn.
Usa MCP JSON-RPC contra el servidor Python.
"""

import json, os, urllib.request, time

URL = "http://localhost:9000/mcp"
API_KEY = os.environ.get("MCP_API_KEY", "")
_RPC = [0]

# Constantes de bloques
AIR, GRASS, DIRT, STONE, WOOD, LEAVES, SAND, WATER, COBBLESTONE, PLANKS, BEDROCK = range(11)

GROUND = 23  # y del suelo


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
                print(f"  RPC error: {resp['error']}")
                return {"error": resp["error"]}
            content = resp.get("content", [])
            if content and isinstance(content[0], dict) and "text" in content[0]:
                return json.loads(content[0]["text"])
            return resp.get("result", {})
    except Exception as e:
        print(f"  Request error: {e}")
        return {"error": str(e)}


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


def build_house(cx=10, cz=8):
    """cx, cz = centro de la casa"""
    hw, hd = 3, 3  # half-width, half-depth (7x7 exterior)
    x1, x2 = cx - hw, cx + hw
    z1, z2 = cz - hd, cz + hd
    wall_low = GROUND + 1
    wall_high = GROUND + 2
    roof_y = GROUND + 3

    blocks = []
    air = []

    # --- 1. Suelo (PLANKS) ---
    for x in range(x1, x2 + 1):
        for z in range(z1, z2 + 1):
            blocks.append({"x": x, "y": GROUND, "z": z, "type": PLANKS})

    # --- 2. Paredes (COBBLESTONE) ---
    for y in range(wall_low, wall_high + 1):
        for x in range(x1, x2 + 1):
            for z in range(z1, z2 + 1):
                if x1 < x < x2 and z1 < z < z2:
                    continue  # interior hueco
                # Puerta (centro frontal, z=z1)
                if z == z1 and x == cx:
                    continue
                # Ventanas en pared frontal y trasera
                if z in (z1, z2) and y == wall_high and x in (cx - 1, cx + 1):
                    continue
                # Ventanas en paredes laterales
                if x in (x1, x2) and y == wall_high and z in (cz - 1, cz + 1):
                    continue
                blocks.append({"x": x, "y": y, "z": z, "type": COBBLESTONE})

    # --- 3. Techo con voladizo (WOOD) ---
    overhang = 1
    rx1, rx2 = x1 - overhang, x2 + overhang
    rz1, rz2 = z1 - overhang, z2 + overhang
    for x in range(rx1, rx2 + 1):
        for z in range(rz1, rz2 + 1):
            blocks.append({"x": x, "y": roof_y, "z": z, "type": WOOD})

    # --- 4. Aire: interior + puerta ---
    # Interior vacio (hasta roof_y-1, el techo es solido)
    for x in range(x1 + 1, x2):
        for z in range(z1 + 1, z2):
            for y in range(wall_low, roof_y):
                air.append({"x": x, "y": y, "z": z, "type": AIR})
    # Puerta: 2 bloques de alto
    air.append({"x": cx, "y": wall_low, "z": z1, "type": AIR})
    air.append({"x": cx, "y": wall_high, "z": z1, "type": AIR})
    # Escalon exterior
    blocks.append({"x": cx, "y": GROUND, "z": z1 - 1, "type": PLANKS})

    # --- 5. Resolver prioridad: aire gana ---
    block_map = {}
    for b in blocks:
        block_map[(b["x"], b["y"], b["z"])] = b["type"]
    for b in air:
        block_map[(b["x"], b["y"], b["z"])] = AIR

    final = [{"x": k[0], "y": k[1], "z": k[2], "type": v} for k, v in block_map.items()]
    return final


def clear_site(cx=10, cz=8):
    """Limpia el area de construccion"""
    r = 5
    air_blocks = []
    for x in range(cx - r, cx + r + 1):
        for z in range(cz - r, cz + r + 1):
            for y in range(GROUND - 1, GROUND + 5):
                air_blocks.append({"x": x, "y": y, "z": z})
    print(f"Limpiando sitio ({cx - r},{cz - r})–({cx + r},{cz + r})...")
    ok = break_batch(air_blocks)
    print(f"Limpios ~{ok} bloques")


if __name__ == "__main__":
    import sys
    # Uso: python3 build_house.py [cx cz] [--clear]
    cx = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].lstrip('-').isdigit() else 10
    cz = int(sys.argv[2]) if len(sys.argv) > 2 and sys.argv[2].lstrip('-').isdigit() else 8

    if "--clear" in sys.argv:
        clear_site(cx, cz)
        time.sleep(0.1)

    final = build_house(cx, cz)
    print(f"Total bloques a colocar: {len(final)}")

    BATCH = 400
    ok_total = 0
    for i in range(0, len(final), BATCH):
        batch = final[i:i + BATCH]
        print(f"Lote {i // BATCH + 1}/{(len(final) - 1) // BATCH + 1} ({len(batch)} bloques)...")
        ok = send_batch(batch)
        ok_total += ok
        time.sleep(0.05)

    print(f"\n✅ Casa construida en centro ({cx},{cz})")
    print(f"   Colocados ~{ok_total}/{len(final)} bloques")
    print(f"   Piso: PLANKS | Paredes: COBBLESTONE | Techo: WOOD")
    print(f"   Puerta frontal en ({cx}, {cz - 3}) | Interior hueco 5x5")
