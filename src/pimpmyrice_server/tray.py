import os
import signal
import sys
from threading import Thread
from typing import Any
from pathlib import Path
import subprocess
import shutil
import logging
import psutil
from PIL import Image
from pystray import Icon, Menu, MenuItem

from pimpmyrice_server import assets


GUI_CMD = "pimp-tauri"
path_to_executable = shutil.which(GUI_CMD)

log = logging.getLogger(__name__)


class TrayIcon:
    def __init__(self) -> None:
        self.process = psutil.Process()
        self.icon = _get_pystray_icon()
        self.icon_thread = Thread(target=self.icon.run)

    def __enter__(self) -> None:
        self.icon_thread.start()

    def __exit__(self, *_: Any) -> None:
        self.icon.stop()

def open_gui() -> None:
    if path_to_executable is None:
        log.error(f'Error: "{GUI_CMD}" not found in PATH')
        return
    else:
        log.debug(f'using "{path_to_executable}"')
    subprocess.Popen([path_to_executable])

def _get_pystray_icon() -> Icon: # type: ignore
    def stop_server() -> None:
        os.kill(os.getpid(), signal.SIGTERM)

    items = [
        MenuItem("Open GUI", open_gui, default=True, enabled=path_to_executable is not None),
        MenuItem("stop server", stop_server),
    ]

    menu = Menu(*items)

    if getattr(sys, 'frozen', False):
        base_path = Path(sys._MEIPASS) / "assets"
    else:
        base_path = Path(__file__).parent / "assets"

    icon_path = base_path / "pimp.ico"

    icon = Icon(
        name="PimpMyRice server",
        title="PimpMyRice server",
        icon=Image.open(icon_path),
        menu=menu,

    )
    return icon