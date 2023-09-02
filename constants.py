# pylint: disable=C0114, C0115, R0903, C0116, W0718, W0612
import os
import sys
import json


class Links:
    oauth_api = (
        "https://account-public-service-prod.ol.epicgames.com/"
        + "account/api/oauth/{0}"
    )
    profile_api = (
        "https://fortnite-public-service-prod11.ol.epicgames.com/"
        + "fortnite/api/game/v2/profile/{0}/client/{1}?profileId={2}"
    )
    auth_code = (
        "https://www.epicgames.com/id/api/redirect?clientId="
        + "34a02cf8f4414e29b15921876da36f9a&responseType=code"
    )


class Headers:
    access = (
        "basic MzRhMDJjZjhmNDQxNGUyOWIxNTkyMTg3NmRhMzZmOWE6"
        + "ZGFhZmJjY2M3Mzc3NDUwMzlkZmZlNTNkOTRmYzc2Y2Y="
    )
    oauth = (
        "basic MzQ0NmNkNzI2OTRjNGE0NDg1ZDgxYjc3YWRiYjIxNDE6O"
        + "TIwOWQ0YTVlMjVhNDU3ZmI5YjA3NDg5ZDMxM2I0MWE="
    )


def read_game_version():
    try:
        # Read game version in fn logs (only for windows)
        log_path = os.path.join(
            os.path.expanduser("~"),
            "AppData",
            "Local",
            "FortniteGame",
            "Saved",
            "Logs",
            "FortniteGame.log",
        )
        if not os.path.exists(log_path):
            raise Exception
        try:
            with open(log_path, "r", encoding="utf-8") as file:
                lines = file.readlines()
        except UnicodeDecodeError:
            with open(log_path, "rb") as file:
                content = file.read().decode("utf-8", errors="replace")
                lines = content.splitlines()
        for line in lines[1:]:
            parts = line.split(":")
            category_name = parts[0].split("]")[-1].strip()
            if category_name == "LogInit":
                log_sub_type = parts[1].strip()
                if log_sub_type == "Build":
                    result = ":".join(parts[2:]).strip()
                    return result
    except Exception:
        return "++Fortnite+Release-26.00-CL-27424790"


def read_jsons():
    full_path = os.path.split(os.path.abspath(__file__))[0]
    fn_path = os.path.join(full_path, "fortnite.json")
    if not os.path.exists(fn_path):
        input(
            "ERROR: fortnite.json file doesn't exist. Get "
            + "it from this program's repository on GitHub: "
            + "https://github.com/zdky/questreroll"
        )
        sys.exit()
    auth_path = os.path.join(full_path, "auth.json")
    if not os.path.exists(auth_path):
        with open(auth_path, "w", encoding="utf-8") as auth_file:
            auth_file.write("{}")
    with open(fn_path, "r", encoding="utf-8") as file:
        fn_json = json.load(file)
    return fn_json


FN_JSON = read_jsons()
GAME_VER = read_game_version()
