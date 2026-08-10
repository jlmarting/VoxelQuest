"""
Limpia una zona rectangular llenandola de aire.
Util para borrar restos de construcciones previas.
"""
import json, urllib.request, time, sys

URL = "http://localhost:9000/mcp"
_RPC = [0]

AIR = 0


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


def clear_area(cx, cz, cy, width=60, depth=60, height=50):
    """Llena de aire un area centrada en (cx, cy, cz)."""
    blocks = []
    half_w = width // 2
    half_d = depth // 2
    for dx in range(-half_w, half_w + 1):
        for dz in range(-half_d, half_d + 1):
            for dy in range(0, height):
                blocks.append({"x": cx + dx, "y": cy + dy, "z": cz + dz, "type": AIR})

    print(f"Limpiando area {width}x{depth}x{height} en ({cx}, {cy}, {cz})...")
    print(f"Total bloques de aire: {len(blocks)}")

    BATCH = 800
    ok_total = 0
    for i in range(0, len(blocks), BATCH):
        batch = blocks[i:i + BATCH]
        ok = send_batch(batch)
        ok_total += ok
        if i % (BATCH * 5) == 0:
            print(f"  Progreso: {ok_total}/{len(blocks)}")
        time.sleep(0.02)

    print(f"\nLimpieza completada: {ok_total}/{len(blocks)} bloques de aire colocados.")
    return ok_total


if __name__ == "__main__":
    players = mcp("list_players", {})
    p = players.get("players", [{}])[0] if isinstance(players, dict) else {}
    px, py, pz = int(p.get("x", 0)), int(p.get("y", 0)), int(p.get("z", 0))

    print(f"Jugador en ({px}, {py}, {pz})")
    print("Este script llenara de AIRE un area grande alrededor tuyo.")
    print("Asegurate de estar en el centro de la zona que quieres limpiar.")
    resp = input("\nContinuar? (s/N): ")
    if resp.lower() != 's':
        print("Cancelado.")
        sys.exit(0)

    clear_area(px, pz, py - 2, width=80, depth=80, height=60)
