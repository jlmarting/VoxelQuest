"""Lluvia de 20 meteoritos de radio 4 con trayectorias inclinadas.

- 20 meteoritos, radio 4, cayendo de forma irregular durante 60 segundos.
- Ángulo de trayectoria: aleatorio entre 0° (perpendicular al suelo) y
  15° respecto a la perpendicular, con dirección azimutal aleatoria.
- Cada impacto crea un cráter de profundidad/dimensión variable.
- 75% de probabilidad de incendios en los alrededores.

Uso: python scripts/lluvia_meteoritos_pequenos.py
"""
from __future__ import annotations
import json
import urllib.request
import sys
import time
import math
import random

AIR = 0
S = 1.0  # subvoxel size (resolution 1)

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

def make_meteorite_voxels(radius=4.0):
    """Esfera de radio 4 con textura rocosa."""
    voxels = []
    r2 = radius * radius
    steps = int(radius / S)
    for ix in range(-steps, steps + 1):
        for iy in range(-steps, steps + 1):
            for iz in range(-steps, steps + 1):
                x = ix * S
                y = iy * S
                z = iz * S
                d2 = x * x + y * y + z * z
                if d2 <= r2:
                    frac = d2 / r2
                    if frac < 0.3:
                        color = 0x5C4033
                    elif frac < 0.7:
                        color = 0x8B4513
                    else:
                        color = 0xA0522D
                    voxels.append({"x": round(x, 3), "y": round(y, 3),
                                   "z": round(z, 3), "color": color, "size": S})
    return voxels

def create_crater(cx, cy, cz, radius, max_depth):
    blocks = []
    r_int = int(radius)
    for dx in range(-r_int, r_int + 1):
        for dz in range(-r_int, r_int + 1):
            dist = math.hypot(dx, dz)
            if dist > radius:
                continue
            depth = int((1 - dist / radius) * max_depth)
            for dy in range(0, depth + 1):
                blocks.append({"x": cx + dx, "y": cy - dy, "z": cz + dz, "type": AIR})
    return blocks

def create_rim(cx, cy, cz, radius):
    rim = []
    for dx in range(-int(radius) - 1, int(radius) + 2):
        for dz in range(-int(radius) - 1, int(radius) + 2):
            dist = math.hypot(dx, dz)
            if radius - 1.0 <= dist <= radius + 1.0:
                rim.append({"x": cx + dx, "y": cy, "z": cz + dz, "type": 3})
    return rim

def spawn_fire(cx, cy, cz):
    voxels = []
    ROJO, NARANJA, AMARILLO = 0xFF4500, 0xFF8C00, 0xFFD700
    for iy in range(4):
        y = iy * 0.25
        frac = iy / 4
        color = ROJO if frac < 0.4 else (NARANJA if frac < 0.75 else AMARILLO)
        r = 0.4 * (1 - frac * 0.6)
        nr = int(r / 0.25)
        for ix in range(-nr, nr + 1):
            for iz in range(-nr, nr + 1):
                if (ix * 0.25) ** 2 + (iz * 0.25) ** 2 <= r * r:
                    voxels.append({"x": round(ix * 0.25, 3), "y": round(y, 3),
                                   "z": round(iz * 0.25, 3), "color": color, "size": 0.25})
    mcp_call("create_sculpture", {
        "position": [cx + 0.5, cy + 0.5, cz + 0.5],
        "resolution": 4, "voxels": voxels, "anchored": True, "color": NARANJA,
    })
    mcp_call("create_object", {
        "kind": "sphere", "position": [cx + 0.5, cy + 1.5, cz + 0.5],
        "scale": [1.0, 1.0, 1.0], "color": NARANJA, "emissive": True,
        "mass": 0.0, "anchored": True,
    })

def main():
    random.seed()
    CENTER_X, CENTER_Z = 10, 10
    GROUND_Y = 24
    START_Y = 55.0
    DURATION = 60.0

    # 20 meteoritos con trayectoria inclinada aleatoria
    meteoritos = []
    for i in range(20):
        # Posición de impacto irregular (radio 15-40 del centro)
        ang = random.uniform(0, 2 * math.pi)
        dist = random.uniform(15, 40)
        impact_x = CENTER_X + math.cos(ang) * dist
        impact_z = CENTER_Z + math.sin(ang) * dist
        # Ángulo de inclinación: 0° a 15° respecto a la perpendicular
        tilt = random.uniform(0, math.radians(15))
        # Dirección azimutal de la inclinación
        azim = random.uniform(0, 2 * math.pi)
        # Desplazamiento horizontal total = altura * tan(tilt)
        fall_height = START_Y - GROUND_Y
        horiz = fall_height * math.tan(tilt)
        # Punto de origen (arriba) = impacto - desplazamiento horizontal
        start_x = impact_x - math.cos(azim) * horiz
        start_z = impact_z - math.sin(azim) * horiz
        # Vector de dirección unitario (de origen a impacto)
        dx = impact_x - start_x
        dz = impact_z - start_z
        dy = GROUND_Y - START_Y
        length = math.sqrt(dx * dx + dy * dy + dz * dz)
        meteoritos.append({
            "start": (start_x, START_Y, start_z),
            "impact": (int(impact_x), GROUND_Y, int(impact_z)),
            "dir": (dx / length, dy / length, dz / length),
            "delay": random.uniform(0, DURATION),
            "max_depth": random.randint(2, 6),
            "crater_radius": 4.0 + random.uniform(1.0, 2.5),
            "fire": random.random() < 0.75,
        })

    print(f"☄️ Lluvia de {len(meteoritos)} meteoritos de radio 4 (60s):")
    for i, m in enumerate(meteoritos):
        tilt_deg = math.degrees(math.atan2(
            math.hypot(m["dir"][0], m["dir"][2]), -m["dir"][1]))
        print(f"  #{i+1}: impacto={m['impact']} inclinación={tilt_deg:.1f}° "
              f"t+{m['delay']:.1f}s incendio={'SÍ' if m['fire'] else 'no'}")

    meteoritos.sort(key=lambda m: m["delay"])
    start = time.time()

    for i, m in enumerate(meteoritos):
        wait = m["delay"] - (time.time() - start)
        if wait > 0:
            print(f"\n⏳ Esperando {wait:.1f}s para meteorito #{i+1}...")
            time.sleep(wait)

        sx, sy, sz = m["start"]
        ix, iy, iz = m["impact"]
        dx, dy, dz = m["dir"]
        print(f"\n☄️ Meteorito #{i+1}: de ({sx:.0f},{sy:.0f},{sz:.0f}) → ({ix},{iy},{iz})")

        # Crear meteorito en el origen
        voxels = make_meteorite_voxels(4.0)
        r = mcp_call("create_sculpture", {
            "position": [sx, sy, sz], "resolution": 1,
            "voxels": voxels, "anchored": True, "color": 0x8B4513,
        })
        if not r.get("success"):
            print(f"  ✗ Error creando meteorito: {r}")
            continue
        oid = r["object_id"]

        # Caída a lo largo de la trayectoria inclinada
        steps = int(fall_height := (sy - iy) / 1.0)
        for s in range(1, steps + 1):
            t = s / steps
            px = sx + dx * (sy - iy) * t
            py = sy + dy * (sy - iy) * t
            pz = sz + dz * (sy - iy) * t
            mcp_call("update_object", {"object_id": oid, "patch": {"position": [px, py, pz]}})
            time.sleep(0.02)

        # Impacto
        print(f"  💥 ¡IMPACTO en ({ix}, {iy}, {iz})!")
        crater = create_crater(ix, iy, iz, m["crater_radius"], m["max_depth"])
        BATCH = 500
        for j in range(0, len(crater), BATCH):
            mcp_call("apply_blocks", {"blocks": crater[j:j + BATCH]}, timeout=120)
        rim = create_rim(ix, iy, iz, m["crater_radius"])
        for j in range(0, len(rim), BATCH):
            mcp_call("apply_blocks", {"blocks": rim[j:j + BATCH]}, timeout=120)

        mcp_call("destroy_object", {"object_id": oid, "cause": "impacto"})

        if m["fire"]:
            n_fires = random.randint(1, 3)
            for _ in range(n_fires):
                fang = random.uniform(0, 2 * math.pi)
                fdist = random.uniform(3, 8)
                fx = ix + math.cos(fang) * fdist
                fz = iz + math.sin(fang) * fdist
                spawn_fire(int(fx), iy, int(fz))
            print(f"  🔥 Incendio ({n_fires} focos)")
        else:
            print(f"  (sin incendio)")

        print(f"  ✓ Cráter radio {m['crater_radius']:.1f}, prof {m['max_depth']}")

    print(f"\n✓ Lluvia de {len(meteoritos)} meteoritos completada en {time.time()-start:.1f}s")

if __name__ == "__main__":
    main()