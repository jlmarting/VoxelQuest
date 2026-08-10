"""
Crea un cilindro vertical de radio 3 voxels y altura 12 voxels.
Eje vertical (Y). Usa bloques estandar.
"""
import json, urllib.request, time, math

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

def detect_ground(wx, wz):
    for y in range(80, 0, -1):
        res = mcp("get_block", {"x": wx, "y": y, "z": wz})
        bt = res.get("type", 0) if isinstance(res, dict) else 0
        if bt != AIR and bt != WATER:
            return y + 1
    return 30

# Obtener posicion del jugador
players = mcp("list_players", {})
p = players.get("players", [{}])[0] if isinstance(players, dict) else {}
px, pz = int(p.get("x", 0)), int(p.get("z", 0))
print(f"Jugador en ({px}, {pz})")

base_y = detect_ground(px, pz)
print(f"Suelo en y={base_y}")

# Colocar cilindro 5 bloques al este del jugador
cx = px + 5
cz = pz
cy = base_y

RADIUS = 3
HEIGHT = 12

print(f"\nConstruyendo cilindro vertical en ({cx}, {cy}, {cz})...")
print(f"Radio: {RADIUS} bloques | Altura: {HEIGHT} bloques")

blocks = []
for y in range(HEIGHT):
    for dx in range(-RADIUS, RADIUS + 1):
        for dz in range(-RADIUS, RADIUS + 1):
            if dx * dx + dz * dz <= RADIUS * RADIUS + 0.5:
                blocks.append({"x": cx + dx, "y": cy + y, "z": cz + dz, "type": STONE})

print(f"Total bloques: {len(blocks)}")

BATCH = 400
ok_total = 0
for i in range(0, len(blocks), BATCH):
    batch = blocks[i:i + BATCH]
    ok = send_batch(batch)
    ok_total += ok
    time.sleep(0.05)

print(f"\n✓ Cilindro vertical construido!")
print(f"{ok_total}/{len(blocks)} bloques colocados")
print(f"Centro: ({cx}, {cy}, {cz}) | Radio: {RADIUS} | Altura: {HEIGHT}")
