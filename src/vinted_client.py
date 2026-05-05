import logging
import time
import requests
from typing import Optional

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
}


class VintedAuthError(Exception):
    pass


class VintedClient:
    def __init__(self, username: str, password: str, domain: str = "fr"):
        self.base_url = f"https://www.vinted.{domain}"
        self.api = f"{self.base_url}/api/v2"
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
        self.user_id: Optional[int] = None
        self._login(username, password)

    # ------------------------------------------------------------------ auth

    def _fetch_csrf(self) -> str:
        resp = self.session.get(self.base_url, timeout=15)
        resp.raise_for_status()
        token = self.session.cookies.get("XSRF-TOKEN", "")
        if token:
            self.session.headers["X-XSRF-TOKEN"] = token
        return token

    def _login(self, username: str, password: str) -> None:
        logger.info("Connexion à Vinted en cours...")
        self._fetch_csrf()
        resp = self.session.post(
            f"{self.api}/users/login",
            json={
                "user": {
                    "login": username,
                    "password": password,
                    "remember": True,
                }
            },
            timeout=15,
        )
        if resp.status_code != 200:
            raise VintedAuthError(
                f"Échec de connexion (HTTP {resp.status_code}) : {resp.text[:200]}"
            )
        data = resp.json()
        user = data.get("user") or data.get("current_user")
        if not user:
            raise VintedAuthError(f"Réponse inattendue : {resp.text[:200]}")
        self.user_id = user["id"]
        logger.info(f"Connecté en tant que {user.get('login')} (id={self.user_id})")

    # ------------------------------------------------------------------ items

    def get_my_items(self) -> list:
        all_items, page = [], 1
        while True:
            resp = self.session.get(
                f"{self.api}/users/{self.user_id}/items",
                params={"page": page, "per_page": 96},
                timeout=15,
            )
            resp.raise_for_status()
            items = resp.json().get("items", [])
            if not items:
                break
            all_items.extend(items)
            page += 1
            if len(items) < 96:
                break
        logger.info(f"{len(all_items)} article(s) trouvé(s)")
        return all_items

    # ------------------------------------------------------------------ likers

    def get_item_likers(self, item_id: int) -> list:
        resp = self.session.get(
            f"{self.api}/items/{item_id}/item_favourite_users",
            params={"page": 1, "per_page": 100},
            timeout=15,
        )
        if resp.status_code == 404:
            return []
        resp.raise_for_status()
        return resp.json().get("users", [])

    # ------------------------------------------------------------------ conversations

    def get_conversations(self) -> list:
        resp = self.session.get(
            f"{self.api}/conversations",
            params={"page": 1, "per_page": 50},
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json().get("conversations", [])

    def get_messages(self, conv_id: int) -> list:
        resp = self.session.get(
            f"{self.api}/conversations/{conv_id}/messages",
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json().get("messages", [])

    def reply(self, conv_id: int, body: str) -> dict:
        resp = self.session.post(
            f"{self.api}/conversations/{conv_id}/messages",
            json={"message": {"body": body}},
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json()

    def start_conversation(self, to_user_id: int, item_id: int, body: str) -> Optional[dict]:
        resp = self.session.post(
            f"{self.api}/conversations",
            json={
                "conversation": {
                    "to_user_id": to_user_id,
                    "item_id": item_id,
                    "body": body,
                }
            },
            timeout=15,
        )
        if resp.status_code in (200, 201):
            return resp.json()
        # Conversation déjà existante : récupérer l'id depuis les headers ou la réponse
        logger.warning(
            f"Impossible de créer la conversation avec user={to_user_id} item={item_id} "
            f"(HTTP {resp.status_code})"
        )
        return None

    # ------------------------------------------------------------------ helpers

    def safe_delay(self, min_sec: float = 30, max_sec: float = 90) -> None:
        import random
        delay = random.uniform(min_sec, max_sec)
        logger.debug(f"Pause {delay:.0f}s pour éviter le rate-limit...")
        time.sleep(delay)
