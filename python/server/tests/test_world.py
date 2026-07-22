"""Tests de motor de mundo y chunks."""

import pytest

from server.engine.chunk import Chunk
from server.engine.constants import BlockType, CHUNK_SIZE, WORLD_HEIGHT
from server.engine.noise import PerlinNoise
from server.engine.world import World


class TestChunk:
    def test_chunk_initially_air(self):
        chunk = Chunk(0, 0)
        assert chunk.get_block(0, 0, 0) == BlockType.AIR
        assert chunk.get_block(8, 30, 8) == BlockType.AIR

    def test_chunk_set_and_get(self):
        chunk = Chunk(0, 0)
        chunk.set_block(1, 2, 3, BlockType.GRASS)
        assert chunk.get_block(1, 2, 3) == BlockType.GRASS
        assert chunk.dirty is True

    def test_chunk_out_of_bounds(self):
        chunk = Chunk(0, 0)
        chunk.set_block(-1, 0, 0, BlockType.GRASS)
        assert chunk.get_block(-1, 0, 0) == BlockType.AIR
        chunk.set_block(CHUNK_SIZE, 0, 0, BlockType.GRASS)
        assert chunk.get_block(CHUNK_SIZE, 0, 0) == BlockType.AIR

    def test_flat_generation(self):
        chunk = Chunk(0, 0)
        chunk.generate_flat(size=16)
        assert chunk.get_block(0, 0, 0) == BlockType.BEDROCK
        assert chunk.get_block(0, 1, 0) == BlockType.GRASS
        assert chunk.get_block(0, 2, 0) == BlockType.AIR

    def test_terrain_generation(self):
        noise = PerlinNoise(seed=42)
        chunk = Chunk(0, 0)
        chunk.generate_terrain(noise)
        # El terreno debería tener bedrock en y=0
        assert chunk.get_block(0, 0, 0) == BlockType.BEDROCK
        # y aire en la parte superior
        assert chunk.get_block(0, WORLD_HEIGHT - 1, 0) == BlockType.AIR


class TestWorld:
    def test_get_block_returns_air_for_unloaded_chunk(self):
        world = World(seed=42)
        assert world.get_block(0, 30, 0) == BlockType.AIR

    def test_set_block_generates_chunk(self):
        world = World(seed=42)
        world.set_block(10, 25, 10, BlockType.GRASS)
        assert world.get_block(10, 25, 10) == BlockType.GRASS

    def test_negative_coordinates(self):
        world = World(seed=42)
        world.set_block(-1, 25, -1, BlockType.STONE)
        assert world.get_block(-1, 25, -1) == BlockType.STONE

    def test_spawn_height(self):
        world = World(seed=42, flat_mode=16)
        world.update_around(0, 0)
        height = world.get_spawn_height(0, 0)
        assert height == 2  # flat mode: bedrock 0, grass 1, spawn = 2

    def test_raycast_hits_block(self):
        world = World(seed=42, flat_mode=16)
        world.update_around(0, 0)
        result = world.raycast((0.5, 5.0, 0.5), (0.0, -1.0, 0.0), max_dist=10)
        assert result is not None
        assert result["block"] == BlockType.GRASS
        assert result["position"]["y"] == 1


class TestPerlinNoise:
    def test_deterministic(self):
        n1 = PerlinNoise(seed=123)
        n2 = PerlinNoise(seed=123)
        assert n1.noise(1.5, 2.5) == n2.noise(1.5, 2.5)

    def test_different_seeds(self):
        n1 = PerlinNoise(seed=123)
        n2 = PerlinNoise(seed=456)
        assert n1.noise(1.5, 2.5) != n2.noise(1.5, 2.5)

    def test_octave_noise_range(self):
        n = PerlinNoise(seed=123)
        for x in range(-10, 11, 2):
            for z in range(-10, 11, 2):
                value = n.octave_noise(x * 0.02, z * 0.02, 4)
                assert -1.0 <= value <= 1.0
