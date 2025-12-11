from subprocess import call as scall
from sys import executable
from os import execl as osexecl
from html import escape
from pyrogram.enums import ChatType

from ..helper.utils.btns import EchoButtons
from ..helper.utils.msg_util import send_message, send_file, edit_reply_markup
from .. import LOGGER, user_data, auth_chats, sudo_users
from ..helper.utils.db import database
from ..helper.utils.xtra import _update_user_ldata, safe_int, _task

@_task
async def _authorize(client, message):
    try:
        msg = message.text.split()
        chat_id = None
        thread_id = None

        if len(msg) > 1:
            token = msg[1].strip()
            if "|" in token:
                parts = token.split("|", 1)
                chat_id = safe_int(parts[0])
                thread_id = safe_int(parts[1], default=None)
            else:
                chat_id = safe_int(token)

            if not chat_id:
                return await send_message(message, "Invalid chat id!")
        elif message.reply_to_message:
            reply_to = message.reply_to_message
            chat_id = (reply_to.from_user or reply_to.sender_chat).id
        else:
            if getattr(message, "is_topic_message", False):
                thread_id = message.message_thread_id
            chat_id = message.chat.id

        if chat_id in user_data and user_data[chat_id].get("AUTH"):
            if (
                thread_id is not None
                and thread_id in user_data[chat_id].get("thread_ids", [])
                or thread_id is None
            ):
                text = "Already Authorized!"
            else:
                if "thread_ids" in user_data[chat_id]:
                    user_data[chat_id]["thread_ids"].append(thread_id)
                else:
                    user_data[chat_id]["thread_ids"] = [thread_id]
                await database._update_user_data(chat_id)
                text = "Authorized"
        else:
            _update_user_ldata(chat_id, "AUTH", True)
            if thread_id is not None:
                _update_user_ldata(chat_id, "thread_ids", [thread_id])
            await database._update_user_data(chat_id)
            text = "Authorized"

        await send_message(message, text)
    except Exception as e:
        LOGGER.error(f"authorize error: {e}")

@_task
async def _unauthorize(client, message):
    try:
        msg = message.text.split()
        chat_id = None
        thread_id = None

        if len(msg) > 1:
            token = msg[1].strip()
            if "|" in token:
                parts = token.split("|", 1)
                chat_id = safe_int(parts[0])
                thread_id = safe_int(parts[1], default=None)
            else:
                chat_id = safe_int(token)

            if not chat_id:
                return await send_message(message, "Invalid chat id!")
        elif message.reply_to_message:
            reply_to = message.reply_to_message
            chat_id = (reply_to.from_user or reply_to.sender_chat).id
        else:
            if getattr(message, "is_topic_message", False):
                thread_id = message.message_thread_id
            chat_id = message.chat.id

        if chat_id in user_data and user_data[chat_id].get("AUTH"):
            if thread_id is not None and thread_id in user_data[chat_id].get(
                "thread_ids", []
            ):
                user_data[chat_id]["thread_ids"].remove(thread_id)
                await database._update_user_data(chat_id)
                text = "Unauthorized"
            else:
                _update_user_ldata(chat_id, "AUTH", False)
                await database._update_user_data(chat_id)
                text = "Unauthorized"
        else:
            text = "Already Unauthorized!"

        await send_message(message, text)
    except Exception as e:
        LOGGER.error(f"unauthorize error: {e}")
        
@_task
async def _log_cmd(client, message):
    try:
        if not message.from_user:
            return
        uid = message.from_user.id
        btns = (
            EchoButtons()
            .data_button("Log Disp", f"log {uid} disp")
            .data_button("Close", f"log {uid} close")
            .build(2)
        )
        await send_file(
            message,
            "log.txt",
            caption="Bot log file",
            buttons=btns,
        )
    except Exception as e:
        LOGGER.error(f"log_cmd error: {e}")

@_task
async def _log_cb(client, query):
    try:
        data = query.data.split()
        message = query.message
        if not query.from_user:
            return
        user_id = query.from_user.id
        if user_id != int(data[1]):
            await query.answer("Not yours!", show_alert=True)
            return

        action = data[2]

        if action == "close":
            await query.answer()
            try:
                await message.delete()
            except Exception:
                pass
            try:
                if message.reply_to_message:
                    await message.reply_to_message.delete()
            except Exception:
                pass
            return

        if action == "disp":
            await query.answer("Fetching log..")
            try:
                with open("log.txt", "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
            except FileNotFoundError:
                await send_message(message, "log.txt not found.")
                return

            def parse(line):
                parts = line.split("] [", 1)
                return f"[{parts[1]}" if len(parts) > 1 else line

            res = []
            total = 0
            for line in reversed(content.splitlines()):
                line = parse(line)
                res.append(line)
                total += len(line) + 1
                if total > 3500:
                    break

            log_text = escape("\n".join(reversed(res)))

            text = (
                f"<b>Showing Last {len(res)} Lines from log.txt:</b>\n\n"
                f"----------<b>START LOG</b>----------\n\n"
                f"<blockquote expandable>{log_text}</blockquote>\n"
                f"----------<b>END LOG</b>----------"
            )

            btns = (
                EchoButtons()
                .data_button("Close", f"log {user_id} close")
                .build(1)
            )

            await send_message(
                message,
                text,
                buttons=btns,
                disable_web_page_preview=True,
            )

            await edit_reply_markup(message, None)
    except Exception as e:
        LOGGER.error(f"log_cb error: {e}")

@_task
async def _restart(client, message):
    try:
        btns = (
            EchoButtons()
            .data_button("Yes", "restart confirm")
            .data_button("No", "restart cancel")
            .build(2)
        )
        await send_message(
            message,
            "<i>Are you sure you want to restart the bot?</i>",
            buttons=btns,
        )
    except Exception as e:
        LOGGER.error(f"restart_cmd error: {e}")

@_task
async def _restart_cb(client, query):
    try:
        await query.answer()
        data = query.data.split()
        action = data[1]
        message = query.message
        reply_to = message.reply_to_message

        if action == "cancel":
            try:
                await message.delete()
            except Exception:
                pass
            try:
                if reply_to:
                    await reply_to.delete()
            except Exception:
                pass
            return

        if action == "confirm":
            try:
                await message.delete()
            except Exception:
                pass

            restart_msg = await send_message(
                reply_to or message,
                "<i>Restarting...</i>",
            )

            with open(".restartmsg", "w") as f:
                f.write(f"{restart_msg.chat.id}\n{restart_msg.id}\n")

            scall(f'"{executable}" update.py', shell=True)

            osexecl(executable, executable, "-m", "echobotz")

    except Exception as e:
        LOGGER.error(f"restart_cb error: {e}")
