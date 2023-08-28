# pylint: disable=E1101, C0114, W0718
import orjson # faster json
import aiofiles
from utils import logging

scheduled_users = []

async def add_new_user(user_id: int, lang: str = "en"):
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
        "stats": {"quest": 0, "skips": 0}
    }
    async with aiofiles.open("auth.json", "r", encoding="utf-8") as file:
        file_data = await file.read()
        file_data = orjson.loads(file_data)
    async with aiofiles.open("auth.json", "w", encoding="utf-8") as file2:
        file_data[str(user_id)] = new_user
        data = orjson.dumps(file_data, option=orjson.OPT_INDENT_2).decode("utf-8")
        await file2.write(data)

async def edit_user_info(user_id:int, field:str = None, new_data = None):
    """Edit user data in auth.json

    Args:
        user_id (int): telegram user id\n
        field (str): "lang" / "buttons" / 
        "acc_token" / "fn_token" / 
        "msg_for_del" / "first_quest_msg"
        or "quest"/"skips" for stats +1\n
        new_data: if field="lang":(str) other:(dict) or empty = {}
    """
    user_id = str(user_id)
    async with aiofiles.open('auth.json', 'r', encoding="utf-8") as file1:
        file_data = await file1.read()
        file_data = orjson.loads(file_data)
        async with aiofiles.open("auth.json", "w", encoding="utf-8") as file2:
            try:
                if field == 'msg_for_del':
                    file_data[user_id][field].append(new_data)
                elif field in ("quest", "skips"):
                    file_data[user_id]["stats"][new_data] += 1
                else:
                    file_data[user_id][field] = new_data
                data = orjson.dumps(file_data,
                                    option=orjson.OPT_INDENT_2).decode("utf-8")
                await file2.write(data)
            except Exception as error:
                logging.error(f"in edit_user_info(), ERROR: {error}")

async def read_user_info(user_id:int):
    """Read user from auth.json

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
    async with aiofiles.open('auth.json', 'r', encoding="utf-8") as file:
        try:
            data = await file.read()
            user_data = orjson.loads(data)
            user_data = user_data.get(str(user_id), {})
            return user_data
        except Exception as error:
            logging.error(f"in read_user_info(), ERROR: {error}")
            return False
