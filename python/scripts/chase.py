"""
Persigue al Jugador 1 usando el gamepad virtual (movimiento natural).
Descompone la direccion hacia el objetivo en stick del gamepad,
y reorienta la camara progresivamente.
"""

import json, math, time, urllib.request

URL = "http://localhost:9000/mcp"
_RPC_ID = 0


def mcp(method, params):
    global _RPC_ID
    _RPC_ID += 1
    req = urllib.request.Request(
        URL,
        data=json.dumps(
            {
                "jsonrpc": "2.0",
                "id": _RPC_ID,
                "method": "tools/call",
                "params": {"name": method, "arguments": params},
            }
        ).encode(),
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=8) as r:
            resp = json.loads(r.read().decode())
            if "error" in resp:
                return {"error": resp["error"].get("message", str(resp["error"]))}
            content = resp.get("result", {}).get("content", [])
            if content and isinstance(content[0], dict) and "text" in content[0]:
                return json.loads(content[0]["text"])
            return {}
    except Exception as e:
        return {"error": str(e)}


def live_pos(pid):
    resp = mcp("get_top_down_view", {"player_id": pid, "radius": 1})
    if resp.get("error"):
        return None
    pp = resp.get("playerPosition")
    return (pp["x"], pp["y"], pp["z"]) if pp else None


def rot_y(pid):
    r = mcp("get_rotation", {"player_id": pid})
    return r.get("rotation", {}).get("y", 0) if "rotation" in r else 0


def norm(a):
    while a > math.pi:
        a -= 2 * math.pi
    while a < -math.pi:
        a += 2 * math.pi
    return a


def clamp(v, lo=-1, hi=1):
    return max(lo, min(hi, v))


def dir_to_move(dx, dz, yaw, mag=1.0):
    f = dx * (-math.sin(yaw)) + dz * (-math.cos(yaw))
    r = dx * math.cos(yaw) + dz * (-math.sin(yaw))
    m = min(1.0, mag)
    return {"x": clamp(r * m), "z": clamp(-f * m)}


def steer(yaw, desired):
    err = norm(desired - yaw)
    return -clamp(err * 1.5)


if __name__ == "__main__":
    for _ in range(25):
        if not mcp("get_top_down_view", {"player_id": 2, "radius": 1}).get("error"):
            if mcp("gamepad_connect", {"player_id": 2}).get("success"):
                print("gamepad virtual listo")
                break
        time.sleep(1)
    else:
        print("sin cliente gamepad")
        raise SystemExit

    for i in range(40):
        p1, p2, yaw = live_pos(1), live_pos(2), rot_y(2)
        if not p1 or not p2:
            time.sleep(0.15)
            continue
        dx, dz = p1[0] - p2[0], p1[2] - p2[2]
        dist = math.hypot(dx, dz)
        print(f"{i}: P1={p1} P2={p2} dist={round(dist, 1)}")
        if dist < 1.5:
            mcp("gamepad_input", {"player_id": 2, "input": {"move": {"x": 0, "z": 0}}})
            print("alcanzado")
            break
        desired = math.atan2(-dx, -dz)
        mag = min(1.0, dist / 3.0)
        move = dir_to_move(dx, dz, yaw, mag)
        lookx = steer(yaw, desired)
        mcp(
            "gamepad_input",
            {"player_id": 2, "input": {"move": move, "look": {"x": lookx, "y": 0}}},
        )
        time.sleep(0.15)

    mcp(
        "gamepad_input",
        {"player_id": 2, "input": {"move": {"x": 0, "z": 0}, "look": {"x": 0, "y": 0}}},
    )
    print("=== fin ===", live_pos(2))
