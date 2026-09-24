"""Telegram bot (aiogram 3): handlers, quest messages and daily scheduler."""

import asyncio
import html
import re
from contextlib import suppress
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware, Bot, F, Router
from aiogram.exceptions import TelegramAPIError, TelegramBadRequest
from aiogram.filters import Command, CommandStart
from aiogram.filters.callback_data import CallbackData
from aiogram.types import (
    BotCommand,
    CallbackQuery,
    FSInputFile,
    InlineKeyboardMarkup,
    Message,
    TelegramObject,
    User,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import first_user, first_user_id
from constants import DEMO_GIF_PATH, FN_JSON, LANGS, Links, text
from database import db
from fortnite import (
    EpicAPIError,
    api,
    get_valid_token,
    login,
    parse_quests,
    rerolls_left,
)
from utils import log, seconds_until_daily_reset, server_status, time_text

AUTH_CODE_RE = re.compile(r"\b[0-9a-f]{32}\b")
QUEST_SEPARATOR = "┄" * 15

router = Router()
router.message.filter(F.chat.type == "private")

# ids of bot owners (first_user mode): from config, else users from auth.json,
# else the first user who sends /start
owners: set[int] = set(first_user_id) or (set(db.user_ids()) if first_user else set())

scheduled: dict[int, asyncio.Task] = {}  # user_id: daily quest update task
background_tasks: set[asyncio.Task] = set()  # keep references to running tasks
user_locks: dict[int, asyncio.Lock] = {}  # one quest request per user at a time
demo_gif: dict[str, str] = {"file_id": FN_JSON["msg"]["en"]["demo.gif"]}


# ------------------------------------------------------------------ callbacks
class LangCallback(CallbackData, prefix="lang"):
    code: str


class QuestCallback(CallbackData, prefix="quest"):
    quest_id: str


class ConfirmCallback(CallbackData, prefix="confirm"):
    quest_id: str
    confirm: bool


# ------------------------------------------------------------------ access
class AccessMiddleware(BaseMiddleware):
    """Ignore everyone except owners when first_user = True."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user: User | None = data.get("event_from_user")
        if user is None:
            return None
        if (
            not owners
            and isinstance(event, Message)
            and event.chat.type == "private"
            and (event.text or "").startswith("/start")
        ):
            owners.add(user.id)
            log.info(f"User {user.id} (@{user.username}) is the bot owner now")
        if first_user and user.id not in owners:
            return None
        return await handler(event, data)


router.message.outer_middleware(AccessMiddleware())
router.callback_query.outer_middleware(AccessMiddleware())


# ------------------------------------------------------------------ helpers
def run_background(coro: Awaitable) -> asyncio.Task:
    task = asyncio.create_task(coro)
    background_tasks.add(task)
    task.add_done_callback(background_tasks.discard)
    return task


async def safe_delete(bot: Bot, chat_id: int, msg_id: int) -> None:
    try:
        await bot.delete_message(chat_id, msg_id)
    except TelegramAPIError as error:
        log.debug(f"Message {msg_id} wasn't deleted: {error}")


def delete_later(*messages: Message | None, delay: float = 0) -> None:
    """Delete messages after delay seconds (without blocking the handler)."""

    async def _delete():
        await asyncio.sleep(delay)
        for msg in messages:
            if msg is not None:
                await safe_delete(msg.bot, msg.chat.id, msg.message_id)

    run_background(_delete())


async def delete_tracked_msgs(bot: Bot, user_id: int) -> None:
    """Delete all service messages saved in msg_for_del."""
    for msg_id in await db.pop_msgs_for_del(user_id):
        await safe_delete(bot, user_id, msg_id)


async def send_tracked(bot: Bot, user_id: int, msg: str) -> Message:
    """Send a message that will be deleted with the next quest list."""
    bot_msg = await bot.send_message(user_id, msg, disable_web_page_preview=True)
    await db.add_msg_for_del(user_id, bot_msg.message_id)
    return bot_msg


def detect_lang(user: User) -> str:
    """Fortnite language by telegram language_code (e.g. "pt-br" -> "pt-BR")."""
    user_lang = (user.language_code or "en").lower()
    codes = {code.lower(): code for code in LANGS}
    if user_lang in codes:
        return codes[user_lang]
    base = user_lang.split("-")[0]
    return next((code for code in LANGS if code.lower().split("-")[0] == base), "en")


async def send_auth_link(message: Message) -> None:
    bot, user_id = message.bot, message.chat.id
    await send_tracked(bot, user_id, text("send.auth.code", Links.auth_code))
    if user_id in owners:
        return
    # warn other users that they're about to give their account to someone else's bot
    try:
        await message.answer_animation(
            demo_gif["file_id"], caption=text("second.start")
        )
    except TelegramBadRequest:  # file_id belongs to another bot, upload the file
        bot_msg = await message.answer_animation(
            FSInputFile(DEMO_GIF_PATH), caption=text("second.start")
        )
        demo_gif["file_id"] = bot_msg.animation.file_id


# ------------------------------------------------------------------ keyboards
def lang_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for code, name in LANGS.items():
        builder.button(text=name, callback_data=LangCallback(code=code))
    builder.adjust(2)
    return builder.as_markup()


def quest_keyboard(buttons: dict[str, str]) -> InlineKeyboardMarkup:
    """buttons: {quest_id: quest_name}"""
    builder = InlineKeyboardBuilder()
    for quest_id, name in buttons.items():
        builder.button(text=name, callback_data=QuestCallback(quest_id=quest_id))
    builder.adjust(1)
    return builder.as_markup()


def confirm_keyboard(quest_id: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(
        text="Yes", callback_data=ConfirmCallback(quest_id=quest_id, confirm=True)
    )
    builder.button(
        text="No", callback_data=ConfirmCallback(quest_id=quest_id, confirm=False)
    )
    return builder.as_markup()


# ------------------------------------------------------------------ quests
def quests_text(quests: dict) -> str:
    parts = []
    for quest in quests.values():
        difficulty = quest["difficulty"]
        parts.append(
            text(
                "quest.pattern",
                html.escape(quest["quest_name"]),
                html.escape(quest["progress"]),
                html.escape(quest["reward"]),
                f"{difficulty}/5 (≈{difficulty * 20} mins)",
                QUEST_SEPARATOR,
            )
        )
    msg = f"{time_text()}\n\n" + "".join(parts)
    # no separator after the last quest
    return msg.removesuffix(f"{QUEST_SEPARATOR}\n") if parts else msg


async def show_quest_message(
    bot: Bot, user_id: int, msg: str, keyboard: InlineKeyboardMarkup | None
) -> None:
    """Edit the previous quest message or send a new one."""
    old_msg_id = (db.get(user_id) or {}).get("first_quest_msg")
    if old_msg_id:
        try:
            await bot.edit_message_text(
                text=msg, chat_id=user_id, message_id=old_msg_id, reply_markup=keyboard
            )
            return
        except TelegramBadRequest as error:
            if "message is not modified" in str(error):
                return
            log.info(
                f"Can't edit quest message {old_msg_id}, user_id: {user_id}: {error}"
            )
            await safe_delete(bot, user_id, old_msg_id)

    bot_msg = await bot.send_message(user_id, msg, reply_markup=keyboard)
    await db.update(user_id, first_quest_msg=bot_msg.message_id)
    log.info(f"New quest message user_id: {user_id}, msg_id: {bot_msg.message_id}")


async def refresh_quests(bot: Bot, user_id: int, notify: bool = True) -> None:
    """Request quests from Fortnite API and show them to the user.

    Args:
        notify: show "waiting" and error messages (False for silent daily update)
    """
    lock = user_locks.setdefault(user_id, asyncio.Lock())
    async with lock:
        user = db.get(user_id)
        if user is None:
            return
        if not user["fn_token"]:
            if notify:
                await send_tracked(bot, user_id, text("error.go.login"))
                await send_tracked(
                    bot, user_id, text("send.auth.code", Links.auth_code)
                )
            return

        if notify:
            await send_tracked(bot, user_id, text("req.quests.wait"))

        fn_token = await get_valid_token(user_id)
        if fn_token is None:
            await send_tracked(bot, user_id, text("error.tokens.died"))
            await send_tracked(bot, user_id, text("send.auth.code", Links.auth_code))
            return

        try:
            campaign = await api.get_campaign(fn_token)
        except EpicAPIError as error:
            log.error(f"refresh_quests(), user_id: {user_id}, {error}")
            if notify:
                await delete_tracked_msgs(bot, user_id)
                delete_later(
                    await bot.send_message(user_id, text("error.quests.failed")),
                    delay=30,
                )
            return

        await db.inc_stat(user_id, "quest")
        quests = parse_quests(campaign, user["lang"])
        keyboard = None
        if not quests:
            msg = text("no.active.quest", time_text())
        elif rerolls_left(campaign) > 0:
            buttons = {
                quest_id: quest["quest_name"] for quest_id, quest in quests.items()
            }
            await db.update(user_id, buttons=buttons)
            keyboard = quest_keyboard(buttons)
            msg = quests_text(quests) + text("click.button")
        else:
            msg = quests_text(quests) + text("already.replaced")

        await show_quest_message(bot, user_id, msg, keyboard)
        await delete_tracked_msgs(bot, user_id)
        schedule_daily_update(bot, user_id)


# ------------------------------------------------------------------ scheduler
def schedule_daily_update(bot: Bot, user_id: int) -> None:
    """Silently update the quest message every day at 00:05 UTC."""
    task = scheduled.get(user_id)
    if task is None or task.done():
        scheduled[user_id] = asyncio.create_task(daily_update(bot, user_id))


async def daily_update(bot: Bot, user_id: int) -> None:
    while True:
        await asyncio.sleep(seconds_until_daily_reset())
        user = db.get(user_id)
        if not user or not user["fn_token"]:
            break
        try:
            await refresh_quests(bot, user_id, notify=False)
        except Exception as error:  # keep the schedule alive on any error
            log.exception(f"daily_update(), user_id: {user_id}, {error}")
    scheduled.pop(user_id, None)


def schedule_all(bot: Bot) -> None:
    for user_id in db.user_ids():
        if (db.get(user_id) or {}).get("fn_token"):
            schedule_daily_update(bot, user_id)
    log.info(f"Daily quest update scheduled for {len(scheduled)} user(s)")


def cancel_all() -> None:
    for task in [*scheduled.values(), *background_tasks]:
        task.cancel()


# ------------------------------------------------------------------ commands
@router.message(CommandStart())
async def start_handler(message: Message, bot: Bot) -> None:
    user_id = message.chat.id
    msg = text("start.hello")
    user = db.get(user_id)
    if user is None:
        lang = detect_lang(message.from_user)
        if lang != "en":
            msg += text("lang.detect", LANGS[lang])
        await message.answer(msg)
        await db.add_user(user_id, lang)
        await send_auth_link(message)
        return

    await message.answer(msg)
    await db.update(user_id, first_quest_msg="")  # new quest message below "hello"
    await refresh_quests(bot, user_id)


@router.message(Command("quest"))
async def quest_handler(message: Message, bot: Bot) -> None:
    await safe_delete(bot, message.chat.id, message.message_id)
    if db.get(message.chat.id) is None:
        await start_handler(message, bot)
        return
    await refresh_quests(bot, message.chat.id)


@router.message(Command("lang"))
async def lang_handler(message: Message) -> None:
    delete_later(message)
    await message.answer(text("choose.lang"), reply_markup=lang_keyboard())


@router.message(Command("status"))
async def status_handler(message: Message) -> None:
    delete_later(message)
    bot_msg = await message.answer(await asyncio.to_thread(server_status))
    delete_later(bot_msg, delay=10)


@router.message(Command("stats"))
async def stats_handler(message: Message) -> None:
    delete_later(message)
    user = db.get(message.chat.id)
    if user is None:
        bot_msg = await message.answer(text("error.not.auth"))
    else:
        stats = user["stats"]
        bot_msg = await message.answer(
            text("user.bot.stats", stats["quest"], stats["skips"])
        )
    delete_later(bot_msg, delay=10)


@router.message(Command("support"))
async def support_handler(message: Message) -> None:
    delete_later(message)
    bot_msg = await message.answer(
        text("support.contact"), disable_web_page_preview=True
    )
    delete_later(bot_msg, delay=60)


# ------------------------------------------------------------------ auth code
@router.message(F.text, ~F.text.startswith("/"))
async def authcode_handler(message: Message, bot: Bot) -> None:
    user_id = message.chat.id
    auth_code = AUTH_CODE_RE.search(message.text.lower())
    if auth_code is None:
        bot_msg = await message.answer(
            html.escape(text("incorrect.auth.code", len(message.text)), quote=False)
        )
        delete_later(bot_msg, message, delay=15)
        return

    # the auth code gives access to the account, don't keep it in the chat
    await safe_delete(bot, user_id, message.message_id)

    user = db.get(user_id)
    if user is None:
        await db.add_user(user_id, detect_lang(message.from_user))
    elif user["fn_token"]:
        delete_later(await message.answer(text("error.already.auth")), delay=10)
        return

    status_msg = await message.answer(text("auth.correct"))
    logged_in = await login(user_id, auth_code[0])
    delete_later(status_msg, delay=2)
    if logged_in:
        await refresh_quests(bot, user_id)
    else:
        delete_later(await message.answer(text("error.auth.failed")), delay=30)


# ------------------------------------------------------------------ buttons
@router.callback_query(LangCallback.filter())
async def lang_button_click(
    callback: CallbackQuery, callback_data: LangCallback, bot: Bot
) -> None:
    await callback.answer()
    user_id = callback.from_user.id
    if callback_data.code not in LANGS or db.get(user_id) is None:
        return
    await db.update(user_id, lang=callback_data.code)
    if isinstance(callback.message, Message):
        bot_msg = await callback.message.edit_text(
            text("lang.changed", LANGS[callback_data.code].upper()), reply_markup=None
        )
        if isinstance(bot_msg, Message):
            delete_later(bot_msg, delay=5)
    if (db.get(user_id) or {}).get("fn_token"):
        await refresh_quests(bot, user_id)


@router.callback_query(QuestCallback.filter())
async def quest_button_click(
    callback: CallbackQuery, callback_data: QuestCallback
) -> None:
    await callback.answer()
    if isinstance(callback.message, Message):
        await callback.message.edit_reply_markup(
            reply_markup=confirm_keyboard(callback_data.quest_id)
        )


@router.callback_query(ConfirmCallback.filter())
async def confirm_button_click(
    callback: CallbackQuery, callback_data: ConfirmCallback, bot: Bot
) -> None:
    user_id = callback.from_user.id
    user = db.get(user_id)
    if user is None:
        await callback.answer()
        return

    if not callback_data.confirm:
        await callback.answer()
        if isinstance(callback.message, Message):
            await callback.message.edit_reply_markup(
                reply_markup=quest_keyboard(user["buttons"])
            )
        return

    fn_token = await get_valid_token(user_id)
    if fn_token is None:
        await callback.answer(text("error.tokens.died"), show_alert=True)
        await refresh_quests(bot, user_id)  # sends the auth link
        return
    try:
        await api.reroll_quest(fn_token, callback_data.quest_id)
    except EpicAPIError as error:
        log.error(f"confirm_button_click(), user_id: {user_id}, {error}")
        await callback.answer(text("error.reroll.failed"), show_alert=True)
    else:
        await callback.answer(text("quest.rerolled"))
        await db.inc_stat(user_id, "skips")
    await db.update(user_id, buttons={})
    await refresh_quests(bot, user_id)  # update the quest list anyway


# ------------------------------------------------------------------ lifecycle
BOT_COMMANDS = [
    BotCommand(command="quest", description="Your quest list"),
    BotCommand(command="lang", description="Change quests language"),
    BotCommand(command="stats", description="Your bot stats"),
    BotCommand(command="status", description="Server load"),
    BotCommand(command="support", description="If something broke"),
]


@router.startup()
async def on_startup(bot: Bot) -> None:
    with suppress(TelegramAPIError):
        await bot.set_my_commands(BOT_COMMANDS)
    schedule_all(bot)
    me = await bot.get_me()
    log.info(f"Bot @{me.username} started")


@router.shutdown()
async def on_shutdown() -> None:
    cancel_all()
    await api.close()
    log.info("Bot stopped")
