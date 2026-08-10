"""Construye una catedral gotica al detalle con planta en cruz.

Caracteristicas:
- Planta en cruz: nave central + naves laterales + transepto + abside semicircular
- Fachada con dos torres y agujas, portal y roseton
- Ventanales goticos con arco ojival en muros y transepto
- Interior: altar, bancos, ambon, candelabros, boveda de cruceria
- Contrafuertes exteriores y pinaculos

Block types: 3=stone, 8=cobblestone, 9=planks, 4=wood, 13=red_brick,
             11=glowstone, 5=leaves, 1=grass
"""
from __future__ import annotations
import json
import urllib.request
import time
import sys

STONE = 3
COBBLE = 8
PLANKS = 9
WOOD = 4
BRICK = 13
GLOW = 11
LEAVES = 5
GRASS = 1
AIR = 0

# Dimensiones (coordenadas relativas)
W = 17          # ancho total en X (0..16)
NAVE_LEN = 40   # largo de la nave en Z (0..39)
TRANSEPT_Z0 = 14
TRANSEPT_Z1 = 25
ABSIDE_LEN = 6  # abside extra (39..44)
TOTAL_LEN = NAVE_LEN + ABSIDE_LEN  # 45

NAVE_H = 20     # altura muros exteriores
AISLE_H = 10    # altura naves laterales
TOWER_H = 30    # altura torres

# Posiciones clave en X
AISLE_L = 3     # nave lateral izquierda: x 0..3
NAVE_L = 4      # nave central: x 4..12
NAVE_R = 12
AISLE_R = 13    # nave lateral derecha: x 13..16


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


def detect_ground(wx, wz):
    """Devuelve la Y de la superficie (techo del bloque solido mas alto).

    Usa la tool MCP get_height (servidor Python), que escanea la columna
    completa de forma fiable. Devuelve `surface` = Y del bloque solido + 1.
    """
    res = mcp_call("get_height", {"x": wx, "z": wz})
    if isinstance(res, dict) and res.get("surface", 0) > 0:
        return res["surface"]
    # Fallback: escaneo manual
    for y in range(50, 0, -1):
        r = mcp_call("get_block", {"x": wx, "y": y, "z": wz})
        bt = r.get("type", 0) if isinstance(r, dict) else 0
        if bt != AIR and bt != 7:
            return y + 1
    return 23


def send_batch(blocks):
    res = mcp_call("apply_blocks", {"blocks": blocks}, timeout=120)
    if isinstance(res, dict) and "error" in res:
        return 0
    return len(blocks)


def flatten_terrain(bx, bz, by, width, length, offset_x=0):
    """Aplana el terreno de la base: rellena con tierra los huecos por debajo
    de `by` y deja la superficie a `by` (nivel del suelo de la catedral).

    `offset_x` desplaza el area en X (para cubrir tambien los contrafuertes
    exteriores en x=-1 y x=W)."""
    blocks = []
    for x in range(width):
        for z in range(length):
            # Buscar el bloque solido mas alto en la columna
            top = 0
            for y in range(by - 1, 0, -1):
                res = mcp_call("get_block", {"x": bx + x + offset_x, "y": y, "z": bz + z})
                bt = res.get("type", 0) if isinstance(res, dict) else 0
                if bt != AIR and bt != 7:
                    top = y
                    break
            # Rellenar desde top+1 hasta by-1 con tierra
            for y in range(top + 1, by):
                blocks.append({"x": bx + x + offset_x, "y": y, "z": bz + z, "type": 2})  # DIRT
    return blocks


# ---------------------------------------------------------------------------
# Generadores de formas
# ---------------------------------------------------------------------------

def ogive_arch(cx, cz, width, height, base_y, depth=1, block=STONE):
    """Arco ojival (apuntado) en el plano XZ. Devuelve lista de bloques.

    El arco se extiende en X desde cx-width/2 hasta cx+width/2, con el
    punto mas alto en cx. `height` es la altura del arco sobre base_y.
    """
    out = []
    half = width // 2
    for dx in range(-half, half + 1):
        # Parabola apuntada: y = height * (1 - (dx/half)^2) * 1.15
        t = abs(dx) / half if half else 0
        h = int(round(height * (1 - t * t) * 1.15))
        for d in range(depth):
            out.append({"x": cx + dx, "y": base_y + h, "z": cz + d, "type": block})
    return out


def round_window(cx, cz, radius, base_y, depth=1, block=STONE):
    """Ventana circular (roseton) en el plano XZ."""
    out = []
    for dx in range(-radius, radius + 1):
        for dy in range(-radius, radius + 1):
            if dx * dx + dy * dy <= radius * radius:
                for d in range(depth):
                    out.append({"x": cx + dx, "y": base_y + dy, "z": cz + d, "type": block})
    return out


def pointed_window(cx, cz, width, height, base_y, depth=1, block=STONE):
    """Ventana gotica: rectangulo + arco ojival encima."""
    out = []
    half = width // 2
    # Rectangulo
    for dx in range(-half, half + 1):
        for dy in range(0, height):
            for d in range(depth):
                out.append({"x": cx + dx, "y": base_y + dy, "z": cz + d, "type": block})
    # Arco ojival
    out.extend(ogive_arch(cx, cz, width, height // 2, base_y + height, depth, block))
    return out


def spire(cx, cz, base_y, height, block=STONE):
    """Aguja piramidal sobre una torre."""
    out = []
    for i in range(height):
        r = max(0, (height - i) // 3)
        for dx in range(-r, r + 1):
            for dz in range(-r, r + 1):
                if abs(dx) + abs(dz) <= r + 1:
                    out.append({"x": cx + dx, "y": base_y + i, "z": cz + dz, "type": block})
    return out


# ---------------------------------------------------------------------------
# Construccion
# ---------------------------------------------------------------------------

def build_cathedral(bx, bz, by):
    blocks = []

    def B(x, y, z, t):
        blocks.append({"x": bx + x, "y": by + y, "z": bz + z, "type": t})

    # ==================================================================
    # 1. Suelo de piedra (toda la planta en cruz)
    # ==================================================================
    for x in range(W):
        for z in range(TOTAL_LEN):
            B(x, 0, z, STONE)
    # Transepto (brazos de la cruz)
    for x in range(W):
        for z in range(TRANSEPT_Z0, TRANSEPT_Z1 + 1):
            B(x, 0, z, STONE)

    # ==================================================================
    # 2. Muros exteriores de la nave
    # ==================================================================
    for z in range(NAVE_LEN):
        for y in range(1, NAVE_H + 1):
            B(0, y, z, STONE)
            B(W - 1, y, z, STONE)
    for x in range(W):
        for y in range(1, NAVE_H + 1):
            B(x, y, 0, STONE)

    # ==================================================================
    # 3. Naves laterales (muros interiores + columnas)
    # ==================================================================
    # Muros que separan nave central de laterales
    for z in range(1, NAVE_LEN):
        for y in range(1, AISLE_H + 1):
            B(NAVE_L, y, z, STONE)
            B(NAVE_R, y, z, STONE)

    # Columnas de la nave central (pilares)
    for z in range(2, NAVE_LEN - 1, 4):
        for y in range(1, NAVE_H + 1):
            B(NAVE_L, y, z, COBBLE)
            B(NAVE_R, y, z, COBBLE)
            B(NAVE_L, y, z + 1, COBBLE)
            B(NAVE_R, y, z + 1, COBBLE)

    # ==================================================================
    # 4. Transepto (brazos de la cruz)
    # ==================================================================
    # Muros exteriores del transepto (en X, a ambos lados)
    for z in range(TRANSEPT_Z0, TRANSEPT_Z1 + 1):
        for y in range(1, NAVE_H + 1):
            B(0, y, z, STONE)
            B(W - 1, y, z, STONE)
    # Muros que cierran el transepto contra la nave (en Z)
    for x in range(W):
        for y in range(1, NAVE_H + 1):
            B(x, y, TRANSEPT_Z0, STONE)
            B(x, y, TRANSEPT_Z1, STONE)

    # ==================================================================
    # 5. Abside semicircular (al norte, z alto)
    # ==================================================================
    # Muro curvo del abside
    for i in range(ABSIDE_LEN):
        z = NAVE_LEN + i
        for x in range(W):
            for y in range(1, NAVE_H + 1):
                B(x, y, z, STONE)
    # Cierre curvo (semicirculo)
    for x in range(W):
        for y in range(1, NAVE_H + 1):
            B(x, y, TOTAL_LEN - 1, STONE)

    # ==================================================================
    # 6. Torres de la fachada con agujas
    # ==================================================================
    for tower_x in [0, W - 5]:
        for x in range(tower_x, tower_x + 5):
            for z in range(0, 5):
                for y in range(1, TOWER_H + 1):
                    B(x, y, z, STONE)
        # Aguja
        cx = tower_x + 2
        blocks.extend(spire(cx, 2, TOWER_H, 8, STONE))
        # Pinaculo en la punta
        B(cx, TOWER_H + 8, 2, BRICK)

    # ==================================================================
    # 7. Portal principal (fachada sur, z=0)
    # ==================================================================
    for x in range(5, 12):
        for y in range(0, 6):
            B(x, y, 0, AIR)
    # Arco ojival del portal
    blocks.extend(ogive_arch(8, 0, 7, 5, 6, 1, STONE))
    # Puerta de madera
    for x in range(6, 10):
        for y in range(0, 4):
            B(x, y, 0, WOOD)

    # ==================================================================
    # 8. Roseton (fachada sur, sobre el portal)
    # ==================================================================
    blocks.extend(round_window(8, 0, 3, 12, 1, STONE))
    # Marco del roseton
    for dx in range(-4, 5):
        for dy in range(-4, 5):
            if abs(dx) == 4 or abs(dy) == 4:
                B(8 + dx, 12 + dy, 0, COBBLE)

    # ==================================================================
    # 9. Ventanales goticos en muros laterales
    # ==================================================================
    for z in range(4, NAVE_LEN - 2, 6):
        # Ventana alta nave central (lado izquierdo y derecho)
        blocks.extend(pointed_window(NAVE_L, z, 3, 6, AISLE_H + 1, 1, STONE))
        blocks.extend(pointed_window(NAVE_R, z, 3, 6, AISLE_H + 1, 1, STONE))
        # Ventanas naves laterales (muros exteriores)
        blocks.extend(pointed_window(1, z, 3, 4, 3, 1, STONE))
        blocks.extend(pointed_window(W - 2, z, 3, 4, 3, 1, STONE))

    # Ventanales del transepto
    for z in [TRANSEPT_Z0 + 2, TRANSEPT_Z1 - 2]:
        blocks.extend(pointed_window(NAVE_L, z, 3, 6, AISLE_H + 1, 1, STONE))
        blocks.extend(pointed_window(NAVE_R, z, 3, 6, AISLE_H + 1, 1, STONE))

    # ==================================================================
    # 10. Contrafuertes exteriores
    # ==================================================================
    for z in range(2, NAVE_LEN, 5):
        for y in range(1, AISLE_H + 1):
            B(-1, y, z, COBBLE)
            B(W, y, z, COBBLE)
        # Pinaculo
        B(-1, AISLE_H + 1, z, BRICK)
        B(W, AISLE_H + 1, z, BRICK)

    # ==================================================================
    # 11. Boveda de cruceria (nave central)
    # ==================================================================
    for z in range(1, NAVE_LEN - 1):
        # Arco transversal cada 4 bloques
        if z % 4 == 0:
            for x in range(NAVE_L + 1, NAVE_R):
                B(x, NAVE_H, z, STONE)
        # Boveda: techo inclinado hacia el centro
        for x in range(NAVE_L + 1, NAVE_R):
            B(x, NAVE_H + 1, z, STONE)
    # Cumbrera central
    for z in range(1, NAVE_LEN - 1):
        B(8, NAVE_H + 2, z, BRICK)

    # Boveda del crucero (mas alta)
    for x in range(NAVE_L + 1, NAVE_R):
        for z in range(TRANSEPT_Z0 + 1, TRANSEPT_Z1):
            B(x, NAVE_H + 1, z, STONE)
    for x in range(NAVE_L + 1, NAVE_R):
        for z in range(TRANSEPT_Z0 + 1, TRANSEPT_Z1):
            B(x, NAVE_H + 2, z, STONE)
    # Torre linterna sobre el crucero
    for x in range(6, 11):
        for z in range(TRANSEPT_Z0 + 3, TRANSEPT_Z1 - 2):
            for y in range(NAVE_H + 3, NAVE_H + 8):
                B(x, y, z, STONE)
    # Ventanas de la linterna
    for z in [TRANSEPT_Z0 + 3, TRANSEPT_Z1 - 3]:
        for y in range(NAVE_H + 4, NAVE_H + 7):
            B(8, y, z, AIR)
    # Tejado de la linterna
    blocks.extend(spire(8, TRANSEPT_Z0 + 4, NAVE_H + 8, 5, STONE))

    # ==================================================================
    # 12. Tejados de naves laterales (inclinados)
    #     Empiezan en z=5 para no superponerse con las torres de la fachada
    #     (que ocupan z=0..4). Asi el tejado conecta con la cara trasera
    #     de las torres en lugar de quedar dentro de ellas.
    # ==================================================================
    for z in range(5, NAVE_LEN):
        for i in range(AISLE_L):
            B(i, AISLE_H + 1 + i, z, BRICK)
            B(W - 1 - i, AISLE_H + 1 + i, z, BRICK)

    # ==================================================================
    # 13. Pasillos interiores despejados (aire) — PRIMERO, para que los
    #     muebles de las secciones siguientes no queden sobrescritos.
    # ==================================================================
    # Nave central transitable
    for x in range(NAVE_L + 1, NAVE_R):
        for z in range(1, NAVE_LEN - 1):
            for y in range(1, AISLE_H):
                B(x, y, z, AIR)
    # Naves laterales transitable
    for x in range(1, NAVE_L):
        for z in range(1, NAVE_LEN - 1):
            for y in range(1, AISLE_H):
                B(x, y, z, AIR)
    for x in range(NAVE_R + 1, W - 1):
        for z in range(1, NAVE_LEN - 1):
            for y in range(1, AISLE_H):
                B(x, y, z, AIR)
    # Transepto transitable
    for x in range(1, W - 1):
        for z in range(TRANSEPT_Z0 + 1, TRANSEPT_Z1):
            for y in range(1, AISLE_H):
                B(x, y, z, AIR)
    # Abside transitable
    for x in range(1, W - 1):
        for z in range(NAVE_LEN, TOTAL_LEN - 1):
            for y in range(1, AISLE_H):
                B(x, y, z, AIR)
    # Altura nave central (sobre las naves laterales)
    for x in range(NAVE_L + 1, NAVE_R):
        for z in range(1, NAVE_LEN - 1):
            for y in range(AISLE_H, NAVE_H):
                B(x, y, z, AIR)

    # ==================================================================
    # 14. Interior: ALTAR
    # ==================================================================
    # Plataforma del altar (en el abside)
    for x in range(5, 12):
        for z in range(NAVE_LEN - 2, NAVE_LEN + 2):
            B(x, 1, z, PLANKS)
    # Mesa del altar
    for x in range(6, 11):
        for z in range(NAVE_LEN, NAVE_LEN + 2):
            B(x, 2, z, PLANKS)
            B(x, 3, z, PLANKS)
    # Mantel (borde)
    for x in range(6, 11):
        B(x, 3, NAVE_LEN + 1, BRICK)
    # Crucifijo (madera)
    for y in range(4, 9):
        B(8, y, NAVE_LEN + 1, WOOD)
    B(7, 8, NAVE_LEN + 1, WOOD)
    B(9, 8, NAVE_LEN + 1, WOOD)
    # Candelabros (glowstone)
    B(6, 4, NAVE_LEN + 1, GLOW)
    B(10, 4, NAVE_LEN + 1, GLOW)

    # ==================================================================
    # 15. Interior: BANCOS
    # ==================================================================
    # Bancos en la nave central, mirando al altar (z alto)
    for z in range(8, 30, 3):
        for x in range(5, 12):
            B(x, 1, z, WOOD)          # asiento
            B(x, 2, z, WOOD)          # respaldo
        # Pasillo central
        for x in range(7, 10):
            B(x, 1, z, AIR)
            B(x, 2, z, AIR)
    # Reposapiés
    for z in range(8, 30, 3):
        for x in range(5, 12):
            B(x, 1, z + 1, PLANKS)

    # ==================================================================
    # 16. Interior: AMBON (púlpito)
    # ==================================================================
    for y in range(1, 4):
        B(4, y, 12, COBBLE)
    B(4, 3, 12, PLANKS)
    B(3, 3, 12, PLANKS)
    B(5, 3, 12, PLANKS)

    # ==================================================================
    # 17. Interior: PILA BAUTISMAL
    # ==================================================================
    for y in range(1, 3):
        B(12, y, 6, COBBLE)
    B(12, 3, 6, STONE)
    B(11, 3, 6, STONE)
    B(13, 3, 6, STONE)

    # ==================================================================
    # 18. Interior: LAMPARAS colgantes (glowstone)
    # ==================================================================
    for z in [6, 14, 22, 30]:
        B(8, NAVE_H - 2, z, GLOW)
        B(8, NAVE_H - 3, z, WOOD)

    # ==================================================================
    # 19. Apertura de la fachada (portal) y acceso
    # ==================================================================
    for x in range(5, 12):
        for y in range(0, 6):
            B(x, y, 0, AIR)

    return blocks


if __name__ == "__main__":
    players = mcp_call("list_players", {})
    p = players.get("players", [{}])[0] if isinstance(players, dict) else {}
    px, pz = int(p.get("x", 0)), int(p.get("z", 0))
    print(f"Jugador en ({px}, {pz})")

    # Construir en una zona despejada al este del jugador
    bx = px + 12
    bz = pz + 12
    by = detect_ground(bx, bz)
    print(f"Suelo en y={by}")

    BATCH = 500

    # Aplanar el terreno de la base (17x46) + franja de contrafuertes (x=-1 y x=W)
    print("Aplanando terreno...")
    flat = flatten_terrain(bx, bz, by, W, TOTAL_LEN)
    flat += flatten_terrain(bx, bz, by, 1, TOTAL_LEN, offset_x=-1)   # contrafuertes izq
    flat += flatten_terrain(bx, bz, by, 1, TOTAL_LEN, offset_x=W)   # contrafuertes der
    for i in range(0, len(flat), BATCH):
        send_batch(flat[i:i + BATCH])
    print(f"Terreno aplanado ({len(flat)} bloques de relleno)")

    print(f"Catedral desde ({bx}, {bz}), y={by}")
    blocks = build_cathedral(bx, bz, by)
    print(f"\nColocando {len(blocks)} bloques...")

    ok_total = 0
    for i in range(0, len(blocks), BATCH):
        batch = blocks[i:i + BATCH]
        ok = send_batch(batch)
        ok_total += ok
        time.sleep(0.05)

    print(f"\nCatedral gotica construida en ({bx}, {by}, {bz})!")
    print(f"{ok_total}/{len(blocks)} bloques colocados")
    print(f"Planta en cruz {W}x{TOTAL_LEN} | torres h={TOWER_H} | altar, bancos, ambon, pila bautismal")
