"""
See https://pimpmyrice.vercel.app/docs for more info.

Usage:
    pimp-server start [--daemon] [options]
    pimp-server stop [options]
    pimp-server info [options]

Options:
    --verbose -v
"""

import logging
import os
import signal
import subprocess
import sys
from importlib.metadata import version

from docopt import DocoptExit, docopt  # type:ignore
from pimpmyrice.config import SERVER_PID_FILE
from pimpmyrice.logger import get_logger
from pimpmyrice.module_utils import run_shell_command_detached
from pimpmyrice.utils import is_locked

from pimpmyrice_server.api import run_server
from pimpmyrice_server.tray import TrayIcon

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
        log.info(f"🍙 PimpMyRice server {version('pimpmyrice_server')}")

    # TODO
    # elif args["attach"]:

    elif args["start"]:
        if server_running:
            log.error("server already running")

        elif args["--daemon"]:
            log.debug("starting server daemon")

            run_shell_command_detached(f"pimp-server start {' '.join(sys.argv)}")

            if sys.platform == "win32":
                # Relaunch using CREATE_NEW_PROCESS_GROUP to fully detach
                subprocess.Popen(
                    [sys.executable] + sys.argv,
                    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
                )
            else:
                # On Unix-like systems, fork and detach
                sys.argv.remove("--daemon")
                subprocess.Popen(
                    [sys.executable] + sys.argv,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    preexec_fn=os.setpgrp,
                )

            log.info("server started in the background")

        else:
            with TrayIcon():
                await run_server()

    elif args["stop"]:
        if server_running:
            os.kill(server_pid, signal.SIGTERM)
            log.info("server stopped")
        else:
            log.error("server not running")
