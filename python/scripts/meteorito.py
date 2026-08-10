"""Crea un meteorito de radio 10 en lo alto, lo hace caer e impactar
creando un cráter en la superficie.

Sin reiniciar el servidor: usa MCP.
- Meteorito: escultura esférica de radio 10 (subvoxels) en y=55.
- Caída: se mueve hacia abajo paso a paso (simulación por MCP).
- Impacto: al llegar al suelo (y=24) crea un cráter (quita bloques en
  un radio con profundidad variable) y destruye el meteorito.
"""
from __future__ import annotations
import json
import urllib.request
import sys
import time
import math

AIR = 0
S = 1.0  # subvoxel size (resolution 1) — esfera de radio 10 ≈ 4189 voxels

METEORITO_COLOR = 0x8B4513  # marrón rocoso
CRATER_COLOR = 0x3A3A3A     # roca oscura del cráter

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

def make_meteorite_voxels(radius=10.0):
    """Genera una esfera de radio 10 con textura rocosa (subvoxels)."""
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
                    # Textura: variar color según profundidad
                    frac = d2 / r2
                    if frac < 0.3:
                        color = 0x5C4033  # núcleo oscuro
                    elif frac < 0.7:
                        color = 0x8B4513  # roca media
                    else:
                        color = 0xA0522D  # corteza clara
                    voxels.append({"x": round(x, 3), "y": round(y, 3),
                                   "z": round(z, 3), "color": color, "size": S})
    return voxels

def create_crater(cx, cy, cz, radius=12.0):
    """Crea un cráter: quita bloques en un radio con profundidad variable."""
    blocks = []
    r_int = int(radius)
    for dx in range(-r_int, r_int + 1):
        for dz in range(-r_int, r_int + 1):
            dist = math.hypot(dx, dz)
            if dist > radius:
                continue
            # Profundidad: más profundo en el centro, 0 en el borde
            depth = int((1 - dist / radius) * 6)  # hasta 6 bloques de profundidad
            for dy in range(0, depth + 1):
                blocks.append({"x": cx + dx, "y": cy - dy, "z": cz + dz, "type": AIR})
    return blocks

def main():
    # Posición del impacto (suelo en y=24)
    CX, CZ = 10, 10
    GROUND_Y = 24
    START_Y = 55.0  # en lo alto

    print("Generando meteorito de radio 10...")
    voxels = make_meteorite_voxels(10.0)
    print(f"  {len(voxels)} subvoxels")

    # Crear el meteorito en lo alto
    r = mcp_call("create_sculpture", {
        "position": [CX, START_Y, CZ],
        "resolution": 1,
        "voxels": voxels,
        "anchored": True,
        "color": METEORITO_COLOR,
    })
    if not r.get("success"):
        print(f"✗ Error creando meteorito: {r}")
        sys.exit(1)
    oid = r["object_id"]
    print(f"✓ Meteorito creado: object_id={oid} en ({CX}, {START_Y}, {CZ})")

    # Simular la caída paso a paso
    y = START_Y
    print("Cayendo...")
    while y > GROUND_Y + 10.0:
        y -= 1.0
        r = mcp_call("update_object", {
            "object_id": oid,
            "patch": {"position": [CX, y, CZ]},
        })
        if not r.get("success"):
            print(f"✗ Error moviendo meteorito: {r}")
            sys.exit(1)
        time.sleep(0.05)
        if int((START_Y - y)) % 5 == 0:
            print(f"  y={y:.1f}")

    # Impacto: crear cráter
    print(f"💥 ¡IMPACTO en ({CX}, {GROUND_Y}, {CZ})!")
    crater = create_crater(CX, GROUND_Y, CZ, radius=12.0)
    print(f"  Creando cráter ({len(crater)} bloques)...")
    BATCH = 500
    for i in range(0, len(crater), BATCH):
        chunk = crater[i:i + BATCH]
        r = mcp_call("apply_blocks", {"blocks": chunk}, timeout=120)
        if not r.get("success"):
            print(f"  ✗ Error cráter: {r}")
            sys.exit(1)

    # Borde del cráter: levantar bloques de roca oscura
    print("  Levantando borde del cráter...")
    rim = []
    for dx in range(-13, 14):
        for dz in range(-13, 14):
            dist = math.hypot(dx, dz)
            if 11.0 <= dist <= 13.0:
                rim.append({"x": CX + dx, "y": GROUND_Y, "z": CZ + dz, "type": 3})  # STONE
    for i in range(0, len(rim), BATCH):
        chunk = rim[i:i + BATCH]
        mcp_call("apply_blocks", {"blocks": chunk}, timeout=120)

    # Destruir el meteorito (se desintegra al impactar)
    mcp_call("destroy_object", {"object_id": oid, "cause": "impacto"})
    print(f"✓ Meteorito destruido tras el impacto")

    print(f"\n✓ Meteorito de radio 10 impactó en ({CX}, {GROUND_Y}, {CZ})")
    print(f"  Cráter de radio 12 con borde elevado creado")

if __name__ == "__main__":
    main()