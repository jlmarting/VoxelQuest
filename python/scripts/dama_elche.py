"""Crea la Dama de Elche con rasgos faciales muy marcados y perceptibles.

Enfoque: cabeza grande en proporción al busto para que quepan los detalles.
Rasgos con contraste y relieve real:
- Ojos almendrados grandes (forma definida, oscuros, con párpado)
- Cejas arqueadas prominentes
- Nariz larga y prominente con puente y aletas
- Boca pequeña con labios definidos
- Pómulos marcados
- Mentón redondeado

Voxels de 0.125 (resolution 8). Cáscara elíptica para el volumen.
Flota sobre Carcassonne (0,0), base en y=38.
"""
from __future__ import annotations
import json
import urllib.request
import sys
import math

S = 0.125

PIEL    = 0xE8DCC8
PIEL_SOMBRA = 0xD0C0A8
PIEL_OSC = 0xB8A888
PIEDRA  = 0xC8B898
PIEDRA_SOMBRA = 0xA89878
ORO     = 0xDAA520
ORO_OSC = 0xB8860B
NEGRO   = 0x3A2A1A   # ojos
ROJO_LABIO = 0x8B5A4A  # labios

def v(x, y, z, color=PIEL):
    return {"x": round(x, 3), "y": round(y, 3), "z": round(z, 3), "color": color, "size": S}

voxels = []

# ============================================================
# PERFIL: (y_frac, half_width, half_depth, color)
# Altura total H = 20 unidades. Cabeza grande (0.36-0.62).
# ============================================================
H = 20.0

PROFILE = [
    # Pecho / base del busto (0.00 - 0.20)
    (0.00, 3.0, 2.0, PIEDRA),
    (0.04, 3.0, 2.0, PIEDRA),
    (0.08, 2.8, 1.8, PIEDRA),
    (0.12, 2.6, 1.6, PIEDRA),
    (0.16, 2.4, 1.5, PIEDRA),
    (0.20, 2.2, 1.4, PIEDRA),
    # Hombros (0.20 - 0.30)
    (0.24, 2.4, 1.5, PIEL),
    (0.28, 2.6, 1.6, PIEL),
    (0.30, 2.6, 1.6, PIEL),
    # Cuello (0.30 - 0.36)
    (0.33, 1.3, 0.9, PIEL),
    (0.36, 1.2, 0.8, PIEL),
    # Cabeza GRANDE (0.36 - 0.62)
    (0.38, 1.9, 1.4, PIEL),
    (0.42, 2.0, 1.5, PIEL),
    (0.46, 2.0, 1.5, PIEL),
    (0.50, 1.9, 1.4, PIEL),
    (0.54, 1.8, 1.3, PIEL),
    (0.58, 1.7, 1.2, PIEL),
    (0.62, 1.5, 1.1, PIEL),
    # Tocado superior (0.62 - 0.82)
    (0.66, 1.4, 1.0, PIEDRA),
    (0.70, 1.3, 0.9, PIEDRA),
    (0.74, 1.2, 0.8, PIEDRA),
    (0.78, 1.1, 0.7, PIEDRA),
    (0.82, 1.0, 0.6, PIEDRA),
    # Remate del tocado (0.82 - 1.00)
    (0.86, 0.9, 0.5, PIEDRA),
    (0.90, 0.8, 0.4, PIEDRA),
    (0.95, 0.7, 0.3, PIEDRA),
    (1.00, 0.6, 0.2, PIEDRA),
]

def add_ellipse_shell(y, w, d, color):
    nx = int(w / S)
    nz = int(d / S)
    for ix in range(-nx, nx + 1):
        for iz in range(-nz, nz + 1):
            x = ix * S
            z = iz * S
            r = (x / w) ** 2 + (z / d) ** 2
            if r <= 1.0:
                r_next = ((x + S) / w) ** 2 + (z / d) ** 2
                r_prev = ((x - S) / w) ** 2 + (z / d) ** 2
                r_zn = (x / w) ** 2 + ((z + S) / d) ** 2
                r_zp = (x / w) ** 2 + ((z - S) / d) ** 2
                if (r > 0.65 and r <= 1.0) or (r <= 0.65 and (r_next > 1.0 or r_prev > 1.0 or r_zn > 1.0 or r_zp > 1.0)):
                    voxels.append(v(x, y, z, color))

for i in range(len(PROFILE) - 1):
    y0f, w0, d0, c0 = PROFILE[i]
    y1f, w1, d1, c1 = PROFILE[i + 1]
    steps = max(1, int((y1f - y0f) * H / S))
    for s in range(steps):
        t = s / steps
        yf = y0f + (y1f - y0f) * t
        w = w0 + (w1 - w0) * t
        d = d0 + (d1 - d0) * t
        color = c0 if t < 0.5 else c1
        y = yf * H
        add_ellipse_shell(y, w, d, color)

# ============================================================
# ROSTRO DETALLADO (cabeza en y ~ 0.40-0.55 de H)
# ============================================================
# Centro del rostro
face_cx = 0.0
face_y = 0.50 * H   # ~10.0
face_z = 0.0

# --- OJOS ALMENDRADOS GRANDES (con párpado y contorno) ---
# Ojo izquierdo (x negativo)
for dx in range(-3, 0):
    x = -0.5 + dx * S
    # Forma almendrada: más ancho en el centro, estrecho en los extremos
    for dy in range(-2, 3):
        y = face_y + dy * S
        # Elipse almendrada: (dx/0.35)² + (dy/0.25)² <= 1
        if (dx * S / 0.35) ** 2 + (dy * S / 0.25) ** 2 <= 1.0:
            # Contorno oscuro (párpado)
            if (dx * S / 0.35) ** 2 + (dy * S / 0.25) ** 2 > 0.5:
                voxels.append(v(x, y, 0.5, NEGRO))
            else:
                voxels.append(v(x, y, 0.5, NEGRO))
# Ojo derecho (x positivo)
for dx in range(0, 4):
    x = 0.5 + dx * S
    for dy in range(-2, 3):
        y = face_y + dy * S
        if (dx * S / 0.35) ** 2 + (dy * S / 0.25) ** 2 <= 1.0:
            voxels.append(v(x, y, 0.5, NEGRO))

# --- CEJAS ARQUEADAS prominentes ---
for dx in range(-4, 0):
    x = -0.5 + dx * S
    # Arco de ceja: sube hacia el centro
    y = face_y + 0.35 + abs(dx * S) * 0.3
    voxels.append(v(x, y, 0.5, PIEL_OSC))
for dx in range(0, 5):
    x = 0.5 + dx * S
    y = face_y + 0.35 + abs(dx * S) * 0.3
    voxels.append(v(x, y, 0.5, PIEL_OSC))

# --- NARIZ LARGA Y PROMINENTE (con puente y aletas) ---
# Puente de la nariz (sube desde entre los ojos)
for dy in range(0, 5):
    y = face_y - 0.1 - dy * S
    voxels.append(v(0, y, 0.75, PIEL))
    voxels.append(v(0, y, 0.875, PIEL))
# Punta de la nariz
voxels.append(v(0, face_y - 0.5, 1.0, PIEL))
voxels.append(v(0, face_y - 0.5, 1.125, PIEL))
# Aletas de la nariz
voxels.append(v(-0.25, face_y - 0.45, 0.875, PIEL))
voxels.append(v(0.25, face_y - 0.45, 0.875, PIEL))
# Sombra bajo la nariz
voxels.append(v(-0.25, face_y - 0.55, 0.75, PIEL_SOMBRA))
voxels.append(v(0, face_y - 0.55, 0.75, PIEL_SOMBRA))
voxels.append(v(0.25, face_y - 0.55, 0.75, PIEL_SOMBRA))

# --- BOCA PEQUEÑA CON LABIOS DEFINIDOS ---
# Labio superior
for dx in range(-2, 3):
    x = dx * S
    voxels.append(v(x, face_y - 0.7, 0.5, ROJO_LABIO))
# Labio inferior (más grueso)
for dx in range(-2, 3):
    x = dx * S
    voxels.append(v(x, face_y - 0.8, 0.5, ROJO_LABIO))
    voxels.append(v(x, face_y - 0.9, 0.5, ROJO_LABIO))
# Comisuras
voxels.append(v(-0.3, face_y - 0.75, 0.5, ROJO_LABIO))
voxels.append(v(0.3, face_y - 0.75, 0.5, ROJO_LABIO))

# --- PÓMULOS MARCADOS ---
for x in [-0.7, 0.7]:
    voxels.append(v(x, face_y - 0.2, 0.5, PIEL))
    voxels.append(v(x, face_y - 0.3, 0.5, PIEL))
    voxels.append(v(x, face_y - 0.4, 0.5, PIEL_SOMBRA))

# --- MENTÓN REDONDEADO ---
for dy in range(0, 3):
    y = face_y - 1.0 - dy * S
    voxels.append(v(0, y, 0.5, PIEL))
    voxels.append(v(-0.2, y, 0.5, PIEL))
    voxels.append(v(0.2, y, 0.5, PIEL))

# --- FRENTE (con sombra suave) ---
for dy in range(0, 4):
    y = face_y + 0.5 + dy * S
    voxels.append(v(0, y, 0.5, PIEL_SOMBRA))

# ============================================================
# TOCADO DE RUEDAS (polos): discos laterales
# ============================================================
head_y0 = 0.40 * H
head_y1 = 0.55 * H
R = 0.5
for iy in range(int((head_y1 - head_y0) / S) + 1):
    y = head_y0 + iy * S
    for dx in range(-4, 0):
        x = -1.8 + dx * S
        for dz in range(-2, 3):
            z = dz * S
            if (x + 1.8) ** 2 + z ** 2 <= R * R:
                voxels.append(v(x, y, z, PIEDRA))
    for dx in range(0, 5):
        x = 1.8 + dx * S
        for dz in range(-2, 3):
            z = dz * S
            if (x - 1.8) ** 2 + z ** 2 <= R * R:
                voxels.append(v(x, y, z, PIEDRA))

# ============================================================
# COLLAR DE CUENTAS
# ============================================================
collar_y = 0.30 * H
for ang in range(0, 360, 10):
    a = math.radians(ang)
    x = math.cos(a) * 1.3
    z = math.sin(a) * 0.9
    voxels.append(v(x, collar_y, z, ORO))
    voxels.append(v(x, collar_y - 0.25, z, ORO_OSC))
voxels.append(v(0, collar_y - 0.5, 0.5, ORO))
voxels.append(v(0, collar_y - 0.75, 0.5, ORO))
voxels.append(v(0, collar_y - 1.0, 0.5, ORO))

# ============================================================
# PECHO
# ============================================================
chest_y = 0.15 * H
for x in [-0.8, -0.6, -0.4, -0.2, 0, 0.2, 0.4, 0.6, 0.8]:
    voxels.append(v(x, chest_y, 0.75, PIEL))
    voxels.append(v(x, chest_y - 0.25, 0.75, PIEL_SOMBRA))

# ============================================================
# PLIEGUES DEL MANTO
# ============================================================
for ang in range(0, 360, 20):
    a = math.radians(ang)
    x = math.cos(a) * 2.8
    z = math.sin(a) * 1.8
    for dy in range(3):
        voxels.append(v(x, 0.05 * H + dy * S, z, PIEDRA_SOMBRA))

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
print(f"Dama de Elche (rostro marcado): {len(unique)} voxels únicos (alto {y_max - y_min:.2f} unidades ≈ {int((y_max - y_min)/S)} subvoxels)")

# Enviar al servidor MCP
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

scale_y = y_max - y_min + S
center_y = 38.0 + scale_y / 2
position = [0, round(center_y, 3), 0]
result = mcp_call("create_sculpture", {
    "position": position,
    "resolution": 8,
    "voxels": unique,
    "anchored": True,
    "color": PIEL,
})
if result.get("success"):
    print(f"✓ Dama de Elche (rostro marcado): object_id={result['object_id']} voxel_count={result['voxel_count']} pos={position}")
else:
    print(f"✗ Error: {result}")
    sys.exit(1)