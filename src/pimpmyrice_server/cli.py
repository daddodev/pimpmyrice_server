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
from pimpmyrice.config_paths import SERVER_PID_FILE
from pimpmyrice.module_utils import run_shell_command_detached, run_shell_command
from pimpmyrice.utils import is_locked

from pimpmyrice_server.api import run_server

log = logging.getLogger(__name__)


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

            sys.argv.remove("--daemon")

            if sys.platform == "win32":
                subprocess.Popen(
                    [sys.executable] + sys.argv,
                    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
                )
            else:
                subprocess.Popen(
                    [sys.executable] + sys.argv,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    preexec_fn=os.setpgrp,
                )

            log.info("server started in the background")
        else:
            try:
                from pimpmyrice_server.tray import TrayIcon

                tray_icon = TrayIcon()
                with tray_icon:
                    await run_server()
            except Exception as e:
                log.debug("exception:", exc_info=e)
                log.error("error starting tray icon")
                await run_server()

    elif args["stop"]:
        if server_running:
            os.kill(server_pid, signal.SIGTERM)
            log.info("server stopped")
        else:
            log.error("server not running")
