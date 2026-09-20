"""
Crea una Venus de Milo de 50 bloques de alto con resolucion subvoxel maxima (8).
Desde el suelo: pie en y=1, altura total 50 unidades = 400 subvoxels.
Silueta delgada (2 capas en Z) para caber en MAX_SCULPTURE_VOXELS=30000.
"""
import json, urllib.request, sys

URL = "http://localhost:9000/mcp"

MARMOL  = 0xE8DCC8
PANHO   = 0xD8C8A8
SOMBRA  = 0xC8B898
CABELLO = 0x9B7A4F
PEDESTAL_COL = 0xB0A090

S = 0.125  # subvoxel size (resolution 8)
H = 50.0   # altura total en unidades = 400 subvoxels

def v(x, y, z, color=MARMOL):
    return {"x": round(x, 3), "y": round(y, 3), "z": round(z, 3), "color": color, "size": S}

def mcp_call(tool, args, timeout=120):
    body = {"jsonrpc": "2.0", "id": 1, "method": "tools/call",
            "params": {"name": tool, "arguments": args}}
    req = urllib.request.Request(URL,
        data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        resp = json.loads(r.read().decode())
        if "content" in resp and resp["content"]:
            return json.loads(resp["content"][0].get("text", "{}"))
        return resp

# Obtener posicion del jugador
players = mcp_call("list_players", {})
p = players.get("players", [{}])[0] if isinstance(players, dict) else {}
px, pz = p.get("x", 0), p.get("z", 0)
print(f"Jugador en ({px:.1f}, {pz:.1f})")

# ============================================================
# PERFIL DE LA SILUETA: (y_frac, half_width, color)
# ============================================================
PROFILE = [
    # Pedestal (0.00 - 0.10)
    (0.00, 4.0, PEDESTAL_COL),
    (0.03, 4.0, PEDESTAL_COL),
    (0.05, 4.0, PEDESTAL_COL),
    (0.08, 3.5, PEDESTAL_COL),
    # Pies (0.10 - 0.14)
    (0.10, 2.0, MARMOL),
    (0.12, 1.6, MARMOL),
    # Tobillos (0.12 - 0.16)
    (0.14, 1.2, MARMOL),
    (0.16, 1.0, MARMOL),
    # Pantorrillas (0.16 - 0.28)
    (0.18, 1.2, MARMOL),
    (0.20, 1.3, MARMOL),
    (0.22, 1.3, MARMOL),
    (0.24, 1.2, MARMOL),
    (0.26, 1.1, MARMOL),
    (0.28, 1.0, MARMOL),
    # Rodillas (0.28 - 0.34)
    (0.30, 1.3, MARMOL),
    (0.32, 1.5, MARMOL),
    (0.34, 1.5, MARMOL),
    # Muslos (0.34 - 0.48)
    (0.36, 1.8, MARMOL),
    (0.38, 2.0, MARMOL),
    (0.40, 2.1, MARMOL),
    (0.42, 2.2, MARMOL),
    (0.44, 2.4, MARMOL),
    (0.46, 2.5, MARMOL),
    (0.48, 2.6, MARMOL),
    # Cadera / panho (0.48 - 0.60)
    (0.50, 3.2, PANHO),
    (0.52, 3.5, PANHO),
    (0.54, 3.6, PANHO),
    (0.56, 3.5, PANHO),
    (0.58, 3.2, PANHO),
    (0.60, 3.0, PANHO),
    # Cintura (0.60 - 0.66)
    (0.62, 2.4, MARMOL),
    (0.64, 2.1, MARMOL),
    (0.66, 1.9, MARMOL),
    # Abdomen (0.66 - 0.74)
    (0.68, 2.0, MARMOL),
    (0.70, 2.2, MARMOL),
    (0.72, 2.3, MARMOL),
    (0.74, 2.5, MARMOL),
    # Pecho (0.74 - 0.84)
    (0.76, 2.8, MARMOL),
    (0.78, 3.0, MARMOL),
    (0.80, 3.2, MARMOL),
    (0.82, 3.0, MARMOL),
    (0.84, 2.8, MARMOL),
    # Hombros (0.84 - 0.90)
    (0.86, 3.5, MARMOL),
    (0.88, 3.8, MARMOL),
    (0.90, 3.8, MARMOL),
    # Munhones (brazos cortados) (0.90 - 0.94)
    (0.92, 3.4, SOMBRA),
    (0.94, 3.0, SOMBRA),
    # Cuello (0.94 - 0.97)
    (0.95, 1.3, MARMOL),
    (0.96, 1.1, MARMOL),
    (0.97, 1.0, MARMOL),
    # Cabeza (0.97 - 1.00)
    (0.98, 1.6, MARMOL),
    (0.99, 1.5, MARMOL),
    (1.00, 1.3, MARMOL),
]

voxels = []

# Generar la silueta: para cada capa Y, rellenar X segun half_width,
# con grosor de 2 subvoxels en Z (z = -0.125 y +0.125)
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

# --- DETALLES FACIALES (cabeza en y ~ 48-50) ---
head_y = 0.98 * H  # ~49.0
# Ojos
voxels.append(v(-0.375, head_y + 0.125, 0.25, SOMBRA))
voxels.append(v(0.375, head_y + 0.125, 0.25, SOMBRA))
# Nariz (proyeccion frontal)
voxels.append(v(0, head_y + 0.25, 0.375, MARMOL))
# Boca
voxels.append(v(0, head_y - 0.125, 0.25, SOMBRA))
# Pelo recogido (parte posterior de la cabeza)
for yf in [0.98, 0.99, 1.0]:
    y = yf * H
    for x in [-1.0, -0.75, -0.5, -0.25, 0, 0.25, 0.5, 0.75, 1.0]:
        for z in [-0.25, -0.125]:
            voxels.append(v(x, y, z, CABELLO))
# Mono
for yf in [0.99, 1.0]:
    y = yf * H
    for x in [-0.5, -0.25, 0, 0.25, 0.5]:
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
print(f"Venus de Milo: {len(unique)} subvoxels (alto {y_max - y_min:.2f} unidades = {int((y_max - y_min)/S)} subvoxels)")

if len(unique) > 30000:
    print(f"⚠ ATENCION: {len(unique)} subvoxels excede el limite de 30000. Reduciendo...")
    ratio = 30000 / len(unique)
    import random
    random.seed(42)
    unique = [vxl for vxl in unique if random.random() < ratio]
    print(f"  Reducido a {len(unique)} subvoxels")

# Posicion desde el suelo
# La escultura va desde y_min hasta y_max. 
# Queremos que y_min toque el suelo (y=1). 
# El centro del objeto debe estar en: y = 1 + H/2 = 26
center_y = 1.0 + H / 2
position = [round(px + 5, 1), round(center_y, 1), round(pz, 1)]

print(f"Enviando escultura...")
print(f"  Posicion: {position}")
print(f"  Resolucion: 8 (subvoxel=0.125)")
print(f"  Anclado: True")

result = mcp_call("create_sculpture", {
    "position": position,
    "resolution": 8,
    "voxels": unique,
    "anchored": True,
    "color": MARMOL,
})

if result.get("success"):
    print(f"\n✓ Venus de Milo creada!")
    print(f"  object_id={result['object_id']}")
    print(f"  voxel_count={result['voxel_count']}")
    print(f"  Posicion: {position}")
    print(f"  Altura: {H} bloques | Desde el suelo y=1")
    print(f"  Resolucion: 8 (subvoxel = 0.125)")
else:
    print(f"\n✗ Error: {result}")
    sys.exit(1)
