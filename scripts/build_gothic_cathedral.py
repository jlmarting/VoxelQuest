"""
Construye una catedral gotica grande con interior accesible.
Usa apply_blocks via MCP (place_block individual si no existe apply_blocks).
"""

import json, urllib.request, time, sys

URL = "http://localhost:9000/mcp"
_RPC = [0]


def mcp(method, params, timeout=15):
    _RPC[0] += 1
    data = json.dumps({
        "jsonrpc": "2.0",
        "id": _RPC[0],
        "method": "tools/call",
        "params": {"name": method, "arguments": params}
    }).encode()
    req = urllib.request.Request(URL, data=data, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            resp = json.loads(r.read().decode())
            if "error" in resp:
                print(f"  RPC error: {resp['error']}")
                return {"error": resp["error"]}
            content = resp.get("result", {}).get("content", [])
            if content and isinstance(content[0], dict) and "text" in content[0]:
                return json.loads(content[0]["text"])
            return resp.get("result", {})
    except Exception as e:
        print(f"  Request error: {e}")
        return {"error": str(e)}


def send_batch(method, blocks):
    """Envia una tanda intentando apply_blocks primero, fallback a place_block."""
    # apply_blocks no esta expuesto como tool, pero game-client lo entiende via relay.
    # Intentamos build_structure con una estructura custom (no va a funcionar)
    # Mejor usar place_block uno a uno
    ok = 0
    for b in blocks:
        res = mcp("place_block", b)
        if res.get("success") or res.get("position") or "error" not in res:
            ok += 1
    return ok


def build_cathedral(base_x=60, base_z=60):
    base_y = 2
    long = 45
    wide = 25
    nave_h = 22
    aisle_h = 12

    blocks = []

    # Suelo
    for dx in range(wide):
        for dz in range(long):
            blocks.append({"x": base_x + dx, "y": base_y, "z": base_z + dz, "type": 3})

    # Muros exteriores
    for dx in range(wide):
        for dz in [0, long - 1]:
            for dy in range(1, aisle_h):
                blocks.append({"x": base_x + dx, "y": base_y + dy, "z": base_z + dz, "type": 3})
    for dz in range(long):
        for dx in [0, wide - 1]:
            for dy in range(1, aisle_h):
                blocks.append({"x": base_x + dx, "y": base_y + dy, "z": base_z + dz, "type": 3})

    # Naves laterales
    left_aisle_x = 7
    right_aisle_x = wide - 8
    for dz in range(1, long - 1):
        for dy in range(1, aisle_h):
            blocks.append({"x": base_x + left_aisle_x, "y": base_y + dy, "z": base_z + dz, "type": 3})
            blocks.append({"x": base_x + right_aisle_x, "y": base_y + dy, "z": base_z + dz, "type": 3})

    # Columnas centrales
    for dz in [8, 22, 36]:
        for dx in [left_aisle_x + 2, right_aisle_x - 2]:
            for dy in range(1, nave_h):
                blocks.append({"x": base_x + dx, "y": base_y + dy, "z": base_z + dz, "type": 3})

    # Tejados naves laterales
    for dz in range(1, long - 1):
        for i, dx in enumerate(range(left_aisle_x)):
            y = aisle_h + i
            blocks.append({"x": base_x + dx, "y": base_y + y, "z": base_z + dz, "type": 5})
            blocks.append({"x": base_x + (wide - 1 - dx), "y": base_y + y, "z": base_z + dz, "type": 5})

    # Cubierta nave central
    center_start = left_aisle_x + 1
    center_end = right_aisle_x
    center_w = center_end - center_start
    mid = center_w // 2
    for dz in range(1, long - 1):
        for i in range(mid + 1):
            y = nave_h + i
            blocks.append({"x": base_x + center_start + i, "y": base_y + y, "z": base_z + dz, "type": 5})
            blocks.append({"x": base_x + center_end - 1 - i, "y": base_y + y, "z": base_z + dz, "type": 5})

    # Torres frontales
    tower_w = 6
    tower_h = 30
    for tower in [0, wide - tower_w]:
        for dx in range(tower_w):
            for dz in range(tower_w):
                for dy in range(1, tower_h):
                    blocks.append({"x": base_x + tower + dx, "y": base_y + dy, "z": base_z + dz, "type": 3})
        # Agujas
        for i in range(8):
            cx = base_x + tower + tower_w // 2
            cz = base_z + tower_w // 2
            blocks.append({"x": cx, "y": base_y + tower_h + i, "z": cz, "type": 3})
            if i < 3:
                blocks.append({"x": cx + 1, "y": base_y + tower_h + i, "z": cz, "type": 3})
                blocks.append({"x": cx - 1, "y": base_y + tower_h + i, "z": cz, "type": 3})
                blocks.append({"x": cx, "y": base_y + tower_h + i, "z": cz + 1, "type": 3})
                blocks.append({"x": cx, "y": base_y + tower_h + i, "z": cz - 1, "type": 3})

    # Crucero (tejado elevado)
    transept_z = long // 2
    transept_w = 12
    half = transept_w // 2
    center_x_mid = wide // 2
    for dx in range(center_x_mid - half, center_x_mid + half + 1):
        for dz in range(transept_z - 6, transept_z + 7):
            h = nave_h if center_start <= dx < center_end else aisle_h
            for i in range(3):
                blocks.append({"x": base_x + dx, "y": base_y + h + i, "z": base_z + dz, "type": 5})

    # Altar
    altar_z = long - 4
    for dx in range(8, wide - 8):
        for dz in range(altar_z, long - 2):
            for dy in range(1, 3):
                blocks.append({"x": base_x + dx, "y": base_y + dy, "z": base_z + dz, "type": 9})

    # Aperturas: puerta, roseton, ventanas, interior libre
    air = []
    # Gran portal y roseton en fachada
    for dx in range(8, wide - 8):
        for dy in range(3, 12):
            air.append({"x": base_x + dx, "y": base_y + dy, "z": base_z, "type": 0})
    # Puerta de entrada (arco)
    for dx in range(10, wide - 10):
        for dy in range(1, 8):
            for dz in range(2):
                air.append({"x": base_x + dx, "y": base_y + dy, "z": base_z + dz, "type": 0})
    # Ventanas naves laterales
    for dz in range(4, long - 4, 5):
        for side_x in [1, 2, wide - 3, wide - 2]:
            for dy in range(3, aisle_h - 1):
                air.append({"x": base_x + side_x, "y": base_y + dy, "z": base_z + dz, "type": 0})
    # Ventanas altas nave central
    for dz in range(5, long - 5, 5):
        for dx in [left_aisle_x + 1, right_aisle_x - 1]:
            for dy in range(aisle_h + 2, nave_h - 1):
                air.append({"x": base_x + dx, "y": base_y + dy, "z": base_z + dz, "type": 0})
    # Interior transitable
    for dx in range(1, wide - 1):
        for dz in range(1, long - 1):
            for dy in range(1, aisle_h):
                if dx not in [left_aisle_x, right_aisle_x] and dz not in [8, 22, 36]:
                    air.append({"x": base_x + dx, "y": base_y + dy, "z": base_z + dz, "type": 0})
            if center_start <= dx < center_end:
                for dy in range(aisle_h, nave_h):
                    air.append({"x": base_x + dx, "y": base_y + dy, "z": base_z + dz, "type": 0})

    # Resolver prioridad: aire (0) gana sobre solido
    block_map = {}
    for b in blocks:
        block_map[(b["x"], b["y"], b["z"])] = b["type"]
    for b in air:
        block_map[(b["x"], b["y"], b["z"])] = 0

    final = [{"x": k[0], "y": k[1], "z": k[2], "type": v} for k, v in block_map.items()]
    print(f"Total bloques a colocar: {len(final)}")
    return final


if __name__ == "__main__":
    final_blocks = build_cathedral()
    BATCH = 400
    ok_total = 0
    for i in range(0, len(final_blocks), BATCH):
        batch = final_blocks[i:i + BATCH]
        print(f"Lote {i // BATCH + 1}/{(len(final_blocks) - 1) // BATCH + 1} ({len(batch)} bloques)...")
        ok = send_batch("place_block", batch)
        ok_total += ok
        time.sleep(0.05)
    print(f"Colocados aproximadamente {ok_total}/{len(final_blocks)} bloques")
