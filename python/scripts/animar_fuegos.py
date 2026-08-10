"""Anima los fuegos: llama y brasas con oscilación senoidal (flicker).

Cada llama/brasa recibe un motion paramétrico que oscila en Y con
amplitud, frecuencia y fase aleatorias → efecto de llama viva.
"""
from __future__ import annotations
import json
import urllib.request
import sys
import random
import math

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

# Obtener todos los objetos
r = mcp_call("list_objects", {})
objs = r.get("objects", [])

llamas = [o for o in objs if o["kind"] == "sculpture"]
brasas = [o for o in objs if o["kind"] == "sphere"]

print(f"Animando {len(llamas)} llamas y {len(brasas)} brasas...")

random.seed()

def animar(oid, base_y, amp, freq, phase):
    """Asigna motion paramétrico de oscilación en Y."""
    expr = f"{base_y:.3f} + {amp:.3f}*sin(t*{freq:.3f} + {phase:.3f})"
    r = mcp_call("move_object", {
        "object_id": oid,
        "motion": {"type": "parametric", "x": None, "y": expr, "z": None, "dt_mul": 1.0},
    })
    return r.get("success", False)

ok = 0
# Llamas: flicker rápido y amplio (la llama baila)
for o in llamas:
    base_y = o["position"][1]
    amp = random.uniform(0.2, 0.5)
    freq = random.uniform(2.5, 4.5)
    phase = random.uniform(0, 2 * math.pi)
    if animar(o["id"], base_y, amp, freq, phase):
        ok += 1

# Brasas: oscilación más suave (luz que parpadea)
for o in brasas:
    base_y = o["position"][1]
    amp = random.uniform(0.1, 0.3)
    freq = random.uniform(1.5, 3.0)
    phase = random.uniform(0, 2 * math.pi)
    if animar(o["id"], base_y, amp, freq, phase):
        ok += 1

print(f"✓ {ok}/{len(llamas) + len(brasas)} objetos de fuego animados")