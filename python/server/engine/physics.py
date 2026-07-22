"""Sistema de física para entidades y colapso de bloques."""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

from server.engine.constants import BlockType, WORLD_HEIGHT, DT
from server.engine.entities import Entity, Player, Vec3

if TYPE_CHECKING:
    from server.engine.world import World


class PhysicsSystem:
    """Aplica movimiento con colisiones AABB sobre el voxel grid."""

    def __init__(self, world: World):
        self.world = world
        self.falling_blocks: list[dict] = []

    def update_entity(self, entity: Entity, dt: float) -> None:
        """Aplica velocidad, gravedad y colisiones a una entidad."""
        if entity.is_flying:
            entity.velocity.y = 0.0
        else:
            entity.velocity.y += -20.0 * dt

        new_pos = entity.position.clone()

        # Eje X
        new_pos.x += entity.velocity.x * dt
        if self._check_collision(new_pos, entity):
            new_pos.x = entity.position.x
            entity.velocity.x = 0.0

        # Eje Z
        new_pos.z += entity.velocity.z * dt
        if self._check_collision(new_pos, entity):
            new_pos.z = entity.position.z
            entity.velocity.z = 0.0

        # Eje Y
        new_pos.y += entity.velocity.y * dt
        if self._check_collision(new_pos, entity):
            if entity.velocity.y < 0:
                entity.on_ground = True
                if entity.is_flying:
                    entity.is_flying = False
            new_pos.y = entity.position.y
            entity.velocity.y = 0.0
        else:
            entity.on_ground = False

        entity.position = new_pos
        entity.position.y = max(1.0, min(float(WORLD_HEIGHT - 2), entity.position.y))

    def _check_collision(self, pos: Vec3, entity: Entity) -> bool:
        radius = entity.width / 2
        height = entity.height

        for dx in (-1, 0, 1):
            for dz in (-1, 0, 1):
                for dy in (0, 1):
                    bx = int(pos.x + dx * radius)
                    by = int(pos.y + dy * height)
                    bz = int(pos.z + dz * radius)
                    block = self.world.get_block(bx, by, bz)
                    if block not in (BlockType.AIR, BlockType.WATER):
                        return True
        return False

    def apply_input(self, player: Player, dt: float) -> None:
        """Convierte input del jugador en velocidad y rotación."""
        # Rotación
        player.rotation.y -= player.input_look.x * 0.05
        player.rotation.x -= player.input_look.y * 0.05
        player.rotation.x = max(-math.pi / 2 + 0.1, min(math.pi / 2 - 0.1, player.rotation.x))

        # Movimiento relativo a la cámara
        yaw = player.rotation.y
        forward = Vec3(-math.sin(yaw), 0.0, -math.cos(yaw))
        right = Vec3(math.cos(yaw), 0.0, -math.sin(yaw))

        move = Vec3()
        move.x += forward.x * -player.input_move.z
        move.z += forward.z * -player.input_move.z
        move.x += right.x * player.input_move.x
        move.z += right.z * player.input_move.x

        length = math.hypot(move.x, move.z)
        if length > 0.001:
            move.x /= length
            move.z /= length
            player.velocity.x = move.x * player.speed
            player.velocity.z = move.z * player.speed
        else:
            player.velocity.x = 0.0
            player.velocity.z = 0.0

        # Salto / vuelo
        if player.is_flying:
            if player.input_jump:
                player.velocity.y = player.speed
        else:
            if player.input_jump and player.on_ground:
                player.velocity.y = 8.0
                player.on_ground = False

    def on_block_broken(self, x: int, y: int, z: int) -> None:
        """Inicia cadena de colapso de bloques flotantes."""
        self._check_unsupported(x, y + 1, z)

    def _check_unsupported(self, x: int, y: int, z: int) -> None:
        if y < 1 or y >= WORLD_HEIGHT:
            return
        block = self.world.get_block(x, y, z)
        if block in (BlockType.AIR, BlockType.WATER):
            return
        below = self.world.get_block(x, y - 1, z)
        if below not in (BlockType.AIR, BlockType.WATER):
            return
        self.world.set_block(x, y, z, BlockType.AIR)
        self.falling_blocks.append({"x": x + 0.5, "y": y + 0.5, "z": z + 0.5, "type": int(block), "vel_y": 0.0})
        self._check_unsupported(x, y + 1, z)

    def update_falling_blocks(self, dt: float) -> list[dict]:
        """Actualiza bloques cayendo y devuelve eventos de colocación."""
        events: list[dict] = []
        dt = min(dt, 0.05)
        for i in range(len(self.falling_blocks) - 1, -1, -1):
            fb = self.falling_blocks[i]
            fb["vel_y"] -= 14.0 * dt
            fb["y"] += fb["vel_y"] * dt

            ground_y = self._get_ground_height(int(fb["x"] - 0.5), int(fb["z"] - 0.5))
            if fb["y"] - 0.45 <= ground_y + 0.5:
                bx, by, bz = int(fb["x"]), int(fb["y"] - 0.45), int(fb["z"])
                if 0 <= by < WORLD_HEIGHT and self.world.get_block(bx, by, bz) == BlockType.AIR:
                    self.world.set_block(bx, by, bz, fb["type"])
                    events.append({"type": "block_placed", "x": bx, "y": by, "z": bz, "block_type": fb["type"]})
                self.falling_blocks.pop(i)
            elif fb["y"] < -10:
                self.falling_blocks.pop(i)
        return events

    def _get_ground_height(self, x: int, z: int) -> int:
        for y in range(WORLD_HEIGHT - 1, -1, -1):
            block = self.world.get_block(x, y, z)
            if block not in (BlockType.AIR, BlockType.WATER):
                return y
        return 0
