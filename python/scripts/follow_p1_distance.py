"""
Mantiene al Jugador 2 siguiendo al Jugador 1 a una distancia fija.

Calcula un punto objetivo a 'distance' bloques de P1 en la linea P1->P2
y conduce a P2 hacia ese punto usando el gamepad virtual. Reorienta la camara
suavemente para mirar hacia P1.
"""

import json, math, time, urllib.request, signal, sys

URL = "http://localhost:9000/mcp"
_RPC_ID = 0
RUNNING = True


def mcp(method, params):
    global _RPC_ID
    _RPC_ID += 1
    req = urllib.request.Request(
        URL,
        data=json.dumps({
            "jsonrpc": "2.0",
            "id": _RPC_ID,
            "method": "tools/call",
            "params": {"name": method, "arguments": params},
        }).encode(),
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=8) as r:
            resp = json.loads(r.read().decode())
            if "error" in resp:
                return {"error": resp["error"].get("message", str(resp["error"]))}
            content = resp.get("content", [])
            if content and isinstance(content[0], dict) and "text" in content[0]:
                return json.loads(content[0]["text"])
            return {}
    except Exception as e:
        return {"error": str(e)}


def player_pos(pid):
    resp = mcp("get_player_state", {"player_id": pid})
    if resp.get("error"):
        return None
    p = resp.get("position")
    r = resp.get("rotation", {})
    return (p["x"], p["y"], p["z"], r.get("y", 0)) if p else None


def norm(a):
    while a > math.pi:
        a -= 2 * math.pi
    while a < -math.pi:
        a += 2 * math.pi
    return a


def clamp(v, lo=-1, hi=1):
    return max(lo, min(hi, v))


def stop():
    mcp("gamepad_input", {"player_id": 2, "input": {"move": {"x": 0, "z": 0}, "look": {"x": 0, "y": 0}}})


def on_signal(*_):
    global RUNNING
    RUNNING = False
    stop()
    print("\n[follow] detenido")
    sys.exit(0)


signal.signal(signal.SIGINT, on_signal)
signal.signal(signal.SIGTERM, on_signal)


def main(distance=4.0):
    # Esperar a que el mundo/jugadores esten listos
    for _ in range(25):
        if not mcp("get_player_state", {"player_id": 2}).get("error"):
            if mcp("gamepad_connect", {"player_id": 2}).get("success"):
                print(f"[follow] gamepad virtual listo, distancia objetivo={distance} bloques")
                break
        time.sleep(0.2)
    else:
        print("[follow] no se pudo conectar gamepad virtual")
        return

    while RUNNING:
        p1 = player_pos(1)
        p2 = player_pos(2)
        if not p1 or not p2:
            time.sleep(0.2)
            continue

        dx = p1[0] - p2[0]
        dz = p1[2] - p2[2]
        dist = math.hypot(dx, dz)

        # Punto objetivo: a 'distance' bloques de P1, en la direccion P1 <- P2
        if dist < 0.1:
            # evitar division por cero
            move = {"x": 0, "z": 0}
        else:
            ratio = distance / dist
            tx = p1[0] - dx * ratio
            tz = p1[2] - dz * ratio

            pdx = tx - p2[0]
            pdz = tz - p2[2]
            pdist = math.hypot(pdx, pdz)
            if pdist < 0.3:
                move = {"x": 0, "z": 0}
            else:
                move = {"x": clamp(pdx / pdist), "z": clamp(pdz / pdist)}

        # Mirar hacia P1
        desired_yaw = math.atan2(-dx, -dz)
        look_x = clamp(-norm(desired_yaw - p2[3]) * 0.6)

        mcp("gamepad_input", {
            "player_id": 2,
            "input": {
                "move": move,
                "look": {"x": look_x, "y": 0},
                "jump": False,
            },
        })
        time.sleep(0.1)


if __name__ == "__main__":
    target = float(sys.argv[1]) if len(sys.argv) > 1 else 4.0
    main(target)
