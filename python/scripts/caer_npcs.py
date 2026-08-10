"""Hace que los NPCs caigan al suelo por gravedad.

1. Para cada NPC: quita el motion (stop_motion), pone mass=1 y anchored=False
   → la física del servidor los integra y caen por gravedad.
2. Espera a que reposen sobre el suelo.
3. Reasigna el motion de patrulla (waypoints) con las posiciones ya sobre el suelo.
"""
from __future__ import annotations
import json
import urllib.request
import sys
import time

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

# 1. Obtener NPCs
r = mcp_call("list_objects", {})
objs = r.get("objects", [])
npcs = [o for o in objs if o["kind"] == "box"]
print(f"NPCs encontrados: {len(npcs)}")

# 2. Quitar motion y hacerlos dinámicos (caen por gravedad)
print("Haciendo caer a los NPCs...")
for o in npcs:
    oid = o["id"]
    # Quitar motion (stop)
    mcp_call("move_object", {"object_id": oid, "motion": {"type": "stop"}})
    # Hacer dinámico: mass=1, anchored=False
    mcp_call("update_object", {"object_id": oid, "patch": {"mass": 1.0, "anchored": False}})
    print(f"  NPC {oid} soltado (y={o['position'][1]:.1f})")

# 3. Esperar a que caigan y reposen
print("Esperando 5s a que caigan...")
time.sleep(5)

# 4. Verificar posiciones finales
r = mcp_call("list_objects", {})
objs = r.get("objects", [])
npcs = [o for o in objs if o["kind"] == "box"]
print("Posiciones tras la caída:")
for o in npcs:
    print(f"  id={o['id']} pos={[round(v,1) for v in o['position']]} vel={[round(v,2) for v in o['velocity']]}")

print("\n✓ NPCs caídos al suelo")