"""Destruye la ciudad de Carcassonne casa por casa con física realista.

Cada casa (bloques WOOD + BRICK) se convierte en fragmentos box con
velocidad radial (explosión) y gravedad. Se procesa en oleadas para
respetar el límite de 100 objetos: se crean fragmentos, se espera a que
caigan, se eliminan los reposados, y se pasa a la siguiente oleada.

1. Escanea el área de la ciudad para detectar bloques WOOD (casas).
2. Agrupa bloques contiguos en clusters (cada casa).
3. Por oleada: crea fragmentos de las casas, espera, limpia.
"""
from __future__ import annotations
import json
import urllib.request
import sys
import time
import math
import random

AIR = 0
WOOD = 4
BRICK = 13
PLANKS = 9

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

def get_block(x, y, z):
    r = mcp_call("get_block", {"x": x, "y": y, "z": z})
    return r.get("type", 0)

# ============================================================
# 1. Escanear el área de la ciudad para detectar casas (WOOD)
# ============================================================
print("1. Escaneando la ciudad para detectar casas...")
GROUND = 21
X0, X1 = -30, 30
Z0, Z1 = -30, 30
# Escanear y=22 (primer nivel de las casas) y y=23
wood_blocks = set()
for x in range(X0, X1 + 1):
    for z in range(Z0, Z1 + 1):
        for y in [22, 23]:
            bt = get_block(x, y, z)
            if bt == WOOD:
                wood_blocks.add((x, y, z))
print(f"  {len(wood_blocks)} bloques WOOD detectados")

# ============================================================
# 2. Agrupar en clusters (cada casa)
# ============================================================
def cluster_blocks(blocks):
    """Agrupa bloques contiguos (6-conectividad) en clusters."""
    clusters = []
    remaining = set(blocks)
    while remaining:
        seed = remaining.pop()
        cluster = {seed}
        queue = [seed]
        while queue:
            (x, y, z) = queue.pop()
            for (dx, dy, dz) in [(1,0,0),(-1,0,0),(0,1,0),(0,-1,0),(0,0,1),(0,0,-1)]:
                nb = (x+dx, y+dy, z+dz)
                if nb in remaining:
                    remaining.discard(nb)
                    cluster.add(nb)
                    queue.append(nb)
        clusters.append(cluster)
    return clusters

clusters = cluster_blocks(wood_blocks)
print(f"  {len(clusters)} casas detectadas")

# ============================================================
# 3. Destruir casa por casa en oleadas
# ============================================================
def explode_house(cluster, house_idx):
    """Convierte una casa en fragmentos con física."""
    # Centro de la casa
    xs = [b[0] for b in cluster]
    ys = [b[1] for b in cluster]
    zs = [b[2] for b in cluster]
    cx = sum(xs) / len(xs)
    cy = sum(ys) / len(ys)
    cz = sum(zs) / len(zs)
    # Tamaño
    size_x = max(xs) - min(xs) + 1
    size_y = max(ys) - min(ys) + 1
    size_z = max(zs) - min(zs) + 1

    # Número de fragmentos según tamaño de la casa
    n_frag = 1 if len(cluster) < 15 else 2

    # Poner aire en todos los bloques de la casa (paredes + tejado)
    # Incluir el tejado (BRICK) y suelo (PLANKS) asociados
    air_blocks = []
    for (bx, by, bz) in cluster:
        air_blocks.append({"x": bx, "y": by, "z": bz, "type": AIR})
        # Tejado (BRICK) encima
        for ty in range(by + 1, by + 3):
            if get_block(bx, ty, bz) == BRICK:
                air_blocks.append({"x": bx, "y": ty, "z": bz, "type": AIR})
        # Suelo (PLANKS) debajo
        if get_block(bx, by - 1, bz) == PLANKS:
            air_blocks.append({"x": bx, "y": by - 1, "z": bz, "type": AIR})

    # Enviar aire
    BATCH = 500
    for i in range(0, len(air_blocks), BATCH):
        mcp_call("apply_blocks", {"blocks": air_blocks[i:i+BATCH]}, timeout=120)

    # Crear fragmentos
    created = []
    for f in range(n_frag):
        # Desplazamiento del fragmento dentro de la casa
        off_x = random.uniform(-size_x/4, size_x/4)
        off_y = random.uniform(-size_y/4, size_y/4)
        off_z = random.uniform(-size_z/4, size_z/4)
        fx = cx + off_x
        fy = cy + off_y
        fz = cz + off_z
        # Velocidad radial desde el centro de la casa
        dx = fx - cx
        dy = fy - cy
        dz = fz - cz
        dist = math.sqrt(dx*dx + dy*dy + dz*dz) or 1.0
        power = random.uniform(6, 12)
        vx = dx / dist * power + random.uniform(-1, 1)
        vy = dy / dist * power + random.uniform(4, 8)
        vz = dz / dist * power + random.uniform(-1, 1)
        # Tamaño del fragmento
        fs = max(0.5, min(size_x, 2.0) * random.uniform(0.5, 1.0))
        r = mcp_call("create_object", {
            "kind": "box",
            "position": [round(fx, 2), round(fy, 2), round(fz, 2)],
            "scale": [round(fs, 2), round(fs, 2), round(fs, 2)],
            "color": 0x8B5A2B,  # madera
            "mass": 0.5 + random.random(),
            "restitution": 0.3,
            "velocity": [round(vx, 2), round(vy, 2), round(vz, 2)],
            "anchored": False,
        })
        if r.get("success"):
            created.append(r["object_id"])
    return created

# Procesar en oleadas de 8 casas
OLEADA = 8
total_fragments = 0
for start in range(0, len(clusters), OLEADA):
    batch = clusters[start:start + OLEADA]
    print(f"\n💥 Oleada {start//OLEADA + 1}: destruyendo {len(batch)} casas...")
    frag_ids = []
    for i, cluster in enumerate(batch):
        house_idx = start + i
        frags = explode_house(cluster, house_idx)
        frag_ids.extend(frags)
        total_fragments += len(frags)
        print(f"  ✓ Casa {house_idx+1}/{len(clusters)} → {len(frags)} fragmentos")

    # Esperar a que los fragmentos vuelen y caigan
    print(f"  ⏳ Esperando 4s a que caigan los fragmentos...")
    time.sleep(4)

    # Eliminar fragmentos reposados (y < 25)
    r = mcp_call("list_objects", {})
    objs = r.get("objects", [])
    reposados = [o["id"] for o in objs
                 if o["kind"] == "box" and o["mass"] > 0 and not o["anchored"]
                 and o["position"][1] < 25]
    for oid in reposados:
        mcp_call("destroy_object", {"object_id": oid, "cause": "escombros"})
    print(f"  🧹 {len(reposados)} fragmentos reposados eliminados")

print(f"\n✓ Ciudad destruida casa por casa: {len(clusters)} casas, {total_fragments} fragmentos")