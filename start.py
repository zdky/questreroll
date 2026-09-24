# 📬 Error?
# Is something broken? Text me about it, we'll be sure to fix it!
# Contact: https://t.me/drnvbot
# or my Github: https://github.com/zdky/questreroll/issues
import asyncio
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from config import tg_token
from tg import router
from utils import log


async def main() -> None:
    bot = Bot(token=tg_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()
    dp.include_router(router)
    # polling reconnects by itself on network errors
    await dp.start_polling(bot, drop_pending_updates=True)


# Start bot
if __name__ == "__main__":
    if len(tg_token) < 20:
        log.error(
            "Please insert your telegram bot token in 'config.py' (or TG_TOKEN env)"
        )
        sys.exit(1)
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
