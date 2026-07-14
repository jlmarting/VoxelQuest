"""
Evade monstruos con el Jugador 2 usando el gamepad virtual.

Bucles:
- get_nearby_entities(radius=30) -> huye del monstruo mas cercano (<16b)
- salta si el monstruo esta pegado (<3b) o si detecta bloqueo
- si bloqueado 10 ticks: rumbo alternativo (±60°)
- si bloqueado >=14 y monstruo cerca: rompe el suelo bajo los pies
- sin amenaza: patrulla hacia delante
"""

import json, math, time, urllib.request, random

URL = "http://localhost:9000/mcp"


def mcp(method, params):
    req = urllib.request.Request(
        URL,
        data=json.dumps({"method": method, "params": params}).encode(),
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=8) as r:
            return json.loads(r.read().decode())
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
    for _ in range(40):
        if not mcp("get_top_down_view", {"player_id": 2, "radius": 1}).get("error"):
            if mcp("gamepad_connect", {"player_id": 2}).get("success"):
                print("gamepad virtual listo")
                break
        time.sleep(1)
    else:
        print("sin cliente gamepad - recarga el navegador")
        raise SystemExit

    print("=== evade ===")
    start = time.time()
    last = live_pos(2)
    stuck = 0
    alt_heading = None
    jump_cd = 0
    break_cd = 0
    tick = 0
    while time.time() - start < 100:
        tick += 1
        p2 = live_pos(2)
        yaw = rot_y(2)
        if not p2:
            time.sleep(0.15)
            continue

        ents = mcp("get_nearby_entities", {"player_id": 2, "radius": 30}).get(
            "entities", []
        )
        enemies = sorted(
            [e for e in ents if e.get("type") == "enemy"],
            key=lambda e: e.get("distance", 1e9),
        )
        near = enemies[0] if enemies else None
        threat = near["distance"] if near else 999

        move, lookx, jump = {"x": 0, "z": 0}, 0, False

        if near and threat < 16:
            dx, dz = p2[0] - near["position"]["x"], p2[2] - near["position"]["z"]
            desired = math.atan2(-dx, -dz)
            if alt_heading is not None:
                desired = alt_heading
                if stuck < 4:
                    alt_heading = None
            move = dir_to_move(dx, dz, yaw, 1.0)
            lookx = steer(yaw, desired)
            if (threat < 3 or stuck > 3) and jump_cd == 0:
                jump = True
                jump_cd = 4
        else:
            move = {"x": 0, "z": -0.5}
            if alt_heading is not None:
                move = dir_to_move(
                    math.sin(alt_heading), math.cos(alt_heading), yaw, 0.5
                )
                if stuck < 4:
                    alt_heading = None

        inp = {"move": move, "look": {"x": lookx, "y": 0}}
        if jump:
            inp["jump"] = True
        mcp("gamepad_input", {"player_id": 2, "input": inp})
        if jump_cd > 0:
            jump_cd -= 1

        dpos = math.hypot(p2[0] - last[0], p2[2] - last[2]) if last else 0
        if move["x"] or move["z"]:
            stuck = stuck + 1 if dpos < 0.25 else 0
        last = p2

        if stuck == 6 and jump_cd == 0:
            mcp("gamepad_input", {"player_id": 2, "input": {"jump": True}})
            jump_cd = 4
        if stuck == 10:
            alt_heading = yaw + random.choice([-1, 1]) * (math.pi / 3)
            stuck = 0
        if stuck >= 14 and threat < 5 and break_cd == 0:
            mcp("look", {"player_id": 2, "pitch": 1.47})
            time.sleep(0.1)
            mcp("break_block_as_player", {"player_id": 2})
            mcp("look", {"player_id": 2, "pitch": 0})
            stuck = 0
            break_cd = 6
        if break_cd > 0:
            break_cd -= 1

        if tick % 10 == 0:
            print(
                f"t={int(time.time() - start)}s {p2} enemigos={len(enemies)} cercano={round(threat, 1)} stuck={stuck}"
            )

        time.sleep(0.15)

    mcp(
        "gamepad_input",
        {"player_id": 2, "input": {"move": {"x": 0, "z": 0}, "look": {"x": 0, "y": 0}}},
    )
    print("=== fin ===", live_pos(2))
