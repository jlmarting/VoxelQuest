"""
Hace que el cilindro gire y aumente su longitud (altura) 2 voxels con cada giro completo.
El script monitorea los giros en segundo plano.
"""
import json, urllib.request, time, math

URL = "http://localhost:9000/mcp"
_RPC = [0]

# Velocidad angular: 1 rad/s
# 1 giro completo = 2π rad ≈ 6.283 segundos
ANGULAR_SPEED = 1.0
SEC_PER_ROTATION = 2 * math.pi / ANGULAR_SPEED  # ≈ 6.283 segundos

# Aumento de longitud por giro
LENGTH_INCREMENT = 2.0

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

# Obtener el cilindro giratorio (el ultimo objeto creado de tipo box con rotacion)
print("Buscando cilindro giratorio...")
result = mcp("list_objects", {})
objects = result.get("objects", [])

if not objects:
    print("✗ No se encontró ningún objeto. Ejecuta cilindro_giratorio.py primero.")
    exit(1)

# Tomar el primer objeto (deberia ser el cilindro)
obj = objects[-1]
obj_id = obj["id"]
initial_scale = obj.get("scale", [6, 12, 6])
current_scale_y = float(initial_scale[1])

print(f"✓ Objeto encontrado: ID={obj_id}")
print(f"  Escala inicial: Y={current_scale_y}")
print(f"  Tiempo por giro: {SEC_PER_ROTATION:.2f}s")
print(f"  Aumento por giro: +{LENGTH_INCREMENT} voxels")
print(f"\n  Iniciando crecimiento continuo...")
print(f"  (Presiona Ctrl+C para detener)\n")

rotation_count = 0
total_time = 0

try:
    while True:
        # Esperar tiempo de un giro completo
        time.sleep(SEC_PER_ROTATION)
        total_time += SEC_PER_ROTATION
        
        rotation_count += 1
        current_scale_y += LENGTH_INCREMENT
        
        # Actualizar escala del objeto (aumentar altura Y)
        new_scale = [initial_scale[0], current_scale_y, initial_scale[2]]
        
        result = mcp("update_object", {
            "object_id": obj_id,
            "patch": {
                "scale": new_scale
            }
        })
        
        if "error" in result:
            print(f"  ✗ Error actualizando: {result['error']}")
            break
        
        print(f"  [Giro #{rotation_count:3d}] | Longitud: {current_scale_y:5.1f} voxels | Tiempo: {total_time:.0f}s")
        
        # Mostrar progreso cada 5 giros
        if rotation_count % 5 == 0:
            print(f"  *** Progreso: {rotation_count} giros | +{rotation_count * LENGTH_INCREMENT} voxels ***")
        
except KeyboardInterrupt:
    print(f"\n{'='*50}")
    print(f"  DETENIDO")
    print(f"{'='*50}")
    print(f"  Giros completados: {rotation_count}")
    print(f"  Longitud final: {current_scale_y:.1f} voxels")
    print(f"  Longitud inicial: {initial_scale[1]}")
    print(f"  Aumento total: +{rotation_count * LENGTH_INCREMENT} voxels")
    print(f"  Tiempo total: {total_time:.0f}s")
