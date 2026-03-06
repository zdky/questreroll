# 📬 Error?
# Is something broken? Text me about it, we'll be sure to fix it!
# Contact: https://t.me/drnvbot
# or my Github: https://github.com/zdky/questreroll/issues
import asyncio

from tg import dp, log, tg_token, bot
from utils import create_auth_json


async def main() -> None:
    create_auth_json()
    if len(tg_token) > 20:
        await dp.start_polling(bot)
    else:
        log.error("Please insert your telegram bot token in 'config.py'")


if __name__ == '__main__':
    asyncio.run(main())
