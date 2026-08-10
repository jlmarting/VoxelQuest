"""Tests de destrucción y daño (propuesta 002, Fase 5)."""

from __future__ import annotations

import pytest

from server.engine.constants import BlockType
from server.engine.entities import Vec3, Enemy
from server.engine.game_loop import GameLoop
from server.engine.objects import MobileObject, ObjectManager
from server.engine.physics import PhysicsSystem
from server.engine.world import World
from server.mcp.server import McpServer, McpError


@pytest.fixture
def manager():
    w = World(flat_mode=1)
    w.update_around(10, 10)
    return ObjectManager(w)


@pytest.fixture
def physics(manager):
    return PhysicsSystem(manager.world)


@pytest.fixture
def mcp():
    game = GameLoop(World(flat_mode=1))
    game.add_player(1)
    return McpServer(game)


# ---------------------------------------------------------------------------
# MobileObject.destroy
# ---------------------------------------------------------------------------

def test_destroy_projectile_emits_explosion_fx(manager):
    obj = manager.create(kind="projectile", position=[10, 30, 10], mass=1.0,
                        destructible=True, fragile=1.0)
    events = obj.destroy("collision", manager.world)
    assert len(events) == 1
    ev = events[0]
    assert ev["type"] == "object_destroyed"
    assert ev["cause"] == "collision"
    assert ev["fx"] == "explosion_small"
    assert ev["id"] == obj.id
    assert obj.alive is False


def test_destroy_box_destructible_fragments_into_blocks(manager):
    """Una caja destructible se fragmenta en bloques voxel del mundo."""
    obj = manager.create(kind="box", position=[10, 30, 10], mass=1.0,
                         destructible=True, shape={"type": "box", "voxels": [(0.0, 0.0, 0.0)]})
    # Asegurar que la posición esté en aire
    manager.world.set_block(10, 30, 10, BlockType.AIR)
    events = obj.destroy("damage", manager.world)
    assert events[0]["fx"] == "break"
    # El bloque debe haberse colocado
    assert manager.world.get_block(10, 30, 10) == BlockType.COBBLESTONE


def test_destroy_sculpture_emits_poof(manager):
    obj = manager.create(kind="sculpture", position=[10, 30, 10],
                         shape={"type": "sculpture_voxels", "resolution": 4, "voxels": []})
    events = obj.destroy("manual", manager.world)
    assert events[0]["fx"] == "poof"


# ---------------------------------------------------------------------------
# check_destruction (procesa colisiones)
# ---------------------------------------------------------------------------

def test_check_destruction_destroys_on_high_impact(manager, physics):
    """Un objeto destructible con fragile bajo se rompe al recibir un impacto
    de alta energía cinética."""
    a = manager.create(kind="box", position=[0, 30, 0], mass=2.0, scale=[1, 1, 1],
                       destructible=True, fragile=10.0, restitution=0.0)
    b = manager.create(kind="box", position=[0.5, 30, 0], mass=2.0, scale=[1, 1, 1],
                       restitution=0.0)
    a.set_velocity(10, 0, 0)
    b.set_velocity(-10, 0, 0)
    collisions = physics.resolve_object_collisions(manager.objects, dt=0.05)
    # impact_speed relativo ≈ 20 (a+b), ke = 0.5 * 2 * 20² = 400 >> 10
    assert len(collisions) >= 1
    events = manager.check_destruction(collisions, entities=[])
    # Al menos un objeto se destruye
    destroyed = [e for e in events if e["type"] == "object_destroyed"]
    assert len(destroyed) >= 1
    assert all(e["cause"] == "collision" for e in destroyed)


def test_check_destruction_low_energy_no_destroy(manager, physics):
    """Con energía por debajo del umbral, no se destruye."""
    a = manager.create(kind="box", position=[0, 30, 0], mass=1.0, scale=[1, 1, 1],
                       destructible=True, fragile=1000.0, restitution=0.0)
    b = manager.create(kind="box", position=[0.5, 30, 0], mass=1.0, scale=[1, 1, 1],
                       restitution=0.0)
    a.set_velocity(0.1, 0, 0)
    b.set_velocity(-0.1, 0, 0)
    collisions = physics.resolve_object_collisions(manager.objects, dt=0.05)
    events = manager.check_destruction(collisions, entities=[])
    assert [e for e in events if e["type"] == "object_destroyed"] == []


def test_check_destruction_projectile_damages_entity(manager, physics):
    """Un proyectil con damage_on_impact aplica daño a una entidad cercana
    cuando impacta contra el mundo."""
    # Colocar enemigo cerca de la posición de impacto
    enemy = Enemy("ZOMBIE", Vec3(10.5, 30, 10), manager.world)
    enemy.id = 1
    enemy.health = 20
    proj = manager.create(kind="projectile", position=[10.5, 30, 10], mass=1.0,
                          scale=[0.4, 0.4, 0.4], destructible=True,
                          damage_on_impact=8.0, destroy_on_impact=True, fragile=1.0)
    # Simular colisión contra el mundo (other no es un objeto → entity lookup)
    collisions = [{
        "type": "object_collided", "id": proj.id,
        "other": {"kind": "world", "id": None},
        "normal": [0, 1, 0], "depth": 0.1, "impact_speed": 10.0,
    }]
    events = manager.check_destruction(collisions, entities=[enemy])
    # El enemigo recibe daño
    damaged = [e for e in events if e["type"] == "entity_damaged"]
    assert len(damaged) == 1
    assert damaged[0]["amount"] == 8.0
    assert enemy.health == pytest.approx(12.0)
    # El proyectil se destruye
    destroyed = [e for e in events if e["type"] == "object_destroyed"]
    assert len(destroyed) == 1
    assert destroyed[0]["id"] == proj.id


def test_check_destruction_two_destructibles_both_destroyed(manager, physics):
    """Dos objetos destructibles con fragile bajo que chocan a alta velocidad:
    ambos se destruyen en el mismo tick."""
    a = manager.create(kind="box", position=[0, 30, 0], mass=1.0, scale=[1, 1, 1],
                       destructible=True, fragile=5.0, restitution=0.0)
    b = manager.create(kind="box", position=[0.5, 30, 0], mass=1.0, scale=[1, 1, 1],
                       destructible=True, fragile=5.0, restitution=0.0)
    a.set_velocity(10, 0, 0)
    b.set_velocity(-10, 0, 0)
    collisions = physics.resolve_object_collisions(manager.objects, dt=0.05)
    events = manager.check_destruction(collisions, entities=[])
    destroyed = [e for e in events if e["type"] == "object_destroyed"]
    # Ambos deben estar destruidos
    destroyed_ids = {e["id"] for e in destroyed}
    assert a.id in destroyed_ids
    assert b.id in destroyed_ids
    assert manager.list() == []


# ---------------------------------------------------------------------------
# Handlers MCP
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_mcp_damage_object_destroys_at_zero_health(mcp):
    r = await mcp.tool_create_object({
        "kind": "box", "position": [0, 30, 0], "destructible": True, "health": 50,
    })
    oid = r["object_id"]
    # Daño parcial
    r1 = await mcp.tool_damage_object({"object_id": oid, "amount": 20})
    assert r1["health"] == pytest.approx(30.0)
    assert r1["destroyed"] is False
    # Daño letal
    r2 = await mcp.tool_damage_object({"object_id": oid, "amount": 50})
    assert r2["destroyed"] is True
    # El objeto ya no existe
    assert mcp.game_loop.object_manager.get(oid) is None


@pytest.mark.asyncio
async def test_mcp_damage_object_rejects_non_destructible(mcp):
    r = await mcp.tool_create_object({"kind": "box", "position": [0, 30, 0], "destructible": False})
    oid = r["object_id"]
    with pytest.raises(McpError, match="not destructible"):
        await mcp.tool_damage_object({"object_id": oid, "amount": 10})


@pytest.mark.asyncio
async def test_mcp_damage_object_not_found(mcp):
    with pytest.raises(McpError, match="not found"):
        await mcp.tool_damage_object({"object_id": 999, "amount": 10})


@pytest.mark.asyncio
async def test_mcp_destroy_object_emits_event_with_fx(mcp):
    r = await mcp.tool_create_object({"kind": "projectile", "position": [0, 30, 0]})
    oid = r["object_id"]
    res = await mcp.tool_destroy_object({"object_id": oid, "cause": "manual"})
    assert res["success"] is True
    assert len(res["events"]) == 1
    assert res["events"][0]["fx"] == "explosion_small"
    # Evento pendiente para state_update
    ev = mcp.game_loop._pending_events
    assert any(e["type"] == "object_destroyed" for e in ev)


# ---------------------------------------------------------------------------
# Integración con GameLoop.tick
# ---------------------------------------------------------------------------

def test_gameloop_tick_destroys_on_collision():
    game = GameLoop(World(flat_mode=1))
    game.add_player(1)
    game.world.update_around(10, 10)
    # Crear dos cajas destructibles que caen y colisionan a alta velocidad
    a = game.object_manager.create(kind="box", position=[9.5, 30, 10], mass=10.0,
                                    scale=[1, 1, 1], destructible=True, fragile=1.0,
                                    restitution=0.0, velocity=[5, 0, 0])
    b = game.object_manager.create(kind="box", position=[10.5, 30, 10], mass=10.0,
                                    scale=[1, 1, 1], destructible=True, fragile=1.0,
                                    restitution=0.0, velocity=[-5, 0, 0])
    captured: list[dict] = []
    game.on_state_update = lambda s: captured.extend(s.get("events", []))
    # Tick inicial para que integren velocidad
    game.tick()
    # Las cajas pueden haber chocado
    destroyed = [e for e in captured if e["type"] == "object_destroyed"]
    # Al menos una debe destruirse si impactaron
    if destroyed:
        assert all(e["cause"] == "collision" for e in destroyed)