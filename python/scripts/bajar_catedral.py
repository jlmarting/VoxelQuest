"""
Baja la catedral existente 10 bloques.
1. Borra la catedral actual
2. Reconstruye con base_y - 10
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

# La catedral actual está en (10, 35, -49)
OLD_BASE_X = 10
OLD_BASE_Z = -49
OLD_BASE_Y = 35

# Dimensiones de la catedral
W = 31
L = 55
H = 60  # suficiente para cubrir torres

# PASO 1: Borrar catedral actual (rellenar con aire)
print("Paso 1: Borrando catedral actual...")
air_blocks = []
for dx in range(-3, W + 3):
    for dz in range(-3, L + 3):
        for dy in range(OLD_BASE_Y - 2, OLD_BASE_Y + H + 5):
            air_blocks.append({"x": OLD_BASE_X + dx, "y": dy, "z": OLD_BASE_Z + dz, "type": AIR})

BATCH = 1000
total_cleared = 0
for i in range(0, len(air_blocks), BATCH):
    batch = air_blocks[i:i + BATCH]
    ok = send_batch(batch)
    total_cleared += ok
    time.sleep(0.02)

print(f"  {total_cleared} bloques borrados")

# PASO 2: Reconstruir 10 bloques más abajo
NEW_BASE_Y = OLD_BASE_Y - 10  # 25
print(f"\nPaso 2: Reconstruyendo catedral en y={NEW_BASE_Y} (10 bloques más abajo)...")

# Importar y ejecutar el builder original
import importlib.util
spec = importlib.util.spec_from_file_location("build_gothic_cathedral", "/home/jl/Proyectos/ia/VoxelQuest/core/python/scripts/build_gothic_cathedral.py")
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)

# Forzar coordenadas
blocks = builder.build_cathedral_detailed(OLD_BASE_X, OLD_BASE_Z, NEW_BASE_Y)
print(f"Total bloques a colocar: {len(blocks)}")

ok_total = 0
for i in range(0, len(blocks), 400):
    batch = blocks[i:i + 400]
    ok = send_batch(batch)
    ok_total += ok
    time.sleep(0.05)

print(f"\n✓ Catedral bajada 10 bloques!")
print(f"Nueva base: ({OLD_BASE_X}, {NEW_BASE_Y}, {OLD_BASE_Z})")
print(f"{ok_total}/{len(blocks)} bloques colocados")
