"""
Usage:
    pimp_server start [options]
    pimp_server stop [options]
    pimp_server info [options]

Options:
    --verbose -v

See https://pimpmyrice.vercel.app/docs for more info.
"""

import logging
import os
import signal

from docopt import DocoptExit, docopt  # type:ignore
from pimpmyrice.config import SERVER_PID_FILE
from pimpmyrice.files import check_config_dirs
from pimpmyrice.logger import get_logger
from pimpmyrice.utils import is_locked

from .api import run_server

log = get_logger(__name__)


async def cli() -> None:
    # TODO move to pimp.init
    check_config_dirs()

    try:
        args = docopt(__doc__)
    except DocoptExit:
        print(__doc__)
        return

    if args["--verbose"]:
        logging.getLogger().setLevel(logging.DEBUG)

    server_running, server_pid = is_locked(SERVER_PID_FILE)

    if args["start"]:
        if server_running:
            log.error("server already running")
        else:
            await run_server()

    elif args["stop"]:
        if server_running:
            os.kill(server_pid, signal.SIGTERM)
            log.info("server stopped")
        else:
            log.error("server not running")
