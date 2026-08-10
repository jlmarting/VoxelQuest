"""
Crea un cilindro como OBJETO MOVIL y lo hace girar sobre el eje horizontal (X)
en sentido antihorario a velocidad media (1 rad/s ≈ 1 vuelta cada 6.3 segundos).
Usa las tools de objetos moviles del servidor Python (propuesta 002).
"""
import json, urllib.request, time, math

URL = "http://localhost:9000/mcp"
_RPC = [0]

AIR = 0

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

def detect_ground(wx, wz):
    for y in range(80, 0, -1):
        res = mcp("get_block", {"x": wx, "y": y, "z": wz})
        bt = res.get("type", 0) if isinstance(res, dict) else 0
        if bt != AIR and bt != 7:  # no aire ni agua
            return y + 1
    return 30

# 1. Obtener posicion del jugador
players = mcp("list_players", {})
p = players.get("players", [{}])[0] if isinstance(players, dict) else {}
px, pz = int(p.get("x", 0)), int(p.get("z", 0))
print(f"Jugador en ({px}, {pz})")

base_y = detect_ground(px, pz)
print(f"Suelo en y={base_y}")

# Posicion del cilindro (5 bloques al este del jugador, elevado para que gire libremente)
cx = px + 5
cy = base_y + 8  # 8 bloques sobre el suelo para que gire sin tocar el suelo
cz = pz

print(f"\nCreando cilindro movil en ({cx}, {cy}, {cz})...")

# 2. Crear objeto tipo box (simula cilindro pixelado)
# Escala: radio 3 → diámetro 6, altura 12
col = 0x888888  # Gris piedra (STONE)
result = mcp("create_object", {
    "kind": "box",
    "position": [cx, cy, cz],
    "scale": [6, 12, 6],
    "color": col,
    "mass": 1.0,
    "anchored": False,
    "restitution": 0.3,
    "friction": 0.5,
})

if "error" in result:
    print(f"✗ Error creando objeto: {result['error']}")
    exit(1)

obj_id = result["object_id"]
print(f"✓ Objeto creado: ID={obj_id}")
print(f"  Posicion: ({cx}, {cy}, {cz})")
print(f"  Escala: [6, 12, 6] (radio 3, altura 12)")

# 3. Aplicar rotacion continua sobre el eje horizontal (X)
# angular_velocity [rad/s]: [eje_x, eje_y, eje_z]
# Sentido antihorario sobre X = valor positivo (regla de la mano derecha)
# Velocidad media: 1 rad/s ≈ 1 vuelta cada 6.28 segundos
print(f"\nAplicando rotacion continua...")
print(f"  Eje: X (horizontal)")
print(f"  Velocidad: 1 rad/s (media, ~1 vuelta/6.3s)")
print(f"  Sentido: antihorario")

rot_result = mcp("move_rotate", {
    "object_id": obj_id,
    "angular_velocity": [1.0, 0.0, 0.0],  # solo sobre eje X
})

if "error" in rot_result:
    print(f"✗ Error aplicando rotacion: {rot_result['error']}")
    exit(1)

print(f"\n✓ Cilindro girando!")
print(f"  Object ID: {obj_id}")
print(f"  Movimiento: {rot_result.get('motion', {})}")
print(f"\nEl cilindro gira indefinidamente sobre su eje horizontal.")
print(f"Para detenerlo: move_rotate con angular_velocity [0,0,0] o stop_motion")
