import logging
import os
import sys

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

logger = logging.getLogger(__name__)


def main() -> None:
    access_token = os.environ.get("VINTED_ACCESS_TOKEN")
    refresh_token = os.environ.get("VINTED_REFRESH_TOKEN")
    domain = os.environ.get("VINTED_DOMAIN", "fr")
    interval = int(os.environ.get("CHECK_INTERVAL_SECONDS", "300"))

    if not access_token or not refresh_token:
        logger.error(
            "Variables manquantes : VINTED_ACCESS_TOKEN et VINTED_REFRESH_TOKEN sont requis."
        )
        sys.exit(1)

    from src.vinted_client import VintedClient, VintedAuthError
    from src.bot import VintedBot

    try:
        client = VintedClient(access_token, refresh_token, domain)
    except VintedAuthError as exc:
        logger.error(f"Échec de l'authentification : {exc}")
        sys.exit(1)

    bot = VintedBot(client, check_interval=interval)
    bot.run()


if __name__ == "__main__":
    main()
