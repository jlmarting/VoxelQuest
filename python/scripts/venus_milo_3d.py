"""
Venus de Milo en MAXIMA RESOLUCION (8, subvoxel=0.125).
50 bloques = 400 cortes horizontales. Shell fina de 1 subvoxel.
Postura contrapposto con maxima definicion.

Tecnica: generacion DIRECTA sin relleno. Solo el borde exacto de cada elipse.
Cada corte horizontal genera ~30-40 subvoxels (perimetro). 
Total estimado: 400 cortes * 35 = ~14,000 + pliegues + detalles = ~25,000 max.
"""
import json, urllib.request, sys, math

URL = "http://localhost:9000/mcp"

MARMOL  = 0xE8DCC8
PANHO   = 0xD8C8A8
SOMBRA  = 0xB8A890
CABELLO = 0x8B6B4A
PEDESTAL = 0xA09080

S = 0.125        # subvoxel size (resolucion 8)
H = 50.0         # altura total
INV_S = 1.0 / S  # 8.0

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
# CONTRAPPOSTO: desplazamientos en X
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
# PERFIL ANATOMICO 3D con 60+ puntos de control para suavidad maxima
# (y_frac, w, df, db, color)
# ============================================================
POINTS = [
    # PEDESTAL
    (0.00, 2.0, 1.5, 1.5, PEDESTAL), (0.02, 2.0, 1.5, 1.5, PEDESTAL),
    (0.04, 2.0, 1.5, 1.5, PEDESTAL), (0.06, 1.9, 1.4, 1.4, PEDESTAL),
    (0.08, 1.8, 1.3, 1.3, PEDESTAL),
    # PIE DERECHO (apoyo)
    (0.10, 0.9, 0.7, 0.6, MARMOL), (0.12, 0.8, 0.6, 0.5, MARMOL),
    (0.14, 0.7, 0.5, 0.45, MARMOL), (0.16, 0.65, 0.45, 0.4, MARMOL),
    # TOBILLO
    (0.18, 0.6, 0.4, 0.35, MARMOL), (0.20, 0.55, 0.38, 0.33, MARMOL),
    # PANTORRILLA
    (0.22, 0.6, 0.42, 0.48, MARMOL), (0.24, 0.65, 0.45, 0.52, MARMOL),
    (0.26, 0.68, 0.48, 0.55, MARMOL), (0.28, 0.65, 0.45, 0.5, MARMOL),
    (0.30, 0.6, 0.4, 0.45, MARMOL),
    # RODILLA
    (0.32, 0.75, 0.55, 0.5, MARMOL), (0.34, 0.85, 0.6, 0.55, MARMOL),
    (0.36, 0.9, 0.65, 0.55, MARMOL),
    # MUSLO
    (0.38, 1.05, 0.75, 0.65, MARMOL), (0.40, 1.15, 0.82, 0.7, MARMOL),
    (0.42, 1.25, 0.88, 0.72, MARMOL), (0.44, 1.35, 0.95, 0.75, MARMOL),
    (0.46, 1.42, 1.0, 0.78, MARMOL), (0.48, 1.48, 1.05, 0.8, MARMOL),
    # CADERA/PANHO
    (0.50, 1.65, 1.15, 0.95, PANHO), (0.52, 1.8, 1.25, 1.0, PANHO),
    (0.54, 1.9, 1.32, 1.05, PANHO), (0.56, 1.95, 1.35, 1.08, PANHO),
    (0.58, 1.9, 1.3, 1.05, PANHO), (0.60, 1.75, 1.2, 0.95, PANHO),
    (0.62, 1.6, 1.1, 0.88, PANHO),
    # CINTURA (muy estrecha)
    (0.64, 1.3, 0.88, 0.72, MARMOL), (0.66, 1.15, 0.75, 0.6, MARMOL),
    (0.68, 1.0, 0.65, 0.52, MARMOL),
    # ABDOMEN
    (0.70, 1.08, 0.72, 0.58, MARMOL), (0.72, 1.18, 0.8, 0.62, MARMOL),
    (0.74, 1.28, 0.88, 0.68, MARMOL), (0.76, 1.38, 0.95, 0.72, MARMOL),
    # PECHO/BUSTO (protuberancia frontal)
    (0.78, 1.55, 1.15, 0.7, MARMOL), (0.80, 1.68, 1.28, 0.75, MARMOL),
    (0.82, 1.75, 1.35, 0.78, MARMOL), (0.84, 1.65, 1.2, 0.72, MARMOL),
    (0.86, 1.5, 1.05, 0.65, MARMOL),
    # HOMBROS
    (0.88, 1.7, 1.0, 0.72, MARMOL), (0.90, 1.82, 1.05, 0.75, MARMOL),
    (0.92, 1.8, 1.0, 0.7, MARMOL),
    # MUNIONES
    (0.94, 1.55, 0.85, 0.6, SOMBRA), (0.96, 1.3, 0.7, 0.5, SOMBRA),
    # CUELLO
    (0.97, 0.75, 0.45, 0.32, MARMOL), (0.98, 0.65, 0.38, 0.26, MARMOL),
    (0.985, 0.58, 0.33, 0.22, MARMOL),
    # CABEZA
    (0.99, 0.82, 0.52, 0.36, MARMOL), (0.995, 0.78, 0.48, 0.32, MARMOL),
    (1.00, 0.72, 0.42, 0.28, MARMOL),
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

# ============================================================
# GENERAR SHELL: solo el BORDE exacto de cada elipse
# ============================================================
num_cuts = int(H / S)  # 400 cortes exactos

for cut in range(num_cuts + 1):
    y = cut * S
    yf = y / H
    w, df, db, color = lerp_profile(yf)
    if w <= 0:
        continue
    
    shift_x = hip_shift(yf)
    twist = math.radians(torso_twist(yf))
    cos_t, sin_t = math.cos(twist), math.sin(twist)
    
    # Shell: recorrer angulos alrededor de la elipse
    # Cada 15 grados = 24 puntos por corte
    # Mas puntos donde la curvatura es mayor (arriba/abajo de la elipse)
    angles = []
    for deg in range(0, 360, 15):
        rad = math.radians(deg)
        angles.append(rad)
    
    for rad in angles:
        # Punto en el borde de la elipse: (x/w)^2 + (z/d)^2 = 1
        # x = w * cos(rad), z depende del cuadrante
        x_ellipse = w * math.cos(rad)
        
        # Determinar profundidad segun si es frente o espalda
        is_front = abs(rad) <= math.pi / 2 or abs(rad) >= 3 * math.pi / 2
        d = df if is_front else db
        z_ellipse = d * math.sin(rad)
        
        # Aplicar torsion
        x_rot = x_ellipse * cos_t - z_ellipse * sin_t
        z_rot = x_ellipse * sin_t + z_ellipse * cos_t
        
        # Aplicar shift
        x_final = x_rot + shift_x
        y_final = y
        z_final = z_rot
        
        # Guardar subvoxel
        voxels.append(v(x_final, y_final, z_final, color))
        
        # Anadir vecinos para grosor minimo (shell de 1 capa)
        # Solo en direccion normal a la superficie
        nx_n = x_ellipse / w if w > 0 else 0
        nz_n = z_ellipse / d if d > 0 else 0
        len_n = math.sqrt(nx_n**2 + nz_n**2)
        if len_n > 0:
            nx_n /= len_n
            nz_n /= len_n
            # Un subvoxel hacia dentro
            voxels.append(v(x_final - nx_n * S * 0.5, y_final, z_final - nz_n * S * 0.5, color))

# ============================================================
# PIERNA IZQUIERDA (adelantada, visible)
# ============================================================
for cut in range(int(0.08 * H / S), int(0.50 * H / S)):
    y = cut * S
    yf = y / H
    offset_z = 0.6 if yf < 0.15 else 0.35
    offset_x = -0.25
    
    if yf < 0.12: w, df, db = 0.65, 0.45, 0.35
    elif yf < 0.25: w, df, db = 0.55, 0.4, 0.45
    elif yf < 0.35: w, df, db = 0.75, 0.55, 0.5
    else: w, df, db = 0.85, 0.6, 0.55
    
    for deg in range(0, 360, 20):
        rad = math.radians(deg)
        x_ell = w * math.cos(rad)
        is_f = abs(rad) <= math.pi/2 or abs(rad) >= 3*math.pi/2
        d = df if is_f else db
        z_ell = d * math.sin(rad)
        voxels.append(v(x_ell + offset_x, y, z_ell + offset_z, MARMOL))

# ============================================================
# PANO: pliegues volumetricos con curvas parametricas
# ============================================================
print("Generando pliegues del panho en alta resolucion...")
# El panho cubre desde cadera (yf=0.50) hasta tobillos (yf=0.15)
# Pliegues ondulados con amplitud variable
for cut in range(int(0.15 * H / S), int(0.52 * H / S)):
    y = cut * S
    yf = y / H
    shift_x = hip_shift(yf)
    
    # Amplitud del pliegue: maxima en medio
    fold_depth = 0.25 * math.sin((yf - 0.15) / 0.37 * math.pi)
    
    # 12 pliegues alrededor (cada 30 grados, solo espalda y lados)
    for deg in [90, 105, 120, 135, 150, 165, 180, 195, 210, 225, 240, 255, 270]:
        rad = math.radians(deg)
        # Radio base desde el perfil
        w_p, df_p, db_p, _ = lerp_profile(yf)
        r_base = (df_p + db_p) / 2
        
        # Ondulacion
        r = r_base + fold_depth * math.sin(deg * math.pi / 45)
        
        x = r * math.cos(rad) + shift_x
        z = r * math.sin(rad)
        
        # Shell del pliegue: 2 subvoxels de grosor
        voxels.append(v(x, y, z, PANHO))
        voxels.append(v(x + S * 0.3, y, z + S * 0.3, PANHO))
        voxels.append(v(x - S * 0.3, y, z - S * 0.3, PANHO))

# ============================================================
# CABEZA: elipse refinada con perfil
# ============================================================
for cut in range(int(0.985 * H / S), int(H / S) + 1):
    y = cut * S
    yf = y / H
    t = max(0, min(1, (yf - 0.985) / 0.015))
    w = 0.55 + t * 0.17
    df = 0.35 + t * 0.07
    db = 0.25 + t * 0.05
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
voxels.append(v(-0.12 + shift_x_head, 0.99 * H, 0.32, SOMBRA))  # ojo izq
voxels.append(v(-0.02 + shift_x_head, 0.99 * H, 0.35, SOMBRA))  # ojo der (mas leve)
voxels.append(v(-0.08 + shift_x_head, 0.992 * H, 0.42, MARMOL))  # nariz
voxels.append(v(-0.1 + shift_x_head, 0.985 * H, 0.22, SOMBRA))   # boca
voxels.append(v(0.25 + shift_x_head, 0.99 * H, 0.08, MARMOL))   # oreja der

# CABELLO
for yf in [0.98, 0.99, 0.995, 1.0]:
    y = yf * H
    sx = hip_shift(yf)
    for deg in range(0, 360, 15):
        rad = math.radians(deg)
        # Cabello solo en parte superior y posterior
        if math.pi/3 < rad < 5*math.pi/3:
            r = 0.5 + 0.1 * math.sin(rad * 3)
            x = r * math.cos(rad) + sx
            z = r * math.sin(rad)
            voxels.append(v(x, y, z, CABELLO))
    # Mono superior
    for x in [-0.2, -0.1, 0, 0.1, 0.2]:
        for z in [-0.25, -0.15, 0, 0.1]:
            voxels.append(v(x + sx, y + S, z, CABELLO))

# DEDUPLICAR
seen = set()
unique = []
for vxl in voxels:
    key = (round(vxl["x"], 3), round(vxl["y"], 3), round(vxl["z"], 3))
    if key not in seen:
        seen.add(key)
        unique.append(vxl)

print(f"Venus resolucion 8: {len(unique)} subvoxels")

# LIMITE: 30,000
if len(unique) > 30000:
    print(f"⚠ {len(unique)} > 30,000. Optimizando manteniendo forma...")
    # Estrategia: cada 2do subvoxel en zonas de alta densidad (pliegues)
    # pero mantener TODOS los del cuerpo principal
    body = [v for v in unique if v["color"] != PANHO]
    drapery = [v for v in unique if v["color"] == PANHO]
    
    # Para pliegues: mantener solo los mas externos
    drapery_sorted = sorted(drapery, key=lambda v: abs(v["z"]) + abs(v["x"])*0.5, reverse=True)
    remaining = 30000 - len(body)
    drapery_sel = drapery_sorted[:max(0, remaining)]
    
    unique = body + drapery_sel
    print(f"  → Cuerpo: {len(body)}, Pliegues: {len(drapery_sel)}, Total: {len(unique)}")

# Borrar anterior
print("\nEliminando Venus anterior...")
for old_id in [12]:
    try:
        r = mcp_call("destroy_object", {"object_id": old_id, "cause": "replacement"})
        if r.get("success"):
            print(f"  ✓ ID={old_id} eliminado")
    except Exception:
        pass

# CREAR
center_y = 1.0 + H / 2
position = [round(px + 5, 1), round(center_y, 1), round(pz, 1)]

print(f"\nEnviando Venus resolucion 8 (maxima calidad)...")
print(f"  Posicion: {position}")
print(f"  Subvoxels: {len(unique)}")
print(f"  Resolucion: 8 (subvoxel={S})")

result = mcp_call("create_sculpture", {
    "position": position,
    "resolution": 8,
    "voxels": unique,
    "anchored": True,
    "color": MARMOL,
})

if result.get("success"):
    print(f"\n✓ Venus de Milo RESOLUCION 8 creada!")
    print(f"  object_id={result['object_id']}")
    print(f"  voxel_count={result['voxel_count']}")
    print(f"  Altura: {H} bloques")
    print(f"  Resolucion: 8 (subvoxel={S})")
    print(f"  Postura: contrapposto completo")
    print(f"  Definicion: {len(unique)} subvoxels con shell fina")
else:
    print(f"\n✗ Error: {result}")
    sys.exit(1)
