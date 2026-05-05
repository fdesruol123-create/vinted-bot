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

# Endpoints connus de l'API Vinted (tentés dans l'ordre)
CURRENT_USER_ENDPOINTS = [
    "/api/v2/users/current",
    "/api/v2/profile",
]

TOKEN_REFRESH_ENDPOINTS = [
    "/api/v2/token_refresh",
    "/api/v2/auth/token_refresh",
    "/oauth/token",
]


class VintedAuthError(Exception):
    pass


def _safe_json(resp: requests.Response) -> dict:
    """Parse JSON en loggant le contenu brut si ça échoue."""
    try:
        return resp.json()
    except Exception:
        preview = resp.text[:300] if resp.text else "(réponse vide)"
        logger.error(
            f"Réponse non-JSON reçue (HTTP {resp.status_code}) "
            f"depuis {resp.url} : {preview}"
        )
        raise


class VintedClient:
    def __init__(self, access_token: str, refresh_token: str, domain: str = "fr"):
        self.domain = domain
        self.base_url = f"https://www.vinted.{domain}"
        self.api = f"{self.base_url}/api/v2"
        self._refresh_token = refresh_token
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
        self.user_id: Optional[int] = None
        self._set_token(access_token)
        self._verify()

    # ------------------------------------------------------------------ auth

    def _set_token(self, token: str) -> None:
        self.session.headers["Authorization"] = f"Bearer {token}"

    def _fetch_xsrf(self) -> None:
        try:
            resp = self.session.get(self.base_url, timeout=15)
            xsrf = self.session.cookies.get("XSRF-TOKEN", "")
            if xsrf:
                self.session.headers["X-XSRF-TOKEN"] = xsrf
        except Exception as exc:
            logger.warning(f"Impossible de récupérer le XSRF token : {exc}")

    def _do_refresh(self) -> None:
        logger.info("Token expiré, renouvellement en cours...")
        last_error = None
        for endpoint in TOKEN_REFRESH_ENDPOINTS:
            url = f"{self.base_url}{endpoint}"
            try:
                resp = self.session.post(
                    url,
                    json={"refresh_token": self._refresh_token},
                    timeout=15,
                )
                if resp.status_code == 404:
                    continue
                if resp.status_code != 200:
                    last_error = f"HTTP {resp.status_code} sur {url}"
                    continue
                data = _safe_json(resp)
                new_token = data.get("access_token") or data.get("token")
                if new_token:
                    self._set_token(new_token)
                    logger.info("Token renouvelé avec succès.")
                    return
            except Exception as exc:
                last_error = str(exc)
                continue
        raise VintedAuthError(
            f"Impossible de renouveler le token ({last_error}). "
            "Mets à jour VINTED_ACCESS_TOKEN et VINTED_REFRESH_TOKEN dans Railway."
        )

    def _verify(self) -> None:
        logger.info("Vérification de la connexion Vinted...")
        self._fetch_xsrf()

        user = None
        for endpoint in CURRENT_USER_ENDPOINTS:
            url = f"{self.base_url}{endpoint}"
            resp = self.session.get(url, timeout=15)
            logger.debug(f"GET {url} → HTTP {resp.status_code}")

            if resp.status_code == 404:
                continue
            if resp.status_code == 401:
                self._do_refresh()
                resp = self.session.get(url, timeout=15)
            if resp.status_code == 200:
                data = _safe_json(resp)
                user = (
                    data.get("user")
                    or data.get("current_user")
                    or (data if "id" in data else None)
                )
                if isinstance(user, dict) and "user" in user:
                    user = user["user"]
                if user and user.get("id"):
                    break

        if not user or not user.get("id"):
            raise VintedAuthError(
                "Impossible de récupérer le profil utilisateur. "
                "Vérifie que tes tokens sont corrects."
            )

        self.user_id = user["id"]
        logger.info(f"Connecté : {user.get('login', '?')} (id={self.user_id})")

    # ------------------------------------------------------------------ wrappers HTTP

    def _get(self, url: str, **kwargs) -> requests.Response:
        resp = self.session.get(url, timeout=15, **kwargs)
        if resp.status_code == 401:
            self._do_refresh()
            resp = self.session.get(url, timeout=15, **kwargs)
        return resp

    def _post(self, url: str, **kwargs) -> requests.Response:
        resp = self.session.post(url, timeout=15, **kwargs)
        if resp.status_code == 401:
            self._do_refresh()
            resp = self.session.post(url, timeout=15, **kwargs)
        return resp

    # ------------------------------------------------------------------ items

    def get_my_items(self) -> list:
        all_items, page = [], 1
        while True:
            resp = self._get(
                f"{self.api}/users/{self.user_id}/items",
                params={"page": page, "per_page": 96},
            )
            resp.raise_for_status()
            items = _safe_json(resp).get("items", [])
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
        resp = self._get(
            f"{self.api}/items/{item_id}/item_favourite_users",
            params={"page": 1, "per_page": 100},
        )
        if resp.status_code == 404:
            return []
        resp.raise_for_status()
        return _safe_json(resp).get("users", [])

    # ------------------------------------------------------------------ conversations

    def get_conversations(self) -> list:
        resp = self._get(
            f"{self.api}/conversations",
            params={"page": 1, "per_page": 50},
        )
        resp.raise_for_status()
        return _safe_json(resp).get("conversations", [])

    def get_messages(self, conv_id: int) -> list:
        resp = self._get(f"{self.api}/conversations/{conv_id}/messages")
        resp.raise_for_status()
        return _safe_json(resp).get("messages", [])

    def reply(self, conv_id: int, body: str) -> dict:
        resp = self._post(
            f"{self.api}/conversations/{conv_id}/messages",
            json={"message": {"body": body}},
        )
        resp.raise_for_status()
        return _safe_json(resp)

    def start_conversation(self, to_user_id: int, item_id: int, body: str) -> Optional[dict]:
        resp = self._post(
            f"{self.api}/conversations",
            json={
                "conversation": {
                    "to_user_id": to_user_id,
                    "item_id": item_id,
                    "body": body,
                }
            },
        )
        if resp.status_code in (200, 201):
            return _safe_json(resp)
        logger.warning(
            f"Impossible de créer la conversation user={to_user_id} item={item_id} "
            f"(HTTP {resp.status_code}) : {resp.text[:150]}"
        )
        return None

    # ------------------------------------------------------------------ helpers

    def safe_delay(self, min_sec: float = 30, max_sec: float = 90) -> None:
        import random
        delay = random.uniform(min_sec, max_sec)
        logger.debug(f"Pause {delay:.0f}s...")
        time.sleep(delay)
