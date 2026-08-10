"""Tests de movimientos programables (propuesta 002, Fase 3)."""

from __future__ import annotations

import math

import pytest

from server.engine.game_loop import GameLoop
from server.engine.objects import ObjectManager, Motion
from server.engine.world import World
from server.mcp.server import McpServer, McpError


@pytest.fixture
def manager():
    return ObjectManager(World(flat_mode=1))


@pytest.fixture
def mcp():
    game = GameLoop(World(flat_mode=1))
    game.add_player(1)
    return McpServer(game)


# ---------------------------------------------------------------------------
# Waypoints
# ---------------------------------------------------------------------------

def test_waypoints_reaches_target(manager):
    obj = manager.create(kind="box", position=[0, 30, 0], mass=1.0)
    obj.motion = manager._build_motion({
        "type": "waypoints",
        "points": [[0, 30, 0], [10, 30, 0]],
        "speed": 10.0,
        "loop": False,
    })
    # En 1s a speed=10 recorre 10 unidades → llega al final
    for _ in range(20):  # 20 ticks * 0.05 = 1s
        manager.update_motions(dt=0.05, now=0.0)
    assert obj.position[0] == pytest.approx(10.0, abs=0.2)
    # Al llegar sin loop, motion se anula
    assert obj.motion is None


def test_waypoints_loops_back_to_start(manager):
    obj = manager.create(kind="box", position=[0, 30, 0], mass=1.0)
    obj.motion = manager._build_motion({
        "type": "waypoints",
        "points": [[0, 30, 0], [2, 30, 0]],
        "speed": 2.0,
        "loop": True,
    })
    # 2s recorre 4 unidades = 2 idas y vueltas (2+2)
    for _ in range(40):
        manager.update_motions(dt=0.05, now=0.0)
    # Tras 2s: ha hecho 0→2 (1s) y 2→0 (1s) → vuelve a 0
    assert obj.position[0] == pytest.approx(0.0, abs=0.3)
    assert obj.motion is not None  # sigue activo (loop)


# ---------------------------------------------------------------------------
# Orbit
# ---------------------------------------------------------------------------

def test_orbit_returns_to_start(manager):
    """Tras un periodo completo 2π/ω, el objeto regresa al punto inicial."""
    obj = manager.create(kind="box", position=[10, 30, 10], mass=1.0)
    center = (10.0, 30.0, 10.0)
    obj.motion = manager._build_motion({
        "type": "orbit",
        "center": list(center),
        "radius": 5.0,
        "axis": "y",
        "angular_speed": 2.0,  # rad/s
    })
    periodo = 2 * math.pi / 2.0  # π s
    ticks = int(periodo / 0.05) + 1
    for _ in range(ticks):
        manager.update_motions(dt=0.05, now=0.0)
    # Regresa cerca del inicio (centro + (R, 0, 0) = (15, 30, 10))
    assert obj.position[0] == pytest.approx(15.0, abs=0.3)
    assert obj.position[2] == pytest.approx(10.0, abs=0.3)


def test_orbit_x_axis(manager):
    obj = manager.create(kind="box", position=[5, 30, 5], mass=1.0)
    obj.motion = manager._build_motion({
        "type": "orbit", "center": [5, 30, 5], "radius": 3.0, "axis": "x", "angular_speed": 1.0,
    })
    manager.update_motions(dt=0.05, now=0.0)
    # Tras un step pequeño, x se mantiene constante (eje x)
    assert obj.position[0] == pytest.approx(5.0, abs=0.1)


# ---------------------------------------------------------------------------
# Parametric
# ---------------------------------------------------------------------------

def test_parametric_sine_oscillates(manager):
    obj = manager.create(kind="box", position=[10, 30, 10], mass=1.0)
    obj.motion = manager._build_motion({
        "type": "parametric",
        "x": "10 + 5*sin(t)",
        "y": "30",
        "z": "10",
        "dt_mul": 1.0,
    })
    # En t=π/2, sin = 1 → x = 15
    for _ in range(int((math.pi / 2) / 0.05)):
        manager.update_motions(dt=0.05, now=0.0)
    assert obj.position[0] == pytest.approx(15.0, abs=0.3)
    assert obj.position[1] == pytest.approx(30.0)


def test_parametric_no_builtins(manager):
    """Expresiones con builtins prohibidos deben fallar (detener motion)."""
    obj = manager.create(kind="box", position=[0, 30, 0], mass=1.0)
    obj.motion = manager._build_motion({
        "type": "parametric",
        "x": "__import__('os').system('echo hacked')",
        "y": "30",
        "z": "0",
    })
    manager.update_motions(dt=0.05, now=0.0)
    # El motion se anula por error
    assert obj.motion is None
    assert obj.position == (0.0, 30.0, 0.0)  # no se movió


def test_parametric_partial_expressions(manager):
    """Solo x definida → y/z se mantienen."""
    obj = manager.create(kind="box", position=[0, 40, 0], mass=1.0)
    obj.motion = manager._build_motion({
        "type": "parametric",
        "x": "t * 10",
        "y": None,
        "z": None,
    })
    for _ in range(10):
        manager.update_motions(dt=0.1, now=0.0)
    assert obj.position[0] == pytest.approx(10.0, abs=0.5)
    assert obj.position[1] == pytest.approx(40.0)


# ---------------------------------------------------------------------------
# Rotate
# ---------------------------------------------------------------------------

def test_rotate_integrates_angular_velocity(manager):
    obj = manager.create(kind="box", position=[0, 30, 0], mass=1.0)
    obj.motion = manager._build_motion({
        "type": "rotate",
        "angular_velocity": [0.0, 1.0, 0.0],
        "loop": True,
    })
    for _ in range(20):
        manager.update_motions(dt=0.05, now=0.0)
    # Tras 1s a 1 rad/s → rotation.y = 1.0
    assert obj.rotation[1] == pytest.approx(1.0, abs=0.05)


# ---------------------------------------------------------------------------
# Dynamic (cae por gravedad tras asignar velocidad)
# ---------------------------------------------------------------------------

def test_dynamic_motion_with_gravity_falls(manager):
    """Un objeto con motion dynamic + gravity debe caer via physics.update_object."""
    from server.engine.physics import PhysicsSystem
    p = PhysicsSystem(manager.world)
    obj = manager.create(kind="box", position=[5, 30, 5], mass=1.0)
    obj.motion = manager._build_motion({
        "type": "dynamic", "velocity": [0, 0, 0], "gravity": True,
    })
    # La velocidad inicial la marca el motion; aquí 0. La gravedad la aplica physics.
    for _ in range(10):
        manager.update_motions(dt=0.05, now=0.0)
        p.update_object(obj, dt=0.05)
    assert obj.position[1] < 30.0
    assert obj.velocity[1] < 0  # acelerando hacia abajo


def test_dynamic_motion_initial_velocity(manager):
    """Si el motion trae velocity, el objeto debe iniciar con esa velocidad."""
    from server.engine.physics import PhysicsSystem
    p = PhysicsSystem(manager.world)
    obj = manager.create(kind="box", position=[5, 30, 5], mass=1.0)
    obj.motion = manager._build_motion({
        "type": "dynamic", "velocity": [3, 0, 0], "gravity": False,
    })
    # Aplicar velocity inicial desde el motion
    obj.set_velocity(*obj.motion.velocity)
    p.update_object(obj, dt=1.0)  # 1s sin gravedad
    assert obj.position[0] == pytest.approx(8.0, abs=0.5)


# ---------------------------------------------------------------------------
# Expiración
# ---------------------------------------------------------------------------

def test_expire_at_destroys_with_motion(manager):
    obj = manager.create(kind="box", position=[0, 30, 0], mass=1.0, expire_at=0.5)
    obj.motion = manager._build_motion({"type": "rotate", "angular_velocity": [0, 1, 0]})
    events = manager.update_motions(dt=0.1, now=obj._spawn_time + 0.6)
    assert len(events) == 1
    assert events[0]["cause"] == "expire"
    assert obj not in manager.objects


# ---------------------------------------------------------------------------
# Handler MCP
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_mcp_move_object_waypoints(mcp):
    r = await mcp.tool_create_object({"kind": "box", "position": [0, 30, 0]})
    oid = r["object_id"]
    r2 = await mcp.tool_move_object({
        "object_id": oid,
        "motion": {"type": "waypoints", "points": [[0, 30, 0], [10, 30, 0]], "speed": 10.0, "loop": False},
    })
    assert r2["success"] is True
    assert r2["motion"]["type"] == "waypoints"
    # Verificar que el motion quedó asignado
    got = await mcp.tool_get_object({"object_id": oid})
    assert got["object"]["motion"]["type"] == "waypoints"


@pytest.mark.asyncio
async def test_mcp_move_object_stop(mcp):
    r = await mcp.tool_create_object({"kind": "box", "position": [0, 30, 0]})
    oid = r["object_id"]
    await mcp.tool_move_object({"object_id": oid, "motion": {"type": "rotate", "angular_velocity": [0, 1, 0]}})
    r2 = await mcp.tool_move_object({"object_id": oid, "motion": {"type": "stop"}})
    assert r2["success"] is True
    assert r2["motion"] is None
    obj = mcp.game_loop.object_manager.get(oid)
    assert obj.motion is None
    assert obj.velocity == (0.0, 0.0, 0.0)


@pytest.mark.asyncio
async def test_mcp_move_object_invalid_motion_type(mcp):
    r = await mcp.tool_create_object({"kind": "box", "position": [0, 30, 0]})
    oid = r["object_id"]
    with pytest.raises(McpError, match="invalid motion type"):
        await mcp.tool_move_object({"object_id": oid, "motion": {"type": "teleport"}})


@pytest.mark.asyncio
async def test_mcp_move_object_not_found(mcp):
    with pytest.raises(McpError, match="not found"):
        await mcp.tool_move_object({"object_id": 999, "motion": {"type": "stop"}})


@pytest.mark.asyncio
async def test_mcp_move_object_in_definitions():
    from pathlib import Path
    p = Path(__file__).resolve().parent.parent.parent.parent / "shared" / "tools" / "definitions.json"
    import json
    with open(p) as f:
        defs = json.load(f)
    assert "move_object" in defs["tools"]
    assert defs["tools"]["move_object"]["category"] == "objects"
    assert "python" in defs["tools"]["move_object"]["servers"]