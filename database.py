# pylint: disable=E1101, C0114, W0718
import orjson  # faster json
import aiofiles
from utils import log

scheduled_users = []


async def add_new_user(user_id: int, lang: str):
    """Add new user_id in auth.json with fields:\n
    {
        "lang": lang,
        "acc_token": {},\n
        "fn_token": {},
        "buttons": {},\n
        "headers": {},
        "msg_for_del": [],\n
        "first_quest_msg": "",\n
        "stats": {"quest": 0, "skips": 0}
    }

    Args:
        user_id (int): telegram user id
    """
    new_user = {
        "lang": lang,
        "acc_token": {},
        "fn_token": {},
        "buttons": {},
        "headers": {},
        "msg_for_del": [],
        "first_quest_msg": "",
        "stats": {"quest": 0, "skips": 0},
    }
    try:
        async with aiofiles.open("auth.json", "r", encoding="utf-8") as file1:
            user_data = orjson.loads(await file1.read())
        user_data[str(user_id)] = new_user
        new_data = orjson.dumps(user_data, option=orjson.OPT_INDENT_2).decode("utf-8")
        async with aiofiles.open("auth.json", "w", encoding="utf-8") as file2:
            await file2.write(new_data)
    except Exception as error:
        log.error(f"in add_new_user(), ERROR: {error}")


async def edit_user_info(user_id: int, field: str = None, new_data=None):
    """Edit user data in auth.json

    Args:
        user_id (int): telegram user id\n
        field (str): for change key in json (lang/buttons/
        acc_token/fn_token/
        msg_for_del/first_quest_msg)
        OR quest/skips for stats +1\n
        new_data: if field="lang":lang_code(str), other:(dict) or empty = {}
    """
    # log.info(f"in edit_user_info():\nuser_id = {user_id}\n"
    #          + f"field = {field}\nnew_data = {new_data}")

    try:
        async with aiofiles.open("auth.json", "r", encoding="utf-8") as file1:
            user_data = orjson.loads(await file1.read())

        user_id = str(user_id)
        if field == "msg_for_del" and new_data:
            user_data[user_id][field].append(new_data)
        elif field in ("quest", "skips"):
            user_data[user_id]["stats"][field] += 1
        else:
            user_data[user_id][field] = new_data

        new_data = orjson.dumps(user_data, option=orjson.OPT_INDENT_2).decode("utf-8")
        if new_data:
            async with aiofiles.open("auth.json", "w", encoding="utf-8") as file2:
                await file2.write(new_data)
    except Exception as error:
        log.error(f"in edit_user_info(), ERROR: {error}")


async def read_user_info(user_id: int):
    """Read user from auth.json by id

    Args:
        user_id (int): telegram user id

    Returns:
        user_data (dict): { "lang": lang,
        "acc_token": {},\n
        "fn_token": {},
        "buttons": {},\n
        "headers": {},
        "msg_for_del": [],\n
        "first_quest_msg": "",\n
        "stats": {"quest": 0, "skips": 0}}
    """
    try:
        async with aiofiles.open("auth.json", "r", encoding="utf-8") as file:
            user_data = orjson.loads(await file.read())
        user_data = user_data.get(str(user_id), {})
        return user_data
    except Exception as error:
        log.error(f"in read_user_info(), ERROR: {error}")
        return False
