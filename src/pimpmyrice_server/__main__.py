import asyncio
import logging

from pimpmyrice_server.cli import cli

log = logging.getLogger(__name__)


def main() -> None:
    try:
        asyncio.run(cli())
    except KeyboardInterrupt:
        log.info("server stopped")


if __name__ == "__main__":
    main()
