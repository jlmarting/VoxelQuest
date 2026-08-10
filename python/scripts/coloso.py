"""Crea una estatua gigante detallada: el Coloso (guerrero con espada y escudo).

Escala: resolution=8 → subvoxel size = 0.125. ~480 subvoxels de alto = 60 unidades.
El mundo tiene WORLD_HEIGHT=64, base en y=1, top en y=61.

Generado como silueta con grosor variable (lámina de 2 subvoxels en Z) para
mantener el count bajo MAX_SCULPTURE_VOXELS (30000). Perfil por secciones.
"""
from __future__ import annotations
import json
import urllib.request
import sys

MARMOL   = 0xE8DCC8   # piel / mármol claro
BRONCE   = 0x8B7355   # armadura bronce
ACERO    = 0xC0C0C0   # espada / acero
ESCUDO   = 0x6B4226   # escudo madera
DETALLE  = 0xC8B898   # sombras / detalles
CABELLO  = 0x9B7A4F   # cabello
PEDESTAL = 0xB0A090   # pedestal
S = 0.125

def v(x, y, z, color=MARMOL):
    return {"x": round(x, 3), "y": round(y, 3), "z": round(z, 3), "color": color, "size": S}

voxels = []

# ============================================================
# PERFIL: (y_frac, half_width, color) — silueta frontal
# ============================================================
H = 60.0

PROFILE = [
    # Pedestal (0.00 - 0.10)
    (0.00, 4.0, PEDESTAL),
    (0.02, 4.0, PEDESTAL),
    (0.04, 4.0, PEDESTAL),
    (0.06, 4.0, PEDESTAL),
    (0.08, 3.5, PEDESTAL),
    (0.10, 3.0, PEDESTAL),
    # Botas / pies (0.10 - 0.16)
    (0.12, 2.2, BRONCE),
    (0.14, 2.0, BRONCE),
    (0.16, 1.8, BRONCE),
    # Piernas con grebas (0.16 - 0.40)
    (0.18, 1.6, BRONCE),
    (0.20, 1.5, BRONCE),
    (0.22, 1.4, BRONCE),
    (0.24, 1.4, BRONCE),
    (0.26, 1.5, BRONCE),
    (0.28, 1.6, BRONCE),
    (0.30, 1.7, BRONCE),
    (0.32, 1.8, BRONCE),
    (0.34, 1.9, BRONCE),
    (0.36, 2.0, BRONCE),
    (0.38, 2.1, BRONCE),
    (0.40, 2.2, BRONCE),
    # Cadera / faldellín (0.40 - 0.50)
    (0.42, 2.6, BRONCE),
    (0.44, 2.8, BRONCE),
    (0.46, 2.9, BRONCE),
    (0.48, 2.8, BRONCE),
    (0.50, 2.6, BRONCE),
    # Torso con coraza (0.50 - 0.72)
    (0.52, 2.4, BRONCE),
    (0.54, 2.3, BRONCE),
    (0.56, 2.3, BRONCE),
    (0.58, 2.4, BRONCE),
    (0.60, 2.5, BRONCE),
    (0.62, 2.6, BRONCE),
    (0.64, 2.7, BRONCE),
    (0.66, 2.8, BRONCE),
    (0.68, 2.9, BRONCE),
    (0.70, 3.0, BRONCE),
    (0.72, 3.0, BRONCE),
    # Hombros / hombreras (0.72 - 0.80)
    (0.74, 3.4, BRONCE),
    (0.76, 3.6, BRONCE),
    (0.78, 3.6, BRONCE),
    (0.80, 3.4, BRONCE),
    # Cuello (0.80 - 0.84)
    (0.82, 1.2, MARMOL),
    (0.84, 1.1, MARMOL),
    # Cabeza con casco (0.84 - 0.96)
    (0.86, 1.6, MARMOL),
    (0.88, 1.7, MARMOL),
    (0.90, 1.7, MARMOL),
    (0.92, 1.6, MARMOL),
    (0.94, 1.5, MARMOL),
    (0.96, 1.3, MARMOL),
    # Casco / penacho (0.96 - 1.00)
    (0.98, 1.2, BRONCE),
    (1.00, 1.0, BRONCE),
]

# Generar silueta con grosor 1 subvoxel en Z (z=0) para reducir count
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
                voxels.append(v(x, y, 0, color))

# ============================================================
# DETALLES
# ============================================================

# --- ESPADA (brazo derecho extendido hacia +z, y ~ 0.70*H) ---
sword_y = 0.70 * H  # ~42
# Brazo derecho extendido
for y in [0.70, 0.71, 0.72]:
    yy = y * H
    for x in [1.2, 1.4, 1.6]:
        for z in [0.5, 0.75, 1.0, 1.25, 1.5]:
            voxels.append(v(x, yy, z, BRONCE))
# Mano
voxels.append(v(1.4, 0.70 * H, 1.75, MARMOL))
# Hoja de la espada (hacia arriba y adelante)
for i in range(8):
    yy = 0.70 * H + i * 0.25
    voxels.append(v(1.4, yy, 1.9, ACERO))
    voxels.append(v(1.4, yy, 2.0, ACERO))
# Punta
voxels.append(v(1.4, 0.70 * H + 2.0, 1.95, ACERO))
# Guarda
voxels.append(v(1.2, 0.70 * H, 1.9, DETALLE))
voxels.append(v(1.6, 0.70 * H, 1.9, DETALLE))

# --- ESCUDO (brazo izquierdo, y ~ 0.60*H) ---
shield_y = 0.60 * H  # ~36
# Brazo izquierdo
for y in [0.58, 0.59, 0.60, 0.61, 0.62]:
    yy = y * H
    for x in [-1.6, -1.4, -1.2]:
        for z in [0.5, 0.75, 1.0]:
            voxels.append(v(x, yy, z, BRONCE))
# Escudo (placa ovalada en z=1.5, 1 capa)
for dx in range(-3, 4):
    for dy in range(-4, 5):
        x = -1.4 + dx * 0.25
        yy = shield_y + dy * 0.25
        if (dx / 3.0) ** 2 + (dy / 4.0) ** 2 <= 1.0:
            voxels.append(v(x, yy, 1.5, ESCUDO))
# Emblema del escudo (cruz)
for dy in range(-3, 4):
    voxels.append(v(-1.4, shield_y + dy * 0.25, 1.75, DETALLE))
for dx in range(-2, 3):
    voxels.append(v(-1.4 + dx * 0.25, shield_y, 1.75, DETALLE))

# --- CINTURÓN (y ~ 0.42*H) ---
belt_y = 0.42 * H
for x in [-2.6, -2.4, -2.2, -2.0, -1.8, -1.6, -1.4, -1.2, -1.0, -0.8, -0.6, -0.4, -0.2,
          0, 0.2, 0.4, 0.6, 0.8, 1.0, 1.2, 1.4, 1.6, 1.8, 2.0, 2.2, 2.4, 2.6]:
    voxels.append(v(x, belt_y, -S, DETALLE))
    voxels.append(v(x, belt_y, S, DETALLE))
# Hebilla
voxels.append(v(0, belt_y, 0.25, ACERO))
voxels.append(v(0, belt_y, 0.375, ACERO))

# --- CORAZA: pectorales (y ~ 0.60*H) ---
for x in [-0.5, -0.25, 0.25, 0.5]:
    voxels.append(v(x, 0.60 * H, 0.25, DETALLE))
    voxels.append(v(x, 0.60 * H, 0.375, DETALLE))

# --- OJOS (cabeza, y ~ 0.90*H) ---
eye_y = 0.90 * H
voxels.append(v(-0.4, eye_y, 0.25, DETALLE))
voxels.append(v(0.4, eye_y, 0.25, DETALLE))
# Nariz
voxels.append(v(0, eye_y - 0.1, 0.375, MARMOL))
# Boca
voxels.append(v(0, eye_y - 0.25, 0.25, DETALLE))
# Barba (detalle)
for i in range(4):
    voxels.append(v(0, eye_y - 0.3 - i * 0.125, 0.25, CABELLO))
    voxels.append(v(-0.2, eye_y - 0.3 - i * 0.125, 0.25, CABELLO))
    voxels.append(v(0.2, eye_y - 0.3 - i * 0.125, 0.25, CABELLO))

# --- PENACHO del casco (y ~ 0.98*H) ---
for i in range(6):
    yy = 0.98 * H + i * 0.25
    voxels.append(v(0, yy, -S, DETALLE))
    voxels.append(v(0, yy, S, DETALLE))

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
print(f"Coloso: {len(unique)} voxels únicos (alto {y_max - y_min:.2f} unidades ≈ {int((y_max - y_min)/S)} subvoxels)")

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

scale_y = y_max - y_min + S
center_y = 1.0 + scale_y / 2
position = [10, round(center_y, 3), 40]
result = mcp_call("create_sculpture", {
    "position": position,
    "resolution": 8,
    "voxels": unique,
    "anchored": True,
    "color": MARMOL,
})
if result.get("success"):
    print(f"✓ Coloso creado: object_id={result['object_id']} voxel_count={result['voxel_count']} pos={position}")
else:
    print(f"✗ Error: {result}")
    sys.exit(1)