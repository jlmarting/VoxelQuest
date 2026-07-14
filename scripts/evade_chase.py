"""
Evasion + chase infinito para Jugador 2.
- Huye de monstruos o persigue a P1 con movimiento natural (gamepad virtual).
- Usa modo vuelo para ascender cuando P1 esta arriba.
- Si queda por encima de P1, apaga el vuelo y cae.
- Para a 2 bloques de distancia horizontal de P1.
- Detecta agujeros, salta, y rompe paredes/techos/suelos si atascado.
- Si detecta >3 paredes solidas (pozo): las rompe por coordenadas directas.
- Ultimo recurso: teletransporte cerca de P1.
"""

import json, math, time, urllib.request, random, sys

URL = "http://localhost:9000/mcp"


def mcp(method, params):
    req = urllib.request.Request(
        URL,
        data=json.dumps({"method": method, "params": params}).encode(),
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=6) as r:
            return json.loads(r.read().decode())
    except Exception:
        return {"error": "exception"}


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


def get_block(wx, wy, wz):
    return mcp("get_block", {"x": wx, "y": wy, "z": wz}).get("type", -1)


def hole_ahead(p2, yaw, look_dist=2):
    sx, sz = -math.sin(yaw), -math.cos(yaw)
    for i in range(1, look_dist + 1):
        fx = int(round(p2[0] + sx * i * 2))
        fz = int(round(p2[2] + sz * i * 2))
        fy = int(p2[1]) - 1
        if get_block(fx, fy, fz) == 0 and get_block(fx, fy - 1, fz) == 0:
            return True, fx, fz
    return False, None, None


# conexion
for _ in range(40):
    if not mcp("get_top_down_view", {"player_id": 2, "radius": 1}).get("error"):
        if mcp("gamepad_connect", {"player_id": 2}).get("success"):
            print("gamepad virtual listo", file=sys.stderr)
            break
    time.sleep(1)
else:
    print("sin gamepad", file=sys.stderr)
    sys.exit(1)

print("evade+chase (escape pozo) iniciado", file=sys.stderr)

last, stuck, alt_heading, jump_cd, break_cd = None, 0, None, 0, 0
fly_active = False
fly_pulse = 0
tick = 0
while True:
    tick += 1
    chase_up = False
    try:
        p2 = live_pos(2)
        yaw = rot_y(2)
        if not p2:
            time.sleep(0.2)
            continue

        sx, sz = -math.sin(yaw), -math.cos(yaw)

        if tick % 4 == 0:
            has_hole, _, _ = hole_ahead(p2, yaw, 2)
            fh = get_block(int(p2[0] + sx), int(p2[1]), int(p2[2] + sz))
            fhh = get_block(int(p2[0] + sx), int(p2[1]) + 1, int(p2[2] + sz))
            above = get_block(int(p2[0]), int(p2[1]) + 1, int(p2[2]))
        else:
            has_hole = False
            fh = -1
            fhh = -1
            above = -1

        ents = mcp("get_nearby_entities", {"player_id": 2, "radius": 30}).get(
            "entities", []
        )
        enemies = sorted(
            [e for e in ents if e.get("type") == "enemy"],
            key=lambda e: e.get("distance", 1e9),
        )
        near = enemies[0] if enemies else None
        threat = near["distance"] if near else 999

        move, lookx, jump, rs = {"x": 0, "z": 0}, 0, False, False
        moving, chasing = False, False

        if near and threat < 16:
            # H U I R
            if fly_active:
                fly_pulse = 1
                fly_active = False
            dx = p2[0] - near["position"]["x"]
            dz = p2[2] - near["position"]["z"]
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
            moving = True
        else:
            # P E R S E G U I R
            p1 = live_pos(1)
            if p1:
                dx = p1[0] - p2[0]
                dz = p1[2] - p2[2]
                dy = p1[1] - p2[1]
                dist = math.hypot(dx, dz)
                need_move = dist > 2.0 or abs(dy) > 1.0

                if need_move:
                    chasing = True
                    chase_up = dy > 0.5
                    desired = math.atan2(-dx, -dz)
                    if alt_heading is not None:
                        desired = alt_heading
                        if stuck < 4:
                            alt_heading = None
                    mag = min(1.0, (dist - 2.0) / 3.0)
                    move = dir_to_move(dx, dz, yaw, mag)
                    lookx = steer(yaw, desired)
                    moving = True

                    # gestion de vuelo
                    if dy > 2.0 and not fly_active:
                        fly_pulse = 1
                        fly_active = True
                        print("  vuelo ON", file=sys.stderr)
                    elif dy < -2.0 and fly_active:
                        fly_pulse = 1
                        fly_active = False
                        print("  vuelo OFF (encima)", file=sys.stderr)
                    elif abs(dy) <= 2.0 and fly_active:
                        fly_pulse = 1
                        fly_active = False
                        print("  vuelo OFF (altura)", file=sys.stderr)

                    if fly_active:
                        if dy > 0.5:
                            jump = True
                        elif dy < -0.5:
                            rs = True
            else:
                move = {"x": 0, "z": -0.5}

        # agujero
        if has_hole and moving and jump_cd == 0:
            jump = True
            jump_cd = 3
            alt_heading = yaw + random.choice([-1, 1]) * (math.pi / 4)

        # input
        inp = {"move": move, "look": {"x": lookx, "y": 0}}
        if jump:
            inp["jump"] = True
        if rs:
            inp["rs"] = True
        if fly_pulse > 0:
            inp["fly"] = True
            fly_pulse -= 1
        mcp("gamepad_input", {"player_id": 2, "input": inp})
        if jump_cd > 0:
            jump_cd -= 1

        # atasco
        dpos = math.hypot(p2[0] - last[0], p2[2] - last[2]) if last else 0
        if moving:
            stuck = stuck + 1 if dpos < 0.25 else 0
        last = p2

        # acciones correctivas
        if stuck == 6 and jump_cd == 0:
            mcp("gamepad_input", {"player_id": 2, "input": {"jump": True}})
            jump_cd = 4
        if stuck == 8 and break_cd == 0:
            if fh not in (-1, 0, 10):
                mcp("look", {"player_id": 2, "pitch": 0})
                time.sleep(0.05)
                mcp("break_block_as_player", {"player_id": 2})
                break_cd = 4
        if stuck == 10 and break_cd == 0:
            if fhh not in (-1, 0, 10):
                mcp("look", {"player_id": 2, "pitch": -0.78})
                time.sleep(0.08)
                mcp("break_block_as_player", {"player_id": 2})
                mcp("look", {"player_id": 2, "pitch": 0})
                break_cd = 4
        if stuck == 12 and break_cd == 0:
            if above not in (-1, 0, 10):
                mcp("look", {"player_id": 2, "pitch": -1.5})
                time.sleep(0.08)
                mcp("break_block_as_player", {"player_id": 2})
                mcp("look", {"player_id": 2, "pitch": 0})
                break_cd = 4
        if stuck == 14 and break_cd == 0 and not chase_up and not fly_active:
            below = get_block(int(p2[0]), int(p2[1]) - 1, int(p2[2]))
            if below not in (-1, 0, 10):
                mcp("look", {"player_id": 2, "pitch": 1.5})
                time.sleep(0.08)
                mcp("break_block_as_player", {"player_id": 2})
                mcp("look", {"player_id": 2, "pitch": 0})
                break_cd = 4
        if stuck >= 16:
            alt_heading = yaw + random.choice([-1, 1]) * (math.pi / 3 + 0.5)
            stuck = 0

        # fallback directo: cavar paredes (por coordenada, no raycast)
        if stuck >= 12:
            env = mcp("get_environment", {"player_id": 2})
            adj = env.get("adjacent", {})
            solid_sides = sum(
                1
                for k in ["north", "south", "east", "west", "above", "below"]
                if adj.get(k, -1) not in (-1, 0, 10)
            )
            if solid_sides >= 3 and break_cd == 0:
                px, py, pz = int(p2[0]), int(p2[1]), int(p2[2])
                dirs = {
                    "north": (0, 0, -1),
                    "south": (0, 0, 1),
                    "east": (1, 0, 0),
                    "west": (-1, 0, 0),
                    "above": (0, 1, 0),
                    "below": (0, -1, 0),
                }
                for k, (dx, dy, dz) in dirs.items():
                    if adj.get(k, -1) not in (-1, 0, 10):
                        mcp("break_block", {"x": px + dx, "y": py + dy, "z": pz + dz})
                break_cd = 6
                stuck = 5
                print(f"  {solid_sides} paredes rotas", file=sys.stderr)
            elif solid_sides >= 3 and break_cd > 2:
                # sigue atrapado -> teleport
                p1 = live_pos(1)
                if p1:
                    h = mcp("get_height", {"x": int(p1[0]), "z": int(p1[2])}).get(
                        "height", 20
                    )
                    tx, tz = int(p1[0]) + 2, int(p1[2]) + 1
                    mcp("teleport", {"player_id": 2, "x": tx, "y": h + 1, "z": tz})
                    print(f"  teleport a ({tx},{h + 1},{tz})", file=sys.stderr)
                    stuck = 0
                    if fly_active:
                        fly_pulse = 1
                        fly_active = False

        if break_cd > 0:
            break_cd -= 1

        if tick % 30 == 0:
            info = f"P2={p2} " + (f"enemigo={round(threat, 1)}" if near else "chase")
            info += f" volando={fly_active} stuck={stuck}"
            print(info, file=sys.stderr)

        time.sleep(0.12)
    except Exception as e:
        print(f"error: {e}", file=sys.stderr)
        time.sleep(1)
