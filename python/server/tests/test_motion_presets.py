"""Tests de presets de movimiento MCP (propuesta 002, Fase 4)."""

from __future__ import annotations

import pytest

from server.engine.game_loop import GameLoop
from server.engine.physics import PhysicsSystem
from server.engine.world import World
from server.mcp.server import McpServer, McpError


@pytest.fixture
def mcp():
    game = GameLoop(World(flat_mode=1))
    game.add_player(1)
    return McpServer(game)


async def _create(mcp, **kw):
    r = await mcp.tool_create_object({"kind": "box", "position": [0, 30, 0], **kw})
    return r["object_id"]


# ---------------------------------------------------------------------------
# move_linear
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_move_linear_sets_dynamic_motion(mcp):
    oid = await _create(mcp)
    r = await mcp.tool_move_linear({"object_id": oid, "velocity": [3, 0, 0]})
    assert r["success"] is True
    assert r["motion"]["type"] == "dynamic"
    assert r["motion"]["velocity"] == [3, 0, 0]
    assert r["motion"]["gravity"] is False
    obj = mcp.game_loop.object_manager.get(oid)
    # La velocidad inicial debe estar aplicada al objeto
    assert obj.velocity == (3.0, 0.0, 0.0)


@pytest.mark.asyncio
async def test_move_linear_moves_object(mcp):
    oid = await _create(mcp, mass=1.0)
    await mcp.tool_move_linear({"object_id": oid, "velocity": [3, 0, 0]})
    p = mcp.game_loop.physics
    obj = mcp.game_loop.object_manager.get(oid)
    for _ in range(20):
        mcp.game_loop.object_manager.update_motions(dt=0.05, now=0.0)
        p.update_object(obj, dt=0.05)
    # 1s a 3 u/s con damping lineal (0.98^20 ≈ 0.67) → x ≈ 2.44
    assert obj.position[0] == pytest.approx(2.44, abs=0.15)
    # Sin damping debería llegar a 3.0; verificar que no supera la cota física
    assert obj.position[0] < 3.0


# ---------------------------------------------------------------------------
# move_orbit
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_move_orbit_assigns_motion(mcp):
    oid = await _create(mcp)
    r = await mcp.tool_move_orbit({
        "object_id": oid, "center": [10, 30, 10], "radius": 5, "axis": "y", "angular_speed": 0.5,
    })
    assert r["motion"]["type"] == "orbit"
    assert r["motion"]["center"] == [10, 30, 10]
    assert r["motion"]["radius"] == 5


# ---------------------------------------------------------------------------
# move_bounce
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_move_bounce_loops(mcp):
    oid = await _create(mcp)
    r = await mcp.tool_move_bounce({
        "object_id": oid, "a": [0, 30, 0], "b": [2, 30, 0], "speed": 2,
    })
    assert r["motion"]["type"] == "waypoints"
    assert r["motion"]["loop"] is True
    obj = mcp.game_loop.object_manager.get(oid)
    # Tras 2s (2+2 unidades a speed 2) → vuelve a 0
    for _ in range(40):
        mcp.game_loop.object_manager.update_motions(dt=0.05, now=0.0)
    assert obj.position[0] == pytest.approx(0.0, abs=0.4)


# ---------------------------------------------------------------------------
# move_projectile
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_move_projectile_promotes_kind_and_marks_destructible(mcp):
    oid = await _create(mcp, kind="box")
    r = await mcp.tool_move_projectile({
        "object_id": oid, "velocity": [5, 10, 0], "gravity": True,
        "damage_on_impact": 5.0, "destroy_on_impact": True,
    })
    assert r["motion"]["type"] == "dynamic"
    assert r["motion"]["gravity"] is True
    obj = mcp.game_loop.object_manager.get(oid)
    assert obj.kind == "projectile"
    assert obj.destructible is True
    assert obj.fragile >= 1.0
    assert obj.damage_on_impact == 5.0
    assert obj.destroy_on_impact is True
    # Velocidad inicial aplicada
    assert obj.velocity == (5.0, 10.0, 0.0)


@pytest.mark.asyncio
async def test_move_projectile_falls_with_gravity(mcp):
    oid = await _create(mcp, mass=1.0)
    await mcp.tool_move_projectile({"object_id": oid, "velocity": [0, 0, 0], "gravity": True})
    p = mcp.game_loop.physics
    obj = mcp.game_loop.object_manager.get(oid)
    y0 = obj.position[1]
    for _ in range(10):
        mcp.game_loop.object_manager.update_motions(dt=0.05, now=0.0)
        p.update_object(obj, dt=0.05)
    assert obj.position[1] < y0  # cayó


# ---------------------------------------------------------------------------
# move_rotate
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_move_rotate_assigns_angular_velocity(mcp):
    oid = await _create(mcp)
    r = await mcp.tool_move_rotate({"object_id": oid, "angular_velocity": [0, 2, 0]})
    assert r["motion"]["type"] == "rotate"
    obj = mcp.game_loop.object_manager.get(oid)
    for _ in range(10):
        mcp.game_loop.object_manager.update_motions(dt=0.05, now=0.0)
    # 0.5s * 2 rad/s = 1 rad
    assert obj.rotation[1] == pytest.approx(1.0, abs=0.1)


# ---------------------------------------------------------------------------
# stop_motion
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_stop_motion_clears_motion_and_velocity(mcp):
    oid = await _create(mcp)
    await mcp.tool_move_rotate({"object_id": oid, "angular_velocity": [0, 5, 0]})
    obj = mcp.game_loop.object_manager.get(oid)
    obj.set_velocity(3, 0, 0)
    r = await mcp.tool_stop_motion({"object_id": oid})
    assert r["success"] is True
    assert r["motion"] is None
    assert obj.motion is None
    assert obj.velocity == (0.0, 0.0, 0.0)


# ---------------------------------------------------------------------------
# apply_impulse
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_apply_impulse_modifies_velocity(mcp):
    oid = await _create(mcp, mass=2.0)
    r = await mcp.tool_apply_impulse({"object_id": oid, "impulse": [0, 10, 0]})
    assert r["success"] is True
    # v += impulse/mass = 10/2 = 5
    assert r["velocity"] == [0.0, 5.0, 0.0]


@pytest.mark.asyncio
async def test_apply_impulse_rejects_static(mcp):
    oid = await _create(mcp, mass=0.0)
    with pytest.raises(McpError, match="static"):
        await mcp.tool_apply_impulse({"object_id": oid, "impulse": [0, 10, 0]})


@pytest.mark.asyncio
async def test_apply_impulse_cancels_kinematic_motion(mcp):
    oid = await _create(mcp, mass=1.0)
    await mcp.tool_move_orbit({"object_id": oid, "center": [0, 30, 0], "radius": 3, "axis": "y"})
    obj = mcp.game_loop.object_manager.get(oid)
    assert obj.motion is not None  # orbit activo
    await mcp.tool_apply_impulse({"object_id": oid, "impulse": [5, 0, 0]})
    assert obj.motion is None  # anulado
    assert obj.velocity == (5.0, 0.0, 0.0)


# ---------------------------------------------------------------------------
# Todas las tools aparecen en definitions.json
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_all_object_tools_in_definitions():
    from pathlib import Path
    import json
    p = Path(__file__).resolve().parent.parent.parent.parent / "shared" / "tools" / "definitions.json"
    with open(p) as f:
        defs = json.load(f)
    expected = ["create_object", "update_object", "list_objects", "get_object", "destroy_object",
                "move_object", "move_linear", "move_orbit", "move_bounce", "move_projectile",
                "move_rotate", "stop_motion", "apply_impulse"]
    for name in expected:
        assert name in defs["tools"], f"missing {name}"
        assert defs["tools"][name]["category"] == "objects"
        assert "python" in defs["tools"][name]["servers"]


# ---------------------------------------------------------------------------
# tools/list expone las 13 tools
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_tools_list_includes_all_object_tools():
    from server.engine.game_loop import GameLoop
    from server.engine.world import World
    mcp = McpServer(GameLoop(World(flat_mode=1)))
    tools = mcp.list_tools()
    names = {t["name"] for t in tools}
    expected = {"create_object", "update_object", "list_objects", "get_object", "destroy_object",
                "move_object", "move_linear", "move_orbit", "move_bounce", "move_projectile",
                "move_rotate", "stop_motion", "apply_impulse"}
    missing = expected - names
    assert not missing, f"missing in tools/list: {missing}"