"""Coloca un cilindro en cada extremo de la viga que atraviesa la esfera.

La viga (box) está en (10,49,10) con scale [40,1.5,1.5] → extremos en
x=-10 y x=30. Cada cilindro: eje a lo largo de X, radio 2, longitud 3,
centrado en cada extremo. Generado como escultura subvoxel (resolution 4).
"""
from __future__ import annotations
import json
import urllib.request
import sys

S = 0.25  # subvoxel size (resolution 4)

def v(x, y, z, color):
    return {"x": round(x, 3), "y": round(y, 3), "z": round(z, 3), "color": color, "size": S}

def cilindro(cx, cy, cz, color):
    """Cilindro con eje a lo largo de X, radio 2, longitud 3."""
    voxels = []
    R = 2.0
    L = 3.0
    steps_x = int(L / S)
    steps_r = int(R / S)
    for ix in range(steps_x + 1):
        x = cx - L / 2 + ix * S
        for iy in range(-steps_r, steps_r + 1):
            for iz in range(-steps_r, steps_r + 1):
                y = cy + iy * S
                z = cz + iz * S
                if (iy * S) ** 2 + (iz * S) ** 2 <= R * R:
                    voxels.append(v(x, y, z, color))
    return voxels

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

# Extremos de la viga: x=-10 (azul celeste) y x=30 (rosa)
AZUL_CELESTE = 0x87CEEB
ROSA = 0xFF69B4
Y, Z = 49, 10

for (cx, color, nombre) in [(-10, AZUL_CELESTE, "azul celeste"), (30, ROSA, "rosa")]:
    voxels = cilindro(cx, Y, Z, color)
    # scale = AABB envolvente
    xs = [vx["x"] for vx in voxels]
    ys = [vx["y"] for vx in voxels]
    zs = [vx["z"] for vx in voxels]
    scale = (max(xs) - min(xs) + S, max(ys) - min(ys) + S, max(zs) - min(zs) + S)
    center = (cx, Y, Z)
    r = mcp_call("create_sculpture", {
        "position": list(center),
        "resolution": 4,
        "voxels": voxels,
        "anchored": True,
        "color": color,
    })
    if r.get("success"):
        print(f"✓ Cilindro {nombre} en {center}: object_id={r['object_id']} voxels={r['voxel_count']} scale={scale}")
    else:
        print(f"✗ Error cilindro {nombre}: {r}")
        sys.exit(1)