# pylint: disable=C0116, C0114, W0511, W0718
import asyncio
import re

from aiogram import Bot, Dispatcher, F, Router, types
from aiogram.filters import BaseFilter, Command
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup

from config import first_user, first_user_id, tg_token
from constants import FN_JSON, Links
from database import add_new_user, edit_user_info, read_user_info
from fortnite import (
    quest_reroll,
    start_3step_login,
    start_quest_api,
    tokens_check_and_update,
)
from utils import get_time, log, server_status


bot = Bot(token=tg_token)
dp = Dispatcher()
router = Router()
dp.include_router(router)


class IsAdmin(BaseFilter):
    def __init__(self, is_admin: bool):
        self.is_admin = is_admin

    async def __call__(self, message: types.Message) -> bool:
        if first_user:
            return (message.from_user.id in first_user_id) == self.is_admin
        return True


async def delete_all_msgs(msgs_list: list, user_id: int):
    """Deletion all telegram messages by id

    Args:
        msgs_list (list): telegram messages id
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


async def later_del_msg(messages: list = None, time: int = 0):
    """Delayed deletion of 1+ messages

    Args:
        messages (list): telegram Message objects
        time (int): seconds before deleting
    """
    if messages:
        log.info(f"Delete messages user_id: {messages[0].chat.id}, time: {time}'s")
        await asyncio.sleep(time)
        for msg in messages:
            try:
                log.info(f"Deleted msg with id: {msg.message_id}")
                await msg.delete()
            except Exception as error:
                log.warning(f"Message already delete: {error}")


async def send_auth_link(message: types.Message):
    msg = FN_JSON["msg"]["en"]["send.auth.code"].format(Links.auth_code)
    bot_msg = await message.answer(msg, parse_mode="HTML", disable_web_page_preview=True)
    if message.chat.id not in first_user_id:
        await message.answer_animation(
            FN_JSON["msg"]["en"]["demo.gif"],
            caption=FN_JSON["msg"]["en"]["second.start"],
            parse_mode="HTML",
        )
    await edit_user_info(message.chat.id, "msg_for_del", bot_msg.message_id)


@router.message(F.text & ~F.text.startswith("/") & F.func(lambda msg: len(msg.text) < 32))
async def authcode_error(message: types.Message):
    if message.chat.id not in first_user_id:
        return
    msg = FN_JSON["msg"]["en"]["incorrect.auth.code"].format(len(message.text))
    bot_msg = await message.answer(msg)
    await later_del_msg([bot_msg, message], time=15)


@router.message(F.text & ~F.text.startswith("/") & F.func(lambda msg: len(msg.text) >= 32))
async def authcode_handler(message: types.Message):
    if message.chat.id not in first_user_id:
        return
    auth_code = re.search(r"[0-9a-f]{32}", message.text)
    if auth_code:
        if not await auth_checker(message):
            bot_msg = await message.answer(FN_JSON["msg"]["en"]["auth.correct"])
            await later_del_msg([bot_msg, message], time=2)
            if await start_3step_login(message.chat.id, auth_code[0]):
                await quest_handler(message)
                return
        msg = FN_JSON["msg"]["en"]["error.already.auth"]
        bot_msg = await message.answer(msg)
        await later_del_msg([bot_msg, message], time=10)
    else:
        await authcode_error(message)


async def auth_checker(message: types.Message) -> bool:
    """FN tokens checker in auth.json by user_id

    Returns: True/False
    """
    user_id = message.chat.id
    user_data = await read_user_info(user_id)
    if user_data:
        acc_data = bool(user_data.get("acc_token", 0))
        fn_data = bool(user_data.get("fn_token", 0))
        if acc_data and fn_data:
            return True
    else:
        bot_msg = await message.answer(FN_JSON["msg"]["en"]["error.not.auth"])
        await later_del_msg([bot_msg], time=60)
    return False


@router.message(Command("start"))
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
    bot_msg = await message.answer(msg, parse_mode="HTML")
    user_data = await read_user_info(user_id)
    if not user_data:
        user_lang = message.from_user.language_code
        if user_lang != "en" and bool(FN_JSON["lang"].get(user_lang, 0)):
            msg += FN_JSON["msg"]["en"]["lang.detect"].format(user_lang)
            await bot_msg.edit_text(msg, parse_mode="HTML")
        else:
            user_lang = "en"
        await add_new_user(user_id, user_lang)
        await send_auth_link(message)
    else:
        if user_data.get("first_quest_msg", 0):
            await edit_user_info(user_id, "first_quest_msg", "")
        await quest_handler(message)


@router.message(Command("quest"))
async def quest_handler(message: types.Message):
    user_id = message.chat.id
    if not first_user_id:
        first_user_id.append(user_id)
    if user_id not in first_user_id:
        return
    if message.text == "/quest":
        await message.delete()
    if not await auth_checker(message):
        bot_msg = await message.answer(FN_JSON["msg"]["en"]["error.go.login"])
        await edit_user_info(user_id, "msg_for_del", bot_msg.message_id)
        await send_auth_link(message)
        return
    bot_msg = await message.answer(FN_JSON["msg"]["en"]["req.quests.wait"])
    await edit_user_info(user_id, "msg_for_del", bot_msg.message_id)
    if await tokens_check_and_update(user_id):
        await start_quest_api(user_id)


@router.message(Command("lang"), IsAdmin(is_admin=first_user))
async def lang_handler(message: types.Message):
    await message.delete()
    keyboard = await asyncio.to_thread(gen_lang_buttons)
    await message.answer(FN_JSON["msg"]["en"]["choose.lang"], reply_markup=keyboard)


@router.message(Command("status"), IsAdmin(is_admin=first_user))
async def status_handler(message: types.Message):
    await message.delete()
    msg = await asyncio.to_thread(server_status)
    bot_msg = await message.answer(msg, parse_mode="HTML")
    await later_del_msg([bot_msg], time=10)


@router.message(Command("stats"), IsAdmin(is_admin=first_user))
async def stats_handler(message: types.Message):
    await message.delete()
    user_data = await read_user_info(message.chat.id)
    if user_data:
        quest_stats = user_data["stats"]["quest"]
        skip_stats = user_data["stats"]["skips"]
        msg = FN_JSON["msg"]["en"]["user.bot.stats"].format(quest_stats, skip_stats)
        bot_msg = await message.answer(msg, parse_mode="HTML")
    else:
        bot_msg = await message.answer("You're not in the auth.json!")
        await start_handler(message)
    await later_del_msg([bot_msg], time=10)


@router.message(Command("support"), IsAdmin(is_admin=first_user))
async def support_handler(message: types.Message):
    await message.delete()
    bot_msg = await message.answer(
        FN_JSON["msg"]["en"]["support.contact"], parse_mode="HTML"
    )
    await later_del_msg([bot_msg], time=60)


def gen_lang_buttons() -> InlineKeyboardMarkup:
    buttons = []
    for button_id, name in FN_JSON["lang"].items():
        cb_data = f"lang:{button_id}:{name}"
        buttons.append(InlineKeyboardButton(text=name, callback_data=cb_data))
    rows = [buttons[i:i + 2] for i in range(0, len(buttons), 2)]
    return InlineKeyboardMarkup(inline_keyboard=rows)


async def gen_quest_buttons(user_id: int, quest_json: dict = None) -> InlineKeyboardMarkup:
    rows = []
    if quest_json is None:  # from confirm_button_click() = no
        user_data = await read_user_info(user_id)
        buttons = user_data.get("buttons", {})
        for button_id, button_name in buttons.items():
            rows.append([InlineKeyboardButton(text=button_name, callback_data=button_id)])
    else:  # from process_quests()
        buttons_data = {}
        for quest_id, data in quest_json.items():
            button_name = data["quest_name"]
            button_id = f"quest:{quest_id}"
            rows.append([InlineKeyboardButton(text=button_name, callback_data=button_id)])
            buttons_data[button_id] = button_name
        await edit_user_info(user_id, "buttons", buttons_data)
    return InlineKeyboardMarkup(inline_keyboard=rows)


async def gen_confirm_buttons(message: types.Message, button_id: str):
    confirm_keyboard = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="Yes", callback_data=f"confirm:{button_id}:yes"),
        InlineKeyboardButton(text="No", callback_data=f"confirm:{button_id}:no"),
    ]])
    await message.edit_reply_markup(reply_markup=confirm_keyboard)


async def gen_quests_msg(quest_json: dict) -> str:
    time_now = await asyncio.to_thread(get_time, "text")
    msg = f"{time_now}\n\n"
    separator = "┄" * 15
    last_item = len(quest_json) - 1
    for item, (_, data) in enumerate(quest_json.items()):
        if item == last_item:
            separator = ""
        difficulty = data["difficulty"]
        difficulty = f"{difficulty}/5 (≈{difficulty * 20} mins)"
        msg += FN_JSON["msg"]["en"]["quest.pattern"].format(
            data["quest_name"], data["progress"], data["reward"], difficulty, separator
        )
    return msg


@router.callback_query(F.data.startswith("lang:"))
async def lang_button_click(callback_query: CallbackQuery):
    _, lang_code, name = callback_query.data.split(":")
    await edit_user_info(callback_query.message.chat.id, "lang", lang_code)
    msg = FN_JSON["msg"]["en"]["lang.changed"].format(name.upper())
    bot_msg = await callback_query.message.edit_text(msg, parse_mode="HTML", reply_markup=None)
    await quest_handler(callback_query.message)
    await later_del_msg([bot_msg], time=5)


@router.callback_query(F.data.startswith("quest:"))
async def quest_button_click(callback_query: CallbackQuery):
    _, quest_id = callback_query.data.split(":")
    await gen_confirm_buttons(callback_query.message, quest_id)
    await callback_query.answer()


@router.callback_query(F.data.startswith("confirm:"))
async def confirm_button_click(callback_query: CallbackQuery):
    _, quest_id, confirm = callback_query.data.split(":")
    user_id = callback_query.message.chat.id
    if confirm == "yes":
        data = await read_user_info(user_id)
        headers = data.get("headers")
        account_id = data.get("acc_token").get("account_id")
        if await quest_reroll(quest_id, headers, account_id):
            await callback_query.answer("🔥Quest rerolled!🔥")
            await edit_user_info(user_id, "skips")  # +1 stats
        else:
            await callback_query.answer()
        await edit_user_info(user_id, "buttons", {})
        await quest_handler(callback_query.message)
    elif confirm == "no":
        await callback_query.message.edit_reply_markup(
            reply_markup=await gen_quest_buttons(user_id)
        )
        await callback_query.answer()
