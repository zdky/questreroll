# pylint: disable=C0116, C0114, W0511, W0718
import re
import asyncio
from aiogram.dispatcher.filters import BoundFilter
from aiogram.dispatcher import Dispatcher
from aiogram import types, Bot
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    CallbackQuery
)
from config import tg_token, first_user, first_user_id
from utils import log, get_time, server_status
from database import add_new_user
from fortnite import (
    quest_reroll, start_3step_login, tokens_check_and_update, FN_JSON,
    read_user_info, edit_user_info, Links, start_quest_api
)


bot = Bot(token=tg_token)
dp = Dispatcher(bot)

class IsAdmin(BoundFilter):
    key = "is_admin"

    def __init__(self, is_admin: bool):
        self.is_admin = is_admin

    async def check(self, message: types.Message) -> bool:
        if first_user:
            return (message.from_user.id in first_user_id) == self.is_admin
        else:
            return True

dp.filters_factory.bind(IsAdmin)

async def delete_all_msgs(msgs_list:dict, user_id:int):
    """Deletion all telegram messages by id
    
    Args:
        user_data (list): telegram messages id
        user_id (int): telegram user id
    """
    if msgs_list:
        log.info(f"Delete messages list: {msgs_list} user_id: {user_id}")
        for msg_id in msgs_list:
            try:
                log.info(f"Delete message with id: {msg_id}")
                await bot.delete_message(user_id, msg_id)
            except Exception as error:
                log.warning(f"Message already delete: {error}")
        await edit_user_info(user_id, "msg_for_del", [])

async def later_del_msg(messages:list=None, time:int=0):
    """Delayed deletion of 1+ messages
    
    Args:
        message (list): telegram object messages in list
        time (int): seconds before deleting
    """
    if messages:
        log.info("Delete messages "
                 + f"user_id: {messages[0].chat.id}, time: {time}'s")
        await asyncio.sleep(time)
        for msg in messages:
            try:
                log.info(f"Deleted msg with id: {msg.message_id}")
                await msg.delete()
            except Exception as error:
                log.warning(f"Message already delete: {error}")

async def send_auth_link(message: types.Message):
    user_id = message.chat.id
    msg = FN_JSON["msg"]["en"]["send.auth.code"].format(Links.auth_code)
    bot_msg = await bot.send_message(user_id, msg, parse_mode="HTML",
                                     disable_web_page_preview=True)
    if not user_id in first_user_id:
        await message.answer_animation(FN_JSON['msg']['en']['demo.gif'],
                                       caption=FN_JSON['msg']['en']['second.start'],
                                       parse_mode="HTML")
    await edit_user_info(user_id, "msg_for_del", bot_msg.message_id, add=True)

@dp.message_handler(lambda msg: not msg.text.startswith("/") and len(msg.text) < 32)
async def authcode_error(message: types.Message):
    user_id = message.chat.id
    if not user_id in first_user_id:
        return
    auth_len = len(message.text)
    msg = FN_JSON["msg"]["en"]["incorrect.auth.code"].format(auth_len)
    bot_msg = await bot.send_message(user_id, msg)
    await later_del_msg([bot_msg, message], time=15)

@dp.message_handler(lambda msg: not msg.text.startswith("/") and len(msg.text) >= 32)
async def authcode_handler(message: types.Message):
    user_id = message.chat.id
    if not user_id in first_user_id:
        return
    auth_code = re.search(r"[0-9a-f]{32}", message.text)
    if auth_code:
        if not await auth_checker(user_id):
            msg = FN_JSON["msg"]["en"]["auth.correct"]
            bot_msg = await bot.send_message(user_id, msg)
            await later_del_msg([bot_msg, message], time=6)
            if await start_3step_login(user_id, auth_code[0]): # Auth Fortnite API
                await quest_handler(message)
                return
        else:
            msg = FN_JSON["msg"]["en"]["error.already.auth"]
        bot_msg = await bot.send_message(user_id, msg)
        await later_del_msg([bot_msg, message], time=10)
    else:
        await authcode_error(message)

async def auth_checker(user_id:int):
    """FN tokens checker in auth.json by user_id
    
    Returns: True/False
    """
    user_data = await read_user_info(user_id)
    if user_data:
        acc_data = bool(user_data.get('acc_token', 0))
        fn_data = bool(user_data.get('fn_token', 0))
        if acc_data and fn_data:
            return True
    else:
        msg = FN_JSON["msg"]["en"]["error.not.auth"]
        bot_msg = await bot.send_message(user_id, msg)
        await later_del_msg([bot_msg], time=60)
    return False

@dp.message_handler(commands=['start'])
async def admin_handler(message: types.Message):
    user_id = message.from_user.id
    if not first_user_id:
        first_user_id.append(user_id)
    if first_user:
        if user_id in first_user_id:
            await start_handler(message)
    else:
        await start_handler(message)

async def start_handler(message: types.Message):
    user_id = message.chat.id
    msg = FN_JSON["msg"]["en"]["start.hello"]
    bot_msg = await bot.send_message(user_id, msg, parse_mode="HTML")
    user_data = await read_user_info(user_id)
    if not user_data:
        locale = message.from_user.locale
        user_lang = locale.language
        if user_lang != "en" and bool(FN_JSON["lang"].get(user_lang, 0)):
            lang_name = locale.english_name
            msg += FN_JSON["msg"]["en"]["lang.detect"].format(lang_name)
            await bot.edit_message_text(msg, user_id, bot_msg.message_id, parse_mode="HTML")
        else:
            user_lang = "en"
        await add_new_user(user_id, user_lang)
        await send_auth_link(message)
    else:
        if user_data.get("first_quest_msg", 0):
            await edit_user_info(user_id, "first_quest_msg", '')
        await quest_handler(message)

@dp.message_handler(commands=['quest'])
async def quest_handler(message: types.Message):
    user_id = message.chat.id
    if not first_user_id:
        first_user_id.append(user_id)
    if not user_id in first_user_id:
        return
    if message.text == "/quest":
        await message.delete()
    # Check user in auth.json
    if not await auth_checker(user_id):
        msg = FN_JSON["msg"]["en"]["error.go.login"]
        bot_msg = await bot.send_message(user_id, msg)
        await edit_user_info(user_id, "msg_for_del", bot_msg.message_id, add=True)
        await send_auth_link(message)
        return
    msg = FN_JSON["msg"]["en"]["req.quests.wait"]
    bot_msg = await bot.send_message(user_id, msg)
    await edit_user_info(user_id, "msg_for_del", bot_msg.message_id, add=True)
    # Check tokens and get quest
    if await tokens_check_and_update(user_id):
        await start_quest_api(user_id)

@dp.message_handler(commands=['lang'], is_admin=first_user)
async def lang_handler(message: types.Message):
    user_id = message.chat.id
    await message.delete()
    msg = FN_JSON["msg"]["en"]["choose.lang"]
    keyboard = await asyncio.to_thread(gen_lang_buttons)
    await bot.send_message(user_id, msg, reply_markup=keyboard)

@dp.message_handler(commands=['status'], is_admin=first_user)
async def status_handler(message: types.Message):
    user_id = message.chat.id
    await message.delete()
    msg = await asyncio.to_thread(server_status)
    botmsg = await bot.send_message(user_id, msg, parse_mode="HTML")
    await later_del_msg([botmsg], time=10)

@dp.message_handler(commands=['stats'], is_admin=first_user)
async def stats_handler(message: types.Message):
    user_id = message.chat.id
    await message.delete()
    user_data = await read_user_info(user_id)
    if user_data:
        quest_stats = user_data['stats']['quest']
        skip_stats = user_data['stats']['skips']
        msg = FN_JSON['msg']['en']['user.bot.stats'].format(quest_stats, skip_stats)
        botmsg = await bot.send_message(user_id, msg, parse_mode="HTML")
    else:
        botmsg = await bot.send_message(user_id, "You're not in the auth.json!")
        await start_handler(message)
    await later_del_msg([botmsg], time=10)

@dp.message_handler(commands=['support'], is_admin=first_user)
async def support_handler(message: types.Message):
    user_id = message.chat.id
    await message.delete()
    msg = FN_JSON['msg']['en']['support.contact']
    bot_msg = await bot.send_message(user_id, msg, parse_mode="HTML")
    await later_del_msg([bot_msg], time=60)

def gen_lang_buttons():
    keyboard = InlineKeyboardMarkup(row_width=2)
    buttons = []
    for button_id, name in FN_JSON["lang"].items():
        button_id = f"lang:{button_id}:{name}"
        button = InlineKeyboardButton(name, callback_data=button_id)
        buttons.append(button)
    keyboard.add(*buttons)
    return keyboard

async def gen_quest_buttons(user_id: int, quest_json: dict = None):
    keyboard = InlineKeyboardMarkup(row_width=1)
    if quest_json is None: # from confirm_button_click() = no
        user_data = await read_user_info(user_id)
        buttons = user_data.get('buttons')
        for button_id, button_name in buttons.items():
            button = InlineKeyboardButton(button_name, callback_data=button_id)
            keyboard.add(button)
    else: # from process_quests()
        buttons_data = {}
        for quest_id, data in quest_json.items():
            button_name = data['quest_name']
            button_id = f"quest:{quest_id}"
            button = InlineKeyboardButton(button_name, callback_data=button_id)
            keyboard.add(button)
            buttons_data[button_id] = button_name
        await edit_user_info(user_id, 'buttons', buttons_data)
    return keyboard

async def gen_confirm_buttons(message: types.Message, button_id: str):
    confirm_keyboard = InlineKeyboardMarkup(row_width=2)
    yes_button = InlineKeyboardButton("Yes", callback_data=f"confirm:{button_id}:yes")
    no_button = InlineKeyboardButton("No", callback_data=f"confirm:{button_id}:no")
    confirm_keyboard.row(yes_button, no_button)
    await bot.edit_message_reply_markup(
        message.chat.id,
        message.message_id,
        reply_markup=confirm_keyboard
    )

async def gen_quests_msg(quest_json: dict):
    time_now = await asyncio.to_thread(get_time, "text")
    msg = f"{time_now}\n\n"
    separator = "┄" * 15
    last_item = len(quest_json) - 1
    for item, (_, data) in enumerate(quest_json.items()):
        if item == last_item:
            separator = ""
        difficulty = data['difficulty']
        difficulty = f"{difficulty}/5 (≈{difficulty*20} mins)"
        msg += FN_JSON["msg"]["en"]["quest.pattern"].format(
            data['quest_name'], data['progress'],
            data['reward'], difficulty, separator
        )
    return msg

@dp.callback_query_handler(lambda query: query.data.startswith('lang:'))
async def lang_button_click(callback_query: CallbackQuery):
    user_id = callback_query.message.chat.id
    msg_id = callback_query.message.message_id
    _, lang_code, name = callback_query.data.split(':')
    await edit_user_info(user_id, 'lang', lang_code)
    msg = FN_JSON["msg"]["en"]["lang.changed"].format(name.upper())
    bot_msg = await bot.edit_message_text(msg, user_id, msg_id,
                                          parse_mode="HTML", reply_markup=None)
    await quest_handler(callback_query.message)
    await later_del_msg([bot_msg], time=5)

@dp.callback_query_handler(lambda query: query.data.startswith('quest:'))
async def quest_button_click(callback_query: CallbackQuery):
    _, quest_id = callback_query.data.split(':')
    await gen_confirm_buttons(callback_query.message, quest_id)

@dp.callback_query_handler(lambda query: query.data.startswith('confirm:'))
async def confirm_button_click(callback_query: CallbackQuery):
    _, quest_id, confirm = callback_query.data.split(':')
    user_id = callback_query.message.chat.id
    msg_id = callback_query.message.message_id
    if confirm == 'yes':
        data = await read_user_info(user_id)
        headers = data.get('headers')
        account_id = data.get('acc_token').get('account_id')
        if await quest_reroll(quest_id, headers, account_id): # request
            await bot.answer_callback_query(callback_query.id,
                                            "🔥Quest rerolled!🔥")
            await edit_user_info(user_id, new_data="skips") # +1 stats
        await edit_user_info(user_id, 'buttons', {}) # Reset buttons for click "no"
        await quest_handler(callback_query.message) # update quest list anyway
    elif confirm == 'no':
        await bot.edit_message_reply_markup(
            user_id,
            msg_id,
            reply_markup=await gen_quest_buttons(user_id)
        )
