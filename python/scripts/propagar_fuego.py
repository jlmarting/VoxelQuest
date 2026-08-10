"""Simula la propagación del fuego por los árboles y su extinción.

Sin reiniciar el servidor: corre en bucle usando MCP.
- Cada llama es una escultura pequeña (subvoxels rojo/naranja/amarillo)
  colocada en la posición de un bloque de árbol (WOOD/LEAVES).
- Cada iteración (~1s): las llamas activas queman bloques adyacentes
  (WOOD/LEAVES) creando llamas nuevas, y convierten el bloque en aire.
- Las llamas con más de 15s de vida se destruyen (se apagan).

Uso: python scripts/propagar_fuego.py [duracion_segundos]
"""
from __future__ import annotations
import json
import urllib.request
import sys
import time
import math

WOOD = 4
LEAVES = 5
AIR = 0
S = 0.25

ROJO = 0xFF4500
NARANJA = 0xFF8C00
AMARILLO = 0xFFD700

def mcp_call(tool, args, timeout=60):
    body = {"jsonrpc": "2.0", "id": 1, "method": "tools/call",
            "params": {"name": tool, "arguments": args}}
    req = urllib.request.Request("http://localhost:9000/mcp",
        data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        resp = json.loads(r.read().decode())
        if "content" in resp and resp["content"]:
            return json.loads(resp["content"][0].get("text", "{}"))
        return resp

def get_block(x, y, z):
    r = mcp_call("get_block", {"x": x, "y": y, "z": z})
    return r.get("type", 0)

def make_flame_voxels():
    """Genera una pequeña llama (3x3x4 subvoxels) con gradiente."""
    voxels = []
    for iy in range(4):
        y = iy * S
        frac = iy / 4
        if frac < 0.4:
            color = ROJO
        elif frac < 0.75:
            color = NARANJA
        else:
            color = AMARILLO
        r = 0.4 * (1 - frac * 0.6)
        nr = int(r / S)
        for ix in range(-nr, nr + 1):
            for iz in range(-nr, nr + 1):
                if (ix * S) ** 2 + (iz * S) ** 2 <= r * r:
                    voxels.append({"x": round(ix * S, 3), "y": round(y, 3),
                                   "z": round(iz * S, 3), "color": color, "size": S})
    return voxels

FLAME_VOXELS = make_flame_voxels()

def spawn_flame(x, y, z):
    """Crea una llama en la posición (x,y,z). Devuelve object_id o None."""
    r = mcp_call("create_sculpture", {
        "position": [x + 0.5, y + 0.5, z + 0.5],
        "resolution": 4,
        "voxels": FLAME_VOXELS,
        "anchored": True,
        "color": NARANJA,
    })
    if r.get("success"):
        return r["object_id"]
    return None

def destroy_flame(oid):
    mcp_call("destroy_object", {"object_id": oid, "cause": "extinguido"})

def burn_block(x, y, z):
    """Convierte un bloque de árbol en aire (se quema)."""
    mcp_call("apply_blocks", {"blocks": [{"x": x, "y": y, "z": z, "type": AIR}]})

# ============================================================
# Estado de las llamas: { (x,y,z): {"oid": int, "born": float} }
# ============================================================
flames = {}
LIFETIME = 15.0  # segundos antes de apagarse
ADJ = [(1,0,0),(-1,0,0),(0,1,0),(0,-1,0),(0,0,1),(0,0,-1)]

def main(duration=120):
    start = time.time()
    print(f"🔥 Propagación del fuego iniciada (duración {duration}s, llama vive {LIFETIME}s)")
    print("   Buscando árboles adyacentes al fuego central...")

    # Sembrar: encender los árboles plantados alrededor del fuego central
    # (mismas posiciones que plantar_arboles.py)
    TREE_POS = [
        (4, 10), (16, 10), (10, 4), (10, 16),
        (3, 3), (17, 17), (3, 17), (17, 3),
        (5, 14), (15, 6), (6, 15), (14, 5),
    ]
    seed = []
    for (tx, tz) in TREE_POS:
        # Tronco base del árbol (y=24)
        seed.append((tx, 24, tz))
        # Copa (y=28-29)
        seed.append((tx, 28, tz))
    for (sx, sy, sz) in seed:
        bt = get_block(sx, sy, sz)
        if bt in (WOOD, LEAVES):
            oid = spawn_flame(sx, sy, sz)
            if oid:
                flames[(sx, sy, sz)] = {"oid": oid, "born": time.time()}
                burn_block(sx, sy, sz)
                print(f"  🔥 Llama en ({sx},{sy},{sz}) [bloque {bt}]")

    print(f"   Llamas iniciales: {len(flames)}")

    while time.time() - start < duration:
        now = time.time()
        new_flames = {}

        # 1. Propagar: cada llama activa quema árboles adyacentes
        for (fx, fy, fz), info in list(flames.items()):
            for (dx, dy, dz) in ADJ:
                nx, ny, nz = fx + dx, fy + dy, fz + dz
                if (nx, ny, nz) in flames or (nx, ny, nz) in new_flames:
                    continue
                bt = get_block(nx, ny, nz)
                if bt in (WOOD, LEAVES):
                    oid = spawn_flame(nx, ny, nz)
                    if oid:
                        new_flames[(nx, ny, nz)] = {"oid": oid, "born": now}
                        burn_block(nx, ny, nz)
                        print(f"  🔥 Propagado a ({nx},{ny},{nz}) [bloque {bt}]")

        # 2. Apagar: llamas con más de LIFETIME segundos
        to_remove = []
        for (fx, fy, fz), info in flames.items():
            if now - info["born"] >= LIFETIME:
                destroy_flame(info["oid"])
                to_remove.append((fx, fy, fz))
                print(f"  💨 Llama apagada en ({fx},{fy},{fz})")

        for k in to_remove:
            del flames[k]

        # Añadir nuevas llamas
        flames.update(new_flames)

        if not flames and not new_flames:
            print("   No quedan llamas activas ni árboles por quemar.")
            break

        print(f"   [t={int(now-start)}s] llamas activas: {len(flames)}")
        time.sleep(1.0)

    # Apagar todo lo que quede
    for (fx, fy, fz), info in flames.items():
        destroy_flame(info["oid"])
    print(f"\n✓ Incendio finalizado. {len(flames)} llamas restantes apagadas.")

if __name__ == "__main__":
    dur = int(sys.argv[1]) if len(sys.argv) > 1 else 120
    main(dur)