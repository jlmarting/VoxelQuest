"""Tests del subsistema de objetos móviles (propuesta 002).

Fase 1: modelo + manager + handlers MCP básicos (create/list/get/update/destroy)
+ expiración por tiempo. Las fases posteriores añaden tests de colisiones,
movimientos, destrucción y esculturas en sus propios ficheros.
"""

from __future__ import annotations

import pytest

from server.engine.game_loop import GameLoop
from server.engine.objects import ObjectManager, MobileObject, Motion, validate_sculpture
from server.engine.world import World
from server.mcp.server import McpServer, McpError


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def manager():
    return ObjectManager(World(flat_mode=1))


@pytest.fixture
def mcp():
    game = GameLoop(World(flat_mode=1))
    game.add_player(2, is_ai=True)
    return McpServer(game)


# ---------------------------------------------------------------------------
# Modelo / Manager
# ---------------------------------------------------------------------------

def test_create_box_defaults(manager):
    obj = manager.create(kind="box", position=[10.0, 40.0, 10.0])
    assert obj.id == 1
    assert obj.kind == "box"
    assert obj.position == (10.0, 40.0, 10.0)
    assert obj.mass == 1.0
    assert obj.shape == {"type": "box"}
    assert obj.alive is True
    assert obj.color == 0xFFFFFF


def test_create_sphere_shape_inferred(manager):
    obj = manager.create(kind="sphere", position=[0, 0, 0], scale=[2.0, 2.0, 2.0])
    assert obj.shape == {"type": "sphere", "radius": 1.0}
    # AABB envolvente = cubo de lado 2*radius
    mn, mx = obj.aabb()
    assert mn == (-1.0, -1.0, -1.0)
    assert mx == (1.0, 1.0, 1.0)


def test_create_projectile_small_scale(manager):
    obj = manager.create(kind="projectile", position=[0, 0, 0])
    assert obj.shape == {"type": "sphere", "radius": 0.2}
    assert obj.scale == (0.4, 0.4, 0.4)


def test_create_invalid_kind(manager):
    with pytest.raises(ValueError, match="invalid kind"):
        manager.create(kind="dragon", position=[0, 0, 0])


def test_create_max_objects_enforced():
    m = ObjectManager(World(flat_mode=1), max_objects=2)
    m.create(kind="box", position=[0, 0, 0])
    m.create(kind="box", position=[1, 0, 0])
    with pytest.raises(ValueError, match="max_objects"):
        m.create(kind="box", position=[2, 0, 0])


def test_create_mass_zero_is_static(manager):
    obj = manager.create(kind="box", position=[0, 0, 0], mass=0.0)
    assert obj.is_static() is True
    obj2 = manager.create(kind="box", position=[0, 0, 0], mass=1.0, anchored=True)
    assert obj2.is_static() is True


def test_get_list_filter(manager):
    a = manager.create(kind="box", position=[0, 0, 0], owner_id=2)
    b = manager.create(kind="projectile", position=[1, 0, 0], owner_id=3)
    assert manager.get(a.id) is a
    assert manager.get(999) is None
    assert manager.list() == [a, b]
    assert manager.list({"owner_id": 2}) == [a]
    assert manager.list({"kind": "projectile"}) == [b]


def test_update_patch(manager):
    obj = manager.create(kind="box", position=[0, 0, 0])
    manager.update(obj, {"color": 0xFF0000, "mass": 5.0})
    assert obj.color == 0xFF0000
    assert obj.mass == 5.0
    # id no se puede parchear
    manager.update(obj, {"id": 999})
    assert obj.id == 1


def test_destroy_removes(manager):
    obj = manager.create(kind="box", position=[0, 0, 0])
    manager.destroy(obj)
    assert obj.alive is False
    assert manager.list() == []


def test_kinetic_energy(manager):
    obj = manager.create(kind="box", position=[0, 0, 0], mass=2.0, velocity=[3, 0, 4.0])
    # KE = 0.5 * 2 * (9+0+16) = 25
    assert obj.kinetic_energy() == pytest.approx(25.0)
    assert obj.speed() == pytest.approx(5.0)


def test_aabb_box(manager):
    obj = manager.create(kind="box", position=[10, 20, 30], scale=[2, 4, 6])
    mn, mx = obj.aabb()
    assert mn == (9.0, 18.0, 27.0)
    assert mx == (11.0, 22.0, 33.0)


def test_aabb_sculpture_envelope(manager):
    voxels = [(0.0, 0.0, 0.0), (0.25, 0.5, 0.0), (-0.25, 0.0, 0.75)]
    obj = manager.create(kind="sculpture", position=[10, 20, 30],
                         shape={"type": "sculpture_voxels", "resolution": 4, "voxels": voxels})
    mn, mx = obj.aabb()
    # min local = (-0.25, 0, 0); max local = (0.25+0.125, 0.5+0.125, 0.75+0.125)
    assert mn == pytest.approx((9.75, 20.0, 30.0))
    assert mx == pytest.approx((10.375, 20.625, 30.875))


def test_motion_build_waypoints(manager):
    obj = manager.create(
        kind="box", position=[0, 0, 0],
        motion={"type": "waypoints", "points": [[0, 0, 0], [10, 0, 0]], "speed": 2.0, "loop": True},
    )
    assert obj.motion.type == "waypoints"
    assert obj.motion.points == [[0, 0, 0], [10, 0, 0]]
    assert obj.motion.speed == 2.0
    assert obj.motion.loop is True


def test_motion_build_invalid_type(manager):
    with pytest.raises(ValueError, match="invalid motion type"):
        manager.create(kind="box", position=[0, 0, 0], motion={"type": "teleport"})


def test_motion_build_orbit_invalid_axis(manager):
    with pytest.raises(ValueError, match="invalid orbit axis"):
        manager.create(kind="box", position=[0, 0, 0],
                        motion={"type": "orbit", "center": [0, 0, 0], "axis": "w"})


def test_to_dict_minimal(manager):
    obj = manager.create(kind="box", position=[1, 2, 3])
    d = obj.to_dict()
    assert d["id"] == 1
    assert d["kind"] == "box"
    assert d["position"] == [1, 2, 3]
    assert d["alive"] is True
    assert "expire_at" not in d
    assert "motion" not in d


def test_get_state_omits_sculpture_voxels(manager):
    """El snapshot incremental (full=False) omite los voxels de esculturas
    (voxels=null + voxel_count). El cliente los pide vía get_object.
    full=True los incluye completos."""
    voxels = [{"x": 0, "y": 0, "z": 0, "color": 0xFF0000, "size": 0.25}]
    obj = manager.create(kind="sculpture", position=[0, 0, 0],
                         shape={"type": "sculpture_voxels", "resolution": 4, "voxels": [(v["x"], v["y"], v["z"]) for v in voxels]})
    state = manager.get_state(full=False)
    assert state[0]["shape"]["voxels"] is None  # incremental: omitidos
    assert state[0]["shape"]["voxel_count"] == 1
    state_full = manager.get_state(full=True)
    assert state_full[0]["shape"]["voxels"] is not None  # full: completos
    assert len(state_full[0]["shape"]["voxels"]) == 1


# ---------------------------------------------------------------------------
# Expiración (tick)
# ---------------------------------------------------------------------------

def test_expire_at_destroys(manager):
    obj = manager.create(kind="box", position=[0, 0, 0], expire_at=0.5)
    events = manager.update_motions(dt=0.1, now=obj._spawn_time + 0.3)
    assert events == []
    assert manager.list() == [obj]
    events = manager.update_motions(dt=0.1, now=obj._spawn_time + 0.6)
    assert len(events) == 1
    assert events[0]["type"] == "object_destroyed"
    assert events[0]["cause"] == "expire"
    assert manager.list() == []


# ---------------------------------------------------------------------------
# Validación de esculturas (helper)
# ---------------------------------------------------------------------------

def test_validate_sculpture_ok():
    validate_sculpture([{"x": 0, "y": 0, "z": 0}], resolution=4)


def test_validate_sculpture_bad_resolution():
    with pytest.raises(ValueError, match="resolution"):
        validate_sculpture([], resolution=3)


def test_validate_sculpture_too_many():
    voxels = [{"x": i * 0.25, "y": 0, "z": 0} for i in range(30001)]
    with pytest.raises(ValueError, match="too many voxels"):
        validate_sculpture(voxels, resolution=4)


# ---------------------------------------------------------------------------
# Handlers MCP
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_mcp_create_object(mcp):
    result = await mcp.tool_create_object({
        "kind": "box", "position": [10, 40, 10], "color": 0xFF8800, "mass": 2.0,
    })
    assert result["success"] is True
    oid = result["object_id"]
    assert oid == 1
    assert result["object"]["color"] == 0xFF8800
    assert result["object"]["mass"] == 2.0


@pytest.mark.asyncio
async def test_mcp_create_object_invalid_kind(mcp):
    with pytest.raises(McpError, match="invalid kind"):
        await mcp.tool_create_object({"kind": "dragon", "position": [0, 0, 0]})


@pytest.mark.asyncio
async def test_mcp_list_objects_filter(mcp):
    await mcp.tool_create_object({"kind": "box", "position": [0, 0, 0], "owner_id": 2})
    await mcp.tool_create_object({"kind": "projectile", "position": [1, 0, 0], "owner_id": 3})
    r_all = await mcp.tool_list_objects({})
    assert len(r_all["objects"]) == 2
    r_filt = await mcp.tool_list_objects({"filter": {"kind": "projectile"}})
    assert len(r_filt["objects"]) == 1
    assert r_filt["objects"][0]["kind"] == "projectile"


@pytest.mark.asyncio
async def test_mcp_get_object(mcp):
    r = await mcp.tool_create_object({"kind": "box", "position": [5, 5, 5]})
    oid = r["object_id"]
    got = await mcp.tool_get_object({"object_id": oid})
    assert got["object"]["id"] == oid
    assert got["object"]["position"] == [5, 5, 5]
    with pytest.raises(McpError, match="not found"):
        await mcp.tool_get_object({"object_id": 999})


@pytest.mark.asyncio
async def test_mcp_update_object(mcp):
    r = await mcp.tool_create_object({"kind": "box", "position": [0, 0, 0], "mass": 1.0})
    oid = r["object_id"]
    upd = await mcp.tool_update_object({"object_id": oid, "patch": {"mass": 5.0, "color": 0xFF}})
    assert upd["object"]["mass"] == 5.0
    assert upd["object"]["color"] == 0xFF


@pytest.mark.asyncio
async def test_mcp_destroy_object_emits_event(mcp):
    r = await mcp.tool_create_object({"kind": "box", "position": [0, 0, 0]})
    oid = r["object_id"]
    res = await mcp.tool_destroy_object({"object_id": oid, "cause": "manual"})
    assert res["success"] is True
    # El evento debe estar pendiente para el próximo state_update
    ev = mcp.game_loop._pending_events
    assert any(e["type"] == "object_destroyed" and e["id"] == oid for e in ev)


@pytest.mark.asyncio
async def test_mcp_destroy_object_not_found(mcp):
    with pytest.raises(McpError, match="not found"):
        await mcp.tool_destroy_object({"object_id": 999})


@pytest.mark.asyncio
async def test_mcp_definitions_list_includes_objects():
    """Las tools de objects aparecen en tools/list filtradas por python."""
    mcp = McpServer(GameLoop(World(flat_mode=1)))
    tools = mcp.list_tools()
    names = {t["name"] for t in tools}
    for expected in ("create_object", "update_object", "list_objects", "get_object", "destroy_object"):
        assert expected in names, f"missing {expected} in tools/list"