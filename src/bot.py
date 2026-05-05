import logging
import time

from .vinted_client import VintedClient
from .templates import PROMO_LIKER, KEYWORD_RESPONSES, DEFAULT_RESPONSE
from . import state

logger = logging.getLogger(__name__)

# Nb max de messages promo envoyés par cycle (anti-ban)
MAX_PROMO_PER_CYCLE = 10


class VintedBot:
    def __init__(self, client: VintedClient, check_interval: int = 300):
        self.client = client
        self.check_interval = check_interval  # secondes entre chaque cycle

    # ------------------------------------------------------------------ run

    def run(self) -> None:
        logger.info(f"Bot démarré. Cycle toutes les {self.check_interval}s.")
        while True:
            try:
                self._cycle()
            except Exception as exc:
                logger.error(f"Erreur durant le cycle : {exc}", exc_info=True)
            logger.info(f"Prochain cycle dans {self.check_interval}s...")
            time.sleep(self.check_interval)

    def _cycle(self) -> None:
        logger.info("=== Nouveau cycle ===")
        self._process_likers()
        self._process_conversations()

    # ------------------------------------------------------------------ likers

    def _process_likers(self) -> None:
        logger.info("Recherche des likers...")
        try:
            items = self.client.get_my_items()
        except Exception as exc:
            logger.error(f"Impossible de récupérer les articles : {exc}")
            return

        sent = 0
        for item in items:
            if sent >= MAX_PROMO_PER_CYCLE:
                logger.info(f"Limite de {MAX_PROMO_PER_CYCLE} messages promo atteinte pour ce cycle.")
                break
            try:
                likers = self.client.get_item_likers(item["id"])
            except Exception as exc:
                logger.warning(f"Erreur likers item {item['id']} : {exc}")
                continue

            for liker in likers:
                if sent >= MAX_PROMO_PER_CYCLE:
                    break
                user_id = liker["id"]
                item_id = item["id"]

                if state.is_liker_messaged(user_id, item_id):
                    continue  # déjà contacté

                username = liker.get("login", "")
                item_title = item.get("title", "votre article favori")
                message = PROMO_LIKER.format(username=username, item_title=item_title)

                try:
                    result = self.client.start_conversation(user_id, item_id, message)
                    if result:
                        state.mark_liker_messaged(user_id, item_id)
                        logger.info(
                            f"Message promo envoyé à {username} pour « {item_title} »"
                        )
                        sent += 1
                        self.client.safe_delay(30, 90)
                except Exception as exc:
                    logger.warning(
                        f"Impossible d'envoyer le message à {username} : {exc}"
                    )

        logger.info(f"{sent} message(s) promo envoyé(s) ce cycle.")

    # ------------------------------------------------------------------ conversations

    def _process_conversations(self) -> None:
        logger.info("Vérification des conversations...")
        try:
            conversations = self.client.get_conversations()
        except Exception as exc:
            logger.error(f"Impossible de récupérer les conversations : {exc}")
            return

        for conv in conversations:
            conv_id = conv["id"]

            if state.is_conversation_replied(conv_id):
                continue

            # Vérifier que le dernier message vient de l'autre personne
            last_msg = conv.get("last_message") or {}
            sender_id = last_msg.get("user_id") or last_msg.get("sender_id")
            if sender_id == self.client.user_id:
                continue  # dernier message = nous → pas de réponse auto

            msg_body = last_msg.get("body", "")
            response = self._pick_response(msg_body)

            try:
                self.client.reply(conv_id, response)
                state.mark_conversation_replied(conv_id)
                logger.info(f"Réponse automatique envoyée dans conversation {conv_id}")
                self.client.safe_delay(10, 30)
            except Exception as exc:
                logger.warning(f"Erreur réponse conversation {conv_id} : {exc}")

    # ------------------------------------------------------------------ helpers

    def _pick_response(self, text: str) -> str:
        text_lower = text.lower()
        for keyword, response in KEYWORD_RESPONSES.items():
            if keyword in text_lower:
                return response
        return DEFAULT_RESPONSE
