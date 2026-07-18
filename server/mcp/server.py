"""Endpoint MCP JSON-RPC 2.0 para controlar el juego desde agentes."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from server.engine.game_loop import GameLoop


class McpError(Exception):
    def __init__(self, code: int, message: str):
        self.code = code
        self.message = message
        super().__init__(message)


class McpServer:
    """Implementación mínima de MCP sobre JSON-RPC 2.0 por HTTP."""

    def __init__(self, game_loop: GameLoop):
        self.game_loop = game_loop

    def list_tools(self) -> list[dict]:
        return [
            {
                "name": "get_config",
                "description": "Obtener configuración actual del servidor",
                "inputSchema": {"type": "object", "properties": {}},
            },
            {
                "name": "list_players",
                "description": "Listar todos los jugadores",
                "inputSchema": {"type": "object", "properties": {}},
            },
            {
                "name": "get_player_state",
                "description": "Obtener estado de un jugador",
                "inputSchema": {
                    "type": "object",
                    "properties": {"player_id": {"type": "integer"}},
                    "required": ["player_id"],
                },
            },
            {
                "name": "place_block",
                "description": "Coloca un bloque en coordenadas absolutas",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "x": {"type": "integer"},
                        "y": {"type": "integer"},
                        "z": {"type": "integer"},
                        "type": {"type": "integer", "minimum": 0, "maximum": 10},
                    },
                    "required": ["x", "y", "z", "type"],
                },
            },
            {
                "name": "break_block",
                "description": "Rompe un bloque en coordenadas absolutas",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "x": {"type": "integer"},
                        "y": {"type": "integer"},
                        "z": {"type": "integer"},
                    },
                    "required": ["x", "y", "z"],
                },
            },
            {
                "name": "get_block",
                "description": "Obtiene el tipo de bloque en coordenadas",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "x": {"type": "integer"},
                        "y": {"type": "integer"},
                        "z": {"type": "integer"},
                    },
                    "required": ["x", "y", "z"],
                },
            },
            {
                "name": "gamepad_input",
                "description": "Inyecta input de gamepad virtual para un jugador",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "player_id": {"type": "integer"},
                        "input": {"type": "object"},
                    },
                    "required": ["player_id", "input"],
                },
            },
            {
                "name": "look",
                "description": "Rota la cámara/jugador",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "player_id": {"type": "integer"},
                        "yaw": {"type": "number"},
                        "pitch": {"type": "number"},
                    },
                    "required": ["player_id"],
                },
            },
            {
                "name": "bt_load",
                "description": "Carga un árbol de comportamiento JSON",
                "inputSchema": {
                    "type": "object",
                    "properties": {"tree": {"type": "object"}},
                    "required": ["tree"],
                },
            },
            {
                "name": "bt_status",
                "description": "Obtiene estado del árbol de comportamiento",
                "inputSchema": {"type": "object", "properties": {}},
            },
            {
                "name": "bt_stop",
                "description": "Detiene el árbol de comportamiento",
                "inputSchema": {"type": "object", "properties": {}},
            },
        ]

    async def handle(self, request: dict) -> dict | None:
        if request.get("jsonrpc") != "2.0":
            return self._error(request.get("id"), -32600, "Invalid Request: jsonrpc must be 2.0")

        method = request.get("method")
        req_id = request.get("id")
        params = request.get("params", {})

        try:
            if method == "initialize":
                return self._result(
                    req_id,
                    {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {"tools": {}},
                        "serverInfo": {"name": "VoxelQuest Python Server", "version": "0.1.0"},
                    },
                )
            elif method == "ping":
                return self._result(req_id, {})
            elif method == "tools/list":
                return self._result(req_id, {"tools": self.list_tools()})
            elif method == "tools/call":
                return await self._call_tool(req_id, params)
            elif method == "resources/list":
                return self._result(req_id, {"resources": []})
            elif method == "notifications/initialized":
                return None
            else:
                return self._error(req_id, -32601, f"Method not found: {method}")
        except McpError as e:
            return self._error(req_id, e.code, e.message)
        except Exception as e:
            return self._error(req_id, -32603, str(e))

    async def _call_tool(self, req_id: Any, params: dict) -> dict:
        name = params.get("name")
        args = params.get("arguments", {})
        if not name:
            raise McpError(-32602, "Tool name required")

        handler = getattr(self, f"tool_{name}", None)
        if handler is None:
            raise McpError(-32602, f"Unknown tool: {name}")

        result = await handler(args)
        return self._result(req_id, result)

    # ---- Tools ----

    async def tool_get_config(self, args: dict) -> dict:
        return {
            "players": len(self.game_loop.players),
            "tick_rate": self.game_loop.tick_rate,
            "seed": self.game_loop.world.seed,
        }

    async def tool_list_players(self, args: dict) -> dict:
        return {"players": [p.to_dict() for p in self.game_loop.players.values()]}

    async def tool_get_player_state(self, args: dict) -> dict:
        player_id = int(args.get("player_id", 0))
        player = self.game_loop.get_player(player_id)
        if player is None:
            raise McpError(-32602, f"Player {player_id} not found")
        return player.to_dict()

    async def tool_place_block(self, args: dict) -> dict:
        x, y, z = int(args["x"]), int(args["y"]), int(args["z"])
        block_type = int(args["type"])
        self.game_loop.world.set_block(x, y, z, block_type)
        return {"success": True, "position": {"x": x, "y": y, "z": z}, "type": block_type}

    async def tool_break_block(self, args: dict) -> dict:
        from server.engine.constants import BlockType

        x, y, z = int(args["x"]), int(args["y"]), int(args["z"])
        block = self.game_loop.world.get_block(x, y, z)
        if block == BlockType.BEDROCK:
            raise McpError(-32602, "Cannot break bedrock")
        self.game_loop.world.set_block(x, y, z, BlockType.AIR)
        return {"success": True, "position": {"x": x, "y": y, "z": z}, "block_type": int(block)}

    async def tool_get_block(self, args: dict) -> dict:
        x, y, z = int(args["x"]), int(args["y"]), int(args["z"])
        block = self.game_loop.world.get_block(x, y, z)
        return {"x": x, "y": y, "z": z, "type": int(block)}

    async def tool_gamepad_input(self, args: dict) -> dict:
        player_id = int(args.get("player_id", 0))
        player = self.game_loop.get_player(player_id)
        if player is None:
            raise McpError(-32602, f"Player {player_id} not found")

        inp = args.get("input", {})
        move = inp.get("move", {})
        look = inp.get("look", {})
        player.input_move.x = max(-1, min(1, float(move.get("x", 0))))
        player.input_move.z = max(-1, min(1, float(move.get("z", 0))))
        player.input_look.x = max(-1, min(1, float(look.get("x", 0))))
        player.input_look.y = max(-1, min(1, float(look.get("y", 0))))
        if "jump" in inp:
            player.input_jump = bool(inp["jump"])
        if "fly" in inp:
            player.input_fly = bool(inp["fly"])
        return {"success": True}

    async def tool_look(self, args: dict) -> dict:
        import math

        player_id = int(args.get("player_id", 0))
        player = self.game_loop.get_player(player_id)
        if player is None:
            raise McpError(-32602, f"Player {player_id} not found")
        if "yaw" in args:
            player.rotation.y = float(args["yaw"])
        if "pitch" in args:
            player.rotation.x = max(-math.pi / 2 + 0.1, min(math.pi / 2 - 0.1, float(args["pitch"])))
        return {"success": True, "rotation": player.rotation.to_dict()}

    async def tool_bt_load(self, args: dict) -> dict:
        from server.bt.engine import BehaviorTree, create_action_catalog

        tree_json = args.get("tree")
        if not tree_json:
            raise McpError(-32602, "tree required")
        catalog = create_action_catalog(self.game_loop)
        bt = BehaviorTree(tree_json, catalog, self.game_loop.blackboard)
        if bt.error:
            raise McpError(-32602, bt.error)
        self.game_loop.bt_engine = bt
        return {"success": True, "message": "Behavior tree loaded"}

    async def tool_bt_status(self, args: dict) -> dict:
        bt = self.game_loop.bt_engine
        return {
            "running": bt is not None,
            "error": bt.error if bt else None,
            "last_result": bt.last_result.value if bt and bt.last_result else None,
            "blackboard": self.game_loop.blackboard,
        }

    async def tool_bt_stop(self, args: dict) -> dict:
        self.game_loop.bt_engine = None
        return {"success": True, "message": "Behavior tree stopped"}

    def _result(self, req_id: Any, result: Any) -> dict:
        return {"jsonrpc": "2.0", "id": req_id, "content": [{"type": "text", "text": json.dumps(result)}]}

    def _error(self, req_id: Any, code: int, message: str) -> dict:
        return {"jsonrpc": "2.0", "id": req_id, "error": {"code": code, "message": message}}


# evitar import circular de json usado en _result
import json
