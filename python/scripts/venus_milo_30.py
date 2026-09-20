"""
Venus de Milo de 30 bloques en las afueras del castillo.
Resolucion 8 (subvoxel=0.125), altura 30 bloques = 240 cortes.
Misma calidad: contrapposto, paño volumetrico, shell fina.
"""
import json, urllib.request, sys, math

URL = "http://localhost:9000/mcp"

MARMOL  = 0xE8DCC8
PANHO   = 0xD8C8A8
SOMBRA  = 0xB8A890
CABELLO = 0x8B6B4A
PEDESTAL = 0xA09080

S = 0.125
H = 30.0  # 30 bloques de alto
INV_S = 1.0 / S

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

players = mcp_call("list_players", {})
p = players.get("players", [{}])[0] if isinstance(players, dict) else {}
px, pz = p.get("x", 0), p.get("z", 0)
print(f"Jugador en ({px:.1f}, {pz:.1f})")

# ============================================================
# CONTRAPPOSTO
# ============================================================
def hip_shift(yf):
    if yf < 0.45:
        return 0
    elif yf < 0.65:
        t = (yf - 0.45) / 0.2
        return -0.6 * math.sin(t * math.pi)
    elif yf < 0.85:
        t = (yf - 0.65) / 0.2
        return -0.6 * (1 - t) + 0.4 * t
    else:
        return 0.4

def torso_twist(yf):
    if yf < 0.5:
        return 0
    elif yf < 0.8:
        t = (yf - 0.5) / 0.3
        return 12 * t
    return 12

# ============================================================
# PERFIL ANATOMICO - ESCALADO para 30 bloques
# ============================================================
SCALE = H / 50.0  # 0.6

POINTS = [
    # PEDESTAL
    (0.00, 2.0*SCALE, 1.5*SCALE, 1.5*SCALE, PEDESTAL),
    (0.04, 2.0*SCALE, 1.5*SCALE, 1.5*SCALE, PEDESTAL),
    (0.08, 1.8*SCALE, 1.3*SCALE, 1.3*SCALE, PEDESTAL),
    # PIE
    (0.10, 0.9*SCALE, 0.7*SCALE, 0.6*SCALE, MARMOL),
    (0.14, 0.7*SCALE, 0.5*SCALE, 0.45*SCALE, MARMOL),
    (0.18, 0.6*SCALE, 0.4*SCALE, 0.35*SCALE, MARMOL),
    # PANTORRILLA
    (0.22, 0.6*SCALE, 0.42*SCALE, 0.48*SCALE, MARMOL),
    (0.26, 0.68*SCALE, 0.48*SCALE, 0.55*SCALE, MARMOL),
    (0.30, 0.6*SCALE, 0.4*SCALE, 0.45*SCALE, MARMOL),
    # RODILLA
    (0.34, 0.85*SCALE, 0.6*SCALE, 0.55*SCALE, MARMOL),
    (0.38, 1.05*SCALE, 0.75*SCALE, 0.65*SCALE, MARMOL),
    # MUSLO
    (0.42, 1.25*SCALE, 0.88*SCALE, 0.72*SCALE, MARMOL),
    (0.46, 1.42*SCALE, 1.0*SCALE, 0.78*SCALE, MARMOL),
    (0.50, 1.65*SCALE, 1.15*SCALE, 0.95*SCALE, PANHO),
    # CADERA
    (0.54, 1.9*SCALE, 1.32*SCALE, 1.05*SCALE, PANHO),
    (0.58, 1.9*SCALE, 1.3*SCALE, 1.05*SCALE, PANHO),
    (0.62, 1.6*SCALE, 1.1*SCALE, 0.88*SCALE, PANHO),
    # CINTURA
    (0.66, 1.15*SCALE, 0.75*SCALE, 0.6*SCALE, MARMOL),
    (0.70, 1.08*SCALE, 0.72*SCALE, 0.58*SCALE, MARMOL),
    # ABDOMEN
    (0.74, 1.28*SCALE, 0.88*SCALE, 0.68*SCALE, MARMOL),
    # PECHO
    (0.78, 1.55*SCALE, 1.15*SCALE, 0.7*SCALE, MARMOL),
    (0.82, 1.75*SCALE, 1.35*SCALE, 0.78*SCALE, MARMOL),
    (0.86, 1.5*SCALE, 1.05*SCALE, 0.65*SCALE, MARMOL),
    # HOMBROS
    (0.90, 1.82*SCALE, 1.05*SCALE, 0.75*SCALE, MARMOL),
    (0.94, 1.55*SCALE, 0.85*SCALE, 0.6*SCALE, SOMBRA),
    # CUELLO
    (0.97, 0.75*SCALE, 0.45*SCALE, 0.32*SCALE, MARMOL),
    (0.985, 0.58*SCALE, 0.33*SCALE, 0.22*SCALE, MARMOL),
    # CABEZA
    (0.995, 0.78*SCALE, 0.48*SCALE, 0.32*SCALE, MARMOL),
    (1.00, 0.72*SCALE, 0.42*SCALE, 0.28*SCALE, MARMOL),
]

def lerp_profile(yf):
    for i in range(len(POINTS) - 1):
        y0, w0, df0, db0, c0 = POINTS[i]
        y1, w1, df1, db1, c1 = POINTS[i + 1]
        if y0 <= yf <= y1 or (i == len(POINTS) - 2 and yf >= y1):
            t = (yf - y0) / (y1 - y0) if y1 > y0 else 0
            t = max(0, min(1, t))
            return (w0 + (w1 - w0) * t,
                    df0 + (df1 - df0) * t,
                    db0 + (db1 - db0) * t,
                    c0 if t < 0.5 else c1)
    return 0, 0, 0, MARMOL

voxels = []

# SHELL fino
num_cuts = int(H / S)
for cut in range(num_cuts + 1):
    y = cut * S
    yf = y / H
    w, df, db, color = lerp_profile(yf)
    if w <= 0:
        continue
    
    shift_x = hip_shift(yf)
    twist = math.radians(torso_twist(yf))
    cos_t, sin_t = math.cos(twist), math.sin(twist)
    
    for deg in range(0, 360, 15):
        rad = math.radians(deg)
        x_ellipse = w * math.cos(rad)
        is_front = abs(rad) <= math.pi / 2 or abs(rad) >= 3 * math.pi / 2
        d = df if is_front else db
        z_ellipse = d * math.sin(rad)
        
        x_rot = x_ellipse * cos_t - z_ellipse * sin_t
        z_rot = x_ellipse * sin_t + z_ellipse * cos_t
        x_final = x_rot + shift_x
        
        voxels.append(v(x_final, y, z_rot, color))
        
        # Vecino para grosor minimo
        nx_n = x_ellipse / w if w > 0 else 0
        nz_n = z_ellipse / d if d > 0 else 0
        len_n = math.sqrt(nx_n**2 + nz_n**2)
        if len_n > 0:
            nx_n /= len_n
            nz_n /= len_n
            voxels.append(v(x_final - nx_n * S * 0.5, y, z_rot - nz_n * S * 0.5, color))

# PIERNA IZQUIERDA
for cut in range(int(0.08 * H / S), int(0.50 * H / S)):
    y = cut * S
    yf = y / H
    offset_z = 0.6*SCALE if yf < 0.15 else 0.35*SCALE
    offset_x = -0.25*SCALE
    
    if yf < 0.12: w, df, db = 0.65*SCALE, 0.45*SCALE, 0.35*SCALE
    elif yf < 0.25: w, df, db = 0.55*SCALE, 0.4*SCALE, 0.45*SCALE
    elif yf < 0.35: w, df, db = 0.75*SCALE, 0.55*SCALE, 0.5*SCALE
    else: w, df, db = 0.85*SCALE, 0.6*SCALE, 0.55*SCALE
    
    for deg in range(0, 360, 20):
        rad = math.radians(deg)
        x_ell = w * math.cos(rad)
        is_f = abs(rad) <= math.pi/2 or abs(rad) >= 3*math.pi/2
        d = df if is_f else db
        z_ell = d * math.sin(rad)
        voxels.append(v(x_ell + offset_x, y, z_ell + offset_z, MARMOL))

# PANO pliegues
for cut in range(int(0.15 * H / S), int(0.52 * H / S)):
    y = cut * S
    yf = y / H
    shift_x = hip_shift(yf)
    fold_depth = 0.25*SCALE * math.sin((yf - 0.15) / 0.37 * math.pi)
    
    for deg in [90, 105, 120, 135, 150, 165, 180, 195, 210, 225, 240, 255, 270]:
        rad = math.radians(deg)
        w_p, df_p, db_p, _ = lerp_profile(yf)
        r_base = (df_p + db_p) / 2
        r = r_base + fold_depth * math.sin(deg * math.pi / 45)
        x = r * math.cos(rad) + shift_x
        z = r * math.sin(rad)
        voxels.append(v(x, y, z, PANHO))
        voxels.append(v(x + S * 0.3, y, z + S * 0.3, PANHO))
        voxels.append(v(x - S * 0.3, y, z - S * 0.3, PANHO))

# CABEZA
for cut in range(int(0.985 * H / S), int(H / S) + 1):
    y = cut * S
    yf = y / H
    t = max(0, min(1, (yf - 0.985) / 0.015))
    w = 0.55*SCALE + t * 0.17*SCALE
    df = 0.35*SCALE + t * 0.07*SCALE
    db = 0.25*SCALE + t * 0.05*SCALE
    shift_x = hip_shift(yf)
    
    for deg in range(0, 360, 12):
        rad = math.radians(deg)
        x_ell = w * math.cos(rad)
        is_f = abs(rad) <= math.pi/2 or abs(rad) >= 3*math.pi/2
        d = df if is_f else db
        z_ell = d * math.sin(rad)
        voxels.append(v(x_ell + shift_x, y, z_ell, MARMOL))

# DETALLES FACIALES
shift_x_head = hip_shift(0.99)
voxels.append(v(-0.12*SCALE + shift_x_head, 0.99 * H, 0.32*SCALE, SOMBRA))
voxels.append(v(-0.02*SCALE + shift_x_head, 0.99 * H, 0.35*SCALE, SOMBRA))
voxels.append(v(-0.08*SCALE + shift_x_head, 0.992 * H, 0.42*SCALE, MARMOL))
voxels.append(v(-0.1*SCALE + shift_x_head, 0.985 * H, 0.22*SCALE, SOMBRA))
voxels.append(v(0.25*SCALE + shift_x_head, 0.99 * H, 0.08*SCALE, MARMOL))

# CABELLO
for yf in [0.98, 0.99, 0.995, 1.0]:
    y = yf * H
    sx = hip_shift(yf)
    for deg in range(0, 360, 15):
        rad = math.radians(deg)
        if math.pi/3 < rad < 5*math.pi/3:
            r = 0.5*SCALE + 0.1*SCALE * math.sin(rad * 3)
            x = r * math.cos(rad) + sx
            z = r * math.sin(rad)
            voxels.append(v(x, y, z, CABELLO))
    for x in [-0.2*SCALE, -0.1*SCALE, 0, 0.1*SCALE, 0.2*SCALE]:
        for z in [-0.25*SCALE, -0.15*SCALE, 0, 0.1*SCALE]:
            voxels.append(v(x + sx, y + S, z, CABELLO))

# DEDUPLICAR
seen = set()
unique = []
for vxl in voxels:
    key = (round(vxl["x"], 3), round(vxl["y"], 3), round(vxl["z"], 3))
    if key not in seen:
        seen.add(key)
        unique.append(vxl)

print(f"Venus 30 bloques: {len(unique)} subvoxels")

if len(unique) > 30000:
    print(f"⚠ {len(unique)} > 30,000, optimizando...")
    body = [v for v in unique if v["color"] != PANHO]
    drapery = [v for v in unique if v["color"] == PANHO]
    drapery_sorted = sorted(drapery, key=lambda v: abs(v["z"]) + abs(v["x"])*0.5, reverse=True)
    remaining = 30000 - len(body)
    drapery_sel = drapery_sorted[:max(0, remaining)]
    unique = body + drapery_sel
    print(f"  → {len(unique)} subvoxels")

# POSICION: afueras del castillo (40 bloques al norte del jugador)
pos_x = round(px, 1)
pos_z = round(pz - 40, 1)  # 40 bloques al norte
pos_y = round(1.0 + H / 2, 1)

print(f"\nColocando Venus en las afueras del castillo...")
print(f"  Posicion: ({pos_x}, {pos_y}, {pos_z})")
print(f"  Altura: {H} bloques")
print(f"  Resolucion: 8 (subvoxel={S})")

result = mcp_call("create_sculpture", {
    "position": [pos_x, pos_y, pos_z],
    "resolution": 8,
    "voxels": unique,
    "anchored": True,
    "color": MARMOL,
})

if result.get("success"):
    print(f"\n✓ Venus de 30 bloques creada en las afueras del castillo!")
    print(f"  object_id={result['object_id']}")
    print(f"  voxel_count={result['voxel_count']}")
    print(f"  Posicion: ({pos_x}, {pos_y}, {pos_z})")
    print(f"  Distancia al jugador: ~40 bloques al norte")
else:
    print(f"\n✗ Error: {result}")
    sys.exit(1)
