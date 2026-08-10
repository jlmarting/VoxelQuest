"""Crea un incendio: llamas de subvoxels (rojo/naranja/amarillo) + brasas luminosas.

- Escultura de llamas: columnas de fuego con gradiente de color (rojo base,
  naranja medio, amarillo punta) generadas proceduralmente.
- Esferas emissive pequeñas (brasas) que emiten luz naranja/roja alrededor.
"""
from __future__ import annotations
import json
import urllib.request
import sys
import math

S = 0.25  # subvoxel size (resolution 4)

ROJO = 0xFF4500
NARANJA = 0xFF8C00
AMARILLO = 0xFFD700
BRAZA = 0xFF6600

def v(x, y, z, color):
    return {"x": round(x, 3), "y": round(y, 3), "z": round(z, 3), "color": color, "size": S}

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

# ============================================================
# 1. Escultura de llamas (hoguera central)
# ============================================================
voxels = []
CX, CY, CZ = 10, 24, 10  # suelo en y=24 (detectado antes)

# Hoguera: troncos (base)
for i in range(6):
    ang = i * math.pi / 3
    x = CX + math.cos(ang) * 1.2
    z = CZ + math.sin(ang) * 1.2
    for dy in range(2):
        voxels.append(v(x, CY + dy * S, z, 0x4A2C1A))  # tronco oscuro

# Llamas: columnas de fuego con gradiente
# 5 columnas de llama
for (lx, lz, h) in [(CX, CZ, 6.0), (CX - 0.5, CZ + 0.3, 4.5),
                    (CX + 0.5, CZ - 0.3, 4.0), (CX - 0.3, CZ - 0.5, 3.5),
                    (CX + 0.3, CZ + 0.5, 3.0)]:
    steps = int(h / S)
    for iy in range(steps + 1):
        y = CY + iy * S
        # Radio de la llama se estrecha hacia arriba
        frac = iy / steps
        r = 0.9 * (1 - frac * 0.7)
        # Color por altura: rojo abajo → naranja → amarillo arriba
        if frac < 0.4:
            color = ROJO
        elif frac < 0.75:
            color = NARANJA
        else:
            color = AMARILLO
        nr = int(r / S)
        for ix in range(-nr, nr + 1):
            for iz in range(-nr, nr + 1):
                x = lx + ix * S
                z = lz + iz * S
                if (ix * S) ** 2 + (iz * S) ** 2 <= r * r:
                    voxels.append(v(x, y, z, color))

# Chispas (puntos sueltos sobre las llamas)
for i in range(20):
    ang = i * 0.314
    x = CX + math.cos(ang) * 0.8
    z = CZ + math.sin(ang) * 0.8
    y = CY + 6.0 + (i % 4) * 0.5
    voxels.append(v(x, y, z, AMARILLO))

# Deduplicar
seen = set()
unique = []
for vxl in voxels:
    key = (round(vxl["x"], 3), round(vxl["y"], 3), round(vxl["z"], 3))
    if key not in seen:
        seen.add(key)
        unique.append(vxl)

print(f"Llamas: {len(unique)} voxels")

xs = [vx["x"] for vx in unique]
ys = [vx["y"] for vx in unique]
zs = [vx["z"] for vx in unique]
scale = (max(xs) - min(xs) + S, max(ys) - min(ys) + S, max(zs) - min(zs) + S)
center = (CX, CY + (max(ys) - min(ys)) / 2, CZ)

r = mcp_call("create_sculpture", {
    "position": list(center),
    "resolution": 4,
    "voxels": unique,
    "anchored": True,
    "color": NARANJA,
})
if r.get("success"):
    print(f"✓ Hoguera de llamas: object_id={r['object_id']} voxels={r['voxel_count']} pos={center}")
else:
    print(f"✗ Error hoguera: {r}")
    sys.exit(1)

# ============================================================
# 2. Brasas luminosas (esferas emissive pequeñas)
# ============================================================
# Esfera central grande (luz principal)
r = mcp_call("create_object", {
    "kind": "sphere",
    "position": [CX, CY + 3.0, CZ],
    "scale": [2.0, 2.0, 2.0],
    "color": NARANJA,
    "emissive": True,
    "mass": 0.0,
    "anchored": True,
})
print(f"✓ Brasa central luminosa: object_id={r.get('object_id')}")

# Brasas pequeñas alrededor (luz secundaria)
for (bx, bz, by) in [(CX - 1.5, CZ, CY + 1.0), (CX + 1.5, CZ, CY + 1.0),
                     (CX, CZ - 1.5, CY + 1.0), (CX, CZ + 1.5, CY + 1.0),
                     (CX - 1.0, CZ - 1.0, CY + 0.5), (CX + 1.0, CZ + 1.0, CY + 0.5)]:
    r = mcp_call("create_object", {
        "kind": "sphere",
        "position": [bx, by, bz],
        "scale": [1.0, 1.0, 1.0],
        "color": BRAZA,
        "emissive": True,
        "mass": 0.0,
        "anchored": True,
    })
    print(f"✓ Brasa en ({bx},{by},{bz}): object_id={r.get('object_id')}")

print("\n✓ Incendio creado: hoguera de llamas + 7 brasas luminosas")