"""Crea una escultura 'Venus de Milo' de 500 subvoxels de alto.

Escala: resolution=8 → subvoxel size = 0.125. 500 subvoxels = 62.5 unidades.
El mundo tiene WORLD_HEIGHT=64, así que la base va en y=1 y el top en y=63.5.

Para no exceder MAX_SCULPTURE_VOXELS (20000), se genera como SILUETA con
grosor de 2 subvoxels en Z (lámina de 0.25 unidades de profundidad). El perfil
de la figura se define por secciones (ancho en X por cada Y).
"""
from __future__ import annotations
import json
import urllib.request
import sys

MARMOL  = 0xE8DCC8
PAÑO    = 0xD8C8A8
SOMBRA  = 0xC8B898
CABELLO = 0x9B7A4F
PEDESTAL_COL = 0xB0A090
S = 0.125  # subvoxel size (resolution 8)

def v(x, y, z, color=MARMOL):
    return {"x": round(x, 3), "y": round(y, 3), "z": round(z, 3), "color": color, "size": S}

voxels = []

# ============================================================
# PERFIL DE LA SILUETA: (y_frac, half_width, color)
# y_frac = fracción de altura (0=base, 1=top)
# half_width = semiancho en X (unidades)
# ============================================================
H = 62.5  # altura total en unidades

PROFILE = [
    # Pedestal (0.00 - 0.08)
    (0.00, 3.0, PEDESTAL_COL),
    (0.02, 3.0, PEDESTAL_COL),
    (0.04, 3.0, PEDESTAL_COL),
    (0.06, 3.0, PEDESTAL_COL),
    (0.08, 2.5, PEDESTAL_COL),
    # Pies (0.08 - 0.12)
    (0.10, 1.5, MARMOL),
    (0.12, 1.2, MARMOL),
    # Tobillos (0.12 - 0.16)
    (0.14, 0.8, MARMOL),
    (0.16, 0.7, MARMOL),
    # Pantorrillas (0.16 - 0.28)
    (0.18, 0.8, MARMOL),
    (0.20, 0.9, MARMOL),
    (0.22, 0.9, MARMOL),
    (0.24, 0.8, MARMOL),
    (0.26, 0.7, MARMOL),
    (0.28, 0.7, MARMOL),
    # Rodillas (0.28 - 0.34)
    (0.30, 0.9, MARMOL),
    (0.32, 1.0, MARMOL),
    (0.34, 1.0, MARMOL),
    # Muslos (0.34 - 0.48)
    (0.36, 1.2, MARMOL),
    (0.38, 1.3, MARMOL),
    (0.40, 1.4, MARMOL),
    (0.42, 1.5, MARMOL),
    (0.44, 1.6, MARMOL),
    (0.46, 1.7, MARMOL),
    (0.48, 1.8, MARMOL),
    # Cadera / paño (0.48 - 0.60)
    (0.50, 2.2, PAÑO),
    (0.52, 2.4, PAÑO),
    (0.54, 2.5, PAÑO),
    (0.56, 2.4, PAÑO),
    (0.58, 2.2, PAÑO),
    (0.60, 2.0, PAÑO),
    # Cintura (0.60 - 0.66)
    (0.62, 1.6, MARMOL),
    (0.64, 1.4, MARMOL),
    (0.66, 1.3, MARMOL),
    # Abdomen (0.66 - 0.74)
    (0.68, 1.4, MARMOL),
    (0.70, 1.5, MARMOL),
    (0.72, 1.6, MARMOL),
    (0.74, 1.7, MARMOL),
    # Pecho (0.74 - 0.84)
    (0.76, 2.0, MARMOL),
    (0.78, 2.2, MARMOL),
    (0.80, 2.3, MARMOL),
    (0.82, 2.2, MARMOL),
    (0.84, 2.0, MARMOL),
    # Hombros (0.84 - 0.90)
    (0.86, 2.6, MARMOL),
    (0.88, 2.8, MARMOL),
    (0.90, 2.8, MARMOL),
    # Muñones (brazos cortados) (0.90 - 0.94)
    (0.92, 2.6, SOMBRA),
    (0.94, 2.4, SOMBRA),
    # Cuello (0.94 - 0.97)
    (0.95, 0.9, MARMOL),
    (0.96, 0.8, MARMOL),
    (0.97, 0.8, MARMOL),
    # Cabeza (0.97 - 1.00)
    (0.98, 1.2, MARMOL),
    (0.99, 1.1, MARMOL),
    (1.00, 0.9, MARMOL),
]

# Generar la silueta: para cada capa Y, rellenar X según half_width,
# con grosor de 2 subvoxels en Z (z = -0.125 y +0.125).
for i in range(len(PROFILE) - 1):
    y0f, w0, c0 = PROFILE[i]
    y1f, w1, c1 = PROFILE[i + 1]
    steps = max(1, int((y1f - y0f) * H / S))
    for s in range(steps):
        t = s / steps
        yf = y0f + (y1f - y0f) * t
        w = w0 + (w1 - w0) * t
        color = c0 if t < 0.5 else c1
        y = yf * H
        nx = int(w / S)
        for ix in range(-nx, nx + 1):
            x = ix * S
            if abs(x) <= w:
                voxels.append(v(x, y, -S, color))
                voxels.append(v(x, y, S, color))

# --- DETALLES FACIALES (cabeza en y ~ 60-62.5) ---
head_y = 0.98 * H  # ~61.25
# Ojos
voxels.append(v(-0.25, head_y + 0.1, 0.25, SOMBRA))
voxels.append(v(0.25, head_y + 0.1, 0.25, SOMBRA))
# Nariz (proyección frontal)
voxels.append(v(0, head_y + 0.2, 0.375, MARMOL))
# Boca
voxels.append(v(0, head_y - 0.1, 0.25, SOMBRA))
# Pelo recogido (parte posterior de la cabeza)
for yf in [0.98, 0.99, 1.0]:
    y = yf * H
    for x in [-0.8, -0.6, -0.4, -0.2, 0, 0.2, 0.4, 0.6, 0.8]:
        for z in [-0.25, -0.125]:
            voxels.append(v(x, y, z, CABELLO))
# Moño
for yf in [0.99, 1.0]:
    y = yf * H
    for x in [-0.3, -0.15, 0, 0.15, 0.3]:
        for z in [-0.25, -0.125, 0]:
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
print(f"Venus de Milo: {len(unique)} voxels únicos (alto {y_max - y_min:.2f} unidades ≈ {int((y_max - y_min)/S)} subvoxels)")

# Enviar al servidor MCP
def mcp_call(tool, args):
    body = {"jsonrpc": "2.0", "id": 1, "method": "tools/call",
            "params": {"name": tool, "arguments": args}}
    req = urllib.request.Request("http://localhost:9000/mcp",
        data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        resp = json.loads(r.read().decode())
        if "content" in resp and resp["content"]:
            return json.loads(resp["content"][0].get("text", "{}"))
        return resp

# Base en y=1 (suelo). scale_y = y_max - y_min + S
scale_y = y_max - y_min + S
center_y = 1.0 + scale_y / 2
position = [10, round(center_y, 3), 10]
result = mcp_call("create_sculpture", {
    "position": position,
    "resolution": 8,
    "voxels": unique,
    "anchored": True,
    "color": MARMOL,
})
if result.get("success"):
    print(f"✓ Venus de Milo creada: object_id={result['object_id']} voxel_count={result['voxel_count']} pos={position}")
else:
    print(f"✗ Error: {result}")
    sys.exit(1)