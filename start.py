#📬 Error?
# Is something broken? Text me about it, we'll be sure to fix it!
# Contact: https://t.me/drnvbot
# or my Github: https://github.com/zdky/questreroll/issues
from time import sleep
from aiogram import executor
from tg import dp, log, tg_token

# Start bot
if __name__ == '__main__':
    if len(tg_token) > 20:
        while True:
            try:
                executor.start_polling(dp, skip_updates=True)
            except Exception as error:
                log.critical(f"BOT DOWN, ERROR: {error}")
            sleep(20)
    else:
        log.error("Please insert your telegram bot token in 'config.py'")
