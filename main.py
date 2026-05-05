import logging
import os
import sys

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ],
)

logger = logging.getLogger(__name__)


def main() -> None:
    session_cookie = os.environ.get("VINTED_SESSION_COOKIE")
    domain = os.environ.get("VINTED_DOMAIN", "fr")
    interval = int(os.environ.get("CHECK_INTERVAL_SECONDS", "300"))

    if not session_cookie:
        logger.error(
            "Variable manquante : VINTED_SESSION_COOKIE est requis. "
            "Récupère ton cookie de session depuis ton navigateur (voir le guide)."
        )
        sys.exit(1)

    from src.vinted_client import VintedClient, VintedAuthError
    from src.bot import VintedBot

    try:
        client = VintedClient(session_cookie, domain)
    except VintedAuthError as exc:
        logger.error(f"Échec de l'authentification Vinted : {exc}")
        sys.exit(1)

    bot = VintedBot(client, check_interval=interval)
    bot.run()


if __name__ == "__main__":
    main()
