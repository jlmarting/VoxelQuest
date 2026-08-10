"""
Construye una piramide de 50x50 con nucleo luminoso concentrica.
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


def build_pyramid(cx, cz, ground, base=50):
    blocks = []

    max_layer = base // 2
    # Columna central de glowstone desde la base hasta arriba
    for y in range(ground, ground + max_layer + 1):
        blocks.append({"x": cx, "y": y, "z": cz, "type": GLOWSTONE})

    for layer in range(max_layer + 1):
        size = base - 2 * layer
        y = ground + layer
        hw = size // 2
        x1, x2 = cx - hw, cx + hw
        z1, z2 = cz - hw, cz + hw

        if size <= 2:
            # Capa superior: solo el centro (ya puesto) mas glowstone extra
            for x in range(x1, x2 + 1):
                for z in range(z1, z2 + 1):
                    if (x, z) != (cx, cz):
                        blocks.append({"x": x, "y": y, "z": z, "type": GLOWSTONE})
            continue

        # Anillo perimetral de piedra
        for x in range(x1, x2 + 1):
            blocks.append({"x": x, "y": y, "z": z1, "type": STONE})
            blocks.append({"x": x, "y": y, "z": z2, "type": STONE})
        for z in range(z1 + 1, z2):
            blocks.append({"x": x1, "y": y, "z": z, "type": STONE})
            blocks.append({"x": x2, "y": y, "z": z, "type": STONE})

        # Relleno interior con glowstone cada 3 capas
        fill_type = GLOWSTONE if layer % 3 == 0 else STONE
        for x in range(x1 + 1, x2):
            for z in range(z1 + 1, z2):
                blocks.append({"x": x, "y": y, "z": z, "type": fill_type})

    return blocks


if __name__ == "__main__":
    players = mcp("list_players", {})
    p = players.get("players", [{}])[0] if isinstance(players, dict) else {}
    px, pz = int(p.get("x", 0)), int(p.get("z", 0))
    print(f"Jugador en ({px}, {pz})")

    ground = detect_ground(px, pz)
    print(f"Suelo en y={ground}")

    # Piramide centrada justo donde esta el jugador
    cx, cz = px, pz
    print(f"Piramide centrada en ({cx}, {cz})")

    blocks = build_pyramid(cx, cz, ground, base=50)
    print(f"\nColocando {len(blocks)} bloques...")

    BATCH = 400
    ok_total = 0
    for i in range(0, len(blocks), BATCH):
        batch = blocks[i:i + BATCH]
        ok = send_batch(batch)
        ok_total += ok
        time.sleep(0.05)

    print(f"\nPiramide construida en ({cx}, {ground}, {cz})!")
    print(f"{ok_total}/{len(blocks)} bloques colocados")
    print(f"Base 50x50 | {50//2 + 1} capas concentricas | nucleo y capas de glowstone")
