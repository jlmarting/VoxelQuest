"""Entidades del juego: jugadores y enemigos."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from server.engine.constants import (
    BlockType,
    PLAYER_HEIGHT,
    PLAYER_WIDTH,
    PLAYER_MAX_HEALTH,
    PLAYER_SPEED,
    PLAYER_JUMP_FORCE,
    GRAVITY,
)

if TYPE_CHECKING:
    from server.engine.world import World


@dataclass
class Vec3:
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0

    def clone(self) -> Vec3:
        return Vec3(self.x, self.y, self.z)

    def to_dict(self) -> dict:
        return {"x": self.x, "y": self.y, "z": self.z}


@dataclass
class Rotation:
    x: float = 0.0  # pitch
    y: float = 0.0  # yaw

    def to_dict(self) -> dict:
        return {"x": self.x, "y": self.y}


@dataclass
class Entity:
    """Base para cualquier entidad con posición, velocidad y vida."""

    id: int
    position: Vec3 = field(default_factory=Vec3)
    velocity: Vec3 = field(default_factory=Vec3)
    rotation: Rotation = field(default_factory=Rotation)
    health: float = 20.0
    max_health: float = 20.0
    on_ground: bool = False
    is_flying: bool = False
    height: float = PLAYER_HEIGHT
    width: float = PLAYER_WIDTH  # ancho total
    speed: float = PLAYER_SPEED

    def is_alive(self) -> bool:
        return self.health > 0

    def take_damage(self, amount: float, attacker_position: Vec3 | None = None) -> bool:
        self.health -= amount
        if attacker_position:
            dx = self.position.x - attacker_position.x
            dz = self.position.z - attacker_position.z
            dist = math.hypot(dx, dz)
            if dist > 0.001:
                self.velocity.x = (dx / dist) * 8
                self.velocity.z = (dz / dist) * 8
                self.velocity.y = 6
        return not self.is_alive()

    def get_forward_direction(self) -> Vec3:
        """Vector hacia donde mira la entidad (sin pitch)."""
        return Vec3(
            x=-math.sin(self.rotation.y),
            y=0.0,
            z=-math.cos(self.rotation.y),
        )

    def get_eye_position(self) -> Vec3:
        return Vec3(self.position.x, self.position.y + 1.6, self.position.z)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "x": self.position.x,
            "y": self.position.y,
            "z": self.position.z,
            "rx": self.rotation.x,
            "ry": self.rotation.y,
            "health": self.health,
            "max_health": self.max_health,
            "on_ground": self.on_ground,
            "is_flying": self.is_flying,
        }


@dataclass
class Player(Entity):
    """Jugador humano o IA."""

    name: str = "Jugador"
    is_ai: bool = False
    selected_slot: int = 0
    camera_mode: int = 0  # 0=first person, 1=third close, 2=third far
    inventory: list = field(default_factory=list)

    # Estado de input para este tick
    input_move: Vec3 = field(default_factory=Vec3)
    input_look: Vec3 = field(default_factory=Vec3)
    input_jump: bool = False
    input_fly: bool = False
    input_place_block: bool = False
    input_break_block: bool = False

    def to_dict(self) -> dict:
        base = super().to_dict()
        base.update(
            {
                "name": self.name,
                "is_ai": self.is_ai,
                "selected_slot": self.selected_slot,
                "camera_mode": self.camera_mode,
            }
        )
        return base


ENEMY_TYPES = {
    "ZOMBIE": {
        "health": 20,
        "damage": 2,
        "speed": 2.0,
        "height": 1.8,
        "follow_distance": 16,
        "attack_distance": 2,
        "attack_cooldown": 1.0,
    },
    "SKELETON": {
        "health": 20,
        "damage": 2,
        "speed": 2.5,
        "height": 1.8,
        "follow_distance": 16,
        "attack_distance": 12,
        "attack_cooldown": 2.0,
        "ranged": True,
    },
    "CREEPER": {
        "health": 20,
        "damage": 0,
        "speed": 1.5,
        "height": 1.5,
        "follow_distance": 16,
        "attack_distance": 3,
        "explode_radius": 4,
    },
}


class Enemy(Entity):
    def __init__(self, enemy_type: str, position: Vec3, world: World):
        config = ENEMY_TYPES[enemy_type]
        super().__init__(
            id=-1,
            position=position.clone(),
            health=config["health"],
            max_health=config["health"],
            height=config["height"],
            speed=config["speed"],
        )
        self.enemy_type = enemy_type
        self.config = config
        self.world = world
        self.state = "idle"
        self.target: Player | None = None
        self.last_attack_time: float = 0.0

    def to_dict(self) -> dict:
        base = super().to_dict()
        base.update(
            {
                "type": self.enemy_type,
                "state": self.state,
            }
        )
        return base

    def update(self, dt: float, players: list[Player], now: float) -> None:
        nearest = None
        nearest_dist = float("inf")
        for player in players:
            if not player.is_alive():
                continue
            dist = math.hypot(
                player.position.x - self.position.x,
                player.position.z - self.position.z,
            )
            if dist < nearest_dist:
                nearest_dist = dist
                nearest = player

        if nearest and nearest_dist < self.config["follow_distance"]:
            self.target = nearest
            if nearest_dist <= self.config["attack_distance"]:
                self.state = "attack"
                self._attack(nearest, now)
            else:
                self.state = "chase"
                self._move_toward(nearest.position, dt)
        else:
            self.state = "idle"
            self.velocity.x = 0.0
            self.velocity.z = 0.0

    def _move_toward(self, target: Vec3, dt: float) -> None:
        dx = target.x - self.position.x
        dz = target.z - self.position.z
        dist = math.hypot(dx, dz)
        if dist > 0.001:
            self.velocity.x = (dx / dist) * self.speed
            self.velocity.z = (dz / dist) * self.speed

        # Salto automático si hay bloque delante
        if self.on_ground:
            front_x = int(self.position.x + (self.velocity.x / self.speed) if self.speed else 0)
            front_z = int(self.position.z + (self.velocity.z / self.speed) if self.speed else 0)
            by = int(self.position.y)
            front_block = self.world.get_block(front_x, by, front_z)
            if front_block not in (BlockType.AIR, BlockType.WATER):
                self.velocity.y = 8.0

    def _attack(self, player: Player, now: float) -> None:
        if now - self.last_attack_time < self.config["attack_cooldown"]:
            return
        self.last_attack_time = now
        player.health -= self.config["damage"]
        if player.health <= 0:
            player.health = player.max_health
            player.position = Vec3(0.0, 40.0, 0.0)


class EnemyManager:
    next_enemy_id = 1

    def __init__(self, world: World, max_enemies: int = 10):
        self.world = world
        self.enemies: list[Enemy] = []
        self.max_enemies = max_enemies
        self.spawn_radius = 20
        self.spawn_cooldown = 5.0
        self.last_spawn_time: float = 0.0

    def find_enemy_by_id(self, enemy_id: int) -> Enemy | None:
        for enemy in self.enemies:
            if enemy.id == enemy_id:
                return enemy
        return None

    def find_nearest_in_cone(
        self,
        player_position: Vec3,
        player_direction: Vec3,
        max_dist: float,
        cone_dot: float,
    ) -> Enemy | None:
        nearest = None
        nearest_dist = float("inf")
        for enemy in self.enemies:
            dx = enemy.position.x - player_position.x
            dz = enemy.position.z - player_position.z
            dist = math.hypot(dx, dz)
            if dist > max_dist:
                continue
            if dist < 0.001:
                continue
            dot = (dx / dist) * player_direction.x + (dz / dist) * player_direction.z
            if dot < cone_dot:
                continue
            if dist < nearest_dist:
                nearest_dist = dist
                nearest = enemy
        return nearest

    def update(self, dt: float, players: list[Player], now: float, is_night: bool) -> list[dict]:
        events: list[dict] = []
        if is_night:
            for player in players:
                if (
                    now - self.last_spawn_time > self.spawn_cooldown
                    and len(self.enemies) < self.max_enemies
                ):
                    self._try_spawn(player)
                    self.last_spawn_time = now

        for i in range(len(self.enemies) - 1, -1, -1):
            enemy = self.enemies[i]
            enemy.update(dt, players, now)
            if not enemy.is_alive():
                events.append(
                    {
                        "type": "entity_died",
                        "target": "enemy",
                        "id": enemy.id,
                    }
                )
                self.enemies.pop(i)
        return events

    def _try_spawn(self, player: Player) -> None:
        import random

        angle = random.random() * math.pi * 2
        distance = 15 + random.random() * 10
        spawn_x = player.position.x + math.cos(angle) * distance
        spawn_z = player.position.z + math.sin(angle) * distance
        spawn_y = self.world.get_spawn_height(int(spawn_x), int(spawn_z))
        if spawn_y < 1 or spawn_y > 50:
            return
        enemy_type = random.choice(list(ENEMY_TYPES.keys()))
        enemy = Enemy(enemy_type, Vec3(spawn_x, float(spawn_y), spawn_z), self.world)
        enemy.id = EnemyManager.next_enemy_id
        EnemyManager.next_enemy_id += 1
        self.enemies.append(enemy)

    def get_enemies_state(self) -> list[dict]:
        return [enemy.to_dict() for enemy in self.enemies]
