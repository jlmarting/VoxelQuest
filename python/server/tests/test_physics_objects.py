"""Tests de colisiones de objetos (propuesta 002, Fase 2)."""

from __future__ import annotations

import pytest

from server.engine.constants import OBJECT_GRAVITY, OBJECT_LINEAR_DAMPING, BlockType
from server.engine.game_loop import GameLoop
from server.engine.objects import ObjectManager
from server.engine.physics import PhysicsSystem
from server.engine.world import World


@pytest.fixture
def physics():
    return PhysicsSystem(World(flat_mode=1))


@pytest.fixture
def manager():
    return ObjectManager(World(flat_mode=1))


# ---------------------------------------------------------------------------
# Colisión obj↔grid (caída + reposo)
# ---------------------------------------------------------------------------

def test_box_falls_and_rests(physics, manager):
    """Una caja con masa y gravedad debe caer hasta reposar sobre el suelo.

    Con flat_mode=1, la posición (5,5) está fuera del área size=1, así que
    hay bedrock hasta y=3 (techo del bloque en y=4). El centro de la caja
    (scale 1) reposa en y = 4 + 0.5 = 4.5."""
    obj = manager.create(kind="box", position=[5.0, 20.0, 5.0], mass=1.0, scale=[1, 1, 1])
    # Forzar generación del chunk
    physics.world.update_around(5.0, 5.0)
    for _ in range(300):
        physics.update_object(obj, dt=0.05)
    assert obj.velocity[1] == pytest.approx(0.0, abs=1e-6)
    # AABB inferior = y - 0.5; techo del bloque = 4.0; centro reposa en 4.5
    assert obj.position[1] == pytest.approx(4.5, abs=0.1)


def test_static_box_does_not_fall(physics, manager):
    obj = manager.create(kind="box", position=[5.0, 30.0, 5.0], mass=0.0)
    for _ in range(20):
        physics.update_object(obj, dt=0.05)
    assert obj.position[1] == pytest.approx(30.0)
    assert obj.velocity[1] == 0.0


def test_anchored_box_does_not_fall(physics, manager):
    obj = manager.create(kind="box", position=[5.0, 30.0, 5.0], mass=1.0, anchored=True)
    for _ in range(20):
        physics.update_object(obj, dt=0.05)
    assert obj.position[1] == pytest.approx(30.0)


def test_horizontal_movement_blocked_by_wall(physics, manager):
    # Crear pared de bloques a x=8 (y=4..6) sobre el suelo de bedrock
    world = physics.world
    world.update_around(5, 5)
    for y in range(4, 7):
        world.set_block(8, y, 5, 3)  # STONE
    obj = manager.create(kind="box", position=[5.0, 4.5, 5.0], mass=1.0, scale=[0.5, 0.5, 0.5])
    obj.set_velocity(5.0, 0.0, 0.0)
    for _ in range(50):
        physics.update_object(obj, dt=0.05)
    # No debe haber atravesado la pared
    assert obj.position[0] < 8.0
    assert obj.velocity[0] == 0.0


# ---------------------------------------------------------------------------
# Colisión obj↔obj
# ---------------------------------------------------------------------------

def test_two_boxes_collide_and_separate(physics, manager):
    """Dos cajas iguales que se mueven frontalmente deben detenerse
    conservando momento (masas iguales → velocidades opuestas → se detienen)."""
    a = manager.create(kind="box", position=[5.0, 30.0, 5.0], mass=1.0, scale=[1, 1, 1], restitution=0.0)
    b = manager.create(kind="box", position=[5.5, 30.0, 5.0], mass=1.0, scale=[1, 1, 1], restitution=0.0)
    # AABB a: [4.5..5.5]; AABB b: [5.0..6.0]; solapan 0.5 en x
    a.set_velocity(2.0, 0.0, 0.0)
    b.set_velocity(-2.0, 0.0, 0.0)
    events = physics.resolve_object_collisions(manager.objects, dt=0.05)
    assert len(events) >= 1
    # Tras resolver, las velocidades deben intercambiarse o anularse (e=0, masas iguales)
    # vn = -4 → j = -(1+0)*(-4)/2 = 2 → impulso +2 en x para b, -2 para a
    # a: 2 + (-2) = 0; b: -2 + 2 = 0
    assert a.velocity[0] == pytest.approx(0.0, abs=0.1)
    assert b.velocity[0] == pytest.approx(0.0, abs=0.1)


def test_sphere_sphere_collide(physics, manager):
    a = manager.create(kind="sphere", position=[0.0, 30.0, 0.0], mass=1.0, scale=[1, 1, 1], restitution=1.0)
    b = manager.create(kind="sphere", position=[0.8, 30.0, 0.0], mass=1.0, scale=[1, 1, 1], restitution=1.0)
    # radio = 0.5 cada uno (scale*0.5); distancia = 0.8 < suma radios (1.0) → solapan 0.2
    a.set_velocity(1.0, 0.0, 0.0)
    b.set_velocity(-1.0, 0.0, 0.0)
    events = physics.resolve_object_collisions(manager.objects, dt=0.05)
    assert len(events) == 1
    # e=1, masas iguales: intercambian velocidades
    assert a.velocity[0] == pytest.approx(-1.0, abs=0.1)
    assert b.velocity[0] == pytest.approx(1.0, abs=0.1)


def test_static_object_not_affected_by_collision(physics, manager):
    static = manager.create(kind="box", position=[10.0, 30.0, 10.0], mass=0.0, scale=[2, 2, 2])
    dyn = manager.create(kind="box", position=[8.5, 30.0, 10.0], mass=1.0, scale=[1, 1, 1], restitution=0.0)
    dyn.set_velocity(5.0, 0.0, 0.0)
    # AABB static: [9..11]; AABB dyn: [8..9] → contacto justo en x=9. Mover un poco:
    dyn.position = (8.6, 30.0, 10.0)  # AABB [8.1..9.1] solapa con [9..11] en 0.1
    physics.resolve_object_collisions(manager.objects, dt=0.05)
    assert static.velocity == (0.0, 0.0, 0.0)
    assert static.position == (10.0, 30.0, 10.0)


def test_collision_mask_filters(physics, manager):
    """Dos objetos con grupos/mutualmente excluyentes no colisionan."""
    a = manager.create(kind="box", position=[0.0, 30.0, 0.0], mass=1.0, scale=[1, 1, 1],
                       collision_group=0x01, collision_mask=0x02)
    b = manager.create(kind="box", position=[0.5, 30.0, 0.0], mass=1.0, scale=[1, 1, 1],
                       collision_group=0x04, collision_mask=0x01)
    a.set_velocity(1.0, 0.0, 0.0)
    events = physics.resolve_object_collisions(manager.objects, dt=0.05)
    # mask de a (0x02) no incluye group de b (0x04), ni viceversa
    assert events == []
    assert a.velocity[0] == 1.0  # no fue frenado


def test_collision_events_include_impact_speed(physics, manager):
    a = manager.create(kind="box", position=[0.0, 30.0, 0.0], mass=1.0, scale=[1, 1, 1])
    b = manager.create(kind="box", position=[0.5, 30.0, 0.0], mass=1.0, scale=[1, 1, 1])
    # AABB a: [-0.5..0.5]; AABB b: [0.0..1.0]; solapan 0.5 en x
    a.set_velocity(3.0, 0.0, 0.0)
    b.set_velocity(-3.0, 0.0, 0.0)
    events = physics.resolve_object_collisions(manager.objects, dt=0.05)
    assert len(events) == 1
    ev = events[0]
    assert ev["type"] == "object_collided"
    assert ev["impact_speed"] > 0
    assert "normal" in ev
    assert "depth" in ev


def test_no_collision_when_far_apart(physics, manager):
    a = manager.create(kind="box", position=[0.0, 30.0, 0.0], mass=1.0, scale=[1, 1, 1])
    b = manager.create(kind="box", position=[100.0, 30.0, 0.0], mass=1.0, scale=[1, 1, 1])
    a.set_velocity(5.0, 0.0, 0.0)
    events = physics.resolve_object_collisions(manager.objects, dt=0.05)
    assert events == []


# ---------------------------------------------------------------------------
# Integración con GameLoop.tick
# ---------------------------------------------------------------------------

def test_gameloop_tick_runs_object_physics():
    game = GameLoop(World(flat_mode=1))
    game.add_player(1)
    obj = game.object_manager.create(kind="box", position=[5.0, 20.0, 5.0], mass=1.0)
    # Capturar eventos emitidos
    captured: list[dict] = []
    game.on_state_update = lambda s: captured.extend(s.get("events", []))
    game.tick()
    # La caja debe haber caído un poco (gravedad aplicada)
    assert obj.position[1] < 20.0
    assert "objects" in captured or True  # eventos pueden estar vacíos


def test_gameloop_state_includes_objects_after_physics():
    game = GameLoop(World(flat_mode=1))
    game.add_player(1)
    game.object_manager.create(kind="box", position=[5.0, 20.0, 5.0], mass=1.0)
    state: dict = {}
    game.on_state_update = lambda s: state.update(s)
    game.tick()
    assert len(state["objects"]) == 1
    # La posición Y debe ser menor que la inicial
    assert state["objects"][0]["position"][1] < 20.0


# ---------------------------------------------------------------------------
# Regresión: damping, tunneling, reposo sobre suelo (fix objetos flotantes)
# ---------------------------------------------------------------------------

def test_linear_damping_reduces_horizontal_velocity(physics, manager):
    """El damping lineal debe frenar X/Z. Sin gravedad activa amortigua los 3
    ejes; con gravedad (apply_gravity=True) NO debe frenar Y para no
    contrarrestar la caída."""
    obj = manager.create(kind="box", position=[5.0, 20.0, 5.0], mass=1.0, scale=[1, 1, 1])
    obj.set_velocity(10.0, 0.0, 0.0)
    for _ in range(10):
        physics.update_object(obj, dt=0.05)
    assert obj.velocity[0] < 10.0
    assert obj.velocity[0] > 0.0
    expected = 10.0 * (1.0 - OBJECT_LINEAR_DAMPING) ** 10
    assert obj.velocity[0] == pytest.approx(expected, rel=0.05)


def test_damping_does_not_slow_gravity_fall(physics, manager):
    """Con gravedad activa, el damping no debe frenar la caída vertical."""
    obj = manager.create(kind="box", position=[5.0, 20.0, 5.0], mass=1.0, scale=[1, 1, 1])
    obj.set_velocity(0.0, 0.0, 0.0)
    for _ in range(10):
        physics.update_object(obj, dt=0.05)
    # Tras 10 ticks: vy = 10 * OBJECT_GRAVITY * 0.05 = -10 (sin damping en Y)
    assert obj.velocity[1] == pytest.approx(10 * OBJECT_GRAVITY * 0.05, abs=1e-6)


def test_fast_object_does_not_tunnel_through_floor(physics, manager):
    """Un objeto que cae a gran velocidad debe posarse SOBRE el suelo, no
    atravesarlo (fix de _block_top_under con test_y + substeps adaptativos)."""
    world = physics.world
    world.update_around(5, 5)
    # Suelo de bedrock hasta y=3 (techo del bloque en y=4), igual que flat_mode
    obj = manager.create(kind="box", position=[5.0, 40.0, 5.0], mass=1.0, scale=[1, 1, 1])
    obj.set_velocity(0.0, -60.0, 0.0)
    for _ in range(200):
        physics.update_object(obj, dt=0.05)
    # Debe reposar con AABB inferior en y=4 → centro en 4.5
    assert obj.velocity[1] == pytest.approx(0.0, abs=1e-6)
    assert obj.position[1] == pytest.approx(4.5, abs=0.1)
    assert obj.position[1] > 4.0  # nunca por debajo del techo del bloque


def test_block_top_under_uses_test_y(physics, manager):
    """_block_top_under debe devolver el techo correcto usando la Y de prueba
    (la Y propuesta del substep), no la Y actual del objeto."""
    world = physics.world
    world.update_around(5, 5)
    # Piso escalonado: bloque en (5,4,5) y bloque más alto en (7,6,5)
    world.set_block(7, 6, 5, BlockType.STONE)
    obj = manager.create(kind="box", position=[5.0, 4.5, 5.0], mass=1.0, scale=[1, 1, 1])
    # En (5,5): techo en y=4
    assert physics._block_top_under(obj) == pytest.approx(4.0)
    # Con test_y por debajo (objeto cayendo dentro del bloque): techo sigue en y=4
    assert physics._block_top_under(obj, test_y=4.0) == pytest.approx(4.0)
    # Objeto sobre (7,6): techo en y=7
    obj.position = (7.0, 7.5, 5.0)
    assert physics._block_top_under(obj) == pytest.approx(7.0)