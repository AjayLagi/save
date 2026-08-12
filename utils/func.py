# Copyright (c) 2025 devgagan : https://github.com/devgaganin.  
# Licensed under the GNU General Public License v3.0.  
# See LICENSE file in the repository root for full license text.

import concurrent.futures
import time
import os
import re
import logging
import asyncio
from datetime import datetime, timedelta
import sqlite3
import json
from pathlib import Path

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

PUBLIC_LINK_PATTERN = re.compile(r'(https?://)?(t\.me|telegram\.me)/([^/]+)(/(\d+))?')
PRIVATE_LINK_PATTERN = re.compile(r'(https?://)?(t\.me|telegram\.me)/c/(\d+)(/(\d+))?')
VIDEO_EXTENSIONS = {"mp4", "mkv", "avi", "mov", "wmv", "flv", "webm", "mpeg", "mpg", "3gp"}

# ---------------------------------------------------
# Local database (SQLite)
# ---------------------------------------------------
# Database file can be changed with the DB_PATH environment variable.
# Default: database.db
DB_PATH = os.getenv("DB_PATH", "saverestrict.db")

def _init_local_db():
    """Create local SQLite tables if they do not exist."""
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                data TEXT NOT NULL DEFAULT '{}'
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS premium_users (
                user_id INTEGER PRIMARY KEY,
                data TEXT NOT NULL DEFAULT '{}'
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS statistics (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS redeem_code (
                code TEXT PRIMARY KEY,
                data TEXT NOT NULL DEFAULT '{}'
            )
        """)
        conn.commit()

_init_local_db()


async def _db_get(table, user_id):
    def _get():
        with sqlite3.connect(DB_PATH) as conn:
            row = conn.execute(
                f"SELECT data FROM {table} WHERE user_id = ?",
                (int(user_id),)
            ).fetchone()

        if not row:
            return None

        try:
            data = json.loads(row[0])
        except (json.JSONDecodeError, TypeError):
            data = {}

        data["user_id"] = int(user_id)
        return data

    return await asyncio.to_thread(_get)


async def _db_upsert(table, user_id, data):
    def _save():
        payload = json.dumps(data, ensure_ascii=False, default=str)
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute(
                f"""
                INSERT INTO {table} (user_id, data)
                VALUES (?, ?)
                ON CONFLICT(user_id)
                DO UPDATE SET data = excluded.data
                """,
                (int(user_id), payload)
            )
            conn.commit()

    await asyncio.to_thread(_save)


async def _db_delete_key(table, user_id, key):
    data = await _db_get(table, user_id)
    if not data:
        return

    data.pop(key, None)
    data.pop("user_id", None)
    await _db_upsert(table, user_id, data)


# Names kept for compatibility/documentation with the old Mongo version.
users_collection = "users"
premium_users_collection = "premium_users"
statistics_collection = "statistics"
codedb = "redeem_code"

# ------- < start > Session Encoder don't change -------

a1 = "c2F2ZV9yZXN0cmljdGVkX2NvbnRlbnRfYm90cw=="
a2 = "Nzk2"
a3 = "Z2V0X21lc3NhZ2Vz" 
a4 = "cmVwbHlfcGhvdG8=" 
a5 = "c3RhcnQ="
attr1 = "cGhvdG8="
attr2 = "ZmlsZV9pZA=="
a7 = "SGkg8J+RiyBXZWxjb21lLCBXYW5uYSBpbnRyby4uLj8gCgrinLPvuI8gSSBjYW4gc2F2ZSBwb3N0cyBmcm9tIGNoYW5uZWxzIG9yIGdyb3VwcyB3aGVyZSBmb3J3YXJkaW5nIGlzIG9mZi4gSSBjYW4gZG93bmxvYWQgdmlkZW9zL2F1ZGlvIGZyb20gWVQsIElOU1RBLCAuLi4gc29jaWFsIHBsYXRmb3JtcwrinLPvuI8gU2ltcGx5IHNlbmQgdGhlIHBvc3QgbGluayBvZiBhIHB1YmxpYyBjaGFubmVsLiBGb3IgcHJpdmF0ZSBjaGFubmVscywgZG8gL2xvZ2luLiBTZW5kIC9oZWxwIHRvIGtub3cgbW9yZS4="
a8 = "Sm9pbiBDaGFubmVs"
a9 = "R2V0IFByZW1pdW0=" 
a10 = "aHR0cHM6Ly90Lm1lL3RlYW1fc3B5X3Bybw==" 
a11 = "aHR0cHM6Ly90Lm1lL2tpbmdvZnBhdGFs" 

# ------- < end > Session Encoder don't change --------

def is_private_link(link):
    return bool(PRIVATE_LINK_PATTERN.match(link))


def thumbnail(sender):
    return f'{sender}.jpg' if os.path.exists(f'{sender}.jpg') else None


def hhmmss(seconds):
    return time.strftime('%H:%M:%S', time.gmtime(seconds))


def E(L):   
    private_match = re.match(r'https://t\.me/c/(\d+)/(?:\d+/)?(\d+)', L)
    public_match = re.match(r'https://t\.me/([^/]+)/(?:\d+/)?(\d+)', L)
    
    if private_match:
        return f'-100{private_match.group(1)}', int(private_match.group(2)), 'private'
    elif public_match:
        return public_match.group(1), int(public_match.group(2)), 'public'
    
    return None, None, None


def get_display_name(user):
    if user.first_name and user.last_name:
        return f"{user.first_name} {user.last_name}"
    elif user.first_name:
        return user.first_name
    elif user.last_name:
        return user.last_name
    elif user.username:
        return user.username
    else:
        return "Unknown User"


def sanitize_filename(filename):
    return re.sub(r'[<>:"/\\|?*]', '_', filename)


def get_dummy_filename(info):
    file_type = info.get("type", "file")
    extension = {
        "video": "mp4",
        "photo": "jpg",
        "document": "pdf",
        "audio": "mp3"
    }.get(file_type, "bin")
    
    return f"downloaded_file_{int(time.time())}.{extension}"


async def is_private_chat(event):
    return event.is_private


async def save_user_data(user_id, key, value):
    try:
        user_data = await _db_get("users", user_id) or {}
        user_data.pop("user_id", None)
        user_data[key] = value
        await _db_upsert("users", user_id, user_data)
    except Exception as e:
        logger.error(f"Error saving user data for {user_id}: {e}")



async def get_user_data_key(user_id, key, default=None):
    try:
        user_data = await _db_get("users", int(user_id))
        return user_data.get(key, default) if user_data else default
    except Exception as e:
        logger.error(f"Error getting user data for {user_id}: {e}")
        return default



async def get_user_data(user_id):
    try:
        return await _db_get("users", user_id)
    except Exception as e:
        logger.error(f"Error retrieving user data for {user_id}: {e}")
        return None



async def save_user_session(user_id, session_string):
    try:
        await save_user_data(user_id, "session_string", session_string)
        await save_user_data(user_id, "updated_at", datetime.now().isoformat())
        logger.info(f"Saved session for user {user_id}")
        return True
    except Exception as e:
        logger.error(f"Error saving session for user {user_id}: {e}")
        return False



async def remove_user_session(user_id):
    try:
        await _db_delete_key("users", user_id, "session_string")
        logger.info(f"Removed session for user {user_id}")
        return True
    except Exception as e:
        logger.error(f"Error removing session for user {user_id}: {e}")
        return False



async def save_user_bot(user_id, bot_token):
    try:
        await save_user_data(user_id, "bot_token", bot_token)
        await save_user_data(user_id, "updated_at", datetime.now().isoformat())
        logger.info(f"Saved bot token for user {user_id}")
        return True
    except Exception as e:
        logger.error(f"Error saving bot token for user {user_id}: {e}")
        return False



async def remove_user_bot(user_id):
    try:
        await _db_delete_key("users", user_id, "bot_token")
        logger.info(f"Removed bot token for user {user_id}")
        return True
    except Exception as e:
        logger.error(f"Error removing bot token for user {user_id}: {e}")
        return False



async def process_text_with_rules(user_id, text):
    if not text:
        return ""
    
    try:
        replacements = await get_user_data_key(user_id, "replacement_words", {})
        delete_words = await get_user_data_key(user_id, "delete_words", [])
        
        processed_text = text
        for word, replacement in replacements.items():
            processed_text = processed_text.replace(word, replacement)
        
        if delete_words:
            words = processed_text.split()
            filtered_words = [w for w in words if w not in delete_words]
            processed_text = " ".join(filtered_words)
        
        return processed_text
    except Exception as e:
        logger.error(f"Error processing text with rules: {e}")
        return text


async def screenshot(video: str, duration: int, sender: str) -> str | None:
    existing_screenshot = f"{sender}.jpg"
    if os.path.exists(existing_screenshot):
        return existing_screenshot

    time_stamp = hhmmss(duration // 2)
    output_file = datetime.now().isoformat("_", "seconds") + ".jpg"

    cmd = [
        "ffmpeg",
        "-ss", time_stamp,
        "-i", video,
        "-frames:v", "1",
        output_file,
        "-y"
    ]

    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    
    stdout, stderr = await process.communicate()

    if os.path.isfile(output_file):
        return output_file
    else:
        print(f"FFmpeg Error: {stderr.decode().strip()}")
        return None


async def get_video_metadata(file_path):
    default_values = {
        "width": 1,
        "height": 1,
        "duration": 1
    }

    try:
        cmd = [
            "ffprobe",
            "-v", "error",
            "-select_streams", "v:0",
            "-show_entries",
            "stream=width,height,duration",
            "-of", "json",
            file_path
        ]

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            logger.error(
                f"FFprobe Error: {stderr.decode().strip()}"
            )
            return default_values

        data = json.loads(stdout.decode())

        streams = data.get("streams", [])

        if not streams:
            return default_values

        stream = streams[0]

        width = int(stream.get("width") or 1)
        height = int(stream.get("height") or 1)
        duration = round(float(stream.get("duration") or 1))

        if duration <= 0:
            duration = 1

        return {
            "width": width,
            "height": height,
            "duration": duration
        }

    except Exception as e:
        logger.error(
            f"Error in get_video_metadata: {e}"
        )
        return default_values


async def add_premium_user(user_id, duration_value, duration_unit):
    try:
        now = datetime.now()
        expiry_date = None

        if duration_unit == "min":
            expiry_date = now + timedelta(minutes=duration_value)
        elif duration_unit == "hours":
            expiry_date = now + timedelta(hours=duration_value)
        elif duration_unit == "days":
            expiry_date = now + timedelta(days=duration_value)
        elif duration_unit == "weeks":
            expiry_date = now + timedelta(weeks=duration_value)
        elif duration_unit == "month":
            expiry_date = now + timedelta(days=30 * duration_value)
        elif duration_unit == "year":
            expiry_date = now + timedelta(days=365 * duration_value)
        elif duration_unit == "decades":
            expiry_date = now + timedelta(days=3650 * duration_value)
        else:
            return False, "Invalid duration unit"

        data = {
            "user_id": int(user_id),
            "subscription_start": now.isoformat(),
            "subscription_end": expiry_date.isoformat(),
            "expireAt": expiry_date.isoformat()
        }

        data.pop("user_id", None)
        await _db_upsert("premium_users", user_id, data)

        return True, expiry_date
    except Exception as e:
        logger.error(f"Error adding premium user {user_id}: {e}")
        return False, str(e)



async def is_premium_user(user_id):
    try:
        user = await _db_get("premium_users", user_id)
        if user and "subscription_end" in user:
            expiry = datetime.fromisoformat(user["subscription_end"])
            return datetime.now() < expiry
        return False
    except Exception as e:
        logger.error(f"Error checking premium status for {user_id}: {e}")
        return False



async def get_premium_details(user_id):
    try:
        user = await _db_get("premium_users", user_id)
        if user and "subscription_end" in user:
            return user
        return None
    except Exception as e:
        logger.error(f"Error getting premium details for {user_id}: {e}")
        return None
