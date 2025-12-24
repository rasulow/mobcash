import json
from dataclasses import dataclass
from typing import Iterable
from urllib.error import HTTPError
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from django.conf import settings
from django.core.cache import cache
from decimal import Decimal, InvalidOperation


@dataclass(frozen=True)
class ExternalUser:
    id: int
    name: str
    email: str | None
    balance: Decimal | None
    referral_token: str | None
    image_url: str | None

    @property
    def label(self) -> str:
        base = self.name or f"User {self.id}"
        if self.email:
            return f"{base} ({self.email})"
        return base


class ExternalApiError(RuntimeError):
    pass


def fetch_yildiztop_users(timeout_s: int = 6) -> list[ExternalUser]:
    """
    Fetch users from the public endpoint:
    https://yildiztop.com/api/users
    """
    return fetch_yildiztop_users_by_referral_token(referral_token=None, timeout_s=timeout_s)


def fetch_yildiztop_users_by_referral_token(
    referral_token: str | None,
    timeout_s: int = 6,
) -> list[ExternalUser]:
    cache_key = f"yildiztop_users_v1:{referral_token or 'all'}"
    cached = cache.get(cache_key)
    if isinstance(cached, list) and cached:
        return cached

    base = getattr(settings, "YILDIZTOP_API_BASE", "https://yildiztop.com/api").rstrip("/")
    params: dict[str, str] = {"page": "1"}
    if referral_token:
        params["referral_token"] = referral_token
    url = f"{base}/users?{urlencode(params)}"
    req = Request(url, headers={"Accept": "application/json", "User-Agent": "mobcash/1.0"})
    last_exc: Exception | None = None
    for _ in range(2):  # small retry for transient 500s/timeouts
        try:
            with urlopen(req, timeout=timeout_s) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
            last_exc = None
            break
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as e:
            last_exc = e
            continue
    if last_exc is not None:
        # If we have stale cache (e.g. from previous process run), use it.
        cached = cache.get(cache_key)
        if isinstance(cached, list) and cached:
            return cached
        raise ExternalApiError(f"Failed to fetch users from {url}") from last_exc

    # Expected shape (Laravel pagination):
    # {"success":true,"data":{"data":[{...},{...}]}}
    data = payload.get("data") or {}
    users: Iterable[dict] = data.get("data") or []
    result: list[ExternalUser] = []
    for u in users:
        try:
            bal = None
            if u.get("balance") is not None:
                try:
                    bal = Decimal(str(u.get("balance")))
                except InvalidOperation:
                    bal = None
            result.append(
                ExternalUser(
                    id=int(u.get("id")),
                    name=str(u.get("name") or ""),
                    email=(u.get("email") or None),
                    balance=bal,
                    referral_token=(u.get("referral_token") or None),
                    image_url=(u.get("image_url") or None),
                )
            )
        except Exception:
            # Skip malformed entries rather than breaking the app.
            continue
    if result:
        ttl = 60 * 10 if not referral_token else 60 * 2
        cache.set(cache_key, result, timeout=ttl)
    return result


def post_yildiztop_update_balance(
    referral_token: str,
    balance: Decimal,
    timeout_s: int = 8,
) -> None:
    """
    POST https://yildiztop.com/api/users/update-balance
    Body: {"referral_token": "...", "balance": 123.45}
    """
    base = getattr(settings, "YILDIZTOP_API_BASE", "https://yildiztop.com/api").rstrip("/")
    url = f"{base}/users/update-balance"
    body = json.dumps({"referral_token": referral_token, "balance": float(balance)}).encode("utf-8")
    req = Request(
        url,
        data=body,
        method="POST",
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "mobcash/1.0",
        },
    )
    try:
        with urlopen(req, timeout=timeout_s) as resp:
            # consume response for debugging/validation if needed
            resp.read()
    except (HTTPError, URLError, TimeoutError) as e:
        raise ExternalApiError(f"Failed to POST update-balance to {url}") from e


