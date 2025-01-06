import asyncio
import json
from pathlib import Path
from typing import Any, AsyncGenerator

import requests
import uvicorn
from fastapi import APIRouter, FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.routing import APIRoute
from pimpmyrice.args import process_args
from pimpmyrice.config import SERVER_PID_FILE
from pimpmyrice.logger import LogLevel, get_logger
from pimpmyrice.theme import ThemeManager
from pimpmyrice.theme_utils import Theme, ThemeConfig
from pimpmyrice.utils import Lock

from .files import ConfigDirWatchdog

log = get_logger(__name__)


class ConnectionManager:
    def __init__(self) -> None:
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket) -> None:
        await websocket.send_text(message)

    async def broadcast(self, message: str | dict[str, Any]) -> None:
        if isinstance(message, dict):
            message = json.dumps(message)
        for connection in self.active_connections:
            await connection.send_text(message)


def custom_generate_unique_id(route: APIRoute) -> str:
    return f"{route.name}"


async def run_server() -> None:
    tm = ThemeManager()
    app = FastAPI(generate_unique_id_function=custom_generate_unique_id)
    manager = ConnectionManager()
    v1_router = APIRouter()

    async def broadcast_config() -> None:
        await manager.broadcast(
            json.dumps({"type": "config_changed", "config": vars(tm.config)})
        )

    tm.event_handler.subscribe(
        "theme_applied",
        broadcast_config,
    )

    @v1_router.websocket("/ws/{client_id}")
    async def websocket_endpoint(websocket: WebSocket, client_id: int) -> None:
        await manager.connect(websocket)
        await manager.send_personal_message(
            json.dumps({"type": "config_changed", "config": vars(tm.config)}), websocket
        )
        try:
            while True:
                data = await websocket.receive_text()
                print(data)
        except WebSocketDisconnect:
            manager.disconnect(websocket)

    @v1_router.get("/tags")
    async def get_tags() -> list[str]:
        tags = [t for t in tm.tags]
        return tags

    @v1_router.get("/current_theme")
    async def get_current_theme() -> Theme | None:
        if not tm.config.theme:
            return None
        theme = tm.themes[tm.config.theme]
        return theme

    @v1_router.put("/current_theme")
    async def set_theme(name: str | None = None, random: str | None = None) -> str:
        if random is None:
            res = await tm.apply_theme(theme_name=name)
        else:
            res = await tm.set_random_theme(name_includes=name)

        msg = {
            "event": "theme_applied",
            "config": vars(tm.config),
            "result": res.dump(),
        }

        json_str = json.dumps(msg)

        return json_str

    @v1_router.get("/theme/{name}")
    async def get_theme(request: Request, name: str) -> Theme:
        theme = tm.themes[name]
        return theme

    @v1_router.get("/themes")
    async def get_themes(request: Request) -> dict[str, Theme]:
        themes = tm.themes

        return themes

    @v1_router.get("/image")
    async def get_image(request: Request, path: str) -> FileResponse:
        file_path = Path(path)

        if not file_path.is_file():
            raise FileNotFoundError(path)

        return FileResponse(file_path)

    @v1_router.get("/base_style")
    async def get_base_style(request: Request) -> dict[str, Any]:
        keywords = tm.base_style
        return keywords

    @v1_router.post("/cli_command")
    async def cli_command(req: Request) -> StreamingResponse:
        req_json = await req.json()

        result = await process_args(tm, req_json)

        msg = {
            "event": "command_executed",
            "config": vars(tm.config),
            "result": result.dump(),
        }

        # TO DO

        async def content() -> AsyncGenerator[str, None]:
            for i, record in enumerate(result.records):
                yield json.dumps({"chunk": i, "data": record.dump()}) + "\n"
                # await asyncio.sleep(0.1)

        stream = StreamingResponse(
            content(),
            status_code=200,
            headers=None,
            media_type=None,
            background=None,
        )

        return stream

        # json_str = json.dumps(msg)

        # return json_str

    app.include_router(v1_router, prefix="/v1")

    config = uvicorn.Config(app, port=5000, host="localhost")
    server = uvicorn.Server(config)

    with Lock(SERVER_PID_FILE), ConfigDirWatchdog(tm):
        await server.serve()
