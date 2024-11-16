"""
See https://pimpmyrice.vercel.app/docs for more info.

Usage:
    pimp-server start [options]
    pimp-server stop [options]
    pimp-server info [options]

Options:
    --verbose -v
"""

import logging
import os
import signal
from importlib.metadata import version

from docopt import DocoptExit, docopt  # type:ignore
from pimpmyrice.config import SERVER_PID_FILE
from pimpmyrice.logger import get_logger
from pimpmyrice.utils import is_locked

from .api import run_server
from .tray import start_tray_icon

log = get_logger(__name__)


async def cli() -> None:
    try:
        args = docopt(__doc__)
    except DocoptExit:
        print(__doc__)
        return

    if args["--verbose"]:
        logging.getLogger().setLevel(logging.DEBUG)

    server_running, server_pid = is_locked(SERVER_PID_FILE)

    if args["info"]:
        print(f'🍙 PimpMyRice server {version("pimpmyrice_server")}')

    elif args["start"]:
        if server_running:
            log.error("server already running")
        else:
            icon = start_tray_icon()

            await run_server()

            icon.stop()

    elif args["stop"]:
        if server_running:
            os.kill(server_pid, signal.SIGTERM)
            log.info("server stopped")
        else:
            log.error("server not running")
