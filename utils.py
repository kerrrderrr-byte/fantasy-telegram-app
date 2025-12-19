# utils.py
import os
import time
import hashlib
import hmac
from urllib.parse import unquote
from typing import Dict

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

def validate_init_data(init_data: str) -> Dict[str, str]:
    if not init_data or not BOT_TOKEN:
        raise ValueError("initData or BOT_TOKEN missing")

    try:
        params = {}
        for part in init_data.split("&"):
            if "=" in part:
                k, v = part.split("=", 1)
                params[k] = unquote(v)

        if "hash" not in params or "auth_date" not in params:
            raise ValueError("Required fields missing")

        auth_date = int(params["auth_date"])
        if abs(time.time() - auth_date) > 86400:
            raise ValueError("initData expired")

        data_check = "\n".join(f"{k}={v}" for k, v in sorted(params.items()) if k != "hash")
        secret = hmac.new(b"WebAppData", BOT_TOKEN.encode(), hashlib.sha256).digest()
        calc_hash = hmac.new(secret, data_check.encode(), hashlib.sha256).hexdigest()

        if calc_hash != params["hash"]:
            raise ValueError("Invalid hash")

        return params
    except Exception as e:
        raise ValueError(f"Validation failed: {e}")