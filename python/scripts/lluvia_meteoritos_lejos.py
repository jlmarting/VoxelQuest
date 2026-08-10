"""Lluvia de 10 meteoritos lejos de Carcassonne.

Centro de impacto en (60,-60) (suelo en y=23), radio 15-40 → impactos entre
x:20..100, z:-100..-20, lejos de la muralla de Carcassonne (±30).
Tiempos aleatorios en [0,20]s, cráteres de profundidad/dimensión variables,
75% de probabilidad de incendios.
"""
from __future__ import annotations
import json
import urllib.request
import sys
import time
import math
import random

AIR = 0
S = 1.0

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

def make_meteorite_voxels(radius):
    voxels = []
    r2 = radius * radius
    steps = int(radius / S)
    for ix in range(-steps, steps + 1):
        for iy in range(-steps, steps + 1):
            for iz in range(-steps, steps + 1):
                x = ix * S; y = iy * S; z = iz * S
                d2 = x*x + y*y + z*z
                if d2 <= r2:
                    frac = d2 / r2
                    color = 0x5C4033 if frac < 0.3 else (0x8B4513 if frac < 0.7 else 0xA0522D)
                    voxels.append({"x": round(x,3), "y": round(y,3), "z": round(z,3), "color": color, "size": S})
    return voxels

def create_crater(cx, cy, cz, radius, max_depth):
    blocks = []
    r_int = int(radius)
    for dx in range(-r_int, r_int + 1):
        for dz in range(-r_int, r_int + 1):
            dist = math.hypot(dx, dz)
            if dist > radius: continue
            depth = int((1 - dist / radius) * max_depth)
            for dy in range(0, depth + 1):
                blocks.append({"x": cx+dx, "y": cy-dy, "z": cz+dz, "type": AIR})
    return blocks

def create_rim(cx, cy, cz, radius):
    rim = []
    for dx in range(-int(radius)-1, int(radius)+2):
        for dz in range(-int(radius)-1, int(radius)+2):
            dist = math.hypot(dx, dz)
            if radius - 1.0 <= dist <= radius + 1.0:
                rim.append({"x": cx+dx, "y": cy, "z": cz+dz, "type": 3})
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
        for ix in range(-nr, nr+1):
            for iz in range(-nr, nr+1):
                if (ix*0.25)**2 + (iz*0.25)**2 <= r*r:
                    voxels.append({"x": round(ix*0.25,3), "y": round(y,3), "z": round(iz*0.25,3), "color": color, "size": 0.25})
    mcp_call("create_sculpture", {"position": [cx+0.5, cy+0.5, cz+0.5], "resolution": 4,
        "voxels": voxels, "anchored": True, "color": NARANJA})
    mcp_call("create_object", {"kind": "sphere", "position": [cx+0.5, cy+1.5, cz+0.5],
        "scale": [1.0,1.0,1.0], "color": NARANJA, "emissive": True, "mass": 0.0, "anchored": True})

def main():
    random.seed()
    CENTER_X, CENTER_Z = 60, -60
    GROUND_Y = 23
    START_Y = 55.0

    meteoritos = []
    for i in range(10):
        ang = random.uniform(0, 2*math.pi)
        dist = random.uniform(15, 40)
        x = CENTER_X + math.cos(ang) * dist
        z = CENTER_Z + math.sin(ang) * dist
        radius = random.uniform(4, 10)
        delay = random.uniform(0, 20)
        meteoritos.append({
            "x": round(x), "z": round(z), "radius": radius, "delay": delay,
            "max_depth": random.randint(3, 8),
            "crater_radius": radius + random.uniform(1.5, 3.5),
            "fire": random.random() < 0.75,
        })

    print(f"☄️ Lluvia de {len(meteoritos)} meteoritos (lejos de Carcassonne):")
    for i, m in enumerate(meteoritos):
        print(f"  #{i+1}: ({m['x']},{m['z']}) radio={m['radius']:.1f} t+{m['delay']:.1f}s "
              f"cráter_r={m['crater_radius']:.1f} prof={m['max_depth']} incendio={'SÍ' if m['fire'] else 'no'}")

    meteoritos.sort(key=lambda m: m["delay"])
    start = time.time()

    for i, m in enumerate(meteoritos):
        wait = m["delay"] - (time.time() - start)
        if wait > 0:
            print(f"\n⏳ Esperando {wait:.1f}s para meteorito #{i+1}...")
            time.sleep(wait)

        cx, cz = m["x"], m["z"]
        radius = m["radius"]
        print(f"\n☄️ Meteorito #{i+1} cayendo en ({cx}, {GROUND_Y}, {cz}) radio={radius:.1f}")

        voxels = make_meteorite_voxels(radius)
        r = mcp_call("create_sculpture", {"position": [cx, START_Y, cz], "resolution": 1,
            "voxels": voxels, "anchored": True, "color": 0x8B4513})
        if not r.get("success"):
            print(f"  ✗ Error creando meteorito: {r}")
            continue
        oid = r["object_id"]

        y = START_Y
        while y > GROUND_Y + radius:
            y -= 1.0
            mcp_call("update_object", {"object_id": oid, "patch": {"position": [cx, y, cz]}})
            time.sleep(0.03)

        print(f"  💥 ¡IMPACTO en ({cx}, {GROUND_Y}, {cz})!")
        crater = create_crater(cx, GROUND_Y, cz, m["crater_radius"], m["max_depth"])
        BATCH = 500
        for j in range(0, len(crater), BATCH):
            mcp_call("apply_blocks", {"blocks": crater[j:j+BATCH]}, timeout=120)
        rim = create_rim(cx, GROUND_Y, cz, m["crater_radius"])
        for j in range(0, len(rim), BATCH):
            mcp_call("apply_blocks", {"blocks": rim[j:j+BATCH]}, timeout=120)

        mcp_call("destroy_object", {"object_id": oid, "cause": "impacto"})

        if m["fire"]:
            n_fires = random.randint(1, 3)
            for _ in range(n_fires):
                fang = random.uniform(0, 2*math.pi)
                fdist = random.uniform(3, 8)
                fx = cx + math.cos(fang) * fdist
                fz = cz + math.sin(fang) * fdist
                spawn_fire(int(fx), GROUND_Y, int(fz))
            print(f"  🔥 Incendio ({n_fires} focos)")
        else:
            print(f"  (sin incendio)")

        print(f"  ✓ Cráter radio {m['crater_radius']:.1f}, prof {m['max_depth']}")

    print(f"\n✓ Lluvia de {len(meteoritos)} meteoritos completada en {time.time()-start:.1f}s")

if __name__ == "__main__":
    main()