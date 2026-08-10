"""
Construye un gran laberinto con muros aleatoriamente luminiscentes.
Generacion DFS, paredes de piedra con glowstone aleatorio.
"""

import json, urllib.request, time, sys, random

URL = "http://localhost:9000/mcp"
_RPC = [0]

AIR, GRASS, DIRT, STONE, WOOD, LEAVES, SAND, WATER, COBBLESTONE, PLANKS, BEDROCK = range(11)
GLOWSTONE = 11


def mcp(method, params, timeout=15):
    _RPC[0] += 1
    data = json.dumps({
        "jsonrpc": "2.0", "id": _RPC[0],
        "method": "tools/call",
        "params": {"name": method, "arguments": params}
    }).encode()
    req = urllib.request.Request(URL, data=data, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            resp = json.loads(r.read().decode())
            if "error" in resp:
                return {"error": resp["error"]}
            content = resp.get("content", [])
            if content and isinstance(content[0], dict) and "text" in content[0]:
                return json.loads(content[0]["text"])
            return resp.get("result", {})
    except Exception as e:
        return {"error": str(e)}


def send_batch(blocks):
    res = mcp("apply_blocks", {"blocks": blocks}, timeout=120)
    if isinstance(res, dict) and "error" in res:
        return 0
    return len(blocks)


def generate_maze(cols, rows):
    grid = [[1] * (2 * cols + 1) for _ in range(2 * rows + 1)]
    for r in range(rows):
        for c in range(cols):
            grid[2 * r + 1][2 * c + 1] = 0

    stack = [(0, 0)]
    visited = {(0, 0)}
    while stack:
        cr, cc = stack[-1]
        dirs = [(0, 1), (1, 0), (0, -1), (-1, 0)]
        random.shuffle(dirs)
        found = False
        for dr, dc in dirs:
            nr, nc = cr + dr, cc + dc
            if 0 <= nr < rows and 0 <= nc < cols and (nr, nc) not in visited:
                grid[2 * cr + 1 + dr][2 * cc + 1 + dc] = 0
                visited.add((nr, nc))
                stack.append((nr, nc))
                found = True
                break
        if not found:
            stack.pop()
    return grid


def build_maze(base_x, base_z, g, grid, wall_h=4):
    blocks = []
    height = len(grid)
    width = len(grid[0])

    for r in range(height):
        for c in range(width):
            wx = base_x + c
            wz = base_z + r
            if grid[r][c] == 1:
                for y in range(g + 1, g + wall_h + 1):
                    if random.random() < 0.08:
                        blocks.append({"x": wx, "y": y, "z": wz, "type": GLOWSTONE})
                    else:
                        blocks.append({"x": wx, "y": y, "z": wz, "type": STONE})
            else:
                blocks.append({"x": wx, "y": g, "z": wz, "type": PLANKS})
                for y in range(g + 1, g + wall_h):
                    blocks.append({"x": wx, "y": y, "z": wz, "type": AIR})

    # Suelo alrededor del laberinto (piedra)
    for x in range(base_x - 1, base_x + width + 1):
        for z in [base_z - 1, base_z + height]:
            blocks.append({"x": x, "y": g, "z": z, "type": STONE})
    for z in range(base_z - 1, base_z + height + 1):
        for x in [base_x - 1, base_x + width]:
            blocks.append({"x": x, "y": g, "z": z, "type": STONE})

    return blocks


if __name__ == "__main__":
    random.seed()
    maze_cols, maze_rows = 30, 30
    wall_h = 4
    grid_w = 2 * maze_cols + 1
    grid_h = 2 * maze_rows + 1

    print(f"Generando laberinto {maze_cols}x{maze_rows} ({grid_w}x{grid_h} bloques)...")
    grid = generate_maze(maze_cols, maze_rows)

    g = 1
    base_x, base_z = 60, -grid_h // 2

    print(f"Laberinto desde ({base_x}, {base_z})")

    blocks = build_maze(base_x, base_z, g, grid, wall_h)
    print(f"\nColocando {len(blocks)} bloques...")

    BATCH = 400
    ok_total = 0
    for i in range(0, len(blocks), BATCH):
        batch = blocks[i:i + BATCH]
        ok = send_batch(batch)
        ok_total += ok
        time.sleep(0.05)

    print(f"\nGran laberinto construido en ({base_x}, {g}, {base_z})!")
    print(f"{ok_total}/{len(blocks)} bloques colocados")
    print(f"{maze_cols}x{maze_rows} celdas | {grid_w}x{grid_h} bloques | paredes {wall_h} de alto | ~8% muros luminiscentes")
