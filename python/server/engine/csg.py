"""Evaluador CSG declarativo: árbol de primitivas y operaciones → mapa de bloques.

Convierte una descripción declarativa (JSON) en un dict {(x,y,z): material}
en coordenadas locales. El árbol se compone de:

- Primitivas: box, sphere, cylinder, pyramid
- Booleanas: union, subtract, intersect
- Transformaciones: at (traslación), rotate (múltiplos de 90°)
- Repetición: array (lineal), radial (alrededor del eje Y)

Materiales: nombre ("cobblestone") o id (0-13) para target=grid;
color (int) para target=sculpture.
"""

from __future__ import annotations

import math
from typing import Any

from server.engine.constants import BlockType

MAX_BLOCKS = 20000

MATERIAL_ALIASES: dict[str, BlockType] = {
    "air": BlockType.AIR,
    "grass": BlockType.GRASS,
    "dirt": BlockType.DIRT,
    "stone": BlockType.STONE,
    "wood": BlockType.WOOD,
    "leaves": BlockType.LEAVES,
    "sand": BlockType.SAND,
    "water": BlockType.WATER,
    "cobblestone": BlockType.COBBLESTONE,
    "cobble": BlockType.COBBLESTONE,
    "planks": BlockType.PLANKS,
    "plank": BlockType.PLANKS,
    "bedrock": BlockType.BEDROCK,
    "glowstone": BlockType.GLOWSTONE,
    "redstone": BlockType.REDSTONE,
    "red_brick": BlockType.RED_BRICK,
    "brick": BlockType.RED_BRICK,
}

PRIMITIVES = ("box", "sphere", "cylinder", "pyramid")
BOOLEANS = ("union", "subtract", "intersect")
TRANSFORMS = ("at", "rotate")
REPEATS = ("array", "radial")
VALID_OPS = PRIMITIVES + BOOLEANS + TRANSFORMS + REPEATS

_ROTATIONS: dict[tuple[str, int], Any] = {
    ("y", 90): lambda x, y, z: (-z, y, x),
    ("y", 180): lambda x, y, z: (-x, y, -z),
    ("y", 270): lambda x, y, z: (z, y, -x),
    ("x", 90): lambda x, y, z: (x, -z, y),
    ("x", 180): lambda x, y, z: (x, -y, -z),
    ("x", 270): lambda x, y, z: (x, z, -y),
    ("z", 90): lambda x, y, z: (-y, x, z),
    ("z", 180): lambda x, y, z: (-x, -y, z),
    ("z", 270): lambda x, y, z: (y, -x, z),
}


def _range_centered(size: int) -> range:
    """Rango de índices para un tamaño centrado en el origen.

    Tamaños impares: centrado exacto (3 → [-1,0,1]).
    Tamaños pares: ligeramente desplazado a la izquierda (4 → [-2,-1,0,1]).
    """
    return range(-(size // 2), size - size // 2)


def _resolve_material(node: dict, inherited: int | None) -> int:
    mat = node.get("material", inherited)
    if mat is None:
        return int(BlockType.STONE)
    if isinstance(mat, int):
        return mat
    if isinstance(mat, str):
        key = mat.strip().lower()
        if key in MATERIAL_ALIASES:
            return int(MATERIAL_ALIASES[key])
        raise ValueError(f"unknown material: {mat!r}")
    raise ValueError(f"invalid material: {mat!r}")


def _children(node: dict, op: str) -> list[dict]:
    children = node.get("children")
    if not isinstance(children, list) or not children:
        raise ValueError(f"{op} requires 'children' (non-empty list)")
    return children


def _eval_primitive(op: str, node: dict, material: int | None) -> dict[tuple[int, int, int], int]:
    mat = _resolve_material(node, material)
    out: dict[tuple[int, int, int], int] = {}

    if op == "box":
        size = node.get("size")
        if not isinstance(size, (list, tuple)) or len(size) != 3:
            raise ValueError("box requires size: [w,h,d]")
        w, h, d = (int(s) for s in size)
        for x in _range_centered(w):
            for y in _range_centered(h):
                for z in _range_centered(d):
                    out[(x, y, z)] = mat

    elif op == "sphere":
        radius = float(node.get("radius", 1.0))
        r = int(math.ceil(radius))
        r2 = radius * radius
        for x in range(-r, r + 1):
            for y in range(-r, r + 1):
                for z in range(-r, r + 1):
                    if x * x + y * y + z * z <= r2:
                        out[(x, y, z)] = mat

    elif op == "cylinder":
        radius = float(node.get("radius", 1.0))
        height = int(node.get("height", 3))
        r = int(math.ceil(radius))
        r2 = radius * radius
        for y in _range_centered(height):
            for x in range(-r, r + 1):
                for z in range(-r, r + 1):
                    if x * x + z * z <= r2:
                        out[(x, y, z)] = mat

    elif op == "pyramid":
        base = node.get("base", 4)
        height = int(node.get("height", 4))
        if isinstance(base, (list, tuple)):
            bw, bd = int(base[0]), int(base[1])
        else:
            bw = bd = int(base)
        ys = list(_range_centered(height))
        ymin, ymax = ys[0], ys[-1]
        span = max(ymax - ymin, 1)
        for y in ys:
            frac = (y - ymin) / span
            half_w = (bw / 2) * (1 - frac)
            half_d = (bd / 2) * (1 - frac)
            for x in range(-int(math.ceil(half_w)), int(math.ceil(half_w)) + 1):
                for z in range(-int(math.ceil(half_d)), int(math.ceil(half_d)) + 1):
                    if abs(x) <= half_w and abs(z) <= half_d:
                        out[(x, y, z)] = mat

    return out


def _eval_boolean(op: str, node: dict, material: int | None) -> dict[tuple[int, int, int], int]:
    children = _children(node, op)
    result = evaluate_tree(children[0], material)
    for child in children[1:]:
        other = evaluate_tree(child, material)
        if op == "union":
            result.update(other)
        elif op == "subtract":
            for key in other:
                result.pop(key, None)
        elif op == "intersect":
            result = {k: v for k, v in result.items() if k in other}
    return result


def _eval_translate(node: dict, material: int | None) -> dict[tuple[int, int, int], int]:
    at = node.get("at")
    if not isinstance(at, (list, tuple)) or len(at) != 3:
        raise ValueError("at requires 'at': [dx,dy,dz]")
    dx, dy, dz = (int(v) for v in at)
    inner = evaluate_tree(_children(node, "at")[0], material)
    return {(x + dx, y + dy, z + dz): m for (x, y, z), m in inner.items()}


def _eval_rotate(node: dict, material: int | None) -> dict[tuple[int, int, int], int]:
    axis = node.get("axis", "y")
    angle = int(node.get("angle", 90)) % 360
    inner = evaluate_tree(_children(node, "rotate")[0], material)
    if angle == 0:
        return inner
    fn = _ROTATIONS.get((axis, angle))
    if fn is None:
        raise ValueError(f"rotate: axis={axis!r} angle={angle} no soportado (múltiplos de 90°)")
    return {fn(x, y, z): m for (x, y, z), m in inner.items()}


def _eval_array(node: dict, material: int | None) -> dict[tuple[int, int, int], int]:
    count = int(node.get("count", 1))
    step = node.get("step", [1, 0, 0])
    if not isinstance(step, (list, tuple)) or len(step) != 3:
        raise ValueError("array requires 'step': [dx,dy,dz]")
    sx, sy, sz = (int(v) for v in step)
    base = evaluate_tree(_children(node, "array")[0], material)
    out: dict[tuple[int, int, int], int] = {}
    for i in range(count):
        for (x, y, z), m in base.items():
            out[(x + sx * i, y + sy * i, z + sz * i)] = m
    return out


def _eval_radial(node: dict, material: int | None) -> dict[tuple[int, int, int], int]:
    count = int(node.get("count", 4))
    radius = float(node.get("radius", 2.0))
    base = evaluate_tree(_children(node, "radial")[0], material)
    out: dict[tuple[int, int, int], int] = {}
    for i in range(count):
        angle = 2 * math.pi * i / count
        dx = round(radius * math.cos(angle))
        dz = round(radius * math.sin(angle))
        rot_angle = int(round(360 * i / count)) % 360
        fn = _ROTATIONS.get(("y", rot_angle))
        for (x, y, z), m in base.items():
            if fn is not None:
                x, y, z = fn(x, y, z)
            out[(x + dx, y, z + dz)] = m
    return out


def evaluate_tree(node: dict, material: int | None = None) -> dict[tuple[int, int, int], int]:
    """Evalúa un nodo CSG a un mapa de bloques en coordenadas locales."""
    if not isinstance(node, dict):
        raise ValueError("CSG node must be an object")
    op = node.get("op")
    if op is None:
        raise ValueError("CSG node missing 'op'")
    if op in PRIMITIVES:
        return _eval_primitive(op, node, material)
    if op in BOOLEANS:
        return _eval_boolean(op, node, material)
    if op == "at":
        return _eval_translate(node, material)
    if op == "rotate":
        return _eval_rotate(node, material)
    if op == "array":
        return _eval_array(node, material)
    if op == "radial":
        return _eval_radial(node, material)
    raise ValueError(f"unknown op: {op!r}")


def validate_tree(node: dict, material: int | None = None) -> None:
    """Valida un árbol CSG estructuralmente. Lanza ValueError con mensaje claro."""
    if not isinstance(node, dict):
        raise ValueError("CSG node must be an object")
    op = node.get("op")
    if op is None:
        raise ValueError("CSG node missing 'op'")
    if op not in VALID_OPS:
        raise ValueError(f"unknown op: {op!r}")

    if op in PRIMITIVES:
        _resolve_material(node, material)
        if op == "box":
            size = node.get("size")
            if not isinstance(size, (list, tuple)) or len(size) != 3:
                raise ValueError("box requires size: [w,h,d]")
        elif op == "sphere":
            if not isinstance(node.get("radius", 1.0), (int, float)):
                raise ValueError("sphere requires numeric radius")
        elif op == "cylinder":
            if not isinstance(node.get("radius", 1.0), (int, float)):
                raise ValueError("cylinder requires numeric radius")
        elif op == "pyramid":
            if not isinstance(node.get("height", 4), (int, float)):
                raise ValueError("pyramid requires numeric height")

    elif op in BOOLEANS:
        children = _children(node, op)
        if len(children) < 2:
            raise ValueError(f"{op} requires at least 2 children")
        for child in children:
            validate_tree(child, material)

    elif op == "at":
        at = node.get("at")
        if not isinstance(at, (list, tuple)) or len(at) != 3:
            raise ValueError("at requires 'at': [dx,dy,dz]")
        validate_tree(_children(node, "at")[0], material)

    elif op == "rotate":
        axis = node.get("axis", "y")
        angle = int(node.get("angle", 90)) % 360
        if angle != 0 and (axis, angle) not in _ROTATIONS:
            raise ValueError(f"rotate: axis={axis!r} angle={angle} no soportado (múltiplos de 90°)")
        validate_tree(_children(node, "rotate")[0], material)

    elif op == "array":
        step = node.get("step", [1, 0, 0])
        if not isinstance(step, (list, tuple)) or len(step) != 3:
            raise ValueError("array requires 'step': [dx,dy,dz]")
        validate_tree(_children(node, "array")[0], material)

    elif op == "radial":
        validate_tree(_children(node, "radial")[0], material)


def aabb(cells: dict[tuple[int, int, int], int]) -> dict:
    """Caja envolvente de un mapa de bloques (coordenadas locales)."""
    if not cells:
        return {"min": [0, 0, 0], "max": [0, 0, 0], "size": [0, 0, 0]}
    xs = [c[0] for c in cells]
    ys = [c[1] for c in cells]
    zs = [c[2] for c in cells]
    return {
        "min": [min(xs), min(ys), min(zs)],
        "max": [max(xs), max(ys), max(zs)],
        "size": [max(xs) - min(xs) + 1, max(ys) - min(ys) + 1, max(zs) - min(zs) + 1],
    }
