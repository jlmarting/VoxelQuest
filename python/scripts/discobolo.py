"""Crea una estatua 'Discóbolo' (lanzador de disco) de 30 voxels completos de alto.

Escala: resolution=1 → subvoxel size = 1.0. 30 voxels = 30 unidades de alto.
Coordenadas locales: y=0 abajo (base), y crece hacia arriba. Centro x=z=0.
El Discóbolo de Mirón: atleta en torsión, brazo derecho extendido con disco,
pierna izquierda flexionada, torso inclinado hacia delante.
"""
from __future__ import annotations
import json
import urllib.request
import sys

MARMOL  = 0xE8DCC8
SOMBRA  = 0xC8B898
CABELLO = 0x9B7A4F
PEDESTAL_COL = 0xB0A090
DISCO_COL = 0x8B7355
S = 1.0  # subvoxel size (resolution 1)

def v(x, y, z, color=MARMOL):
    return {"x": round(x, 3), "y": round(y, 3), "z": round(z, 3), "color": color, "size": S}

voxels = []

# ============================================================
# 30 voxels de alto (y de 0 a 30).
# Proporciones: pedestal 3, piernas 12, torso 10, cabeza 5.
# ============================================================

# --- PEDESTAL (y 0 - 3) ---
for x in [-2, -1, 0, 1, 2]:
    for z in [-2, -1, 0, 1, 2]:
        for y in [0, 1, 2]:
            voxels.append(v(x, y, z, PEDESTAL_COL))

# --- PIERNA DERECHA (apoyo, y 3 - 12) ---
# Pie
for x in [-1, 0]:
    for z in [-1, 0]:
        voxels.append(v(x, 3, z))
# Pierna derecha (recta, apoyo)
for y in [4, 5, 6, 7, 8, 9, 10, 11]:
    for x in [-1, 0]:
        for z in [-1, 0]:
            voxels.append(v(x, y, z))

# --- PIERNA IZQUIERDA (flexionada, y 3 - 9) ---
# Pie izquierdo (adelantado y elevado)
for x in [1, 2]:
    for z in [-1, 0]:
        voxels.append(v(x, 3, z))
# Muslo izquierdo (flexionado, sube hacia delante)
for y in [4, 5, 6, 7, 8]:
    for x in [1, 2]:
        for z in [-1, 0]:
            voxels.append(v(x, y, z))

# --- CADERA (y 12 - 14) ---
for y in [12, 13]:
    for x in [-1, 0, 1, 2]:
        for z in [-1, 0, 1]:
            voxels.append(v(x, y, z))

# --- TORSO (y 14 - 24, inclinado hacia delante) ---
# Torso inferior
for y in [14, 15, 16]:
    for x in [-1, 0, 1]:
        for z in [-1, 0, 1]:
            voxels.append(v(x, y, z))
# Torso medio (se inclina hacia +z, dirección del lanzamiento)
for y in [17, 18, 19, 20]:
    for x in [-1, 0, 1]:
        for z in [-1, 0, 1]:
            voxels.append(v(x, y, z))
# Torso superior (hombros, más ancho)
for y in [21, 22, 23]:
    for x in [-2, -1, 0, 1, 2]:
        for z in [-1, 0, 1]:
            voxels.append(v(x, y, z))

# --- BRAZO IZQUIERDO (atrás, contrapeso, y 20 - 24) ---
for y in [20, 21, 22, 23]:
    for x in [-2, -3]:
        for z in [-1, 0]:
            voxels.append(v(x, y, z, SOMBRA))

# --- BRAZO DERECHO (extendido con disco, y 22 - 24) ---
# Brazo extendido hacia +z (dirección del lanzamiento)
for y in [22, 23]:
    for x in [0, 1]:
        for z in [1, 2, 3, 4]:
            voxels.append(v(x, y, z))
# Mano con disco (disco plano en z=5)
for x in [0, 1]:
    for z in [5]:
        voxels.append(v(x, 22, z, DISCO_COL))
        voxels.append(v(x, 23, z, DISCO_COL))
# Disco (placa circular)
for x in [-1, 0, 1, 2]:
    for z in [5]:
        voxels.append(v(x, 22, z, DISCO_COL))
        voxels.append(v(x, 23, z, DISCO_COL))

# --- CUELLO (y 24 - 25) ---
for y in [24, 25]:
    for x in [0]:
        for z in [0]:
            voxels.append(v(x, y, z))

# --- CABEZA (y 25 - 30) ---
# Cabeza (girada hacia el lanzamiento)
for y in [26, 27, 28, 29]:
    for x in [-1, 0, 1]:
        for z in [-1, 0, 1]:
            voxels.append(v(x, y, z))
# Ojos (mirando hacia +z)
voxels.append(v(-1, 28, 1, SOMBRA))
voxels.append(v(1, 28, 1, SOMBRA))
# Nariz
voxels.append(v(0, 28, 2))
# Pelo corto
for y in [29]:
    for x in [-1, 0, 1]:
        for z in [-1, 0, 1]:
            voxels.append(v(x, y, z, CABELLO))

# --- DEDUPLICAR ---
seen = set()
unique = []
for vxl in voxels:
    key = (round(vxl["x"], 3), round(vxl["y"], 3), round(vxl["z"], 3))
    if key not in seen:
        seen.add(key)
        unique.append(vxl)

y_max = max(v['y'] for v in unique)
y_min = min(v['y'] for v in unique)
print(f"Discóbolo: {len(unique)} voxels únicos (alto {y_max - y_min:.2f} unidades ≈ {int((y_max - y_min)/S)} voxels)")

# Enviar al servidor MCP
def mcp_call(tool, args):
    body = {"jsonrpc": "2.0", "id": 1, "method": "tools/call",
            "params": {"name": tool, "arguments": args}}
    req = urllib.request.Request("http://localhost:9000/mcp",
        data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        resp = json.loads(r.read().decode())
        if "content" in resp and resp["content"]:
            return json.loads(resp["content"][0].get("text", "{}"))
        return resp

# Base en y=1 (suelo). scale_y = y_max - y_min + S
scale_y = y_max - y_min + S
center_y = 1.0 + scale_y / 2
position = [30, round(center_y, 3), 10]
result = mcp_call("create_sculpture", {
    "position": position,
    "resolution": 1,
    "voxels": unique,
    "anchored": True,
    "color": MARMOL,
})
if result.get("success"):
    print(f"✓ Discóbolo creado: object_id={result['object_id']} voxel_count={result['voxel_count']} pos={position}")
else:
    print(f"✗ Error: {result}")
    sys.exit(1)