"""Tests del evaluador CSG declarativo (propuesta 004, Fase 1)."""

from __future__ import annotations

import pytest

from server.engine.csg import (
    aabb,
    evaluate_tree,
    validate_tree,
    MAX_BLOCKS,
)
from server.engine.constants import BlockType


# ---------------------------------------------------------------------------
# Primitivas
# ---------------------------------------------------------------------------

def test_box_centered_size():
    cells = evaluate_tree({"op": "box", "size": [3, 1, 3], "material": "stone"})
    assert len(cells) == 9
    assert all(y == 0 for (_, y, _) in cells)
    assert all(cells[(x, 0, z)] == int(BlockType.STONE) for x in (-1, 0, 1) for z in (-1, 0, 1))


def test_box_even_size_centered():
    cells = evaluate_tree({"op": "box", "size": [4, 2, 4], "material": 3})
    assert len(cells) == 32
    xs = {c[0] for c in cells}
    assert xs == {-2, -1, 0, 1}


def test_sphere_radius():
    cells = evaluate_tree({"op": "sphere", "radius": 2.0, "material": "stone"})
    assert len(cells) > 0
    for (x, y, z) in cells:
        assert x * x + y * y + z * z <= 4.0


def test_cylinder_vertical():
    cells = evaluate_tree({"op": "cylinder", "radius": 1.0, "height": 5, "material": "stone"})
    ys = {c[1] for c in cells}
    assert ys == {-2, -1, 0, 1, 2}
    for (x, y, z) in cells:
        assert x * x + z * z <= 1.0


def test_pyramid_decreasing():
    cells = evaluate_tree({"op": "pyramid", "base": 5, "height": 5, "material": "stone"})
    assert len(cells) > 0
    ys = {c[1] for c in cells}
    assert len(ys) == 5
    top = [c for c in cells if c[1] == max(ys)]
    assert len(top) == 1


# ---------------------------------------------------------------------------
# Booleanas
# ---------------------------------------------------------------------------

def test_union_merges():
    tree = {
        "op": "union",
        "children": [
            {"op": "box", "size": [3, 1, 1], "material": "stone"},
            {"op": "box", "size": [1, 1, 3], "material": "planks"},
        ],
    }
    cells = evaluate_tree(tree)
    assert len(cells) == 5  # 3 + 3 - 1 (centro compartido)
    assert cells[(0, 0, 0)] == int(BlockType.PLANKS)  # última escritura gana


def test_subtract_removes():
    tree = {
        "op": "subtract",
        "children": [
            {"op": "box", "size": [5, 3, 5], "material": "cobblestone"},
            {"op": "box", "size": [3, 3, 3], "material": "air"},
        ],
    }
    cells = evaluate_tree(tree)
    # 5x3x5 = 75, menos 3x3x3 = 27 → 48
    assert len(cells) == 48
    assert (0, 0, 0) not in cells


def test_intersect_keeps_overlap():
    tree = {
        "op": "intersect",
        "children": [
            {"op": "box", "size": [5, 1, 5], "material": "stone"},
            {"op": "box", "size": [3, 1, 3], "material": "planks"},
        ],
    }
    cells = evaluate_tree(tree)
    assert len(cells) == 9
    # intersect conserva el material del primer operando
    assert all(cells[c] == int(BlockType.STONE) for c in cells)


# ---------------------------------------------------------------------------
# Transformaciones y repetición
# ---------------------------------------------------------------------------

def test_at_translates():
    tree = {
        "op": "at",
        "at": [10, 5, -3],
        "children": [{"op": "box", "size": [1, 1, 1], "material": "stone"}],
    }
    cells = evaluate_tree(tree)
    assert set(cells) == {(10, 5, -3)}


def test_rotate_90_y():
    tree = {
        "op": "rotate",
        "axis": "y",
        "angle": 90,
        "children": [{"op": "box", "size": [3, 1, 1], "material": "stone"}],
    }
    cells = evaluate_tree(tree)
    # El eje largo pasa de X a Z
    xs = {c[0] for c in cells}
    zs = {c[2] for c in cells}
    assert xs == {0}
    assert zs == {-1, 0, 1}


def test_array_linear():
    tree = {
        "op": "array",
        "count": 4,
        "step": [0, 0, 2],
        "children": [{"op": "box", "size": [1, 1, 1], "material": "stone"}],
    }
    cells = evaluate_tree(tree)
    zs = sorted({c[2] for c in cells})
    assert zs == [0, 2, 4, 6]


def test_radial_around_y():
    tree = {
        "op": "radial",
        "count": 4,
        "radius": 3.0,
        "children": [{"op": "box", "size": [1, 1, 1], "material": "stone"}],
    }
    cells = evaluate_tree(tree)
    assert len(cells) == 4
    for (x, y, z) in cells:
        assert round((x * x + z * z) ** 0.5) == 3


# ---------------------------------------------------------------------------
# Materiales
# ---------------------------------------------------------------------------

def test_material_by_name_and_id():
    assert evaluate_tree({"op": "box", "size": [1, 1, 1], "material": "red_brick"})[(0, 0, 0)] == int(BlockType.RED_BRICK)
    assert evaluate_tree({"op": "box", "size": [1, 1, 1], "material": 5})[(0, 0, 0)] == 5


def test_material_inherited():
    tree = {
        "op": "union",
        "children": [
            {"op": "box", "size": [1, 1, 1]},
            {"op": "at", "at": [2, 0, 0], "children": [{"op": "box", "size": [1, 1, 1], "material": "planks"}]},
        ],
    }
    cells = evaluate_tree(tree, material=int(BlockType.STONE))
    assert cells[(0, 0, 0)] == int(BlockType.STONE)
    assert cells[(2, 0, 0)] == int(BlockType.PLANKS)


# ---------------------------------------------------------------------------
# Validación y límites
# ---------------------------------------------------------------------------

def test_validate_unknown_op():
    with pytest.raises(ValueError, match="unknown op"):
        validate_tree({"op": "nope"})


def test_validate_box_requires_size():
    with pytest.raises(ValueError, match="size"):
        validate_tree({"op": "box"})


def test_validate_boolean_requires_children():
    with pytest.raises(ValueError, match="children"):
        validate_tree({"op": "union", "children": []})


def test_validate_rotate_unsupported_angle():
    with pytest.raises(ValueError, match="rotate"):
        validate_tree({"op": "rotate", "axis": "y", "angle": 45, "children": [{"op": "box", "size": [1, 1, 1]}]})


def test_validate_unknown_material():
    with pytest.raises(ValueError, match="unknown material"):
        validate_tree({"op": "box", "size": [1, 1, 1], "material": "obsidian"})


def test_aabb():
    cells = evaluate_tree({"op": "box", "size": [3, 2, 3], "material": "stone"})
    bb = aabb(cells)
    assert bb["size"] == [3, 2, 3]
    assert bb["min"] == [-1, -1, -1]
    assert bb["max"] == [1, 0, 1]


def test_max_blocks_constant():
    assert MAX_BLOCKS == 20000
