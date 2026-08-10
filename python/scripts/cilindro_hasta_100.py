"""
Hace crecer el cilindro hasta 100 voxels de altura, luego se detiene automaticamente.
Cada giro completo (6.3s) aumenta +2 voxels.
"""
import json, urllib.request, time, math

URL = "http://localhost:9000/mcp"
_RPC = [0]

ANGULAR_SPEED = 1.0
SEC_PER_ROTATION = 2 * math.pi / ANGULAR_SPEED  # ≈ 6.283 segundos
LENGTH_INCREMENT = 2.0
MAX_LENGTH = 100.0

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

# Obtener el cilindro
result = mcp("list_objects", {})
objects = result.get("objects", [])
if not objects:
    print("✗ No se encontró ningún objeto.")
    exit(1)

obj = objects[-1]
obj_id = obj["id"]
initial_scale = obj.get("scale", [6, 12, 6])
current_scale_y = float(initial_scale[1])

print(f"✓ Objeto ID={obj_id}")
print(f"  Longitud actual: {current_scale_y:.1f} voxels")
print(f"  Objetivo: {MAX_LENGTH} voxels")
print(f"  Faltan: {MAX_LENGTH - current_scale_y:.1f} voxels")
print(f"  Giros necesarios: {math.ceil((MAX_LENGTH - current_scale_y) / LENGTH_INCREMENT)}")
print(f"  Tiempo estimado: {math.ceil((MAX_LENGTH - current_scale_y) / LENGTH_INCREMENT) * SEC_PER_ROTATION:.0f}s")
print(f"\n  Iniciando crecimiento hasta {MAX_LENGTH} voxels...\n")

rotation_count = 0

while current_scale_y < MAX_LENGTH:
    time.sleep(SEC_PER_ROTATION)
    rotation_count += 1
    current_scale_y = min(current_scale_y + LENGTH_INCREMENT, MAX_LENGTH)
    
    new_scale = [initial_scale[0], current_scale_y, initial_scale[2]]
    result = mcp("update_object", {
        "object_id": obj_id,
        "patch": {"scale": new_scale}
    })
    
    if "error" in result:
        print(f"  ✗ Error: {result['error']}")
        break
    
    print(f"  [Giro #{rotation_count}] Longitud: {current_scale_y:.1f} voxels")
    
    if current_scale_y >= MAX_LENGTH:
        break

print(f"\n{'='*50}")
print(f"  ✓ OBJETIVO ALCANZADO: {current_scale_y:.1f} voxels")
print(f"{'='*50}")
print(f"  Giros totales: {rotation_count}")
print(f"  Longitud inicial: {initial_scale[1]}")
print(f"  Longitud final: {current_scale_y:.1f}")
print(f"  Aumento total: +{current_scale_y - float(initial_scale[1]):.1f} voxels")
