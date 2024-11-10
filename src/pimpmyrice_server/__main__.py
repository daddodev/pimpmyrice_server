import asyncio

from pimpmyrice.logger import get_logger

from .cli import cli

log = get_logger(__name__)


def main() -> None:
    try:
        asyncio.run(cli())
    except KeyboardInterrupt:
        log.info("server stopped")


if __name__ == "__main__":
    main()
