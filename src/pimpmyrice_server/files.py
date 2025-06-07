from __future__ import annotations

import asyncio
import logging
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any, Awaitable

from pimpmyrice.config_paths import (
    BASE_STYLE_FILE,
    CONFIG_FILE,
    LOG_FILE,
    MODULES_DIR,
    PALETTES_DIR,
    PIMP_CONFIG_DIR,
    STYLES_DIR,
    TEMP_DIR,
    THEMES_DIR,
)
from pimpmyrice.parsers import parse_theme
from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

if TYPE_CHECKING:
    from pimpmyrice.theme import ThemeManager

log = logging.getLogger(__name__)


class ConfigDirWatchdog(FileSystemEventHandler):
    def __init__(self, tm: ThemeManager) -> None:
        self.observer = Observer()
        self.tm = tm
        self.debounce_table: dict[str, float] = {}
        self.loop = asyncio.new_event_loop()

    def on_any_event(self, event: FileSystemEvent) -> None:
        try:
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

            elif path.name == "theme.json" and path.parents[1] == THEMES_DIR:
                theme_name = path.parent.name
                if event.event_type == "modified":
                    self.tm.themes[theme_name] = self.tm.parse_theme(path.parent)
                    log.info(f'theme "{theme_name}" loaded')

                    if self.tm.config.theme == theme_name:
                        self.run_async(self.tm.apply_theme())
                elif event.event_type == "deleted":
                    self.tm.themes.pop(theme_name)
                    log.info(f'theme "{theme_name}" deleted')

            elif MODULES_DIR in path.parents:
                if (
                    path.suffix == ".j2"
                    or path.name
                    in (
                        "module.yaml",
                        "module.json",
                    )
                ) or "templates" in path.parts:
                    if event.event_type == "modified":
                        module_dir = (
                            MODULES_DIR / path.relative_to(MODULES_DIR).parts[0]
                        )
                        log.debug(f"reloading {module_dir.name} for", event)
                        self.tm.mm.load_module(module_dir)
                        module = self.tm.mm.modules.get(module_dir.name, None)

                        if module and module.enabled:
                            self.run_async(
                                self.tm.apply_theme(include_modules=[module.name])
                            )

        except Exception as e:
            log.exception(e)
            log.error("^")

    def run_async(self, f: Awaitable[Any]) -> None:
        self.loop.run_until_complete(f)

    def __enter__(self) -> None:
        logging.getLogger("watchdog.observers.inotify_buffer").setLevel(logging.WARNING)
        self.observer.schedule(self, PIMP_CONFIG_DIR, recursive=True)
        self.observer.start()

    def __exit__(self, *_: Any) -> None:
        self.observer.stop()
        self.observer.join()
