from pyrogram.enums import ChatType
from config import Config
from echobotz.eco import echo
from ..helper.tmdb_helper import _s, _i
from ..helper.utils.msg_util import send_message, edit_message
from ..helper.utils.btns import EchoButtons
from ..helper.utils.xtra import _sync_to_async, _task

@_task
async def _p(client, message):
    if message.chat.type not in (ChatType.PRIVATE, ChatType.GROUP, ChatType.SUPERGROUP):
        return
    if not getattr(message, "command", None) or len(message.command) < 2:
        return await send_message(message, "Usage:\n/poster Movie or Series Name")

    q = " ".join(message.command[1:])
    w = await send_message(message, f"Searching:\n<code>{q}</code>")

    r = await _sync_to_async(_s, q)
    if not r:
        return await edit_message(w, "Not Found")

    kind, mid, title, year = r
    imgs = await _sync_to_async(_i, kind, mid)

    t = f"🎬 {title}"
    if year:
        t += f" ({year})"

    ls = []
    if imgs["backdrops"]:
        ls.append("• English Landscape:")
        for i, x in enumerate(imgs["backdrops"], 1):
            ls.append(f"{i}. <a href=\"{x}\">Click Here</a>")
        ls.append("")
    landscape = "\n".join(ls)

    lg = []
    for i, x in enumerate(imgs["logos"], 1):
        lg.append(f"{i}. <a href=\"{x}\">Click Here</a>")
    logos = "\n".join(lg) if lg else "No Logos Found"

    ps = []
    for i, x in enumerate(imgs["posters"], 1):
        ps.append(f"{i}. <a href=\"{x}\">Click Here</a>")
    posters = "\n".join(ps) if ps else "No Posters Found"

    text = Config.POSER_TEMPLATE.format(
        title=t,
        landscape=landscape,
        logos=logos,
        posters=posters,
    )

    btns = EchoButtons()
    btns.url_button(echo.UP_BTN, echo.UPDTE)
    btns.url_button(echo.ST_BTN, echo.REPO)
    buttons = btns.build(2)

    await edit_message(
        w,
        text,
        buttons=buttons,
        disable_web_page_preview=False
    )
