"""Gestión de WebSocket de juego: input de clientes y envío de estado."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from fastapi import WebSocket, WebSocketDisconnect

if TYPE_CHECKING:
    from server.engine.game_loop import GameLoop


class GameConnectionManager:
    """Maneja conexiones WebSocket de clientes de juego."""

    def __init__(self, game_loop: GameLoop):
        self.game_loop = game_loop
        self.connections: dict[int, WebSocket] = {}
        self.next_client_id = 1

    async def connect(self, websocket: WebSocket) -> int:
        await websocket.accept()
        client_id = self.next_client_id
        self.next_client_id += 1
        self.connections[client_id] = websocket

        # Asignar player_id según orden de conexión (1, 2, ...)
        player_id = client_id
        player = self.game_loop.add_player(player_id)

        await websocket.send_json(
            {
                "type": "welcome",
                "client_id": client_id,
                "player_id": player_id,
                "tick_rate": self.game_loop.tick_rate,
                "world": {
                    "seed": self.game_loop.world.seed,
                    "spawn": {
                        "x": player.position.x,
                        "y": player.position.y,
                        "z": player.position.z,
                    },
                },
                "constants": {
                    "CHUNK_SIZE": 16,
                    "WORLD_HEIGHT": 64,
                    "BLOCK_TYPES": {
                        "AIR": 0,
                        "GRASS": 1,
                        "DIRT": 2,
                        "STONE": 3,
                        "WOOD": 4,
                        "LEAVES": 5,
                        "SAND": 6,
                        "WATER": 7,
                        "COBBLESTONE": 8,
                    },
                },
            }
        )
        return client_id

    def disconnect(self, client_id: int) -> None:
        websocket = self.connections.pop(client_id, None)
        if websocket:
            self.game_loop.remove_player(client_id)

    async def broadcast(self, message: dict) -> None:
        data = json.dumps(message)
        for websocket in list(self.connections.values()):
            try:
                await websocket.send_text(data)
            except Exception:
                pass

    async def handle_message(self, client_id: int, raw: str) -> None:
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return

        msg_type = data.get("type")
        player_id = data.get("player_id", client_id)
        player = self.game_loop.get_player(player_id)
        if player is None:
            return

        if msg_type == "input":
            move = data.get("move", {})
            look = data.get("look", {})
            player.input_move.x = max(-1, min(1, float(move.get("x", 0))))
            player.input_move.z = max(-1, min(1, float(move.get("z", 0))))
            player.input_look.x = max(-1, min(1, float(look.get("x", 0))))
            player.input_look.y = max(-1, min(1, float(look.get("y", 0))))
            player.input_jump = bool(data.get("jump", False))
            player.input_fly = bool(data.get("fly", False))
            player.input_place_block = bool(data.get("place_block", False))
            player.input_break_block = bool(data.get("break_block", False))
            if "selected_slot" in data:
                player.selected_slot = max(0, min(8, int(data["selected_slot"])))
        elif msg_type == "ping":
            websocket = self.connections.get(client_id)
            if websocket:
                await websocket.send_json(
                    {
                        "type": "pong",
                        "server_time": data.get("client_time", 0),
                    }
                )

    async def send_chunk(self, client_id: int, chunk_data: dict) -> None:
        websocket = self.connections.get(client_id)
        if websocket:
            await websocket.send_json({"type": "chunk_full", "chunk": chunk_data})

    async def receive_loop(self, client_id: int, websocket: WebSocket) -> None:
        try:
            while True:
                raw = await websocket.receive_text()
                await self.handle_message(client_id, raw)
        except WebSocketDisconnect:
            self.disconnect(client_id)
