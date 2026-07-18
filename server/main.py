"""Punto de entrada del servidor VoxelQuest Python."""

import argparse
import asyncio

from fastapi import FastAPI, Request, WebSocket
from fastapi.responses import JSONResponse
from uvicorn import Config, Server

from server.engine.game_loop import GameLoop
from server.engine.world import World
from server.mcp.server import McpServer
from server.websocket.game import GameConnectionManager


def create_app() -> FastAPI:
    app = FastAPI(title="VoxelQuest Server", version="0.1.0")

    world = World(seed=12345)
    game_loop = GameLoop(world)
    ws_manager = GameConnectionManager(game_loop)
    mcp_server = McpServer(game_loop)

    # El game loop reenvía estado por WebSocket
    game_loop.on_state_update = lambda state: asyncio.create_task(ws_manager.broadcast(state))

    @app.on_event("startup")
    async def startup():
        asyncio.create_task(game_loop.run())

    @app.on_event("shutdown")
    async def shutdown():
        game_loop.stop()

    @app.get("/health")
    async def health():
        return {
            "status": "ok",
            "players": len(game_loop.players),
            "tick": game_loop.tick_count,
        }

    @app.websocket("/ws")
    async def game_websocket(websocket: WebSocket):
        client_id = await ws_manager.connect(websocket)
        try:
            await ws_manager.receive_loop(client_id, websocket)
        finally:
            ws_manager.disconnect(client_id)

    @app.post("/mcp")
    async def mcp_endpoint(request: Request):
        body = await request.json()
        response = await mcp_server.handle(body)
        if response is None:
            return JSONResponse(content={}, status_code=200)
        return JSONResponse(content=response)

    return app


app = create_app()


def main():
    parser = argparse.ArgumentParser(description="VoxelQuest Python Server")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=9000)
    args = parser.parse_args()

    config = Config(app=app, host=args.host, port=args.port, log_level="info")
    server = Server(config)
    asyncio.run(server.serve())


if __name__ == "__main__":
    main()
