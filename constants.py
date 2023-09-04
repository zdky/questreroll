# pylint: disable=C0114, C0115, R0903, C0116, W0718, W0612
import os
import asyncio
import aiohttp
import orjson


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


async def fn_json_read():
    full_path = os.path.split(os.path.abspath(__file__))[0]
    fn_path = os.path.join(full_path, "fortnite.json")
    if not os.path.exists(fn_path):
        url = ("https://raw.githubusercontent.com"
               + "/zdky/questreroll/main/fortnite.json")
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as r:
                content = await r.read()
        with open(fn_path, "wb") as f:
            f.write(content)
    with open(fn_path, "rb") as file:
        fn_json = orjson.loads(file.read())
    return fn_json


FN_JSON = asyncio.get_event_loop().run_until_complete(fn_json_read())
GAME_VER = "++Fortnite+Release-26.00-CL-27424790"
