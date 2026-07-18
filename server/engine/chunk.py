"""Chunk voxel: almacenamiento y generación de terreno."""

from __future__ import annotations

import numpy as np
from typing import TYPE_CHECKING

from server.engine.constants import BlockType, CHUNK_SIZE, WORLD_HEIGHT, SEA_LEVEL
from server.engine.noise import PerlinNoise

if TYPE_CHECKING:
    from server.engine.world import World


class Chunk:
    """Un chunk de CHUNK_SIZE x WORLD_HEIGHT x CHUNK_SIZE bloques."""

    def __init__(self, cx: int, cz: int, world: World | None = None):
        self.cx = cx
        self.cz = cz
        self.world = world
        # Layout compatible con js/world.js: x + z*CHUNK_SIZE + y*CHUNK_SIZE^2
        self.blocks = np.zeros(CHUNK_SIZE * WORLD_HEIGHT * CHUNK_SIZE, dtype=np.uint8)
        self.dirty = True

    @staticmethod
    def _index(x: int, y: int, z: int) -> int:
        return x + z * CHUNK_SIZE + y * CHUNK_SIZE * CHUNK_SIZE

    def get_block(self, x: int, y: int, z: int) -> BlockType:
        if not (0 <= x < CHUNK_SIZE and 0 <= y < WORLD_HEIGHT and 0 <= z < CHUNK_SIZE):
            return BlockType.AIR
        return BlockType(self.blocks[self._index(x, y, z)])

    def set_block(self, x: int, y: int, z: int, block_type: BlockType | int) -> None:
        if not (0 <= x < CHUNK_SIZE and 0 <= y < WORLD_HEIGHT and 0 <= z < CHUNK_SIZE):
            return
        self.blocks[self._index(x, y, z)] = int(block_type)
        self.dirty = True

    def generate_flat(self, size: int) -> None:
        wx0 = self.cx * CHUNK_SIZE
        wz0 = self.cz * CHUNK_SIZE
        for x in range(CHUNK_SIZE):
            for z in range(CHUNK_SIZE):
                wx = wx0 + x
                wz = wz0 + z
                for y in range(WORLD_HEIGHT):
                    if wx < 0 or wx >= size or wz < 0 or wz >= size:
                        if y <= 3:
                            self.set_block(x, y, z, BlockType.BEDROCK)
                    else:
                        if y == 0:
                            self.set_block(x, y, z, BlockType.BEDROCK)
                        elif y == 1:
                            self.set_block(x, y, z, BlockType.GRASS)

    def generate_terrain(self, noise: PerlinNoise) -> None:
        """Genera terreno procedural con el mismo algoritmo que js/world.js."""
        for x in range(CHUNK_SIZE):
            for z in range(CHUNK_SIZE):
                world_x = self.cx * CHUNK_SIZE + x
                world_z = self.cz * CHUNK_SIZE + z
                height = int(noise.octave_noise(world_x * 0.02, world_z * 0.02, 4) * 15 + 25)

                for y in range(WORLD_HEIGHT):
                    block_type = BlockType.AIR
                    if y == 0:
                        block_type = BlockType.BEDROCK
                    elif y < height - 4:
                        block_type = BlockType.STONE
                    elif y < height - 1:
                        block_type = BlockType.DIRT
                    elif y == height - 1:
                        block_type = BlockType.GRASS if height > SEA_LEVEL else BlockType.SAND
                    elif y < SEA_LEVEL:
                        block_type = BlockType.WATER
                    self.set_block(x, y, z, block_type)

                if height > SEA_LEVEL + 2 and np.random.random() < 0.02:
                    self._generate_tree(x, height - 1, z)

    def _generate_tree(self, x: int, y: int, z: int) -> None:
        h = 4 + int(np.random.random() * 3)
        for i in range(h):
            self.set_block(x, y + i, z, BlockType.WOOD)
        for dx in range(-2, 3):
            for dz in range(-2, 3):
                for dy in range(-1, 2):
                    if abs(dx) + abs(dz) + abs(dy) < 4:
                        lx, ly, lz = x + dx, y + h + dy, z + dz
                        if 0 <= lx < CHUNK_SIZE and 0 <= lz < CHUNK_SIZE and 0 <= ly < WORLD_HEIGHT:
                            self.set_block(lx, ly, lz, BlockType.LEAVES)

    def get_modified_blocks(self) -> list[tuple[int, int, int, int]]:
        """Devuelve lista [x, y, z, type] de bloques no aire (para serialización inicial)."""
        result: list[tuple[int, int, int, int]] = []
        for idx, block in enumerate(self.blocks):
            if block == BlockType.AIR:
                continue
            y = idx // (CHUNK_SIZE * CHUNK_SIZE)
            remainder = idx % (CHUNK_SIZE * CHUNK_SIZE)
            z = remainder // CHUNK_SIZE
            x = remainder % CHUNK_SIZE
            result.append((x, y, z, int(block)))
        return result

    def to_dict(self) -> dict:
        """Serialización ligera del chunk."""
        return {
            "cx": self.cx,
            "cz": self.cz,
            "blocks": self.get_modified_blocks(),
        }
