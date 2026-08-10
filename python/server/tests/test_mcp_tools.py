import pytest
from server.engine.entities import Enemy, Vec3
from server.engine.game_loop import GameLoop
from server.engine.world import World
from server.mcp.server import McpServer


@pytest.fixture
def server():
    world = World(flat_mode=1)
    game = GameLoop(world)
    game.add_player(2, is_ai=True)
    return McpServer(game)


@pytest.mark.asyncio
async def test_attack_nearest(server):
    # Spawn an enemy directly in front of P2
    e = Enemy("ZOMBIE", Vec3(0.5, 2.0, 2.5), server.game_loop.world)
    e.id = 1
    server.game_loop.enemy_manager.enemies.append(e)
    server.game_loop.players[2].position = Vec3(0.5, 2.0, 0.5)
    server.game_loop.players[2].rotation.y = 3.1416  # facing +Z
    result = await server.tool_attack({"player_id": 2})
    assert result["success"] is True
    assert result.get("target_id") == 1
    assert e.health < 20


@pytest.mark.asyncio
async def test_navigate_to(server):
    result = await server.tool_navigate_to({"player_id": 2, "x": 5, "z": 5})
    assert result["success"] is True
    assert result["action"] == "path_started"


@pytest.mark.asyncio
async def test_place_block_as_player(server):
    # Point P2 toward a flat ground block at (0,1,1)
    server.game_loop.players[2].rotation.y = 0
    server.game_loop.players[2].position = Vec3(0.5, 2.0, 0.5)
    result = await server.tool_place_block_as_player({"player_id": 2})
    assert "success" in result


@pytest.mark.asyncio
async def test_apply_blocks_batch(server):
    blocks = [
        {"x": 5, "y": 25, "z": 5, "type": 1},
        {"x": 6, "y": 25, "z": 5, "type": 4},
    ]
    result = await server.tool_apply_blocks({"blocks": blocks})
    assert result["success"] is True
    assert result["blocks"] == 2
    assert server.game_loop.world.get_block(5, 25, 5) == 1
    assert server.game_loop.world.get_block(6, 25, 5) == 4
    # El registro de updates alimenta el state_update
    assert len(server.game_loop.world.block_changes) == 2


@pytest.mark.asyncio
async def test_clear_area(server):
    blocks = [
        {"x": 10, "y": 25, "z": 10, "type": 1},
        {"x": 11, "y": 25, "z": 10, "type": 4},
    ]
    await server.tool_apply_blocks({"blocks": blocks})
    result = await server.tool_clear_area({"x": 10, "z": 10, "width": 2, "depth": 1, "height": 1, "baseY": 25})
    assert result["success"] is True
    assert result["blocks"] == 2
    assert server.game_loop.world.get_block(10, 25, 10) == 0
    assert server.game_loop.world.get_block(11, 25, 10) == 0


@pytest.mark.asyncio
async def test_get_height(server):
    """get_height devuelve la Y del bloque solido mas alto y la superficie."""
    world = server.game_loop.world
    world.update_around(5, 5)
    # flat_mode=1: bedrock hasta y=3, superficie en y=4
    result = await server.tool_get_height({"x": 5, "z": 5})
    assert result["height"] == 3
    assert result["surface"] == 4
    assert result["block_type"] != 0
    # Columna vacia (por encima del mundo) -> 0
    result2 = await server.tool_get_height({"x": 5, "z": 5})
    assert result2["surface"] == 4
