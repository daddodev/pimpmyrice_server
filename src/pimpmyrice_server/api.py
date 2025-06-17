import asyncio
import json
import logging
from pathlib import Path
from typing import Any, AsyncGenerator, Awaitable, Callable

import uvicorn
from fastapi import APIRouter, FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.routing import APIRoute
from pimpmyrice.args import process_args
from pimpmyrice.config_paths import SERVER_PID_FILE
from pimpmyrice.logger import request_id, serialize_logrecord
from pimpmyrice.theme import ThemeManager
from pimpmyrice.theme_utils import Theme, ThemeConfig
from pimpmyrice.utils import Lock
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from pimpmyrice_server.files import ConfigDirWatchdog

log = logging.getLogger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        token = request_id.set(f"request-{id(request)}")
        try:
            response = await call_next(request)
        finally:
            request_id.reset(token)

        return response


class QueueHandler(logging.Handler):
    def __init__(self, req_id: int, queue: asyncio.Queue[logging.LogRecord]) -> None:
        super().__init__()
        self.queue = queue
        self.request_id = req_id

    def emit(self, record: logging.LogRecord) -> None:
        if hasattr(record, "request_id") and record.request_id == self.request_id:
            asyncio.create_task(self.queue.put(record))


async def with_end_log(fn: Awaitable[Any]) -> None:
    try:
        await fn
    except Exception as e:
        log.debug("exception:", exc_info=e)
        log.error(str(e))
    log.info("QUEUE_DONE")


class ConnectionManager:
    def __init__(self) -> None:
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active_connections.append(websocket)
        print(f"{self.active_connections=}")

    def disconnect(self, websocket: WebSocket) -> None:
        self.active_connections.remove(websocket)
        print(f"{self.active_connections=}")

    async def send_personal_message(self, message: str, websocket: WebSocket) -> None:
        await websocket.send_text(message)
        print(f"{self.active_connections=}")

    async def broadcast(self, message: str | dict[str, Any]) -> None:
        print(f"{self.active_connections=}")
        if isinstance(message, dict):
            message = json.dumps(message)
        for connection in self.active_connections:
            print(f"{message}")
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
            pass  # Normal disconnect
        except Exception as e:
            log.error(f"Unexpected WebSocket error: {e}", exc_info=True)
        finally:
            manager.disconnect(websocket)

    @v1_router.get("/tags")
    async def get_tags() -> list[str]:
        tags = [t for t in tm.tags]
        return tags

    @v1_router.get("/current_theme")
    async def get_current_theme() -> Theme:
        if not tm.config.theme:
            return None
        theme = tm.themes[tm.config.theme]
        return theme

    @v1_router.get("/config")
    async def get_config() -> ThemeConfig:
        return tm.config

    @v1_router.put("/current_theme")
    async def set_theme(name: str | None = None, random: str | None = None, mode: str | None = None) -> str:
        if random is None:
            await tm.apply_theme(theme_name=name, mode_name=mode)
        else:
            await tm.set_random_theme(name_includes=name, mode_name=mode)

        msg = {"event": "theme_applied", "config": vars(tm.config)}

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

        queue: asyncio.Queue[logging.LogRecord] = asyncio.Queue()

        log_handler = QueueHandler(request_id.get(), queue)
        # log_handler.setFormatter(formatter)
        logging.getLogger().addHandler(log_handler)
        # TODO remove handler

        async def log_generator() -> AsyncGenerator[str, None]:
            try:
                while True:
                    log_record = await queue.get()
                    if "QUEUE_DONE" in log_record.getMessage():
                        break
                    serialized = serialize_logrecord(log_record)
                    yield serialized
            except asyncio.CancelledError:
                # print("canceled")
                pass
            finally:
                logging.getLogger().removeHandler(log_handler)

        stream = StreamingResponse(
            log_generator(),
            status_code=200,
            headers=None,
            media_type=None,
            background=None,
        )

        asyncio.create_task(with_end_log(process_args(tm, req_json)))

        return stream

    @v1_router.get("/modules")
    async def get_modules() -> dict[str, Any]:
        """Get all modules and their states"""
        return {name: module.model_dump() for name, module in tm.mm.modules.items()}

    @v1_router.post("/modules/clone")
    async def clone_module(source: str | list[str]) -> dict[str, Any]:
        """Clone a module from a source (git URL, local path, or pimp:// URL)"""
        await tm.mm.clone_module(source)
        return {"status": "success", "message": f"Module(s) cloned successfully"}

    @v1_router.post("/modules/create")
    async def create_module(module_name: str) -> dict[str, Any]:
        """Create a new module with the given name"""
        await tm.mm.create_module(module_name)
        return {"status": "success", "message": f"Module {module_name} created successfully"}

    @v1_router.delete("/modules/{module_name}")
    async def delete_module(module_name: str) -> dict[str, Any]:
        """Delete a module by name"""
        await tm.mm.delete_module(module_name)
        return {"status": "success", "message": f"Module {module_name} deleted successfully"}

    @v1_router.post("/modules/{module_name}/init")
    async def init_module(module_name: str) -> dict[str, Any]:
        """Initialize a module by name"""
        await tm.mm.init_module(module_name)
        return {"status": "success", "message": f"Module {module_name} initialized successfully"}

    @v1_router.post("/modules/{module_name}/command/{command_name}")
    async def run_module_command(
        module_name: str,
        command_name: str,
        request: Request
    ) -> dict[str, Any]:
        """Run a specific command on a module"""
        cmd_args = await request.json()
        await tm.mm.run_module_command(
            tm,
            module_name=module_name,
            command=command_name,
            **cmd_args
        )
        return {
            "status": "success",
            "message": f"Command {command_name} executed on module {module_name} successfully"
        }

    @v1_router.post("/modules/rewrite")
    async def rewrite_modules(name_includes: str | None = None) -> dict[str, Any]:
        """Rewrite module configuration files"""
        await tm.mm.rewrite_modules(name_includes)
        return {
            "status": "success",
            "message": "Modules rewritten successfully"
        }

    app.include_router(v1_router, prefix="/v1")
    app.add_middleware(LoggingMiddleware)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    config = uvicorn.Config(app, port=5000, host="localhost")
    server = uvicorn.Server(config)

    with Lock(SERVER_PID_FILE), ConfigDirWatchdog(tm):
        await server.serve()
