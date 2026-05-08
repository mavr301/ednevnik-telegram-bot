import logging
import os

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s: %(message)s",
)


def main() -> None:
    import asyncio
    asyncio.set_event_loop(asyncio.new_event_loop())

    from bot import build_app
    app = build_app()
    logger = logging.getLogger(__name__)
    logger.info("Bot starting...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
