# pylint: disable=C0116, C0115, C0114, W0511, W0718, R0903, W0621, W0719, W1201, W1203, C0415
from datetime import datetime, timedelta
import asyncio
import aiohttp
from constants import Links, Headers, GAME_VER, FN_JSON
from database import read_user_info, edit_user_info, scheduled_users
from utils import get_time, log


async def aiorequest(method: str, link: str, headers: dict, data: dict = None,
                    json: dict = None, from_func: str = ""):
    """aiohttp post/get request

    Args:
        method (str): "post" or "get"
        link (str): FN API link
        from_func (str): to debug

    Raises:
        ValueError: json error data

    Returns:
        (json): fortnite API response
    """
    try:
        async with aiohttp.ClientSession() as session:
            if method == "post":
                response = await session.post(link, headers=headers, data=data, json=json)
            elif method == "get":
                response = await session.get(link, headers=headers, data=data)
            else:
                raise ValueError("Invalid request method")
            res_json = await response.json()
            if "errorMessage" in res_json:
                raise Exception(res_json)
            return res_json
    except Exception as error:
        log.error(f"aiorequest() from func {from_func}(): {error}")
        log.error(f"method: {method}\nheaders: {headers}\ndata: {data}\njson: {json}")
    return False

# Auth Step-1
async def get_access_token(token:str, grant_type="authorization_code"):
    """Epic Games Launcher access token.\n
    *access_token live 8h\n
    *refresh_token live 23d

    Args:
        token (str): auth_code or refresh_token
        grant_type (str): string "authorization_code" 
        or "refresh_token"

    Returns:
        (json): with access_token data
    """
    if grant_type == "refresh_token":
        token_type = grant_type
    else:
        token_type = "code"
    link = Links.oauth_api.format("token")
    headers_ = {"Authorization": Headers.access}
    data = {"grant_type": grant_type, token_type: token,}
    res_json = await aiorequest("post", link, headers_, data, from_func="get_access_token")
    return res_json if res_json else False

# Auth Step-2
async def get_exchange_token(access_token:str):
    """Token live 299 sec

    Args:
        access_token (str)

    Returns:
        (json): with code for final auth
    """
    link = Links.oauth_api.format("exchange")
    headers = {"Authorization": f"bearer {access_token}"}
    data = {"grant_type": "authorization_code"}
    res_json = await aiorequest("get", link, headers, data, from_func="get_exchange_token")
    return res_json if res_json else False

# Auth Step-3
async def get_fortnite_token(token:str, grant_type="exchange_code"):
    """*access_token live 2h\n
    *refresh_token live 8h

    Args:
        token (str): exchange code or refresh token
        grant_type (str): string "exchange_code"
        or "refresh_token"

    Returns:
        data (json): with access_token
    """
    if grant_type == "exchange_code":
        token_type = grant_type
    else:
        token_type = "refresh_token"
    link = Links.oauth_api.format("token")
    headers_ = {"Authorization": Headers.oauth}
    data = {
        "grant_type": grant_type,
        token_type: token,
        "token_type": "eg1"
    }
    res_json = await aiorequest("post", link, headers_, data, from_func="get_fortnite_token")
    return res_json if res_json else False

# Request quests(campaign data)
async def get_quests(access_token:str, account_id:str):
    """Request on FN API campaign(PvE)
    
    Args:
        access_token (str): main fortnite access_token
        account_id (str): from any token, always same

    Returns:
        data (dict): with campaign, headers
    """
    link = Links.profile_api.format(account_id, "ClientQuestLogin", "campaign")
    headers = {
        "User-Agent": f"Fortnite/{GAME_VER} Windows/10.0.19045.3155.64bit",
        "Authorization": f"bearer {access_token}",
        "Content-Type": "application/json",
    }
    data = "{}"
    res_json = await aiorequest("post", link, headers, data, from_func="get_quests")
    if res_json:
        campaign = res_json["profileChanges"][0]["profile"]
        # await file_log("in get_quests(), campaign: \n\n", campaign) #! DEL
        return {"campaign": campaign, "headers": headers}
    return False

# Readable quest with select lang
def rename_quests(data: dict, lang: str):
    """Readable names and rewards

    Args:
        data (dict): from get_quests()
        lang (str): from auth.json - 'user_id' - 'lang'

    Returns:
        data (dict): for gen_quest_buttons(), gen_quests_info_msg()
    """
    quests_data = {}
    for quest_id in data.get("items"):
        item_data = data.get("items").get(quest_id)
        if (item_data.get("templateId").lower().startswith("quest:daily_") and
            item_data.get("attributes").get("quest_state").lower() == "active"):
            template_id = item_data.get("templateId")
            quest_json = FN_JSON.get("Items").get(template_id)
            objs = quest_json.get("objectives")
            progress = ""
            for obj in objs:
                complete_num = item_data.get("attributes").get(f"completion_{obj}", 0)
                progress += f"{complete_num}/{objs[obj]['count']} {objs[obj]['name'][lang]},"
            progress = progress[:-1]
            rewards = quest_json.get("rewards")
            reward_text = ""
            for rwrd in rewards:
                reward_amount = rewards[rwrd]
                reward_name = FN_JSON.get("Items").get(rwrd).get("name").get(lang)
                if rwrd.startswith("ConditionalResource:"):
                    reward_text += f"{reward_amount}x {reward_name['PassedConditionItem']},"
                    reward_name = reward_name["FailedConditionItem"]
                reward_text += f" {reward_amount}x {reward_name},"
            reward_text = reward_text[:-1]
            quest_name = quest_json.get("name").get(lang)
            difficulty = quest_json.get("difficulty")
            quests_data[quest_id] = {
                "quest_name": quest_name,
                "progress": progress,
                "reward": reward_text,
                "difficulty": difficulty
            }
    return quests_data if quests_data else False

# Request to reroll quest
async def quest_reroll(quest_id: str, headers: dict, account_id: str):
    """Request on FN API for replace quest

    Args:
        quest_id (str): from get_quests()
        headers (dict): from get_quests()
        account_id (str): from any token

    Returns:
        (bool): True/False
    """
    link = Links.profile_api.format(account_id, "FortRerollDailyQuest", "campaign")
    json = {"questId": quest_id}
    res_json = await aiorequest("post", link, headers, json=json, from_func="quest_reroll")
    # await file_log("in quest_reroll(), res_json: \n\n", res_json) #! DEL
    return True if res_json else False

async def start_3step_login(user_id: int, auth_code: str):
    """Login FN API with auth_code

    Args:
        user_id (int): for record tokens in auth.json
        auth_code (str): code from link

    Returns:
        (bool): True/False
    """
    first_token = await get_access_token(auth_code)
    if not first_token:
        return
    exchange_token = await get_exchange_token(first_token["access_token"])
    if not exchange_token:
        return
    main_token = await get_fortnite_token(exchange_token["code"])
    if not main_token:
        return
    await edit_user_info(user_id, "acc_token", first_token)
    await edit_user_info(user_id, "fn_token", main_token)
    return True

async def refresh_all_tokens(user_id: int, refresh_token: str):
    """Refresh tokens with refresh_token

    Returns:
        (bool): True/False
    """
    new_token = await get_access_token(refresh_token, "refresh_token")
    if new_token:
        exchange_data = await get_exchange_token(new_token["access_token"])
        if exchange_data:
            new_fn_token = await get_fortnite_token(exchange_data["code"])
            await edit_user_info(user_id, 'acc_token', new_token)
            await edit_user_info(user_id, 'fn_token', new_fn_token)
            return True
    return False

async def check_refresh_expires(token: dict, minus_hour: int = 0):
    """Refresh token live checker

    Returns:
        (bool): True/False
    """
    if token:
        refresh_expires = datetime.fromisoformat(token.get('refresh_expires_at'))
        now = await asyncio.to_thread(get_time)
        log.info(f"Refresh token time {refresh_expires}, now {now}")
        if minus_hour:  # maybe api lie? (-2h for refresh fn_token)
            refresh_expires -= timedelta(hours=minus_hour)
        if refresh_expires > now: # live
            log.info("Refresh token live!")
            return True
    return False

async def check_token_expires(token: dict):
    """Token died checker

    Returns:
        (bool): True/False
    """
    if token:
        token_expires = datetime.fromisoformat(token.get('expires_at'))
        now = await asyncio.to_thread(get_time)
        log.info(f"Token time {token_expires}, now {now}")
        if now > token_expires: # died
            log.warning("Token died!")
            return True
    return False

async def tokens_check_and_update(user_id: int):
    user_data = await read_user_info(user_id)
    token = user_data.get('fn_token', 0)
    if await check_token_expires(token):
        if await check_refresh_expires(token): #! maybe -2h
            log.warning(f"tokens_check_and_update(), user_id:{user_id}, "
                        + "fn_token died, try refresh..")
            new_token = await get_fortnite_token(
                token.get('refresh_token'), "refresh_token")
            if new_token:
                log.info(f"tokens_check_and_update(), user_id:{user_id}, "
                         + "fn_token refreshed!")
                await edit_user_info(user_id, 'fn_token', new_token)
                return True
        else: # full update tokens
            log.warning(f"tokens_check_and_update(), user_id:{user_id}, "
                        + "fn_token refresh died, try refresh..")
            token = user_data.get('acc_token', 0)
            if await check_token_expires(token):
                if await refresh_all_tokens(user_id, token.get('refresh_token')):
                    log.info(f"tokens_check_and_update(), user_id:{user_id}, "
                                + "acc_token and fn_token refreshed!")
                    return True
    else: # token live
        log.info(f"tokens_check_and_update(), user_id:{user_id}, fn_token live!")
        return True

    log.error(f"tokens_check_and_update(), user_id:{user_id}, all tokens died!")
    return False

async def scheduling_update_quest(user_id: int):
    """Schedule quest request to next day +5 min 
    (silent update msg + PvE login)
    """
    time_now = await asyncio.to_thread(get_time)
    time_request = time_now + timedelta(days=1)
    # next day 00:05am UTC+0
    time_request = time_request.replace(hour=0, minute=5, second=0)
    time_request = (time_request - time_now).total_seconds()
    scheduled_users.append(user_id)
    await asyncio.sleep(time_request)
    scheduled_users.remove(user_id)
    if await tokens_check_and_update(user_id):
        await start_quest_api(user_id)

async def send_quest_message(user_id, user_data, msg, keyboard):
    from tg import bot
    try:
        await bot.edit_message_text(
            msg,
            user_id,
            user_data["first_quest_msg"],
            parse_mode="HTML",
            reply_markup=keyboard
        )
        log.info(f"Edit quest message user_id: {user_id}, "
                 + f"msg_id: {user_data['first_quest_msg']}")
    except Exception as error:
        bot_msg = await bot.send_message(user_id,
                                         msg,
                                         parse_mode="HTML",
                                         reply_markup=keyboard)
        log.info(f"Send first quest message user_id: {user_id}, "
                 + f"msg_id: {bot_msg.message_id}")
        await edit_user_info(user_id, 'first_quest_msg', bot_msg.message_id)

async def process_quests(user_id, user_data, pve_data):
    from tg import gen_quests_msg, gen_quest_buttons
    renamed_quests = await asyncio.to_thread(rename_quests, pve_data,
                                             user_data["lang"])
    if renamed_quests:
        msg = await gen_quests_msg(renamed_quests)
        can_reroll = (pve_data.get("stats", {}).get("attributes", {})
                      .get("quest_manager", {}).get("dailyQuestRerolls", 0))
        if can_reroll > 0:
            keyboard = await gen_quest_buttons(user_id, renamed_quests)
            msg += FN_JSON["msg"]["en"]["click.button"]
        else:
            keyboard = None
            msg += FN_JSON["msg"]["en"]["already.replaced"]
    else:
        keyboard = None
        time_now = await asyncio.to_thread(get_time, "text")
        msg = FN_JSON["msg"]["en"]["no.active.quest"].format(time_now)

    await send_quest_message(user_id, user_data, msg, keyboard)

async def start_quest_api(user_id):
    from tg import delete_all_msgs
    user_data = await read_user_info(user_id)
    access_token = user_data["fn_token"]["access_token"]
    account_id = user_data["fn_token"]["account_id"]
    pve_data = await get_quests(access_token, account_id)

    if pve_data:
        await edit_user_info(user_id, new_data="quest") # +1 stats
        await edit_user_info(user_id, 'headers', pve_data['headers'])
        await process_quests(user_id, user_data, pve_data['campaign'])
        await delete_all_msgs(user_data['msg_for_del'], user_id)
        if not user_id in scheduled_users:
            await scheduling_update_quest(user_id)
