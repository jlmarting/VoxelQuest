"""Destruye las catedrales construidas (limpia el volumen completo a aire).

Cada catedral ocupa W=17 x TOTAL_LEN=46 en planta, con torres de hasta
~55 bloques de alto. Se limpia desde el suelo hasta y=70 para cubrir
torres + agujas + terreno aplanado.
"""
from __future__ import annotations
import json
import urllib.request
import time

AIR = 0

# Ubicaciones de las catedrales: (bx, bz, by_base)
CATEDRALES = [
    (38, 3, 24),    # primera (38,3)
    (20, 20, 24),   # segunda (20,20)
    (23, 17, 31),   # tercera (23,17)
]

W = 17
TOTAL_LEN = 46
MAX_Y = 70


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


def send_batch(blocks):
    res = mcp_call("apply_blocks", {"blocks": blocks}, timeout=120)
    if isinstance(res, dict) and "error" in res:
        return 0
    return len(blocks)


def destroy_cathedral(bx, bz, by):
    """Limpia el volumen de la catedral a aire."""
    blocks = []
    for x in range(W):
        for z in range(TOTAL_LEN):
            for y in range(by, MAX_Y + 1):
                blocks.append({"x": bx + x, "y": y, "z": bz + z, "type": AIR})
    return blocks


if __name__ == "__main__":
    BATCH = 500
    total = 0
    for bx, bz, by in CATEDRALES:
        print(f"Destruyendo catedral en ({bx}, {bz}), base y={by}...")
        blocks = destroy_cathedral(bx, bz, by)
        ok = 0
        for i in range(0, len(blocks), BATCH):
            ok += send_batch(blocks[i:i + BATCH])
            time.sleep(0.02)
        total += ok
        print(f"  {ok}/{len(blocks)} bloques limpiados")
    print(f"\nTotal: {total} bloques a aire")
