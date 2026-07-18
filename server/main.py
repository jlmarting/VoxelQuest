"""Punto de entrada del servidor VoxelQuest Python."""

import argparse
import asyncio

from fastapi import FastAPI
from uvicorn import Config, Server

app = FastAPI(title="VoxelQuest Server", version="0.1.0")


@app.get("/health")
async def health():
    return {"status": "ok"}


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
