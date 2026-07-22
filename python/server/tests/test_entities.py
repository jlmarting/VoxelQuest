"""Tests de entidades, física y game loop."""

import pytest

from server.engine.constants import BlockType
from server.engine.entities import Enemy, EnemyManager, Entity, Player, Vec3
from server.engine.game_loop import GameLoop
from server.engine.physics import PhysicsSystem
from server.engine.world import World


class TestEntity:
    def test_take_damage_reduces_health(self):
        e = Entity(id=1, health=20)
        assert not e.take_damage(5)
        assert e.health == 15

    def test_take_damage_with_knockback(self):
        e = Entity(id=1, position=Vec3(0, 0, 0), health=20)
        e.take_damage(5, attacker_position=Vec3(10, 0, 0))
        assert e.velocity.x < 0
        assert e.velocity.y == 6

    def test_forward_direction(self):
        p = Player(id=1)
        p.rotation.x = 0
        p.rotation.y = 0
        fwd = p.get_forward_direction()
        assert fwd.x == pytest.approx(0, abs=1e-6)
        assert fwd.z == pytest.approx(-1, abs=1e-6)


class TestPhysics:
    def test_gravity_pulls_down(self):
        world = World(seed=42, flat_mode=16)
        physics = PhysicsSystem(world)
        player = Player(id=1, position=Vec3(0.5, 10.0, 0.5))
        world.update_around(0.5, 0.5)

        physics.update_entity(player, 0.05)
        assert player.velocity.y < 0

    def test_player_lands_on_ground(self):
        world = World(seed=42, flat_mode=16)
        physics = PhysicsSystem(world)
        player = Player(id=1, position=Vec3(0.5, 5.0, 0.5))
        world.update_around(0.5, 0.5)

        for _ in range(60):
            physics.update_entity(player, 0.05)

        assert player.on_ground is True
        assert player.position.y == pytest.approx(2.0, abs=1.0)

    def test_input_moves_player(self):
        world = World(seed=42, flat_mode=16)
        physics = PhysicsSystem(world)
        player = Player(id=1, position=Vec3(0.5, 5.0, 0.5))
        player.rotation.y = 0
        world.update_around(0.5, 0.5)

        player.input_move = Vec3(0, 0, -1)  # adelante
        physics.apply_input(player, 0.05)
        assert player.velocity.z < 0

    def test_block_collapse(self):
        world = World(seed=42, flat_mode=16)
        world.set_block(0, 3, 0, BlockType.DIRT)
        world.set_block(0, 4, 0, BlockType.DIRT)
        physics = PhysicsSystem(world)

        physics.on_block_broken(0, 2, 0)
        assert world.get_block(0, 3, 0) == BlockType.AIR
        assert world.get_block(0, 4, 0) == BlockType.AIR
        assert len(physics.falling_blocks) == 2


class TestGameLoop:
    def test_add_player(self):
        world = World(seed=42, flat_mode=16)
        loop = GameLoop(world)
        player = loop.add_player(1)
        assert player.id == 1
        assert player in loop.players.values()

    def test_build_state(self):
        world = World(seed=42, flat_mode=16)
        loop = GameLoop(world)
        loop.add_player(1)
        state = loop._build_state()
        assert state["type"] == "state_update"
        assert "players" in state
        assert "1" in state["players"]


class TestEnemy:
    def test_enemy_chases_player(self):
        world = World(seed=42, flat_mode=16)
        enemy = Enemy("ZOMBIE", Vec3(0, 2, 0), world)
        player = Player(id=1, position=Vec3(10, 2, 0))
        enemy.update(0.05, [player], now=0)
        assert enemy.state == "chase"
        assert enemy.velocity.x > 0

    def test_enemy_attacks_close_player(self):
        world = World(seed=42, flat_mode=16)
        enemy = Enemy("ZOMBIE", Vec3(0, 2, 0), world)
        player = Player(id=1, position=Vec3(0.5, 2, 0), health=20)
        enemy.update(0.05, [player], now=1.0)
        assert player.health < 20


class TestEnemyManager:
    def test_spawn_at_night(self):
        world = World(seed=42, flat_mode=16)
        manager = EnemyManager(world, max_enemies=1)
        player = Player(id=1, position=Vec3(0, 2, 0))
        events = manager.update(0.05, [player], now=10.0, is_night=True)
        assert len(manager.enemies) > 0
        assert all(e["type"] == "entity_died" for e in events if events)

    def test_no_spawn_during_day(self):
        world = World(seed=42, flat_mode=16)
        manager = EnemyManager(world, max_enemies=1)
        player = Player(id=1, position=Vec3(0, 2, 0))
        manager.update(0.05, [player], now=10.0, is_night=False)
        assert len(manager.enemies) == 0
