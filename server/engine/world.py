"""Mundo voxel: chunks, generación, acceso global a bloques."""

from __future__ import annotations

from typing import TYPE_CHECKING

from server.engine.chunk import Chunk
from server.engine.constants import BlockType, CHUNK_SIZE, WORLD_HEIGHT, RENDER_DISTANCE
from server.engine.noise import PerlinNoise

if TYPE_CHECKING:
    from server.engine.entities import Player


class World:
    """Mundo autoritativo: contiene chunks y resuelve coordenadas globales."""

    def __init__(self, seed: int = 12345, flat_mode: int | None = None):
        self.seed = seed
        self.noise = PerlinNoise(seed)
        self.flat_mode = flat_mode
        self.chunks: dict[tuple[int, int], Chunk] = {}
        self._players: list[Player] = []

    @staticmethod
    def _chunk_key(cx: int, cz: int) -> tuple[int, int]:
        return (cx, cz)

    def get_chunk(self, cx: int, cz: int) -> Chunk | None:
        return self.chunks.get(self._chunk_key(cx, cz))

    def ensure_chunk(self, cx: int, cz: int) -> Chunk:
        key = self._chunk_key(cx, cz)
        if key not in self.chunks:
            chunk = Chunk(cx, cz, self)
            if self.flat_mode is not None:
                chunk.generate_flat(self.flat_mode)
            else:
                chunk.generate_terrain(self.noise)
            self.chunks[key] = chunk
        return self.chunks[key]

    def get_block(self, wx: int, wy: int, wz: int) -> BlockType:
        if wy < 0 or wy >= WORLD_HEIGHT:
            return BlockType.AIR
        cx = int(wx // CHUNK_SIZE) if wx >= 0 else int((wx - (CHUNK_SIZE - 1)) // CHUNK_SIZE)
        cz = int(wz // CHUNK_SIZE) if wz >= 0 else int((wz - (CHUNK_SIZE - 1)) // CHUNK_SIZE)
        chunk = self.get_chunk(cx, cz)
        if chunk is None:
            return BlockType.AIR
        lx = wx - cx * CHUNK_SIZE
        lz = wz - cz * CHUNK_SIZE
        return chunk.get_block(lx, wy, lz)

    def set_block(self, wx: int, wy: int, wz: int, block_type: BlockType | int) -> None:
        if wy < 0 or wy >= WORLD_HEIGHT:
            return
        cx = int(wx // CHUNK_SIZE) if wx >= 0 else int((wx - (CHUNK_SIZE - 1)) // CHUNK_SIZE)
        cz = int(wz // CHUNK_SIZE) if wz >= 0 else int((wz - (CHUNK_SIZE - 1)) // CHUNK_SIZE)
        chunk = self.ensure_chunk(cx, cz)
        lx = wx - cx * CHUNK_SIZE
        lz = wz - cz * CHUNK_SIZE
        chunk.set_block(lx, wy, lz, block_type)
        # Marcar chunks vecinos como dirty si el bloque está en el borde
        if lx == 0:
            neighbor = self.get_chunk(cx - 1, cz)
            if neighbor:
                neighbor.dirty = True
        elif lx == CHUNK_SIZE - 1:
            neighbor = self.get_chunk(cx + 1, cz)
            if neighbor:
                neighbor.dirty = True
        if lz == 0:
            neighbor = self.get_chunk(cx, cz - 1)
            if neighbor:
                neighbor.dirty = True
        elif lz == CHUNK_SIZE - 1:
            neighbor = self.get_chunk(cx, cz + 1)
            if neighbor:
                neighbor.dirty = True

    def update_around(self, px: float, pz: float) -> None:
        """Genera chunks alrededor de la posición dada."""
        pcx = int(px // CHUNK_SIZE)
        pcz = int(pz // CHUNK_SIZE)
        for dx in range(-RENDER_DISTANCE, RENDER_DISTANCE + 1):
            for dz in range(-RENDER_DISTANCE, RENDER_DISTANCE + 1):
                self.ensure_chunk(pcx + dx, pcz + dz)

    def get_spawn_height(self, x: int, z: int) -> int:
        for y in range(WORLD_HEIGHT - 1, -1, -1):
            block = self.get_block(x, y, z)
            if block != BlockType.AIR and block != BlockType.WATER:
                return y + 1
        return 30

    def get_deltas_since(self, known_chunks: dict[tuple[int, int], int]) -> dict:
        """Devuelve cambios de bloques desde la última snapshot conocida.

        known_chunks: dict {(cx, cz): serial} donde serial es un contador de versión.
        """
        deltas: dict = {}
        for (cx, cz), chunk in self.chunks.items():
            current = chunk.dirty  # placeholder: en v0.2 usaremos un serial por chunk
            if current:
                deltas[f"{cx},{cz}"] = {
                    "modified": chunk.get_modified_blocks(),
                    "full": True,
                }
                chunk.dirty = False
        return deltas

    def raycast(
        self,
        origin: tuple[float, float, float],
        direction: tuple[float, float, float],
        max_dist: float = 8.0,
    ) -> dict | None:
        """Raycast simple sobre voxel grid."""
        import math

        step = 0.1
        dx, dy, dz = direction
        length = math.sqrt(dx * dx + dy * dy + dz * dz)
        if length == 0:
            return None
        dx, dy, dz = dx / length * step, dy / length * step, dz / length * step

        px, py, pz = origin
        last: tuple[int, int, int] | None = None
        steps = int(max_dist / step)

        for _ in range(steps):
            bx, by, bz = int(px), int(py), int(pz)
            block = self.get_block(bx, by, bz)
            if block != BlockType.AIR and block != BlockType.WATER:
                normal = {"x": 0, "y": 1, "z": 0}
                if last:
                    normal = {"x": last[0] - bx, "y": last[1] - by, "z": last[2] - bz}
                return {
                    "position": {"x": bx, "y": by, "z": bz},
                    "normal": normal,
                    "block": int(block),
                }
            last = (bx, by, bz)
            px += dx
            py += dy
            pz += dz
        return None
