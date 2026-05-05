import logging
import os
import time
import random
import requests
from playwright.sync_api import sync_playwright
from typing import Optional

logger = logging.getLogger(__name__)

SESSION_FILE = os.environ.get("SESSION_FILE", "data/playwright_session.json")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "fr-FR,fr;q=0.9",
    "Accept-Encoding": "gzip, deflate",
}

CHROMIUM_ARGS = [
    "--no-sandbox",
    "--disable-setuid-sandbox",
    "--disable-dev-shm-usage",
    "--disable-gpu",
    "--disable-extensions",
    "--single-process",
    "--no-zygote",
]


class VintedAuthError(Exception):
    pass


class VintedClient:
    def __init__(self, email: str, password: str, domain: str = "fr"):
        self.email = email
        self.password = password
        self.domain = domain
        self.base_url = f"https://www.vinted.{domain}"
        self.api = f"{self.base_url}/api/v2"
        self.http = requests.Session()
        self.http.headers.update(HEADERS)
        self.user_id: Optional[int] = None
        self._authenticate()

    # ------------------------------------------------------------------ auth

    def _authenticate(self) -> None:
        logger.info("Lancement du navigateur pour authentification...")
        token_box: list = []

        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True, args=CHROMIUM_ARGS)

            ctx_kwargs: dict = {"user_agent": HEADERS["User-Agent"], "locale": "fr-FR"}
            if os.path.exists(SESSION_FILE):
                logger.info("Restauration de la session précédente...")
                ctx_kwargs["storage_state"] = SESSION_FILE

            ctx = browser.new_context(**ctx_kwargs)
            page = ctx.new_page()

            # Capture le Bearer token depuis les requêtes sortantes
            def on_request(req):
                auth = req.headers.get("authorization", "")
                if auth.startswith("Bearer ") and "/api/v2/" in req.url:
                    t = auth[7:]
                    if t not in token_box:
                        token_box.append(t)

            page.on("request", on_request)

            page.goto(self.base_url, wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(2000)

            if not self._is_logged_in(page):
                logger.info("Connexion au compte Vinted...")
                self._do_login(page)

            # Charge la messagerie pour déclencher des appels API
            page.goto(f"{self.base_url}/member/inbox", wait_until="networkidle", timeout=30000)
            page.wait_for_timeout(2000)

            # Sauvegarde la session pour le prochain démarrage
            os.makedirs(os.path.dirname(SESSION_FILE), exist_ok=True)
            ctx.storage_state(path=SESSION_FILE)
            browser.close()

        if not token_box:
            raise VintedAuthError(
                "Aucun token capturé. Vérifie VINTED_EMAIL et VINTED_PASSWORD."
            )

        self.http.headers["Authorization"] = f"Bearer {token_box[-1]}"
        logger.info("Token capturé avec succès.")

        # Récupère l'identifiant utilisateur
        resp = self.http.get(f"{self.api}/users/current", timeout=15)
        if resp.status_code != 200:
            raise VintedAuthError(f"Profil inaccessible (HTTP {resp.status_code})")

        data = resp.json()
        user = data.get("user") or data.get("current_user") or data
        if isinstance(user, dict) and "user" in user:
            user = user["user"]
        self.user_id = user.get("id")
        logger.info(f"Connecté : {user.get('login', '?')} (id={self.user_id})")

    def _is_logged_in(self, page) -> bool:
        selectors = [
            'a[href*="/member/profile"]',
            'a[href*="/logout"]',
            '[data-testid*="user"]',
            '[class*="userAvatar"]',
            'img[alt*="avatar"]',
        ]
        for sel in selectors:
            try:
                if page.query_selector(sel):
                    return True
            except Exception:
                pass
        return False

    def _do_login(self, page) -> None:
        # Clic sur "Se connecter"
        for sel in ['a[href*="login"]', 'a:has-text("Se connecter")', 'button:has-text("Se connecter")']:
            try:
                el = page.query_selector(sel)
                if el:
                    el.click()
                    page.wait_for_load_state("domcontentloaded")
                    break
            except Exception:
                pass

        # Remplir email
        for sel in ['input[name="username"]', 'input[name="user[login]"]', 'input[type="email"]', '#username']:
            try:
                el = page.wait_for_selector(sel, timeout=5000)
                if el:
                    el.fill(self.email)
                    break
            except Exception:
                pass

        # Remplir mot de passe
        for sel in ['input[name="password"]', 'input[name="user[password]"]', 'input[type="password"]']:
            try:
                el = page.query_selector(sel)
                if el:
                    el.fill(self.password)
                    break
            except Exception:
                pass

        # Soumettre
        for sel in ['button[type="submit"]', 'button:has-text("Connexion")', 'button:has-text("Se connecter")']:
            try:
                el = page.query_selector(sel)
                if el:
                    el.click()
                    page.wait_for_load_state("networkidle", timeout=20000)
                    break
            except Exception:
                pass

        if not self._is_logged_in(page):
            raise VintedAuthError("Connexion échouée. Vérifie VINTED_EMAIL et VINTED_PASSWORD.")
        logger.info("Connexion réussie.")

    # ------------------------------------------------------------------ wrappers HTTP

    def _get(self, url: str, **kwargs) -> requests.Response:
        resp = self.http.get(url, timeout=15, **kwargs)
        if resp.status_code == 401:
            self._authenticate()
            resp = self.http.get(url, timeout=15, **kwargs)
        return resp

    def _post(self, url: str, **kwargs) -> requests.Response:
        resp = self.http.post(url, timeout=15, **kwargs)
        if resp.status_code == 401:
            self._authenticate()
            resp = self.http.post(url, timeout=15, **kwargs)
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
        resp = self._get(
            f"{self.api}/items/{item_id}/item_favourite_users",
            params={"page": 1, "per_page": 100},
        )
        if resp.status_code == 404:
            return []
        resp.raise_for_status()
        return resp.json().get("users", [])

    # ------------------------------------------------------------------ conversations

    def get_conversations(self) -> list:
        resp = self._get(f"{self.api}/conversations", params={"page": 1, "per_page": 50})
        resp.raise_for_status()
        return resp.json().get("conversations", [])

    def get_messages(self, conv_id: int) -> list:
        resp = self._get(f"{self.api}/conversations/{conv_id}/messages")
        resp.raise_for_status()
        return resp.json().get("messages", [])

    def reply(self, conv_id: int, body: str) -> dict:
        resp = self._post(
            f"{self.api}/conversations/{conv_id}/messages",
            json={"message": {"body": body}},
        )
        resp.raise_for_status()
        return resp.json()

    def start_conversation(self, to_user_id: int, item_id: int, body: str) -> Optional[dict]:
        resp = self._post(
            f"{self.api}/conversations",
            json={"conversation": {"to_user_id": to_user_id, "item_id": item_id, "body": body}},
        )
        if resp.status_code in (200, 201):
            return resp.json()
        logger.warning(f"Conversation non créée (HTTP {resp.status_code}) : {resp.text[:100]}")
        return None

    def safe_delay(self, min_sec: float = 30, max_sec: float = 90) -> None:
        delay = random.uniform(min_sec, max_sec)
        logger.debug(f"Pause {delay:.0f}s...")
        time.sleep(delay)
