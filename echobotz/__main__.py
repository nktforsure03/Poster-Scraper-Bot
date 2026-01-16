import os
import asyncio
from datetime import datetime
from logging import Formatter
from threading import Thread

from flask import Flask
from pytz import timezone as tz
from pyrogram import idle

from config import Config
from . import LOGGER
from .core.EchoClient import EchoBot
from .core.plugs import add_plugs
from .helper.utils.db import database
from .helper.utils.bot_cmds import _get_bot_commands

# --- STICKY WEB SERVER FOR RENDER ---
app = Flask(__name__)

@app.route('/')
def health_check():
    return "Bot is alive and running!", 200

def run_web_server():
    # Render uses the 'PORT' environment variable
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def start_keep_alive():
    t = Thread(target=run_web_server)
    t.daemon = True
    t.start()
# ------------------------------------

def main():
    def changetz(*args):
        return datetime.now(tz(Config.TIMEZONE)).timetuple()

    Formatter.converter = changetz

    loop = asyncio.get_event_loop()
    loop.run_until_complete(database._load_all())

    EchoBot.start()
    EchoBot.set_bot_commands(_get_bot_commands())
    LOGGER.info("Bot Cmds Set Successfully")
    me = EchoBot.get_me()
    LOGGER.info(f"Echo Bot Started as: @{me.username}")

    if os.path.isfile(".restartmsg"):
        try:
            with open(".restartmsg") as f:
                chat_id, msg_id = map(int, f.read().splitlines())

            now = datetime.now(tz(Config.TIMEZONE)).strftime(
                "%d/%m/%Y %I:%M:%S %p"
            )

            EchoBot.edit_message_text(
                chat_id=chat_id,
                message_id=msg_id,
                text=f"<b>Restarted Successfully!</b>\n<code>{now}</code>",
                disable_web_page_preview=True,
            )

            os.remove(".restartmsg")
        except Exception as e:
            LOGGER.error(f"Restart notify error: {e}")

    add_plugs()
    
    # Start the web server automatically for Render
    LOGGER.info("Starting Render Keep-Alive Web Server...")
    start_keep_alive()
    
    idle()

    EchoBot.stop()
    LOGGER.info("Echo Client stopped.")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        LOGGER.error(f"Error deploying: {e}")
        try:
            EchoBot.stop()
        except Exception:
            pass
