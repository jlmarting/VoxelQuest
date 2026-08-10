"""Tests de esculturas subvoxel (propuesta 002, Fase 6)."""

from __future__ import annotations

import pytest

from server.engine.constants import MAX_SCULPTURE_VOXELS, SUBVOXEL_MIN_SIZE
from server.engine.game_loop import GameLoop
from server.engine.objects import (
    ObjectManager,
    generate_sculpture,
    validate_sculpture,
    VALID_GENERATORS,
)
from server.engine.world import World
from server.mcp.server import McpServer, McpError


@pytest.fixture
def manager():
    w = World(flat_mode=1)
    w.update_around(10, 10)
    return ObjectManager(w)


@pytest.fixture
def mcp():
    game = GameLoop(World(flat_mode=1))
    game.add_player(1)
    return McpServer(game)


# ---------------------------------------------------------------------------
# Generadores
# ---------------------------------------------------------------------------

def test_generator_sphere_produces_voxels_within_radius():
    voxels = generate_sculpture("sphere", {"radius": 1.5, "color": 0xFF0000}, resolution=4)
    assert len(voxels) > 0
    # Todos los voxels deben estar dentro del radio (considerando size)
    size = 1.0 / 4
    for v in voxels:
        r = (v["x"] ** 2 + v["y"] ** 2 + v["z"] ** 2) ** 0.5
        assert r <= 1.5 + size


def test_generator_cube_produces_solid_cube():
    voxels = generate_sculpture("cube", {"side": 2.0}, resolution=4)
    assert len(voxels) > 0
    size = 1.0 / 4
    # Todos dentro de [-1, 1]
    for v in voxels:
        assert abs(v["x"]) <= 1.0 + size
        assert abs(v["y"]) <= 1.0 + size
        assert abs(v["z"]) <= 1.0 + size


def test_generator_pyramid_decreasing_radius():
    voxels = generate_sculpture("pyramid", {"height": 2.0, "base": 2.0}, resolution=4)
    assert len(voxels) > 0
    # Los voxels más altos deben tener |x| menor
    ys = sorted({round(v["y"], 3) for v in voxels})
    assert len(ys) > 1
    bottom_y = ys[0]
    top_y = ys[-1]
    bottom_x = max(abs(v["x"]) for v in voxels if abs(round(v["y"], 3) - bottom_y) < 0.01)
    top_x = max(abs(v["x"]) for v in voxels if abs(round(v["y"], 3) - top_y) < 0.01)
    assert top_x < bottom_x


def test_generator_cross_three_arms():
    voxels = generate_sculpture("cross", {"arm": 1.0}, resolution=4)
    # Debe haber voxels en los 3 brazos (x, y, z)
    has_x = any(v["x"] != 0 and v["y"] == 0 and v["z"] == 0 for v in voxels)
    has_y = any(v["y"] != 0 and v["x"] == 0 and v["z"] == 0 for v in voxels)
    has_z = any(v["z"] != 0 and v["x"] == 0 and v["y"] == 0 for v in voxels)
    assert has_x and has_y and has_z


def test_generator_helix_increases_y():
    voxels = generate_sculpture("helix", {"height": 3.0, "radius": 1.0, "turns": 2.0}, resolution=4)
    assert len(voxels) > 0
    ys = [v["y"] for v in voxels]
    assert min(ys) == pytest.approx(0.0, abs=0.1)
    assert max(ys) <= 3.0 + 0.1


def test_generator_humanoid_bust_has_head_and_torso():
    voxels = generate_sculpture("humanoid_bust", {}, resolution=4)
    assert len(voxels) > 10
    # Debe haber voxels por encima de y=1.2 (cabeza) y por debajo (torso)
    has_head = any(v["y"] > 1.2 for v in voxels)
    has_torso = any(v["y"] < 1.0 for v in voxels)
    assert has_head and has_torso


def test_generator_invalid_name():
    with pytest.raises(ValueError, match="invalid generator"):
        generate_sculpture("dragon", {}, resolution=4)


# ---------------------------------------------------------------------------
# Validación
# ---------------------------------------------------------------------------

def test_validate_sculpture_resolution_invalid():
    with pytest.raises(ValueError, match="resolution"):
        validate_sculpture([], resolution=3)


def test_validate_sculpture_too_many():
    voxels = [{"x": i * 0.25, "y": 0, "z": 0} for i in range(MAX_SCULPTURE_VOXELS + 1)]
    with pytest.raises(ValueError, match="too many voxels"):
        validate_sculpture(voxels, resolution=4)


# ---------------------------------------------------------------------------
# ObjectManager.create con sculpture
# ---------------------------------------------------------------------------

def test_create_sculpture_with_explicit_voxels(manager):
    voxels = [
        {"x": 0.0, "y": 0.0, "z": 0.0, "color": 0xFF0000, "size": 0.25},
        {"x": 0.25, "y": 0.0, "z": 0.0, "color": 0xFF0000, "size": 0.25},
        {"x": -0.5, "y": 0.5, "z": 0.5, "color": 0x00FF00, "size": 0.25},
    ]
    obj = manager.create(
        kind="sculpture", position=[10, 30, 10],
        shape={"type": "sculpture_voxels", "resolution": 4, "voxels": [(v["x"], v["y"], v["z"]) for v in voxels]},
        anchored=True,
    )
    assert obj.kind == "sculpture"
    assert obj.shape["type"] == "sculpture_voxels"
    assert obj.shape["resolution"] == 4
    assert len(obj.shape["voxels"]) == 3
    assert obj.is_static()  # anchored


def test_sculpture_aabb_envelope(manager):
    voxels = [(0.0, 0.0, 0.0), (0.5, 0.5, 0.5), (-0.25, 0.0, 0.0)]
    obj = manager.create(
        kind="sculpture", position=[10, 30, 10],
        shape={"type": "sculpture_voxels", "resolution": 4, "voxels": voxels},
    )
    mn, mx = obj.aabb()
    # min local = (-0.25, 0, 0); max local = (0.5+0.125, 0.5+0.125, 0.5+0.125)
    assert mn == pytest.approx((9.75, 30.0, 10.0))
    assert mx == pytest.approx((10.625, 30.625, 10.625))


# ---------------------------------------------------------------------------
# get_state: voxels completos la primera vez, omitir después
# ---------------------------------------------------------------------------

def test_get_state_sends_voxels_first_time(manager):
    """El snapshot incremental (full=False) siempre omite voxels (null).
    full=True siempre los incluye. El cliente los pide vía get_object."""
    voxels = [(0.0, 0.0, 0.0), (0.25, 0.0, 0.0)]
    obj = manager.create(
        kind="sculpture", position=[0, 30, 0],
        shape={"type": "sculpture_voxels", "resolution": 4, "voxels": voxels},
    )
    state1 = manager.get_state(full=False)
    s1 = state1[0]["shape"]
    assert s1["voxels"] is None  # incremental: siempre null
    assert s1["voxel_count"] == 2
    state2 = manager.get_state(full=False)
    s2 = state2[0]["shape"]
    assert s2["voxels"] is None  # segunda vez: también null
    assert s2["voxel_count"] == 2
    # full=True sí los incluye
    state_full = manager.get_state(full=True)
    assert state_full[0]["shape"]["voxels"] is not None
    assert len(state_full[0]["shape"]["voxels"]) == 2


def test_get_state_full_always_sends_voxels(manager):
    voxels = [(0.0, 0.0, 0.0)]
    manager.create(
        kind="sculpture", position=[0, 30, 0],
        shape={"type": "sculpture_voxels", "resolution": 4, "voxels": voxels},
    )
    # Dos llamadas full=True → siempre envía
    s1 = manager.get_state(full=True)[0]["shape"]
    s2 = manager.get_state(full=True)[0]["shape"]
    assert s1["voxels"] is not None
    assert s2["voxels"] is not None


# ---------------------------------------------------------------------------
# Handler MCP create_sculpture
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_mcp_create_sculpture_with_generator(mcp):
    r = await mcp.tool_create_sculpture({
        "position": [10, 40, 10],
        "resolution": 4,
        "generator": "sphere",
        "params": {"radius": 1.0, "color": 0xFF8800},
        "anchored": True,
    })
    assert r["success"] is True
    assert r["voxel_count"] > 10
    obj = mcp.game_loop.object_manager.get(r["object_id"])
    assert obj.kind == "sculpture"
    assert obj.shape["type"] == "sculpture_voxels"
    assert obj.is_static()


@pytest.mark.asyncio
async def test_mcp_create_sculpture_with_explicit_voxels(mcp):
    r = await mcp.tool_create_sculpture({
        "position": [0, 40, 0],
        "resolution": 4,
        "voxels": [
            {"x": 0, "y": 0, "z": 0, "color": 16711680, "size": 0.25},
            {"x": 0.25, "y": 0, "z": 0, "color": 16711680, "size": 0.25},
        ],
        "anchored": False,
        "mass": 1.0,
    })
    assert r["success"] is True
    assert r["voxel_count"] == 2
    obj = mcp.game_loop.object_manager.get(r["object_id"])
    assert not obj.is_static()


@pytest.mark.asyncio
async def test_mcp_create_sculpture_invalid_generator(mcp):
    with pytest.raises(McpError, match="invalid generator"):
        await mcp.tool_create_sculpture({
            "position": [0, 40, 0], "generator": "dragon", "params": {},
        })


@pytest.mark.asyncio
async def test_mcp_create_sculpture_too_many_voxels(mcp):
    voxels = [{"x": i * 0.25, "y": 0, "z": 0, "color": 0, "size": 0.25}
              for i in range(MAX_SCULPTURE_VOXELS + 1)]
    with pytest.raises(McpError, match="too many voxels"):
        await mcp.tool_create_sculpture({
            "position": [0, 40, 0], "resolution": 4, "voxels": voxels,
        })


@pytest.mark.asyncio
async def test_mcp_create_sculpture_in_definitions():
    from pathlib import Path
    import json
    p = Path(__file__).resolve().parent.parent.parent.parent / "shared" / "tools" / "definitions.json"
    with open(p) as f:
        defs = json.load(f)
    assert "create_sculpture" in defs["tools"]
    assert defs["tools"]["create_sculpture"]["category"] == "objects"


@pytest.mark.asyncio
async def test_mcp_create_sculpture_in_tools_list():
    m = McpServer(GameLoop(World(flat_mode=1)))
    tools = m.list_tools()
    names = {t["name"] for t in tools}
    assert "create_sculpture" in names
    assert "damage_object" in names


# ---------------------------------------------------------------------------
# Escultura anclada no cae (integración con física)
# ---------------------------------------------------------------------------

def test_sculpture_anchored_does_not_fall(manager):
    from server.engine.physics import PhysicsSystem
    p = PhysicsSystem(manager.world)
    voxels = [(0.0, 0.0, 0.0), (0.25, 0.0, 0.0)]
    obj = manager.create(
        kind="sculpture", position=[10, 30, 10], mass=0.0, anchored=True,
        shape={"type": "sculpture_voxels", "resolution": 4, "voxels": voxels},
    )
    for _ in range(20):
        p.update_object(obj, dt=0.05)
    assert obj.position[1] == pytest.approx(30.0)