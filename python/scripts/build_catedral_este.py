"""Construye la catedral gótica en el área preparada al este del castillo.

Área 50x50 (x:50-99, z:0-49) ya aplanada con suelo de tierra en y=21.
La catedral (45x25 de base) se centra: base_x=62, base_z=2, base_y=21.
Reutiliza build_cathedral de build_gothic_cathedral.py.
"""
from __future__ import annotations
import json
import urllib.request
import sys
import time

sys.path.insert(0, "scripts")
from build_gothic_cathedral import build_cathedral, send_batch

# Coordenadas fijas en el área preparada
BASE_X = 62
BASE_Z = 2
BASE_Y = 21

print(f"Catedral desde ({BASE_X}, {BASE_Z}), y={BASE_Y}")

blocks = build_cathedral(BASE_X, BASE_Z, BASE_Y)
print(f"\nColocando {len(blocks)} bloques...")

BATCH = 400
ok_total = 0
for i in range(0, len(blocks), BATCH):
    batch = blocks[i:i + BATCH]
    ok = send_batch(batch)
    ok_total += ok
    time.sleep(0.05)

print(f"\n✓ Catedral gótica construida en ({BASE_X}, {BASE_Y}, {BASE_Z})!")
print(f"{ok_total}/{len(blocks)} bloques colocados")
print(f"45x25 de base | torres de 38 bloques | interior hueco | suelo de tierra")