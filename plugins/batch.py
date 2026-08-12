# Copyright (c) 2025 devgagan : https://github.com/devgaganin.  
# Licensed under the GNU General Public License v3.0.  
# See LICENSE file in the repository root for full license text.

import os, re, time, asyncio, json, asyncio 
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.errors import UserNotParticipant
from config import API_ID, API_HASH, LOG_GROUP, STRING, FORCE_SUB, FREEMIUM_LIMIT, PREMIUM_LIMIT
from utils.func import get_user_data, screenshot, thumbnail, get_video_metadata
from utils.func import get_user_data_key, process_text_with_rules, is_premium_user, E
from shared_client import app as X
from plugins.settings import rename_file
from plugins.start import subscribe as sub
from utils.custom_filters import login_in_progress
from utils.encrypt import dcs
from typing import Dict, Any, Optional


Y = None if not STRING else __import__('shared_client').userbot
Z, P, UB, UC, emp = {}, {}, {}, {}, {}

ACTIVE_USERS = {}
ACTIVE_USERS_FILE = "active_users.json"

# fixed directory file_name problems 
def sanitize(filename):
    return re.sub(r'[<>:"/\\|?*\']', '_', filename).strip(" .")[:255]

def load_active_users():
    try:
        if os.path.exists(ACTIVE_USERS_FILE):
            with open(ACTIVE_USERS_FILE, 'r') as f:
                return json.load(f)
        return {}
    except Exception:
        return {}

async def save_active_users_to_file():
    try:
        with open(ACTIVE_USERS_FILE, 'w') as f:
            json.dump(ACTIVE_USERS, f)
    except Exception as e:
        print(f"Error saving active users: {e}")

async def add_active_batch(user_id: int, batch_info: Dict[str, Any]):
    ACTIVE_USERS[str(user_id)] = batch_info
    await save_active_users_to_file()

def is_user_active(user_id: int) -> bool:
    return str(user_id) in ACTIVE_USERS

async def update_batch_progress(user_id: int, current: int, success: int):
    if str(user_id) in ACTIVE_USERS:
        ACTIVE_USERS[str(user_id)]["current"] = current
        ACTIVE_USERS[str(user_id)]["success"] = success
        await save_active_users_to_file()

async def request_batch_cancel(user_id: int):
    if str(user_id) in ACTIVE_USERS:
        ACTIVE_USERS[str(user_id)]["cancel_requested"] = True
        await save_active_users_to_file()
        return True
    return False

def should_cancel(user_id: int) -> bool:
    user_str = str(user_id)
    return user_str in ACTIVE_USERS and ACTIVE_USERS[user_str].get("cancel_requested", False)

async def remove_active_batch(user_id: int):
    if str(user_id) in ACTIVE_USERS:
        del ACTIVE_USERS[str(user_id)]
        await save_active_users_to_file()

def get_batch_info(user_id: int) -> Optional[Dict[str, Any]]:
    return ACTIVE_USERS.get(str(user_id))

ACTIVE_USERS = load_active_users()

async def upd_dlg(c):
    try:
        async for _ in c.get_dialogs(limit=100): pass
        return True
    except Exception as e:
        print(f'Failed to update dialogs: {e}')
        return False

# fixed the old group of 2021-2022 extraction 🌝 (buy krne ka fayda nhi ab old group) ✅ 
async def get_msg(c, u, i, d, lt):
    """
    Ambil message Telegram.

    Private:
        https://t.me/c/2254980132/397
        -> -1002254980132
        -> 397

    u = Pyrogram user client dari session /login
    c = bot client dari /setbot
    """

    try:
        chat_id = i
        message_id = int(d)

        # =====================================================
        # PUBLIC LINK
        # =====================================================
        if lt == 'public':
            try:
                # User client
                if u:
                    try:
                        msg = await u.get_messages(
                            chat_id,
                            message_id
                        )

                        if msg and not getattr(msg, "empty", False):
                            emp[chat_id] = False
                            print(
                                f"[GET_MSG] Public SUCCESS via user: "
                                f"{chat_id}/{message_id}"
                            )
                            return msg

                    except Exception as e:
                        print(
                            f"[GET_MSG] Public user error: "
                            f"{type(e).__name__}: {e}"
                        )

                # Bot client
                if c:
                    try:
                        msg = await c.get_messages(
                            chat_id,
                            message_id
                        )

                        if msg and not getattr(msg, "empty", False):
                            emp[chat_id] = False
                            print(
                                f"[GET_MSG] Public SUCCESS via bot: "
                                f"{chat_id}/{message_id}"
                            )
                            return msg

                    except Exception as e:
                        print(
                            f"[GET_MSG] Public bot error: "
                            f"{type(e).__name__}: {e}"
                        )

                return None

            except Exception as e:
                print(
                    f"[GET_MSG] Public error: "
                    f"{type(e).__name__}: {e}"
                )
                return None

        # =====================================================
        # PRIVATE LINK
        # =====================================================
        if lt == 'private':

            if not u:
                print(
                    "[GET_MSG] User session tidak tersedia. "
                    "Pastikan /login sudah dilakukan."
                )
                return None

            try:
                chat_id = int(i)
                message_id = int(d)
            except (TypeError, ValueError) as e:
                print(
                    f"[GET_MSG] Invalid private ID: "
                    f"i={i!r}, d={d!r}: {e}"
                )
                return None

            print(
                f"[GET_MSG] PRIVATE REQUEST -> "
                f"chat_id={chat_id}, "
                f"message_id={message_id}"
            )

            # -------------------------------------------------
            # CARA UTAMA
            # Sama seperti test.py yang sudah berhasil.
            # -------------------------------------------------
            try:
                msg = await u.get_messages(
                    chat_id,
                    message_id
                )

                if msg and not getattr(msg, "empty", False):
                    print(
                        f"[GET_MSG] PRIVATE SUCCESS -> "
                        f"{chat_id}/{message_id}"
                    )
                    return msg

                print(
                    f"[GET_MSG] Message kosong: "
                    f"{chat_id}/{message_id}"
                )

            except Exception as e:
                print(
                    f"[GET_MSG] Private get_messages ERROR -> "
                    f"{type(e).__name__}: {e}"
                )

            # -------------------------------------------------
            # FALLBACK: refresh dialog
            # -------------------------------------------------
            try:
                print("[GET_MSG] Refreshing dialogs...")

                async for dialog in u.get_dialogs():
                    if dialog.id == chat_id:

                        print(
                            f"[GET_MSG] Channel ditemukan di dialog: "
                            f"{dialog.name} ({dialog.id})"
                        )

                        try:
                            msg = await u.get_messages(
                                dialog.chat,
                                message_id
                            )

                            if msg and not getattr(
                                msg,
                                "empty",
                                False
                            ):
                                print(
                                    "[GET_MSG] PRIVATE SUCCESS "
                                    "via dialog"
                                )
                                return msg

                        except Exception as e:
                            print(
                                f"[GET_MSG] Dialog get_messages ERROR -> "
                                f"{type(e).__name__}: {e}"
                            )

                        break

            except Exception as e:
                print(
                    f"[GET_MSG] Dialog refresh ERROR -> "
                    f"{type(e).__name__}: {e}"
                )

            print(
                f"[GET_MSG] PRIVATE FAILED -> "
                f"{chat_id}/{message_id}"
            )

            return None

        print(f"[GET_MSG] Unknown link type: {lt!r}")
        return None

    except Exception as e:
        print(
            f"[GET_MSG] Unexpected ERROR -> "
            f"{type(e).__name__}: {e}"
        )
        return None

async def get_ubot(uid):
    bt = await get_user_data_key(uid, "bot_token", None)
    if not bt: return None
    if uid in UB: return UB.get(uid)
    try:
        bot = Client(f"user_{uid}", bot_token=bt, api_id=API_ID, api_hash=API_HASH)
        await bot.start()
        UB[uid] = bot
        return bot
    except Exception as e:
        print(f"Error starting bot for user {uid}: {e}")
        return None

async def get_uclient(uid):
    ud = await get_user_data(uid)
    ubot = UB.get(uid)
    cl = UC.get(uid)
    if cl: return cl
    if not ud: return ubot if ubot else None
    xxx = ud.get('session_string')
    if xxx:
        try:
            ss = dcs(xxx)
            gg = Client(f'{uid}_client', api_id=API_ID, api_hash=API_HASH, device_model="v3saver", session_string=ss)
            await gg.start()
            await upd_dlg(gg)
            UC[uid] = gg
            return gg
        except Exception as e:
            print(f'User client error: {e}')
            return ubot if ubot else Y
    return Y

async def prog(c, t, C, h, m, st):
    global P
    p = c / t * 100
    interval = 10 if t >= 100 * 1024 * 1024 else 20 if t >= 50 * 1024 * 1024 else 30 if t >= 10 * 1024 * 1024 else 50
    step = int(p // interval) * interval
    if m not in P or P[m] != step or p >= 100:
        P[m] = step
        c_mb = c / (1024 * 1024)
        t_mb = t / (1024 * 1024)
        bar = '🟢' * int(p / 10) + '🔴' * (10 - int(p / 10))
        speed = c / (time.time() - st) / (1024 * 1024) if time.time() > st else 0
        eta = time.strftime('%M:%S', time.gmtime((t - c) / (speed * 1024 * 1024))) if speed > 0 else '00:00'
        await C.edit_message_text(h, m, f"__**Pyro Handler...**__\n\n{bar}\n\n⚡**__Completed__**: {c_mb:.2f} MB / {t_mb:.2f} MB\n📊 **__Done__**: {p:.2f}%\n🚀 **__Speed__**: {speed:.2f} MB/s\n⏳ **__ETA__**: {eta}\n\n**__Powered by Team SPY__**")
        if p >= 100: P.pop(m, None)

async def send_direct(c, m, tcid, ft=None, rtmid=None):
    try:
        if m.video:
            await c.send_video(tcid, m.video.file_id, caption=ft, duration=m.video.duration, width=m.video.width, height=m.video.height, reply_to_message_id=rtmid)
        elif m.video_note:
            await c.send_video_note(tcid, m.video_note.file_id, reply_to_message_id=rtmid)
        elif m.voice:
            await c.send_voice(tcid, m.voice.file_id, reply_to_message_id=rtmid)
        elif m.sticker:
            await c.send_sticker(tcid, m.sticker.file_id, reply_to_message_id=rtmid)
        elif m.audio:
            await c.send_audio(tcid, m.audio.file_id, caption=ft, duration=m.audio.duration, performer=m.audio.performer, title=m.audio.title, reply_to_message_id=rtmid)
        elif m.photo:
            photo_id = m.photo.file_id if hasattr(m.photo, 'file_id') else m.photo[-1].file_id
            await c.send_photo(tcid, photo_id, caption=ft, reply_to_message_id=rtmid)
        elif m.document:
            await c.send_document(tcid, m.document.file_id, caption=ft, file_name=m.document.file_name, reply_to_message_id=rtmid)
        else:
            return False
        return True
    except Exception as e:
        print(f'Direct send error: {e}')
        return False

async def process_msg(c, u, m, d, lt, uid, i, single=False):
    """Process one Telegram message.

    single=False: old /batch behaviour; bot token is used for upload.
    single=True: user session from /login is used for download AND upload.
    """
    f = None
    status = None
    # /single:
    # - user session (u) hanya digunakan untuk mengambil/download media
    # - main bot (X) digunakan untuk mengirim hasil kembali ke user
    #
    # User session tidak tepat digunakan sebagai pengirim hasil ke
    # chat user yang sedang berinteraksi dengan bot utama, karena
    # session tersebut bisa merupakan akun Telegram yang berbeda.
    upload_client = X if single else c

    try:
        print(
            f"[PROCESS] START user={uid} chat={d} source={i} "
            f"type={lt} single={single}"
        )

        # Destination for /single is always the user who requested it.
        # /batch keeps the existing configurable chat_id behaviour.
        if single:
            tcid = int(d)
            rtmid = None
        else:
            cfg_chat = await get_user_data_key(d, 'chat_id', None)
            tcid = int(d)
            rtmid = None

            if cfg_chat:
                if '/' in str(cfg_chat):
                    parts = str(cfg_chat).split('/', 1)
                    tcid = int(parts[0])
                    rtmid = int(parts[1]) if len(parts) > 1 else None
                else:
                    tcid = int(cfg_chat)

        print(
            f"[PROCESS] Destination={tcid} "
            f"upload_client={'MAIN_BOT' if single else 'SETBOT'} "
            f"download_client={'USER_SESSION' if u else 'NONE'}"
        )

        # ---------------------------------------------------------
        # TEXT ONLY
        # ---------------------------------------------------------
        if not m.media:
            if m.text:
                await upload_client.send_message(
                    tcid,
                    text=m.text.markdown,
                    reply_to_message_id=None if single else rtmid
                )
                return 'Sent.'
            return 'No media.'

        orig_text = m.caption.markdown if m.caption else ''
        proc_text = await process_text_with_rules(d, orig_text)
        user_cap = await get_user_data_key(d, 'caption', '')

        ft = (
            f'{proc_text}\n\n{user_cap}'
            if proc_text and user_cap
            else user_cap
            if user_cap
            else proc_text
        )

        # ---------------------------------------------------------
        # PUBLIC DIRECT SEND
        # Only use this optimisation for batch. For /single we
        # deliberately download once so the same path works for
        # public and private links.
        # ---------------------------------------------------------
        if not single and lt == 'public' and not emp.get(i, False):
            print('[PROCESS] Public direct-send mode')
            if await send_direct(c, m, tcid, ft, rtmid):
                return 'Sent directly.'

        # ---------------------------------------------------------
        # STATUS MESSAGE
        # Main bot X is used only for status/progress. It does NOT
        # need the user's /setbot token.
        # ---------------------------------------------------------
        status_client = X
        status_chat = int(d)
        status = await status_client.send_message(status_chat, 'Downloading...')
        st = time.time()

        # ---------------------------------------------------------
        # FILE NAME
        # ---------------------------------------------------------
        if m.video:
            c_name = sanitize(m.video.file_name or f'{time.time()}.mp4')
        elif m.audio:
            c_name = sanitize(m.audio.file_name or f'{time.time()}.mp3')
        elif m.document:
            c_name = sanitize(m.document.file_name or f'{time.time()}')
        elif m.photo:
            c_name = sanitize(f'{time.time()}.jpg')
        else:
            c_name = sanitize(f'{time.time()}')

        print(f'[PROCESS] DOWNLOAD ONCE -> {c_name}')

        # ---------------------------------------------------------
        # DOWNLOAD EXACTLY ONCE
        # ---------------------------------------------------------
        f = await u.download_media(
            m,
            file_name=c_name,
            progress=prog,
            progress_args=(status_client, status_chat, status.id, st)
        )

        if not f or not os.path.exists(f):
            await status.edit('Download failed.')
            return 'Failed.'

        print(f'[PROCESS] DOWNLOAD SUCCESS -> {f}')

        # Rename is optional. If the user's rename configuration
        # causes an error, keep the downloaded file instead of
        # starting another download.
        # ---------------------------------------------------------
        # RENAME / RENAME TAG
        # ---------------------------------------------------------
        # rename_file() reads:
        #   - rename_tag
        #   - delete_words
        #   - replacement_words
        # directly from the user's local SQLite data.
        #
        # Run it for every downloadable file type, even when the
        # original Telegram file_name is empty. The settings.py
        # implementation can handle a missing extension itself.
        try:
            await status.edit('Renaming...')
            if m.video or m.audio or m.document:
                old_file = f
                renamed = await rename_file(f, d, status)

                if renamed and os.path.exists(renamed):
                    f = renamed
                    print(
                        f'[PROCESS] RENAME SUCCESS -> '
                        f'{old_file} => {f}'
                    )
                else:
                    print(
                        f'[PROCESS] RENAME NOT CHANGED -> {f}'
                    )

        except Exception as e:
            print(
                f'[PROCESS] Rename skipped: '
                f'{type(e).__name__}: {e}'
            )

        # ---------------------------------------------------------
        # MEDIA INFORMATION
        # ---------------------------------------------------------
        file_ext = os.path.splitext(f)[1].lower()
        video_extensions = {
            '.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv',
            '.webm', '.m4v', '.3gp', '.ogv'
        }
        audio_extensions = {
            '.mp3', '.wav', '.flac', '.aac', '.ogg', '.wma',
            '.m4a', '.opus', '.aiff', '.ac3'
        }

        th = None
        dur = h = w = None

        if m.video or (m.document and file_ext in video_extensions):
            mtd = await get_video_metadata(f)
            dur = mtd['duration']
            h = mtd['height']
            w = mtd['width']

            # -----------------------------------------------------
            # THUMBNAIL
            # -----------------------------------------------------
            # Priority:
            #   1. User custom thumbnail: <user_id>.jpg
            #   2. Automatically generated thumbnail from video
            # -----------------------------------------------------
            custom_thumb = thumbnail(d)

            if custom_thumb and os.path.isfile(custom_thumb):
                th = custom_thumb
                print(
                    f'[PROCESS] CUSTOM THUMBNAIL -> {th}'
                )
            else:
                th = await screenshot(f, dur, d)

                if th and os.path.isfile(th):
                    print(
                        f'[PROCESS] AUTO THUMBNAIL -> {th}'
                    )
                else:
                    print(
                        '[PROCESS] THUMBNAIL NOT AVAILABLE'
                    )

        # ---------------------------------------------------------
        # UPLOAD
        # /single -> user's logged-in session
        # /batch  -> configured bot token
        # ---------------------------------------------------------
        await status.edit('Uploading...')
        upload_start = time.time()

        upload_args = {
            'progress': prog,
            'progress_args': (
                status_client,
                status_chat,
                status.id,
                upload_start
            )
        }

        if not single and rtmid is not None:
            upload_args['reply_to_message_id'] = rtmid

        if m.video or (m.document and file_ext in video_extensions):
            print(
                f'[PROCESS] VIDEO UPLOAD -> file={f} '
                f'thumb={th!r} width={w} height={h} duration={dur}'
            )

            await upload_client.send_video(
                tcid,
                video=f,
                caption=ft if m.caption else None,
                thumb=th,
                width=w,
                height=h,
                duration=dur,
                **upload_args
            )

        elif m.video_note:
            await upload_client.send_video_note(
                tcid,
                video_note=f,
                **upload_args
            )

        elif m.voice:
            await upload_client.send_voice(
                tcid,
                voice=f,
                **upload_args
            )

        elif m.audio or (m.document and file_ext in audio_extensions):
            await upload_client.send_audio(
                tcid,
                audio=f,
                caption=ft if m.caption else None,
                thumb=th,
                **upload_args
            )

        elif m.photo:
            await upload_client.send_photo(
                tcid,
                photo=f,
                caption=ft if m.caption else None,
                **upload_args
            )

        elif m.document:
            await upload_client.send_document(
                tcid,
                document=f,
                caption=ft if m.caption else None,
                **upload_args
            )

        else:
            await upload_client.send_document(
                tcid,
                document=f,
                caption=ft if m.caption else None,
                **upload_args
            )

        print('[PROCESS] UPLOAD SUCCESS')

        try:
            await status.delete()
        except Exception:
            pass

        return 'Done.'

    except Exception as e:
        print(
            f'[PROCESS] ERROR -> {type(e).__name__}: {e}'
        )

        if status:
            try:
                await status.edit(
                    f'Failed: {type(e).__name__}: {str(e)[:120]}'
                )
            except Exception:
                pass

        return f'Error: {str(e)[:100]}'

    finally:
        # Only delete the local file after the single upload attempt.
        if f and os.path.exists(f):
            try:
                os.remove(f)
                print(f'[PROCESS] TEMP FILE REMOVED -> {f}')
            except Exception as e:
                print(f'[PROCESS] Could not remove temp file: {e}')

@X.on_message(filters.command(['batch', 'single']))
async def process_cmd(c, m):
    uid = m.from_user.id
    cmd = m.command[0].lower()

    if FREEMIUM_LIMIT == 0 and not await is_premium_user(uid):
        await m.reply_text("This bot does not provide free servies, get subscription from OWNER")
        return

    if await sub(c, m) == 1:
        return

    pro = await m.reply_text('Doing some checks hold on...')

    if is_user_active(uid):
        await pro.edit('You have an active task. Use /stop to cancel it.')
        return

    # ---------------------------------------------------------
    # /single does NOT require /setbot.
    # It uses the encrypted session saved by /login.
    # ---------------------------------------------------------
    if cmd == 'single':
        uc = await get_uclient(uid)
        if not uc:
            await pro.edit('Please /login first. User session not found.')
            return

        Z[uid] = {'step': 'start_single'}
        await pro.edit('Send the Telegram link you want to process.')
        return

    # ---------------------------------------------------------
    # /batch keeps the existing /setbot requirement.
    # ---------------------------------------------------------
    ubot = await get_ubot(uid)
    if not ubot:
        await pro.edit('Add your bot with /setbot first')
        return

    Z[uid] = {'step': 'start'}
    await pro.edit('Send start link...')

@X.on_message(filters.command(['cancel', 'stop']))
async def cancel_cmd(c, m):
    uid = m.from_user.id
    if is_user_active(uid):
        if await request_batch_cancel(uid):
            await m.reply_text('Cancellation requested. The current batch will stop after the current download completes.')
        else:
            await m.reply_text('Failed to request cancellation. Please try again.')
    else:
        await m.reply_text('No active batch process found.')

@X.on_message(filters.text & filters.private & ~login_in_progress & ~filters.command([
    'start', 'batch', 'cancel', 'login', 'logout', 'stop', 'set',
    'pay', 'redeem', 'gencode', 'single', 'generate', 'keyinfo',
    'encrypt', 'decrypt', 'keys', 'setbot', 'rembot'
]))
async def text_handler(c, m):
    uid = m.from_user.id

    if uid not in Z:
        return

    s = Z[uid].get('step')

    # /single does not need a bot token.
    # /batch still needs the configured bot token.
    if s != 'start_single' and s != 'process_single':
        x = await get_ubot(uid)
        if not x:
            await m.reply_text("Add your bot /setbot `token`")
            return

    if s == 'start':
        L = m.text.strip()
        i, d, lt = E(L)

        if not i or not d:
            await m.reply_text('Invalid link format.')
            Z.pop(uid, None)
            return

        Z[uid].update({
            'step': 'count',
            'cid': i,
            'sid': d,
            'lt': lt
        })
        await m.reply_text('How many messages?')
        return

    if s == 'start_single':
        L = m.text.strip()
        i, d, lt = E(L)

        if not i or not d:
            await m.reply_text('Invalid link format.')
            Z.pop(uid, None)
            return

        Z[uid].update({
            'step': 'process_single',
            'cid': i,
            'sid': d,
            'lt': lt
        })

        pt = await m.reply_text('Processing...')
        uc = await get_uclient(uid)

        if not uc:
            await pt.edit('Cannot proceed without user session. Please /login first.')
            Z.pop(uid, None)
            return

        if is_user_active(uid):
            await pt.edit('Active task exists. Use /stop first.')
            Z.pop(uid, None)
            return

        try:
            print(
                f'[SINGLE] user={uid} source={i} '
                f'message={d} type={lt}'
            )

            msg = await get_msg(None, uc, i, d, lt)

            if msg:
                res = await process_msg(
                    X,
                    uc,
                    msg,
                    str(m.chat.id),
                    lt,
                    uid,
                    i,
                    single=True
                )
                await pt.edit(f'1/1: {res}')
            else:
                await pt.edit('Message not found')

        except Exception as e:
            print(
                f'[SINGLE] ERROR -> '
                f'{type(e).__name__}: {e}'
            )
            await pt.edit(
                f'Error: {type(e).__name__}: {str(e)[:120]}'
            )
        finally:
            Z.pop(uid, None)

        return

    if s == 'count':
        if not m.text.isdigit():
            await m.reply_text('Enter valid number.')
            return

        count = int(m.text)
        maxlimit = PREMIUM_LIMIT if await is_premium_user(uid) else FREEMIUM_LIMIT

        if count > maxlimit:
            await m.reply_text(f'Maximum limit is {maxlimit}.')
            return

        Z[uid].update({
            'step': 'process',
            'did': str(m.chat.id),
            'num': count
        })

        i, s_id, n, lt = (
            Z[uid]['cid'],
            Z[uid]['sid'],
            Z[uid]['num'],
            Z[uid]['lt']
        )
        success = 0

        pt = await m.reply_text('Processing batch...')
        uc = await get_uclient(uid)
        ubot = UB.get(uid)

        if not uc or not ubot:
            await pt.edit('Missing client setup')
            Z.pop(uid, None)
            return

        if is_user_active(uid):
            await pt.edit('Active task exists')
            Z.pop(uid, None)
            return

        await add_active_batch(uid, {
            'total': n,
            'current': 0,
            'success': 0,
            'cancel_requested': False,
            'progress_message_id': pt.id
        })

        try:
            for j in range(n):
                if should_cancel(uid):
                    await pt.edit(
                        f'Cancelled at {j}/{n}. Success: {success}'
                    )
                    break

                await update_batch_progress(uid, j, success)
                mid = int(s_id) + j

                try:
                    msg = await get_msg(ubot, uc, i, mid, lt)
                    if msg:
                        res = await process_msg(
                            ubot,
                            uc,
                            msg,
                            str(m.chat.id),
                            lt,
                            uid,
                            i,
                            single=False
                        )

                        if any(x in res for x in ('Done', 'Copied', 'Sent')):
                            success += 1

                except Exception as e:
                    try:
                        await pt.edit(
                            f'{j + 1}/{n}: Error - {str(e)[:50]}'
                        )
                    except Exception:
                        pass

                await asyncio.sleep(10)

            await pt.edit(f'Batch Completed. Success: {success}/{n}')

        finally:
            await remove_active_batch(uid)
            Z.pop(uid, None)


