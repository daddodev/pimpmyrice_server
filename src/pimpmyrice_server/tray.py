import os
import signal
from importlib import resources
from threading import Thread
from typing import Any

import psutil
from PIL import Image
from pystray import Icon, Menu, MenuItem

from pimpmyrice_server import assets


class TrayIcon:
    def __init__(self) -> None:
        self.process = psutil.Process()
        self.icon = get_pystray_icon()
        self.icon_thread = Thread(target=self.icon.run)

    def __enter__(self) -> None:
        self.icon_thread.start()

    def __exit__(self, *_: Any) -> None:
        self.icon.stop()


def get_pystray_icon() -> Icon:
    def stop_server() -> None:
        os.kill(os.getpid(), signal.SIGTERM)

    menu = Menu(
        MenuItem("stop server", stop_server),
    )

    icon_t = resources.files(assets) / "pimp.ico"
    with resources.as_file(icon_t) as f:
        icon_path = f

    icon = Icon(
        name="PimpMyRice server",
        title="PimpMyRice server",
        icon=Image.open(icon_path),
        menu=menu,
    )

    return icon
