"""Pathfinding A* sobre voxel grid (port de js/navigation.js)."""

from __future__ import annotations

import heapq
from typing import TYPE_CHECKING

from server.engine.constants import BlockType

if TYPE_CHECKING:
    from server.engine.world import World


class PathNode:
    def __init__(self, x: int, z: int, parent: PathNode | None = None, g: float = 0, h: float = 0):
        self.x = x
        self.z = z
        self.parent = parent
        self.g = g
        self.h = h
        self.f = g + h
        self.jump = False

    def __lt__(self, other: PathNode) -> bool:
        return self.f < other.f


class Pathfinder:
    def __init__(self, world: World, max_steps: int = 500):
        self.world = world
        self.max_steps = max_steps

    def find_path(self, start_x: float, start_z: float, goal_x: float, goal_z: float, start_y: float) -> list[dict] | None:
        sx, sz = int(start_x), int(start_z)
        gx, gz = int(goal_x), int(goal_z)
        base_y = int(start_y)

        start = PathNode(sx, sz, None, 0, self._heuristic(sx, sz, gx, gz))
        open_set: list[PathNode] = [start]
        closed: set[tuple[int, int]] = set()
        best: dict[tuple[int, int], PathNode] = {(sx, sz): start}

        steps = 0
        while open_set and steps < self.max_steps:
            steps += 1
            current = heapq.heappop(open_set)
            if (current.x, current.z) in closed:
                continue

            if current.x == gx and current.z == gz:
                return self._reconstruct_path(current)

            closed.add((current.x, current.z))

            for neighbor in self._get_neighbors(current, gx, gz, base_y):
                key = (neighbor.x, neighbor.z)
                if key in closed:
                    continue
                existing = best.get(key)
                if existing is None or neighbor.g < existing.g:
                    best[key] = neighbor
                    heapq.heappush(open_set, neighbor)

        return None

    def _get_neighbors(self, node: PathNode, goal_x: int, goal_z: int, base_y: int) -> list[PathNode]:
        neighbors = []
        for dx, dz in [(0, -1), (0, 1), (-1, 0), (1, 0)]:
            nx, nz = node.x + dx, node.z + dz
            if self._is_walkable(nx, nz, base_y):
                jump = self._requires_jump(nx, nz, base_y)
                cost = 2 if jump else 1
                g = node.g + cost
                h = self._heuristic(nx, nz, goal_x, goal_z)
                n = PathNode(nx, nz, node, g, h)
                n.jump = jump
                neighbors.append(n)
        return neighbors

    def _is_walkable(self, x: int, z: int, base_y: int) -> bool:
        # base_y es la altura de los pies: foot está en base_y, head en base_y+1, support en base_y-1
        foot = self.world.get_block(x, base_y, z)
        head = self.world.get_block(x, base_y + 1, z)
        if foot not in (BlockType.AIR, BlockType.WATER):
            return False
        if head not in (BlockType.AIR, BlockType.WATER):
            return False
        support = self.world.get_block(x, base_y - 1, z)
        if support in (BlockType.AIR, BlockType.WATER):
            return False
        return True

    def _requires_jump(self, x: int, z: int, base_y: int) -> bool:
        foot = self.world.get_block(x, base_y, z)
        return foot not in (BlockType.AIR, BlockType.WATER)

    def _heuristic(self, x1: int, z1: int, x2: int, z2: int) -> int:
        return abs(x1 - x2) + abs(z1 - z2)

    def _reconstruct_path(self, node: PathNode) -> list[dict]:
        path = []
        current: PathNode | None = node
        while current:
            path.append({"x": current.x, "z": current.z, "jump": current.jump})
            current = current.parent
        path.reverse()
        return path
