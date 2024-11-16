import os
import signal
from importlib import resources
from threading import Thread

from PIL import Image
from pystray import Icon, Menu, MenuItem

from . import assets


def stop_server() -> None:
    os.kill(os.getpid(), signal.SIGTERM)


def start_tray_icon() -> Icon:
    menu = Menu(MenuItem("stop server", stop_server))

    icon_t = resources.files(assets) / "pimp.ico"
    with resources.as_file(icon_t) as f:
        icon_path = f

    icon = Icon(
        name="PimpMyRice server",
        title="PimpMyRice server",
        icon=Image.open(icon_path),
        menu=menu,
    )

    t = Thread(target=icon.run)
    t.start()

    return icon
