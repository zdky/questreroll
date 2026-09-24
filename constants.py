"""Static data: Epic Games endpoints, client credentials and fortnite.json."""

import urllib.request
from pathlib import Path

import orjson

BASE_DIR = Path(__file__).resolve().parent
FN_JSON_PATH = BASE_DIR / "fortnite.json"
FN_JSON_URL = "https://raw.githubusercontent.com/zdky/questreroll/main/fortnite.json"
DEMO_GIF_PATH = BASE_DIR / "res" / "demo.gif"

GAME_VER = "++Fortnite+Release-26.00-CL-27424790"


class Links:
    oauth_api = (
        "https://account-public-service-prod.ol.epicgames.com/account/api/oauth/{0}"
    )
    profile_api = (
        "https://fortnite-public-service-prod11.ol.epicgames.com/"
        "fortnite/api/game/v2/profile/{0}/client/{1}?profileId={2}"
    )
    auth_code = (
        "https://www.epicgames.com/id/api/redirect?clientId="
        "34a02cf8f4414e29b15921876da36f9a&responseType=code&prompt=login"
    )


class Headers:
    # Epic Launcher client
    access = (
        "basic MzRhMDJjZjhmNDQxNGUyOWIxNTkyMTg3NmRhMzZmOWE6"
        "ZGFhZmJjY2M3Mzc3NDUwMzlkZmZlNTNkOTRmYzc2Y2Y="
    )
    # Fortnite game client
    oauth = (
        "basic MzQ0NmNkNzI2OTRjNGE0NDg1ZDgxYjc3YWRiYjIxNDE6O"
        "TIwOWQ0YTVlMjVhNDU3ZmI5YjA3NDg5ZDMxM2I0MWE="
    )
    oauth_content_type = "application/x-www-form-urlencoded"
    user_agent = f"Fortnite/{GAME_VER} Windows/10.0.19045.3155.64bit"


def load_fn_json() -> dict:
    """Load fortnite.json, downloading it from GitHub if it's missing."""
    if not FN_JSON_PATH.exists():
        with urllib.request.urlopen(FN_JSON_URL, timeout=30) as response:
            FN_JSON_PATH.write_bytes(response.read())
    return orjson.loads(FN_JSON_PATH.read_bytes())


FN_JSON = load_fn_json()
LANGS: dict[str, str] = FN_JSON["lang"]


def text(key: str, *args) -> str:
    """Bot UI text by key from fortnite.json (formatted with args)."""
    msg = FN_JSON["msg"]["en"][key]
    return msg.format(*args) if args else msg
