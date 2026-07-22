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
