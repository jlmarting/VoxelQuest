"""Hace explotar la Dama de Elche (id=359) dispersando fragmentos con física realista.

1. Obtiene los voxels de la estatua vía get_object.
2. Agrupa los voxels en ~50 fragmentos (clusters por proximidad).
3. Crea cada fragmento como objeto box con:
   - masa > 0 (cae por gravedad)
   - velocidad inicial radial (impulso de explosión) + componente hacia arriba
   - restitution (rebote al impactar)
4. Destruye la estatua original.

La física del servidor (update_object) aplica gravedad y colisión con el suelo,
así que los fragmentos vuelan y caen de forma realista.
"""
from __future__ import annotations
import json
import urllib.request
import sys
import math
import random

def mcp_call(tool, args, timeout=120):
    body = {"jsonrpc": "2.0", "id": 1, "method": "tools/call",
            "params": {"name": tool, "arguments": args}}
    req = urllib.request.Request("http://localhost:9000/mcp",
        data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        resp = json.loads(r.read().decode())
        if "content" in resp and resp["content"]:
            return json.loads(resp["content"][0].get("text", "{}"))
        return resp

STATUE_ID = 359
N_FRAGMENTS = 50
EXPLOSION_POWER = 18.0  # velocidad radial máxima (u/s)
UPWARD_BOOST = 8.0      # componente vertical extra

# 1. Obtener voxels de la estatua
print(f"Obteniendo voxels de la estatua {STATUE_ID}...")
r = mcp_call("get_object", {"object_id": STATUE_ID})
obj = r.get("object", {})
voxels = obj.get("shape", {}).get("voxels", [])
if not voxels:
    print(f"✗ No se obtuvieron voxels: {r}")
    sys.exit(1)
print(f"  {len(voxels)} voxels obtenidos")

# Centro de la estatua
cx, cy, cz = obj["position"]
print(f"  Centro: ({cx:.1f}, {cy:.1f}, {cz:.1f})")

# 2. Agrupar voxels en N fragmentos (clusters por posición)
# Usar agrupación por cubos espaciales simples
random.seed(42)
# Dividir el espacio en celdas y asignar voxels a fragmentos
# Método simple: asignar cada voxel a un fragmento según su ángulo y altura
fragments = [[] for _ in range(N_FRAGMENTS)]
for vxl in voxels:
    # Coordenadas locales del voxel
    lx = vxl["x"] if isinstance(vxl, dict) else vxl[0]
    ly = vxl["y"] if isinstance(vxl, dict) else vxl[1]
    lz = vxl["z"] if isinstance(vxl, dict) else vxl[2]
    # Asignar a fragmento por ángulo azimutal + altura
    ang = math.atan2(lz, lx) if (lx or lz) else 0
    # Normalizar ángulo a [0, 2π)
    if ang < 0: ang += 2 * math.pi
    # Índice por ángulo (mitad de fragmentos) y por altura (mitad)
    ang_idx = int(ang / (2 * math.pi) * (N_FRAGMENTS // 2))
    h_idx = int((ly + 10) / 20 * (N_FRAGMENTS - N_FRAGMENTS // 2))
    idx = (ang_idx + h_idx) % N_FRAGMENTS
    fragments[idx].append(vxl)

# Filtrar fragmentos vacíos
fragments = [f for f in fragments if f]
print(f"  {len(fragments)} fragmentos generados")

# 3. Crear cada fragmento como objeto box con física
print("Creando fragmentos con física realista...")
created = 0
for i, frag in enumerate(fragments):
    # Centro del fragmento (promedio de voxels)
    xs = [v["x"] if isinstance(v, dict) else v[0] for v in frag]
    ys = [v["y"] if isinstance(v, dict) else v[1] for v in frag]
    zs = [v["z"] if isinstance(v, dict) else v[2] for v in frag]
    fx = cx + sum(xs) / len(xs)
    fy = cy + sum(ys) / len(ys)
    fz = cz + sum(zs) / len(zs)
    # Tamaño del fragmento (AABB)
    size_x = max(xs) - min(xs) + 0.25
    size_y = max(ys) - min(ys) + 0.25
    size_z = max(zs) - min(zs) + 0.25
    size_x = max(0.3, min(size_x, 2.0))
    size_y = max(0.3, min(size_y, 2.0))
    size_z = max(0.3, min(size_z, 2.0))

    # Dirección radial desde el centro de la estatua
    dx = fx - cx
    dy = fy - cy
    dz = fz - cz
    dist = math.sqrt(dx*dx + dy*dy + dz*dz) or 1.0
    # Velocidad radial: más lejos del centro = más velocidad (hasta un tope)
    power = EXPLOSION_POWER * (0.4 + 0.6 * min(1.0, dist / 8.0))
    vx = dx / dist * power
    vy = dy / dist * power + UPWARD_BOOST + random.uniform(0, 3)
    vz = dz / dist * power
    # Pequeña variación aleatoria
    vx += random.uniform(-1, 1)
    vz += random.uniform(-1, 1)

    # Color del fragmento (promedio de colores de voxels)
    colors = [v["color"] if isinstance(v, dict) else 0xE8DCC8 for v in frag]
    color = sum(colors) // len(colors) if colors else 0xE8DCC8

    # Crear objeto box con masa y velocidad (física realista)
    r = mcp_call("create_object", {
        "kind": "box",
        "position": [round(fx, 2), round(fy, 2), round(fz, 2)],
        "scale": [round(size_x, 2), round(size_y, 2), round(size_z, 2)],
        "color": color,
        "mass": 0.5 + random.random() * 1.5,  # masa variable
        "restitution": 0.3,                    # rebote moderado
        "velocity": [round(vx, 2), round(vy, 2), round(vz, 2)],
        "anchored": False,
    })
    if r.get("success"):
        created += 1
    else:
        print(f"  ✗ Error fragmento {i}: {r}")

print(f"  {created} fragmentos creados con velocidad de explosión")

# 4. Destruir la estatua original
print(f"Destruyendo estatua original {STATUE_ID}...")
mcp_call("destroy_object", {"object_id": STATUE_ID, "cause": "explosion"})
print("  ✓ Estatua destruida")

print(f"\n✓ Explosión completada: {created} fragmentos dispersados con física realista")
print(f"  - Velocidad radial hasta {EXPLOSION_POWER} u/s")
print(f"  - Impulso vertical +{UPWARD_BOOST} u/s")
print(f"  - Gravedad y colisión con el suelo aplicadas por el servidor")