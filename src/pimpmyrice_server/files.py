from __future__ import annotations

import asyncio
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any, Awaitable

from pimpmyrice.config import (ALBUMS_DIR, BASE_STYLE_FILE, CONFIG_FILE,
                               LOG_FILE, MODULES_DIR, PALETTES_DIR,
                               PIMP_CONFIG_DIR, STYLES_DIR, TEMP_DIR)
from pimpmyrice.keywords import base_style
from pimpmyrice.logger import get_logger
from pimpmyrice.utils import Result
from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

if TYPE_CHECKING:
    from pimpmyrice.theme import ThemeManager

log = get_logger(__name__)


class ConfigDirWatchdog(FileSystemEventHandler):
    def __init__(self, tm: ThemeManager) -> None:
        self.observer = Observer()
        self.tm = tm
        self.debounce_table: dict[str, float] = {}
        self.loop = asyncio.new_event_loop()

    def on_any_event(self, event: FileSystemEvent) -> None:
        path = Path(event.src_path)

        event_id = f"{event.src_path}:{event.event_type}"
        if event_id in self.debounce_table:
            time_passed = time.time() - self.debounce_table[event_id]
            if time_passed < 2:
                return

        self.debounce_table[event_id] = time.time()

        if path == BASE_STYLE_FILE and (
            event.event_type == "modified" or event.event_type == "created"
        ):
            log.info("reloading base_style.json")
            self.tm.base_style = self.tm.get_base_style()
            self.run_async(self.tm.apply_theme())

        elif path.parent == ALBUMS_DIR and event.is_directory:
            album_name = path.name
            if event.event_type == "created":
                self.tm.albums[album_name] = {}
                log.info(f'album "{album_name}" created')
            elif event.event_type == "deleted":
                self.tm.albums.pop(album_name)
                log.info(f'album "{album_name}" deleted')
            elif hasattr(event, "dest_path"):
                new_album_name = Path(event.dest_path).name
                self.tm.albums[new_album_name] = self.tm.get_themes(
                    Path(event.dest_path)
                )
                self.tm.albums.pop(album_name)
                log.info(f'album "{album_name}" renamed to "{new_album_name}"')

                if self.tm.config.album == album_name:
                    self.tm.config.album = new_album_name

        elif path.name == "theme.json" and path.parents[2] == ALBUMS_DIR:
            theme_name = path.parent.name
            album_name = path.parents[1].name
            if event.event_type == "modified":
                self.tm.albums[album_name][theme_name] = self.tm.get_theme(path.parent)
                log.info(f'theme "{theme_name}" in album {album_name} loaded')

                if (
                    self.tm.config.theme == theme_name
                    and self.tm.config.album == album_name
                ):
                    self.run_async(self.tm.apply_theme())
            elif event.event_type == "deleted":
                self.tm.albums[album_name].pop(theme_name)
                log.info(f'theme "{theme_name}" in album {album_name} deleted')

        elif path.name == "module.yaml" and path.parents[1] == MODULES_DIR:
            module_name = path.parent.name
            if event.event_type == "modified":
                self.tm.mm.load_module(module_name)

    def run_async(self, f: Awaitable[Any]) -> None:
        self.loop.run_until_complete(f)

    def __enter__(self) -> None:
        self.observer.schedule(self, PIMP_CONFIG_DIR, recursive=True)
        self.observer.start()

    def __exit__(self, *_: Any) -> None:
        self.observer.stop()
        self.observer.join()
