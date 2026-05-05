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
    email = os.environ.get("VINTED_EMAIL")
    password = os.environ.get("VINTED_PASSWORD")
    domain = os.environ.get("VINTED_DOMAIN", "fr")
    interval = int(os.environ.get("CHECK_INTERVAL_SECONDS", "300"))

    if not email or not password:
        logger.error("Variables manquantes : VINTED_EMAIL et VINTED_PASSWORD sont requis.")
        sys.exit(1)

    from src.vinted_client import VintedClient, VintedAuthError
    from src.bot import VintedBot

    try:
        client = VintedClient(email, password, domain)
    except VintedAuthError as exc:
        logger.error(f"Échec de l'authentification : {exc}")
        sys.exit(1)

    bot = VintedBot(client, check_interval=interval)
    bot.run()


if __name__ == "__main__":
    main()
