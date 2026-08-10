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
        # True hasta que el chunk se haya serializado completo una vez.
        # Evita re-serializar chunks completos en cada tick.
        self.needs_full = True
        # Coordenadas [x, y, z] de bloques modificados desde la última
        # serialización. Incluye aire: así una destrucción llega al cliente.
        # Se limpia con _reset_modified() al serializar.
        self._modified: set[tuple[int, int, int]] = set()

    @staticmethod
    def _index(x: int, y: int, z: int) -> int:
        return x + z * CHUNK_SIZE + y * CHUNK_SIZE * CHUNK_SIZE

    def get_block(self, x: int, y: int, z: int) -> BlockType:
        if not (0 <= x < CHUNK_SIZE and 0 <= y < WORLD_HEIGHT and 0 <= z < CHUNK_SIZE):
            return BlockType.AIR
        return BlockType(self.blocks[self._index(x, y, z)])

    def set_block(self, x: int, y: int, z: int, block_type: BlockType | int) -> None:
        self.write_block(x, y, z, block_type)

    def write_block(self, x: int, y: int, z: int, block_type: BlockType | int, track: bool = True) -> None:
        """Escritura directa del bloque.

        track=False se usa en generación de terreno: el chunk completo se envía
        la primera vez, así que no queremos inflar _modified.
        """
        if not (0 <= x < CHUNK_SIZE and 0 <= y < WORLD_HEIGHT and 0 <= z < CHUNK_SIZE):
            return
        self.blocks[self._index(x, y, z)] = int(block_type)
        if track:
            self._modified.add((x, y, z))
        self.dirty = True

    def _reset_modified(self) -> None:
        self._modified = set()

    def generate_flat(self, size: int) -> None:
        # LLANURA INFINITA para entrenamiento IA.
        # Ignora el parámetro size: no hay barreras. Solo bedrock en y=0 e hierba en y=1.
        for x in range(CHUNK_SIZE):
            for z in range(CHUNK_SIZE):
                for y in range(WORLD_HEIGHT):
                    if y == 0:
                        self.write_block(x, y, z, BlockType.BEDROCK, track=False)
                    elif y == 1:
                        self.write_block(x, y, z, BlockType.GRASS, track=False)

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
                    self.write_block(x, y, z, block_type, track=False)

                if height > SEA_LEVEL + 2 and np.random.random() < 0.02:
                    self._generate_tree(x, height - 1, z)

    def _generate_tree(self, x: int, y: int, z: int) -> None:
        h = 4 + int(np.random.random() * 3)
        for i in range(h):
            self.write_block(x, y + i, z, BlockType.WOOD, track=False)
        for dx in range(-2, 3):
            for dz in range(-2, 3):
                for dy in range(-1, 2):
                    if abs(dx) + abs(dz) + abs(dy) < 4:
                        lx, ly, lz = x + dx, y + h + dy, z + dz
                        if 0 <= lx < CHUNK_SIZE and 0 <= lz < CHUNK_SIZE and 0 <= ly < WORLD_HEIGHT:
                            self.write_block(lx, ly, lz, BlockType.LEAVES, track=False)

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

    def get_modified_since(self) -> list[tuple[int, int, int, int]]:
        """Devuelve [x, y, z, type] de bloques modificados desde el último reset.

        A diferencia de get_modified_blocks, INCLUYE el aire: así un bloque
        destruido llega al cliente como aire en vez de ser omitido.
        """
        result: list[tuple[int, int, int, int]] = []
        for (x, y, z) in self._modified:
            result.append((x, y, z, int(self.blocks[self._index(x, y, z)])))
        self._reset_modified()
        return result

    def to_dict(self) -> dict:
        """Serialización ligera del chunk."""
        return {
            "cx": self.cx,
            "cz": self.cz,
            "blocks": self.get_modified_blocks(),
        }
