import os

# Your telegram token bot via @BotFather #! required
# (can also be passed through the TG_TOKEN environment variable)
tg_token = os.getenv("TG_TOKEN", "YOUR TOKEN")

# True = for bot use only by you / False = for everyone #? optional
first_user = True

# Telegram ids allowed to use the bot when first_user = True #? optional
# like this: [123456789]
# If empty, users already saved in auth.json are allowed,
# otherwise the first user who sends /start becomes the owner.
first_user_id = []

# If you want console log file
create_log_file = True
