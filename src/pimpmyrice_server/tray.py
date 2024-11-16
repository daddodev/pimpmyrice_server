import os
import signal
from threading import Thread

import pkg_resources
from PIL import Image
from pystray import Icon, Menu, MenuItem


def stop_server() -> None:
    os.kill(os.getpid(), signal.SIGTERM)


def start_tray_icon() -> Icon:
    menu = Menu(MenuItem("stop server", stop_server))

    icon_path = pkg_resources.resource_filename(__name__, "assets/pimp.ico")
    icon = Icon(
        name="PimpMyRice server",
        title="PimpMyRice server",
        icon=Image.open(icon_path),
        menu=menu,
    )

    t = Thread(target=icon.run)
    t.start()

    return icon
