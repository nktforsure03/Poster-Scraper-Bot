from pyrogram.errors import MediaEmpty, PhotoInvalidDimensions, WebpageMediaEmpty

from config import Config
from ..core.EchoClient import EchoBot
from ..helper.utils.btns import EchoButtons
from ..helper.utils.msg_util import send_message, edit_message, delete_message
from ..helper.utils.xtra import _get_readable_time, _sync_to_async, _task
from ..helper.anilist_api import _search, _get


LIST_ITEMS = 3


def _cut(text: str, limit: int = 600) -> str:
    if not text:
        return "N/A"
    text = text.replace("<br>", " ").replace("<br />", " ")
    if len(text) > limit:
        return text[:limit].rstrip() + "..."
    return text


def _dt(d):
    if not d or not d.get("year"):
        return "N/A"
    y = d.get("year")
    m = d.get("month") or 1
    day = d.get("day") or 1
    return f"{day:02d}/{m:02d}/{y}"


def _air(s, e):
    s2 = _dt(s)
    e2 = _dt(e)
    if s2 == "N/A" and e2 == "N/A":
        return "N/A"
    if e2 == "N/A":
        return f"{s2} - ?"
    return f"{s2} - {e2}"


def _next(n):
    if not n:
        return "N/A"
    ep = n.get("episode")
    t = n.get("timeUntilAiring")
    if not ep:
        return "N/A"
    if t:
        return f"Ep {ep} in {_get_readable_time(t)}"
    return f"Ep {ep}"


def _tags(k):
    if not k:
        return "N/A"
    if len(k) == 1:
        return "#" + k[0].replace(" ", "_")
    data = k[:LIST_ITEMS]
    return " ".join("#" + i.replace(" ", "_") + "," for i in data)[:-1]


def _st(s):
    m = {
        "FINISHED": "Finished ✅",
        "RELEASING": "Airing 🟢",
        "NOT_YET_RELEASED": "Not yet released ⏳",
        "CANCELLED": "Cancelled ❌",
        "HIATUS": "Hiatus 💤",
    }
    return m.get(s, s or "N/A")


def _fm(f):
    m = {
        "TV": "TV Series",
        "TV_SHORT": "TV Short",
        "MOVIE": "Movie",
        "SPECIAL": "Special",
        "OVA": "OVA",
        "ONA": "ONA",
        "MUSIC": "Music",
    }
    return m.get(f, f or "N/A")


def _sn(season, year):
    if not season and not year:
        return "N/A"
    if not season:
        return str(year)
    s = season.capitalize()
    if year:
        return f"{s} {year}"
    return s


def _rank_info(rankings):
    sr = ""
    pr = ""
    if not rankings:
        return sr, pr
    for r in rankings:
        if r.get("type") == "RATED" and r.get("allTime"):
            sr = f"(#{r.get('rank')} rated)"
        if r.get("type") == "POPULAR" and r.get("allTime"):
            pr = f"(#{r.get('rank')} popular)"
    return sr, pr


def _alts(info):
    t = info.get("title") or {}
    syn = info.get("synonyms") or []
    names = []
    for k in ("english", "romaji", "native"):
        v = t.get(k)
        if v and v not in names:
            names.append(v)
    for s in syn:
        if s not in names:
            names.append(s)
    if not names:
        return "N/A"
    if len(names) == 1:
        return names[0]
    if len(names) > LIST_ITEMS:
        names = names[:LIST_ITEMS]
    return " | ".join(names)


def _links(info):
    mal = ""
    ext = ""
    mal_id = info.get("idMal")
    if mal_id:
        mal = f' • <a href="https://myanimelist.net/anime/{mal_id}">MAL</a>'
    ex = info.get("externalLinks") or []
    sites_seen = set()
    parts = []
    for e in ex:
        site = e.get("site")
        url = e.get("url")
        if not site or not url:
            continue
        if site in sites_seen:
            continue
        sites_seen.add(site)
        if site.lower() in ("anilist", "myanimelist"):
            continue
        parts.append(f' • <a href="{url}">{site}</a>')
        if len(parts) >= 3:
            break
    if parts:
        ext = "".join(parts)
    return mal, ext

@_task
async def _anime(client, message):
    if " " not in message.text:
        return await send_message(
            message,
            "<i>Send Anime Name along with /anime command.</i>",
        )

    k = await send_message(message, "<i>Searching AniList ...</i>")
    q = message.text.split(" ", 1)[1].strip()
    user_id = message.from_user.id
    btn = EchoButtons()

    try:
        res = await _sync_to_async(_search, q)
    except Exception:
        return await edit_message(k, "<i>Something went wrong while searching.</i>")

    if not res:
        return await edit_message(k, "<i>No Results Found</i>")

    for m in res:
        mid = m["id"]
        t = m["title"]
        name = t.get("english") or t.get("romaji") or t.get("native") or "Unknown"
        year = m.get("seasonYear") or "N/A"
        fmt = _fm(m.get("format"))
        st = _st(m.get("status"))
        btn.data_button(
            f"🎌 {name} ({year}) [{fmt}] {st}",
            f"anime {user_id} media {mid}",
        )

    btn.data_button("🚫 Close 🚫", f"anime {user_id} close")
    await edit_message(
        k,
        "<b><i>Search Results from AniList</i></b>",
        btn.build(1),
    )

@_task
async def _anime_cb(client, query):
    message = query.message
    user_id = query.from_user.id
    data = query.data.split()

    if user_id != int(data[1]):
        return await query.answer("Not Yours!", show_alert=True)

    if data[2] == "media":
        await query.answer("Processing...")
        aid = int(data[3])

        try:
            info = await _sync_to_async(_get, aid)
        except Exception:
            return await query.answer("Failed to fetch details.", show_alert=True)

        tdata = info.get("title") or {}
        title = (
            tdata.get("english")
            or tdata.get("romaji")
            or tdata.get("native")
            or "Unknown Title"
        )
        romaji = tdata.get("romaji") or "-"
        native = tdata.get("native") or ""

        cover = (
            info.get("bannerImage")
            or (info.get("coverImage") or {}).get("extraLarge")
            or (info.get("coverImage") or {}).get("large")
            or "https://telegra.ph/file/5af8d90a479b0d11df298.jpg"
        )

        year = info.get("seasonYear") or "N/A"
        score_val = info.get("averageScore")
        score = f"{score_val}/100" if score_val is not None else "N/A"
        rankings = info.get("rankings") or []
        score_rank, pop_rank = _rank_info(rankings)
        genres = _tags(info.get("genres") or [])
        fmt = _fm(info.get("format"))
        eps = info.get("episodes") or "N/A"
        dur = info.get("duration")
        duration = f"{dur} min" if dur else "N/A"
        aired = _air(info.get("startDate"), info.get("endDate"))
        pop = info.get("popularity") or "N/A"
        fav = info.get("favourites") or "N/A"
        studios = info.get("studios", {}).get("nodes") or []
        studio = studios[0]["name"] if studios else "N/A"
        status = _st(info.get("status"))
        season = _sn(info.get("season"), info.get("seasonYear"))
        next_ep = _next(info.get("nextAiringEpisode"))
        description = _cut(info.get("description"), 400)
        anilist_url = info.get("siteUrl") or "https://anilist.co/"
        alt_titles = _alts(info)
        mal_link, ext_links = _links(info)

        ctx = {
            "title": title,
            "year": year,
            "romaji": romaji,
            "native": native,
            "status": status,
            "season": season,
            "format": fmt,
            "episodes": eps,
            "duration": duration,
            "score": score,
            "score_rank": score_rank,
            "popularity": pop,
            "pop_rank": pop_rank,
            "favourites": fav,
            "genres": genres,
            "studio": studio,
            "next_ep": next_ep,
            "aired": aired,
            "alt_titles": alt_titles,
            "description": description,
            "anilist_url": anilist_url,
            "mal_link": mal_link,
            "ext_links": ext_links,
        }

        tpl = getattr(Config, "ANILIST_TEMPLATE", None)
        if tpl:
            cap = tpl.format(**ctx)
        else:
            cap = f"<b>{title}</b> ({year})\n\n{description}"

        btn = EchoButtons()
        btn.data_button("🚫 Close 🚫", f"anime {user_id} close")
        kb = btn.build(1)

        target_msg = message.reply_to_message or message

        try:
            await EchoBot.send_photo(
                chat_id=target_msg.chat.id,
                photo=cover,
                caption=cap,
                reply_to_message_id=target_msg.id,
                reply_markup=kb,
            )
        except (MediaEmpty, PhotoInvalidDimensions, WebpageMediaEmpty):
            await send_message(
                target_msg,
                cap,
                kb,
                photo="https://telegra.ph/file/5af8d90a479b0d11df298.jpg",
            )

        await delete_message(message, message.reply_to_message)
    else:
        await query.answer()
        await delete_message(message, message.reply_to_message)
