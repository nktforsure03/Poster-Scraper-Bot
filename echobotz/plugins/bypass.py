from pyrogram.enums import ChatType

from .. import LOGGER
from ..helper.ott import _extract_url_from_message
from ..helper.bypsr import _bp_info, _bp_links
from ..helper.utils.msg_util import send_message, edit_message
from ..helper.utils.xtra import _task
from config import Config

from echobotz.eco import echo
from ..helper.utils.btns import EchoButtons

def _sexy(name):
    if not name:
        return None
    name = str(name).lower()
    mapping = {
        "gdflix": "GDFlix",
        "hubcloud": "HubCloud",
        "hubdrive": "HubDrive",
        "transfer_it": "Transfer.it",
    }
    return mapping.get(name, name.title())

@_task
async def _bypass_cmd(client, message):
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
                    f"/{cmd_name} &lt;url&gt;  <i>or</i>\n"
                    f"Reply to a URL with <code>/{cmd_name}</code>"
                ),
            )

        wait_msg = await send_message(
            message,
            f"<i>Processing:</i>\n<code>{target_url}</code>",
        )

        info, err = await _bp_info(cmd_name, target_url)
        if err:
            return await edit_message(
                wait_msg,
                f"<b>Error:</b> <code>{err}</code>",
            )

        service = _sexy(info.get("service"))
        title = info.get("title")
        filesize = info.get("filesize")
        file_format = info.get("format")

        header_lines = []
        if service:
            header_lines.append(f"<b>✺Source:</b> {service}")
        if title and title != "N/A":
            if header_lines:
                header_lines.append("")
            header_lines.append("<b>File:</b>")
            header_lines.append(f"<blockquote>{title}</blockquote>")
        header_block = "\n".join(header_lines) if header_lines else ""
        meta_lines = []
        if filesize and filesize != "N/A":
            meta_lines.append(f"<b>Size:</b> {filesize}")
        if file_format and file_format != "N/A":
            meta_lines.append(f"<b>Format:</b> {file_format}")
        meta_block = ("\n".join(meta_lines) + "\n\n") if meta_lines else ""
        links_block = _bp_links(info.get("links") or {})
        text = Config.BYPASS_TEMPLATE.format(
            header_block=header_block,
            meta_block=meta_block,
            links_block=links_block,
            original_url=target_url,
        )
        btns = EchoButtons()
        btns.url_button(echo.UP_BTN, echo.UPDTE)
        btns.url_button(echo.ST_BTN, echo.REPO)
        buttons = btns.build(2)
        await edit_message(
            wait_msg,
            text,
            buttons=buttons,
        )
    except Exception as e:
        LOGGER.error(f"bypass_cmd error: {e}", exc_info=True)
        try:
            await send_message(
                message,
                "<b>Error:</b> <code>Something went wrong while bypassing the URL.</code>",
            )
        except Exception:
            pass
