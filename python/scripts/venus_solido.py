"""
Venus de Milo SOLIDA con resolucion 2 (subvoxel=0.5).
30 bloques de alto = 60 cortes. Perfil GENEROSO (cuerpo ancho, no delgado).
~25,000 subvoxels = solida, visible, bien iluminada.
Blanco mármol 0xF5F5F5.

Perfil generoso: multiplicador 2.5x sobre las proporciones anatomicas reales
para que se vea sustancial desde lejos.
"""
import json, urllib.request, sys, math

URL = "http://localhost:9000/mcp"

MARMOL  = 0xF5F5F5
PANHO   = 0xE8DDD0
SOMBRA  = 0xD0C8C0
CABELLO = 0x8B6B4A
PEDESTAL = 0xC0B8B0

S = 0.5   # resolucion 2
H = 30.0  # 30 bloques

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
    if yf < 0.45: return 0
    elif yf < 0.65:
        t = (yf - 0.45) / 0.2
        return -1.2 * math.sin(t * math.pi)
    elif yf < 0.85:
        t = (yf - 0.65) / 0.2
        return -1.2 * (1 - t) + 0.8 * t
    return 0.8

def torso_twist(yf):
    if yf < 0.5: return 0
    elif yf < 0.8:
        t = (yf - 0.5) / 0.3
        return 15 * t
    return 15

# ============================================================
# PERFIL GENEROSO para 30 bloques
# Multiplicador: 2.5x para cuerpo sustancial
# ============================================================
M = 2.5  # multiplicador de volumen

POINTS = [
    # PEDESTAL
    (0.00, 2.0*M, 1.5*M, 1.5*M, PEDESTAL),
    (0.05, 2.0*M, 1.5*M, 1.5*M, PEDESTAL),
    (0.08, 1.8*M, 1.3*M, 1.3*M, PEDESTAL),
    # PIES
    (0.10, 1.0*M, 0.8*M, 0.7*M, MARMOL),
    (0.14, 0.8*M, 0.6*M, 0.5*M, MARMOL),
    (0.18, 0.7*M, 0.5*M, 0.4*M, MARMOL),
    # PANTORRILLAS
    (0.22, 0.75*M, 0.55*M, 0.6*M, MARMOL),
    (0.26, 0.85*M, 0.6*M, 0.7*M, MARMOL),
    (0.30, 0.75*M, 0.55*M, 0.6*M, MARMOL),
    # RODILLAS
    (0.34, 0.95*M, 0.7*M, 0.65*M, MARMOL),
    (0.38, 1.15*M, 0.85*M, 0.75*M, MARMOL),
    # MUSLOS
    (0.42, 1.4*M, 1.0*M, 0.85*M, MARMOL),
    (0.46, 1.6*M, 1.15*M, 0.9*M, MARMOL),
    (0.50, 1.8*M, 1.3*M, 1.05*M, PANHO),
    # CADERA / PANHO
    (0.54, 2.1*M, 1.5*M, 1.2*M, PANHO),
    (0.58, 2.2*M, 1.5*M, 1.2*M, PANHO),
    (0.62, 1.85*M, 1.3*M, 1.0*M, PANHO),
    # CINTURA
    (0.66, 1.35*M, 0.9*M, 0.7*M, MARMOL),
    (0.70, 1.25*M, 0.85*M, 0.65*M, MARMOL),
    # ABDOMEN
    (0.74, 1.45*M, 1.0*M, 0.75*M, MARMOL),
    # PECHO
    (0.78, 1.75*M, 1.3*M, 0.8*M, MARMOL),
    (0.82, 2.0*M, 1.5*M, 0.9*M, MARMOL),
    (0.86, 1.75*M, 1.25*M, 0.75*M, MARMOL),
    # HOMBROS
    (0.90, 2.1*M, 1.2*M, 0.85*M, MARMOL),
    (0.94, 1.75*M, 1.0*M, 0.7*M, SOMBRA),
    # CUELLO
    (0.97, 0.85*M, 0.5*M, 0.35*M, MARMOL),
    (0.985, 0.65*M, 0.4*M, 0.25*M, MARMOL),
    # CABEZA
    (0.995, 0.9*M, 0.6*M, 0.4*M, MARMOL),
    (1.00, 0.85*M, 0.55*M, 0.35*M, MARMOL),
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

# RELLENO SOLIDO
num_cuts = int(H / S)  # 60 cortes
for cut in range(num_cuts + 1):
    y = cut * S
    yf = y / H
    w, df, db, color = lerp_profile(yf)
    if w <= 0:
        continue
    
    shift_x = hip_shift(yf)
    twist = math.radians(torso_twist(yf))
    cos_t, sin_t = math.cos(twist), math.sin(twist)
    
    # Elipse solida completa
    nx = int(w / S) + 1
    nz = int(max(df, db) / S) + 1
    
    for ix in range(-nx, nx + 1):
        for iz in range(-nz, nz + 1):
            x = ix * S
            z = iz * S
            
            if w > 0:
                x_ratio = abs(x) / w
            else:
                x_ratio = 0
            
            z_limit = df if z >= 0 else db
            if z_limit > 0:
                z_ratio = abs(z) / z_limit
            else:
                z_ratio = 0
            
            if x_ratio ** 2 + z_ratio ** 2 <= 1.0:
                x_rot = x * cos_t - z * sin_t
                z_rot = x * sin_t + z * cos_t
                x_final = x_rot + shift_x
                voxels.append(v(x_final, y, z_rot, color))

# PIERNA IZQUIERDA
for cut in range(int(0.08 * H / S), int(0.50 * H / S)):
    y = cut * S
    yf = y / H
    offset_z = 0.8*M if yf < 0.15 else 0.5*M
    offset_x = -0.4*M
    
    if yf < 0.12: w, df, db = 0.8*M, 0.55*M, 0.45*M
    elif yf < 0.25: w, df, db = 0.7*M, 0.5*M, 0.55*M
    elif yf < 0.35: w, df, db = 0.9*M, 0.65*M, 0.6*M
    else: w, df, db = 1.05*M, 0.75*M, 0.7*M
    
    nx = int(w / S) + 1
    nz = int(max(df, db) / S) + 1
    for ix in range(-nx, nx + 1):
        for iz in range(-nz, nz + 1):
            x = ix * S + offset_x
            z = iz * S + offset_z
            x_rel = x - offset_x
            z_rel = z - offset_z
            if w > 0 and (abs(x_rel)/w)**2 + (abs(z_rel)/max(df,db))**2 <= 1.0:
                voxels.append(v(x, y, z, MARMOL))

# CABEZA
for cut in range(int(0.985 * H / S), int(H / S) + 1):
    y = cut * S
    yf = y / H
    t = max(0, min(1, (yf - 0.985) / 0.015))
    w = 0.65*M + t * 0.2*M
    df = 0.45*M + t * 0.1*M
    db = 0.3*M + t * 0.08*M
    shift_x = hip_shift(yf)
    
    nx = int(w / S) + 1
    nz = int(max(df, db) / S) + 1
    for ix in range(-nx, nx + 1):
        for iz in range(-nz, nz + 1):
            x = ix * S
            z = iz * S
            if w > 0 and (abs(x)/w)**2 + (abs(z)/max(df,db))**2 <= 1.0:
                voxels.append(v(x + shift_x, y, z, MARMOL))

# CABELLO
for yf in [0.98, 0.99, 0.995, 1.0]:
    y = yf * H
    sx = hip_shift(yf)
    for deg in range(0, 360, 15):
        rad = math.radians(deg)
        if math.pi/3 < rad < 5*math.pi/3:
            r = 0.6*M + 0.12*M * math.sin(rad * 3)
            x = r * math.cos(rad) + sx
            z = r * math.sin(rad)
            voxels.append(v(x, y, z, CABELLO))

# DEDUPLICAR
seen = set()
unique = []
for vxl in voxels:
    key = (round(vxl["x"], 3), round(vxl["y"], 3), round(vxl["z"], 3))
    if key not in seen:
        seen.add(key)
        unique.append(vxl)

print(f"Venus SOLIDO generoso: {len(unique)} subvoxels (resolucion 2)")

# LIMITE 30k
if len(unique) > 30000:
    print(f"⚠ {len(unique)} > 30,000. Reduciendo...")
    def surface_score(vxl):
        yf = vxl["y"] / H
        w, df, db, _ = lerp_profile(yf)
        if w <= 0:
            return 0
        x_rel = abs(vxl["x"] - hip_shift(yf))
        z_limit = df if vxl["z"] >= 0 else db
        return (x_rel/w)**2 + (abs(vxl["z"])/max(z_limit,0.1))**2
    
    unique_sorted = sorted(unique, key=surface_score, reverse=True)
    unique = unique_sorted[:30000]
    print(f"  → {len(unique)} subvoxels")

# BORRAR anterior (ID=15)
print("\nEliminando Venus anterior...")
for old_id in [15]:
    try:
        r = mcp_call("destroy_object", {"object_id": old_id, "cause": "replacement"})
        if r.get("success"):
            print(f"  ✓ ID={old_id} eliminado")
    except Exception:
        pass

# CREAR
center_y = 1.0 + H / 2
position = [round(px + 8, 1), round(center_y, 1), round(pz - 15, 1)]

print(f"\nEnviando Venus SOLIDA generosa (resolucion 2)...")
print(f"  Posicion: {position}")
print(f"  Subvoxels: {len(unique)}")
print(f"  Multiplicador: {M}x (cuerpo ancho)")

result = mcp_call("create_sculpture", {
    "position": position,
    "resolution": 2,
    "voxels": unique,
    "anchored": True,
    "color": MARMOL,
})

if result.get("success"):
    print(f"\n✓ Venus de Milo SOLIDA GENEROSA creada!")
    print(f"  object_id={result['object_id']}")
    print(f"  voxel_count={result['voxel_count']}")
    print(f"  Altura: {H} bloques")
    print(f"  Resolucion: 2 (subvoxel={S})")
    print(f"  Multiplicador: {M}x")
else:
    print(f"\n✗ Error: {result}")
    sys.exit(1)
