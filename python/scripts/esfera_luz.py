"""Crea una esfera de radio 10, naranja y luminosa, flotando 10 voxels
por encima del tejado del castillo medieval.

El castillo está en (25, 25, 0) con el torreón central cuyo techo está en
y=33. La esfera (radio 10) flota a 10 voxels por encima → centro en
y = 33 + 10 + 10 = 53. Centrada en x=25, z=0.
"""
from __future__ import annotations
import json
import urllib.request
import sys

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

# Radio 10 → scale = [20, 20, 20] (scale es el diámetro en unidades de voxel)
# Centro: x=25, y=53, z=0
result = mcp_call("create_object", {
    "kind": "sphere",
    "position": [25, 53, 0],
    "scale": [20, 20, 20],
    "color": 0xFF8800,       # naranja
    "emissive": True,        # emite luz
    "mass": 0.0,             # estático (flota)
    "anchored": True,        # no responde a física
    "restitution": 0.5,
})
if result.get("success"):
    oid = result["object_id"]
    print(f"✓ Esfera naranja luminosa creada: object_id={oid} pos=[25, 53, 0] radio=10")
    print(f"  color=0xFF8800 emissive=True")
else:
    print(f"✗ Error: {result}")
    sys.exit(1)