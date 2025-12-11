from pyrogram.enums import ChatType

from .. import LOGGER
from ..eco import echo
from ..helper.ott import _extract_url_from_message, _fetch_ott_info
from ..helper.utils.btns import EchoButtons
from ..helper.utils.msg_util import send_message, edit_message
from ..helper.utils.xtra import _task

@_task
async def _poster_cmd(client, message):
    try:
        if message.chat.type not in (ChatType.PRIVATE, ChatType.GROUP, ChatType.SUPERGROUP):
            return

        if not getattr(message, "command", None) or not message.command:
            return

        cmd_name = message.command[0].lstrip("/").split("@")[0].lower()

        target_url = _extract_url_from_message(message)
        if not target_url:
            return await send_message(
                message,
                (
                    "<b>Usage:</b>\n"
                    f"/{cmd_name} &lt;ott-url&gt;  <i>or</i>\n"
                    f"Reply to a URL with <code>/{cmd_name}</code>"
                ),
            )

        wait_msg = await send_message(
            message,
            f"<i>Fetching poster for:</i>\n<code>{target_url}</code>",
        )

        info, err = await _fetch_ott_info(cmd_name, target_url)
        if err:
            return await edit_message(
                wait_msg,
                f"<b>Error:</b> <code>{err}</code>",
            )

        title = info["title"]
        year = info["year"]
        otype = info["type"]
        source = info["source"]
        poster = info["poster"]
        landscape = info["landscape"]

        header_lines = [f"<b>📺 Source:</b> {source}"]
        if title and title != "N/A":
            header_lines.append(f"<b>🎬 Title:</b> {title}")
        if year and year != "N/A":
            header_lines.append(f"<b>📅 Year:</b> {year}")
        if otype and otype != "N/A":
            header_lines.append(f"<b>🎞 Type:</b> {otype}")

        header_lines.append("")
        header_lines.append("<b>✺ Original URL:</b>")
        header_lines.append(f"<code>{target_url}</code>")

        poster_lines = []
        if poster:
            poster_lines.append(f"• Portrait: <a href=\"{poster}\">Click Here</a>")
        if landscape and landscape != poster:
            poster_lines.append(f"• Landscape: <a href=\"{landscape}\">Click Here</a>")
        if not poster_lines:
            poster_lines.append("• No poster URLs found in response.")

        body = "\n".join(header_lines)
        posters_block = "<b>⧉ Posters:</b>\n" + "\n".join(poster_lines)
        credit = "<blockquote>Bot By ➤ @NxTalks</blockquote>"

        text = f"{body}\n\n{posters_block}\n\n{credit}"

        btns = EchoButtons()
        btns.url_button(echo.UP_BTN, echo.UPDTE)
        btns.url_button(echo.ST_BTN, echo.REPO)
        buttons = btns.build(2)

        await edit_message(
            wait_msg,
            text,
            buttons=buttons,
            disable_web_page_preview=False,
        )
    except Exception as e:
        LOGGER.error(f"poster_cmd error: {e}", exc_info=True)
        try:
            await send_message(
                message,
                "<b>Error:</b> <code>Something went wrong while fetching poster.</code>",
            )
        except Exception:
            pass
