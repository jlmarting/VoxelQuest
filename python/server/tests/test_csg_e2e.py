"""Tests e2e de las tools MCP CSG (propuesta 004, Fase 2)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from server.engine.game_loop import GameLoop
from server.engine.world import World
from server.mcp.server import McpServer, McpError

HOUSE_TREE = {
    "op": "union",
    "children": [
        {
            "op": "subtract",
            "children": [
                {"op": "box", "size": [7, 3, 7], "material": "cobblestone"},
                {"op": "box", "size": [5, 3, 5], "material": "air"},
            ],
        },
        {
            "op": "at",
            "at": [0, -1, 0],
            "children": [{"op": "box", "size": [5, 1, 5], "material": "planks"}],
        },
    ],
}


@pytest.fixture
def mcp():
    game = GameLoop(World(flat_mode=1))
    game.add_player(1)
    return McpServer(game)


# ---------------------------------------------------------------------------
# preview_csg
# ---------------------------------------------------------------------------

async def test_preview_csg_returns_metrics(mcp):
    r = await mcp.tool_preview_csg({"tree": HOUSE_TREE})
    assert r["success"] is True
    assert r["blocks"] == 147 - 75 + 25  # paredes + cimentación - interior
    assert r["aabb"]["size"] == [7, 3, 7]
    assert 8 in r["materials"]  # cobblestone
    assert 9 in r["materials"]  # planks


async def test_preview_csg_invalid_tree(mcp):
    with pytest.raises(McpError):
        await mcp.tool_preview_csg({"tree": {"op": "nope"}})


async def test_preview_csg_requires_tree(mcp):
    with pytest.raises(McpError):
        await mcp.tool_preview_csg({})


# ---------------------------------------------------------------------------
# build_csg (grid)
# ---------------------------------------------------------------------------

async def test_build_csg_grid_places_blocks(mcp):
    r = await mcp.tool_build_csg({"tree": HOUSE_TREE, "position": [10, 20, 10]})
    assert r["success"] is True
    assert r["blocks_placed"] == 147 - 75 + 25
    # Un bloque de pared exterior (dz=-3 desde el centro)
    assert mcp.game_loop.world.get_block(10, 21, 7) == 8  # cobblestone
    # Interior hueco
    assert mcp.game_loop.world.get_block(10, 21, 10) == 0  # air
    # Cimentación
    assert mcp.game_loop.world.get_block(10, 19, 10) == 9  # planks


async def test_build_csg_requires_position(mcp):
    with pytest.raises(McpError):
        await mcp.tool_build_csg({"tree": HOUSE_TREE})


# ---------------------------------------------------------------------------
# build_csg (sculpture)
# ---------------------------------------------------------------------------

async def test_build_csg_sculpture_creates_object(mcp):
    tree = {"op": "sphere", "radius": 1.0, "material": 1}
    r = await mcp.tool_build_csg({
        "tree": tree,
        "position": [5, 30, 5],
        "target": "sculpture",
        "resolution": 2,
        "color": 0xFF0000,
    })
    assert r["success"] is True
    assert r["target"] == "sculpture"
    assert r["voxel_count"] > 0
    obj = mcp.game_loop.object_manager.get(r["object_id"])
    assert obj is not None
    assert obj.kind == "sculpture"


# ---------------------------------------------------------------------------
# list_csg_structures / build_csg_named
# ---------------------------------------------------------------------------

async def test_list_csg_structures(mcp, tmp_path):
    d = tmp_path / "structures"
    d.mkdir()
    (d / "casa.json").write_text(json.dumps({"tree": HOUSE_TREE}))
    mcp._csg_structures_dir = lambda: d
    r = await mcp.tool_list_csg_structures({})
    assert "casa" in r["structures"]


async def test_build_csg_named(mcp, tmp_path):
    d = tmp_path / "structures"
    d.mkdir()
    (d / "casa.json").write_text(json.dumps({"tree": HOUSE_TREE}))
    mcp._csg_structures_dir = lambda: d
    r = await mcp.tool_build_csg_named({"name": "casa", "position": [0, 20, 0]})
    assert r["success"] is True
    assert r["blocks_placed"] == 147 - 75 + 25


async def test_build_csg_named_unknown(mcp):
    with pytest.raises(McpError, match="unknown csg structure"):
        await mcp.tool_build_csg_named({"name": "no_existe", "position": [0, 0, 0]})


# ---------------------------------------------------------------------------
# definitions.json
# ---------------------------------------------------------------------------

def test_csg_tools_in_definitions():
    defs_path = Path(__file__).resolve().parent.parent.parent.parent / "shared" / "tools" / "definitions.json"
    with open(defs_path) as f:
        defs = json.load(f)
    for name in ("build_csg", "preview_csg", "list_csg_structures", "build_csg_named"):
        assert name in defs["tools"]
        assert "python" in defs["tools"][name]["servers"]
        assert defs["tools"][name]["category"] == "building"


def test_csg_tools_in_tools_list(mcp):
    names = [t["name"] for t in mcp.list_tools()]
    for name in ("build_csg", "preview_csg", "list_csg_structures", "build_csg_named"):
        assert name in names
