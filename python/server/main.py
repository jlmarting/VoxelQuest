"""Punto de entrada del servidor VoxelQuest Python."""

import argparse
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, WebSocket
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from uvicorn import Config, Server

from server.engine.game_loop import GameLoop
from server.engine.world import World
from server.mcp.server import McpServer
from server.websocket.game import GameConnectionManager


@asynccontextmanager
async def lifespan(app: FastAPI):
    world = World(seed=12345)
    game_loop = GameLoop(world)
    ws_manager = GameConnectionManager(game_loop)
    mcp_server = McpServer(game_loop)

    game_loop.on_state_update = lambda state: asyncio.create_task(ws_manager.broadcast(state))

    app.state.world = world
    app.state.game_loop = game_loop
    app.state.ws_manager = ws_manager
    app.state.mcp_server = mcp_server

    loop_task = asyncio.create_task(game_loop.run())

    yield

    game_loop.stop()
    loop_task.cancel()
    try:
        await loop_task
    except asyncio.CancelledError:
        pass


def create_app() -> FastAPI:
    app = FastAPI(title="VoxelQuest Server", version="0.1.0", lifespan=lifespan)

    @app.get("/health")
    async def health(request: Request):
        gl = request.app.state.game_loop
        return {
            "status": "ok",
            "players": len(gl.players),
            "tick": gl.tick_count,
        }

    @app.websocket("/ws")
    async def game_websocket(websocket: WebSocket):
        ws_manager = websocket.app.state.ws_manager
        client_id = await ws_manager.connect(websocket)
        try:
            await ws_manager.receive_loop(client_id, websocket)
        finally:
            ws_manager.disconnect(client_id)

    @app.post("/mcp")
    async def mcp_endpoint(request: Request):
        body = await request.json()
        response = await request.app.state.mcp_server.handle(body)
        if response is None:
            return JSONResponse(content={}, status_code=200)
        return JSONResponse(content=response)

    import os
    web_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'web')
    app.mount('/', StaticFiles(directory=web_dir, html=True), name='web')

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
