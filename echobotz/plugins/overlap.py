import io
import time
import hashlib
import requests
from functools import partial

from pyrogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from pyrogram.enums import ChatType

from ..helper.utils.msg_util import send_message, edit_message, send_file
from ..helper.utils.xtra import _sync_to_async, _task
from .. import LOGGER
from ..eco import echo

try:
    from PIL import Image
except Exception as e:
    Image = None
    LOGGER.error(f"{e}")

OVER_STORE = {}

POS_MAP = {
    "tl": ("left", "top"),
    "t": ("center", "top"),
    "tr": ("right", "top"),
    "ml": ("left", "center"),
    "c": ("center", "center"),
    "mr": ("right", "center"),
    "bl": ("left", "bottom"),
    "b": ("center", "bottom"),
    "br": ("right", "bottom"),
}

POS_NAME = {
    "tl": "Top Left",
    "t": "Top",
    "tr": "Top Right",
    "ml": "Middle Left",
    "c": "Center",
    "mr": "Middle Right",
    "bl": "Bottom Left",
    "b": "Bottom",
    "br": "Bottom Right",
}

def _uid(a, b, s):
    h = hashlib.sha256()
    h.update((a or "").encode("utf-8"))
    h.update(b"\x00")
    h.update((b or "").encode("utf-8"))
    h.update(b"\x00")
    h.update(str(s).encode("utf-8"))
    h.update(str(time.time()).encode("utf-8"))
    return h.hexdigest()[:18]

def _place_coords(pw, ph, lw, lh, pos):
    hx = {"left": 0, "center": (pw - lw) // 2, "right": pw - lw}
    hy = {"top": 0, "center": (ph - lh) // 2, "bottom": ph - lh}
    return hx[pos[0]], hy[pos[1]]

def _merge_images(pbytes, lbytes, scale_percent, pos_key):
    if Image is None:
        raise RuntimeError("Pillow not found")

    im = Image.open(io.BytesIO(pbytes)).convert("RGBA")
    lg = Image.open(io.BytesIO(lbytes)).convert("RGBA")

    pw, ph = im.size
    scale = max(1, int(scale_percent))

    tgt_w = max(1, pw * scale // 100)
    wpercent = tgt_w / float(lg.size[0])
    tgt_h = int((float(lg.size[1]) * float(wpercent)))

    lg = lg.resize((tgt_w, tgt_h), Image.LANCZOS)

    x, y = _place_coords(pw, ph, lg.size[0], lg.size[1], POS_MAP.get(pos_key, ("center", "center")))

    base = Image.new("RGBA", im.size)
    base.paste(im, (0, 0))
    base.alpha_composite(lg, dest=(x, y))

    out = io.BytesIO()
    base.convert("RGB").save(out, format="JPEG", quality=95)
    out.seek(0)
    out.name = "overlap.jpg"
    return out

def _dl(url):
    try:
        r = requests.get(url, timeout=20)
        r.raise_for_status()
        return r.content
    except Exception as e:
        LOGGER.error(str(e), exc_info=True)
        return None

@_task
async def _olap_cmd(client, message):
    if Image is None:
        return await send_message(
            message,
            "Pillow not found"
        )

    if message.chat.type not in (ChatType.PRIVATE, ChatType.GROUP, ChatType.SUPERGROUP):
        return

    if not getattr(message, "command", None) or len(message.command) < 3:
        return await send_message(message, "Formate:\n <code>/overlap {poster_url} {logo_url} [scale_percent]</code>")

    poster_url = message.command[1]
    logo_url = message.command[2]

    scale = 20
    if len(message.command) >= 4:
        try:
            scale = int(message.command[3])
        except:
            scale = 20

    uid = _uid(poster_url, logo_url, scale)

    rows = [
        [
            InlineKeyboardButton("↖ Top Left", callback_data=f"ov pos {uid} tl"),
            InlineKeyboardButton("🔼 Top", callback_data=f"ov pos {uid} t"),
            InlineKeyboardButton("↗ Top Right", callback_data=f"ov pos {uid} tr"),
        ],
        [
            InlineKeyboardButton("◀ Middle Left", callback_data=f"ov pos {uid} ml"),
            InlineKeyboardButton("🎯 Center", callback_data=f"ov pos {uid} c"),
            InlineKeyboardButton("▶ Middle Right", callback_data=f"ov pos {uid} mr"),
        ],
        [
            InlineKeyboardButton("↙ Bottom Left", callback_data=f"ov pos {uid} bl"),
            InlineKeyboardButton("🔽 Bottom", callback_data=f"ov pos {uid} b"),
            InlineKeyboardButton("↘ Bottom Right", callback_data=f"ov pos {uid} br"),
        ],
        [
            InlineKeyboardButton("🗑️ Remove", callback_data=f"ov rem {uid}"),
        ],
    ]
    buttons = InlineKeyboardMarkup(rows)

    sent = await send_message(message, f"🥂Overlay: None | Scale: {scale}%", buttons=buttons)

    pbytes = await _sync_to_async(_dl, poster_url)
    lbytes = await _sync_to_async(_dl, logo_url)

    if not pbytes or not lbytes:
        try:
            await edit_message(sent, "Failed to download one or both images")
        except Exception:
            pass
        return

    OVER_STORE[uid] = {
        "poster": pbytes,
        "logo": lbytes,
        "scale": scale,
        "time": time.time(),
        # user_id not urs
    }

@_task
async def _olap_cb(client, query: CallbackQuery):
    if Image is None:
        await query.answer("Pillow not installed", show_alert=True)
        try:
            await edit_message(query.message, "Pillow is not installed.")
        except Exception:
            pass
        return

    data = query.data or ""
    parts = data.split()
    if len(parts) < 3:
        return await query.answer()

    act = parts[1]
    uid = parts[2]
    if act == "rem":
        entry = OVER_STORE.pop(uid, None)
        try:
            await query.message.delete()
        except:
            pass
        try:
            if query.message.reply_to_message:
                await query.message.reply_to_message.delete()
        except:
            pass

        await query.answer("Removed")
        return
    if act == "pos":
        pos = parts[3] if len(parts) >= 4 else "c"
        entry = OVER_STORE.get(uid)

        if not entry:
            await query.answer("Expired")
            try:
                await edit_message(query.message, "Session expired or invalid")
            except:
                pass
            return

        await query.answer()
        try:
            await edit_message(query.message, "Processing...")
        except:
            pass

        try:
            out = await _sync_to_async(
                partial(_merge_images, entry["poster"], entry["logo"], entry["scale"], pos)
            )
            out.name = "overlap.jpg"

            pos_label = POS_NAME.get(pos, "Custom")
            caption = f"🥂Overlay: {pos_label} | Scale: {entry['scale']}%"

            await send_file(query.message.chat.id, out, caption=caption)

            OVER_STORE.pop(uid, None)
            try:
                await query.message.delete()
            except:
                pass

        except Exception as e:
            LOGGER.error(str(e), exc_info=True)
            await query.answer("Failed")
            try:
                await edit_message(query.message, "Failed to process image")
            except:
                pass
