"""Generador de ruido Perlin compatible con js/noise.js."""

import math
from typing import Self


class PerlinNoise:
    """Implementación Python del PerlinNoise de VoxelQuest (js/noise.js).

    Usa el mismo generador congruencial lineal (LCG) y mismas constantes
    para producir terreno idéntico al cliente original.
    """

    def __init__(self, seed: int = 0) -> None:
        self._initial_seed = seed
        self.seed = seed
        self.permutation = self._generate_permutation()

    def _generate_permutation(self) -> list[int]:
        perm = list(range(256))
        for i in range(255, 0, -1):
            j = math.floor(self._seeded_random() * (i + 1))
            perm[i], perm[j] = perm[j], perm[i]
        # Duplicar para evitar buffer overflow al interpolar
        return perm + perm

    def _seeded_random(self) -> float:
        # Mismas constantes que js/noise.js
        self.seed = (self.seed * 16807 + 0) % 2147483647
        return (self.seed - 1) / 2147483646

    @staticmethod
    def _fade(t: float) -> float:
        return t * t * t * (t * (t * 6 - 15) + 10)

    @staticmethod
    def _lerp(t: float, a: float, b: float) -> float:
        return a + t * (b - a)

    @staticmethod
    def _grad(hash_: int, x: float, y: float) -> float:
        h = hash_ & 3
        u = x if h < 2 else y
        v = y if h < 2 else x
        return ((-u if h & 1 else u) + (-v if h & 2 else v))

    def noise(self, x: float, y: float) -> float:
        X = math.floor(x) & 255
        Y = math.floor(y) & 255
        x -= math.floor(x)
        y -= math.floor(y)
        u = self._fade(x)
        v = self._fade(y)

        A = self.permutation[X] + Y
        B = self.permutation[X + 1] + Y

        return self._lerp(
            v,
            self._lerp(
                u,
                self._grad(self.permutation[A], x, y),
                self._grad(self.permutation[B], x - 1, y),
            ),
            self._lerp(
                u,
                self._grad(self.permutation[A + 1], x, y - 1),
                self._grad(self.permutation[B + 1], x - 1, y - 1),
            ),
        )

    def octave_noise(self, x: float, y: float, octaves: int = 4, persistence: float = 0.5) -> float:
        total = 0.0
        frequency = 1.0
        amplitude = 1.0
        max_value = 0.0

        for _ in range(octaves):
            total += self.noise(x * frequency, y * frequency) * amplitude
            max_value += amplitude
            amplitude *= persistence
            frequency *= 2

        return total / max_value

    def with_seed(self, seed: int) -> Self:
        """Devuelve una nueva instancia con otra seed (útil para tests)."""
        return self.__class__(seed)
