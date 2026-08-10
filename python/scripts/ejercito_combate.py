"""Ejército: persigue y mata monstruos dentro de Carcassonne.

Conecta al WebSocket del servidor, lee `enemies[]` en cada state_update,
y dirige a los soldados (objetos box) hacia el monstruo más cercano.
Cuando un soldado está a distancia de ataque, usa `attack_enemy` para
aplicar daño. Los soldados que no tienen monstruo cerca patrullan.

Uso: python scripts/ejercito_combate.py [duracion_segundos]
"""
from __future__ import annotations
import json
import urllib.request
import sys
import time
import math
import asyncio
import websockets

def mcp_call(tool, args, timeout=30):
    body = {"jsonrpc": "2.0", "id": 1, "method": "tools/call",
            "params": {"name": tool, "arguments": args}}
    req = urllib.request.Request("http://localhost:9000/mcp",
        data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        resp = json.loads(r.read().decode())
        if "content" in resp and resp["content"]:
            return json.loads(resp["content"][0].get("text", "{}"))
        return resp

def get_soldiers():
    r = mcp_call("list_objects", {})
    objs = r.get("objects", [])
    return [o for o in objs if o["kind"] == "box"]

def move_soldier(oid, x, y, z):
    mcp_call("update_object", {"object_id": oid, "patch": {"position": [x, y, z]}})

def attack_enemy(eid, amount=2.0):
    r = mcp_call("attack_enemy", {"enemy_id": eid, "amount": amount})
    return r.get("died", False)

async def main(duration=120):
    print(f"⚔️ Ejército en combate (duración {duration}s)...")
    start = time.time()
    last_enemies = {}

    async with websockets.connect("ws://127.0.0.1:9000/ws") as ws:
        await ws.recv()  # welcome
        while time.time() - start < duration:
            try:
                msg = await asyncio.wait_for(ws.recv(), timeout=2.0)
            except asyncio.TimeoutError:
                continue
            data = json.loads(msg)
            if data.get("type") != "state_update":
                continue

            enemies = data.get("enemies", [])
            if not enemies:
                continue

            soldiers = get_soldiers()
            if not soldiers:
                print("  ⚠️ No hay soldados")
                continue

            # Para cada soldado, encontrar el monstruo más cercano
            for s in soldiers:
                sx, sy, sz = s["position"]
                best = None
                best_dist = 20.0  # radio de detección
                for e in enemies:
                    ex, ey, ez = e["x"], e["y"], e["z"]
                    dist = math.hypot(ex - sx, ez - sz)
                    if dist < best_dist:
                        best_dist = dist
                        best = e

                if best is None:
                    continue  # patrulla (motion ya asignado)

                ex, ey, ez = best["x"], best["y"], best["z"]
                eid = best["id"]

                if best_dist < 2.0:
                    # A distancia de ataque
                    died = attack_enemy(eid, amount=2.0)
                    if died:
                        print(f"  💀 Soldado {s['id']} mató al monstruo {eid}")
                else:
                    # Perseguir: mover hacia el monstruo
                    dx = ex - sx
                    dz = ez - sz
                    dist = math.hypot(dx, dz) or 1.0
                    step = 0.5  # velocidad de persecución
                    nx = sx + dx / dist * step
                    nz = sz + dz / dist * step
                    move_soldier(s["id"], nx, sy, nz)

            # Reporte periódico
            if int(time.time() - start) % 5 == 0 and int(time.time() - start) != last_enemies.get("t", 0):
                last_enemies["t"] = int(time.time() - start)
                print(f"  [t={int(time.time()-start)}s] monstruos: {len(enemies)}, soldados: {len(soldiers)}")

    print(f"\n✓ Combate finalizado tras {time.time()-start:.0f}s")

if __name__ == "__main__":
    dur = int(sys.argv[1]) if len(sys.argv) > 1 else 120
    asyncio.run(main(dur))