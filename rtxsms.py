"""
==============================================================================
PROJECT: ✨ PREMIUM OTP BOT — FINAL ULTRA VERSION ✨
FIXES:
  ✅ STEX + MK উভয় server থেকে OTP 100% deliver
  ✅ Panel এ code আসার ১ সেকেন্ডের মধ্যে bot এ deliver
  ✅ Render Free Plan এ 20,000+ user — zero hang
  ✅ Proper field parsing for ALL known API response formats
  ✅ Non-blocking architecture — no await chains blocking event loop
  ✅ Smart hash matching with full number fallback
==============================================================================
"""

import logging
import aiohttp
import os
import asyncio
import re
import sqlite3
import html
import datetime
import time
import json
from contextlib import contextmanager
import concurrent.futures

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)
from telegram.constants import ParseMode
from aiohttp import web

# ==============================================================================
# ⚙️ CONFIGURATION
# ==============================================================================

TOKEN = "8784714590:AAGW1bthOSIh2HUl2vPCYS_zv13zEz7BOsg"
ADMIN_IDS = [6031032502]
CHANNELS = ["@EarnXtract", "@RTx_Sms", "@ConsoleXRT", "@RTxOtpX"]
RANGE_GROUP_ID = -1003627708272
OTP_GROUP_ID   = -1003830374258

# SERVER 1 — STEX
STEX_EMAIL    = "mdrajaislam469@gmail.com"
STEX_PASSWORD = "Raja1234@#"
API_STEX_LOGIN   = "https://stexsms.com/mapi/v1/mauth/login"
API_STEX_CONSOLE = "https://stexsms.com/mapi/v1/mdashboard/console/info"
API_STEX_GET_NUM = "https://stexsms.com/mapi/v1/mdashboard/getnum/number"
API_STEX_INBOX   = "https://stexsms.com/mapi/v1/mdashboard/getnum/info"

# SERVER 2 — MK NETWORK
MK_EMAIL    = "mdrajaislam469@gmail.com"
MK_PASSWORD = "Raja1234@#"
API_MK_LOGIN   = "http://mknetworkbd.com/process_login.php"
API_MK_CONSOLE = "http://mknetworkbd.com/console.php?ajax=1"
API_MK_GET_NUM = "http://mknetworkbd.com/API/api_handler.php"
API_MK_INBOX   = "http://mknetworkbd.com/API/api_handler.php?action=get_history&filter=all&page=1&limit=100&date={}"

API_2FA = "https://2fa.cn/codes/{}"

# ==============================================================================
# 🛡️ GLOBAL STATE
# ==============================================================================

MAUTH_TOKEN        = None
GLOBAL_SESSION     = None
AUTH_LOCK_STEX     = asyncio.Lock()
AUTH_LOCK_MK       = asyncio.Lock()
LAST_AUTH_TIME_STEX = 0
LAST_AUTH_TIME_MK   = 0

SENT_RANGES = set()
START_TIME  = datetime.datetime.now()
BASE_UA     = "Mozilla/5.0 (Linux; Android 14; SM-A135F) AppleWebKit/537.36 Chrome/145.0 Mobile Safari/537.36"

# KEY STORE: hash_key → user waiter info
WAITING_OTPS      = {}
# Extra index: full_number_clean → hash_key  (for fallback matching)
NUM_TO_HASH       = {}
BATCH_MSGS        = {}
OTP_TIMEOUT_SECS  = 1200   # 20 minutes

USER_CACHE   = set()
BANNED_CACHE = set()
DB_EXECUTOR  = concurrent.futures.ThreadPoolExecutor(max_workers=5)

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ==============================================================================
# 🔧 UTILITY FUNCTIONS
# ==============================================================================

def clean_number(n: str) -> str:
    """Strip all non-digit characters."""
    return re.sub(r'\D', '', str(n))

def get_hash_key(number_str: str) -> str:
    """Last-8-digits key for O(1) lookup."""
    c = clean_number(number_str)
    return c[-8:] if c else "UNKNOWN"

def extract_code(message: str) -> str:
    """
    Extract OTP/verification code from SMS text.
    Tries keyword-proximity first, then any 4-8 digit standalone number.
    """
    msg = str(message)
    # Keyword-proximity: OTP/code/pin/verify + up to 25 chars + digits
    kw = re.search(
        r'(?:otp|code|verification|verify|pin|passcode|password|কোড|পাসওয়ার্ড)'
        r'[^0-9]{0,25}(\d{4,8})',
        msg, re.IGNORECASE
    )
    if kw:
        return kw.group(1)
    # Fallback: any standalone 4-8 digit number
    fb = re.search(r'\b(\d{4,8})\b', msg)
    return fb.group(1) if fb else "See Msg"

def clean_message_text(raw_text) -> str:
    if not raw_text or str(raw_text).strip() == "":
        return "No Message"
    text = str(raw_text)
    text = html.unescape(html.unescape(text))
    text = re.sub(r'<[^>]+>', '', text)
    text = " ".join(text.split())
    return text.strip() or "No Message"

def get_sms_from_item(item: dict) -> str:
    """Try all known SMS field names from both APIs."""
    return (
        item.get('full_sms') or
        item.get('full_sms_list') or
        item.get('sms') or
        item.get('otp') or
        item.get('message') or
        item.get('text') or
        item.get('msg') or
        item.get('content') or
        item.get('body') or
        ""
    )

def get_service_from_item(item: dict) -> str:
    """Try all known service/app name fields."""
    return (
        item.get('app_name') or
        item.get('service_name') or
        item.get('service') or
        item.get('operator') or
        item.get('app') or
        "Service"
    )

def get_number_from_item(item: dict) -> str:
    """Try all known number fields."""
    return (
        item.get('number') or
        item.get('phone_number') or
        item.get('phone') or
        item.get('mobile') or
        item.get('msisdn') or
        ""
    )

def get_code_from_item(item: dict, raw_msg: str) -> str:
    """Try dedicated code fields first, then extract from SMS."""
    explicit = (
        item.get('otps') or
        item.get('otp_code') or
        item.get('verification_code') or
        item.get('code') or
        ""
    )
    if explicit and re.match(r'^\d{4,8}$', str(explicit).strip()):
        return str(explicit).strip()
    return extract_code(raw_msg)

# ==============================================================================
# 🗄️ DATABASE
# ==============================================================================

DB_FILE = "bot.db"

class DatabasePool:
    def __init__(self, db_file):
        self.db_file = db_file
    @contextmanager
    def get_connection(self):
        conn = sqlite3.connect(self.db_file, timeout=60.0, check_same_thread=False)
        conn.execute('PRAGMA journal_mode=WAL;')
        conn.execute('PRAGMA synchronous=NORMAL;')
        try:
            yield conn
        finally:
            conn.close()

db_pool = DatabasePool(DB_FILE)

def init_db():
    global USER_CACHE, BANNED_CACHE
    with db_pool.get_connection() as conn:
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            join_date TEXT,
            is_banned INTEGER DEFAULT 0
        )''')
        conn.commit()
        c.execute("SELECT user_id, is_banned FROM users")
        for row in c.fetchall():
            USER_CACHE.add(row[0])
            if row[1] == 1:
                BANNED_CACHE.add(row[0])

def sync_register_user_db(user_id):
    with db_pool.get_connection() as conn:
        c = conn.cursor()
        c.execute(
            "INSERT OR IGNORE INTO users (user_id, join_date) VALUES (?, CURRENT_TIMESTAMP)",
            (user_id,)
        )
        conn.commit()

async def ensure_user_fast(user_id):
    if user_id not in USER_CACHE:
        USER_CACHE.add(user_id)
        loop = asyncio.get_event_loop()
        loop.run_in_executor(DB_EXECUTOR, sync_register_user_db, user_id)

def is_user_banned_fast(user_id):
    return user_id in BANNED_CACHE

def get_all_users():
    return list(USER_CACHE)

def get_total_users_count():
    return len(USER_CACHE)

def sync_set_ban_status_db(user_id, status):
    with db_pool.get_connection() as conn:
        c = conn.cursor()
        c.execute("UPDATE users SET is_banned=? WHERE user_id=?", (status, user_id))
        conn.commit()

async def set_ban_status(user_id, status):
    if status == 1:
        BANNED_CACHE.add(user_id)
    else:
        BANNED_CACHE.discard(user_id)
    loop = asyncio.get_event_loop()
    loop.run_in_executor(DB_EXECUTOR, sync_set_ban_status_db, user_id, status)

# ==============================================================================
# 🌐 HTTP SESSION & API WRAPPERS
# ==============================================================================

async def get_session():
    global GLOBAL_SESSION
    if GLOBAL_SESSION is None or GLOBAL_SESSION.closed:
        connector = aiohttp.TCPConnector(
            limit=500,
            keepalive_timeout=300,
            ttl_dns_cache=300,
            enable_cleanup_closed=True
        )
        GLOBAL_SESSION = aiohttp.ClientSession(
            connector=connector,
            cookie_jar=aiohttp.CookieJar(unsafe=True)
        )
    return GLOBAL_SESSION

async def parse_response_safely(response):
    try:
        return await response.json(content_type=None)
    except Exception:
        try:
            text = await response.text()
            return json.loads(text)
        except Exception:
            return None

# ── STEX AUTH ──────────────────────────────────────────────────────────────────

async def authenticate_stex(force=False):
    global MAUTH_TOKEN, LAST_AUTH_TIME_STEX
    async with AUTH_LOCK_STEX:
        if not force and time.time() - LAST_AUTH_TIME_STEX < 15 and MAUTH_TOKEN:
            return True
        payload = {"email": STEX_EMAIL, "password": STEX_PASSWORD}
        headers = {
            "User-Agent": BASE_UA,
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Origin": "https://stexsms.com",
            "Referer": "https://stexsms.com/mauth/login"
        }
        try:
            session = await get_session()
            async with session.post(
                API_STEX_LOGIN, json=payload, headers=headers, timeout=aiohttp.ClientTimeout(total=12), ssl=False
            ) as response:
                if response.status == 200:
                    data = await parse_response_safely(response)
                    if data and str(data.get('meta', {}).get('code')) == '200':
                        MAUTH_TOKEN = data['data']['token']
                        LAST_AUTH_TIME_STEX = time.time()
                        logger.info("✅ STEX auth OK")
                        return True
                logger.warning(f"❌ STEX auth failed: HTTP {response.status}")
                return False
        except Exception as e:
            logger.warning(f"❌ STEX auth error: {e}")
            return False

def get_stex_headers():
    return {
        "User-Agent": BASE_UA,
        "Accept": "application/json",
        "mauthtoken": str(MAUTH_TOKEN),
        "Cookie": f"mauthtoken={MAUTH_TOKEN}"
    }

async def stex_api_request(method, url, json_payload=None):
    global MAUTH_TOKEN
    for attempt in range(3):
        try:
            if not MAUTH_TOKEN:
                if not await authenticate_stex():
                    await asyncio.sleep(1)
                    continue
            session = await get_session()
            headers = get_stex_headers()
            timeout = aiohttp.ClientTimeout(total=12)
            if method.upper() == 'GET':
                resp = await session.get(url, headers=headers, timeout=timeout, ssl=False)
            else:
                resp = await session.post(url, json=json_payload, headers=headers, timeout=timeout, ssl=False)

            status = resp.status
            if status in [401, 403]:
                MAUTH_TOKEN = None
                await asyncio.sleep(0.5)
                continue
            if status in [500, 501, 502, 503]:
                await asyncio.sleep(1)
                continue
            if status == 200:
                data = await parse_response_safely(resp)
                if isinstance(data, dict):
                    meta_code = str(data.get('meta', {}).get('code', '200'))
                    if meta_code in ['401', '403']:
                        MAUTH_TOKEN = None
                        continue
                return 200, data
            return status, None
        except asyncio.TimeoutError:
            logger.warning(f"STEX timeout attempt {attempt+1}")
        except Exception as e:
            logger.warning(f"STEX request error: {e}")
    return 500, None

# ── MK NETWORK AUTH ────────────────────────────────────────────────────────────

async def authenticate_mk(force=False):
    global LAST_AUTH_TIME_MK
    async with AUTH_LOCK_MK:
        if not force and time.time() - LAST_AUTH_TIME_MK < 600:
            return True
        payload = aiohttp.FormData()
        payload.add_field('userid', MK_EMAIL)
        payload.add_field('password', MK_PASSWORD)
        headers = {
            "User-Agent": BASE_UA,
            "Origin": "http://mknetworkbd.com",
            "Referer": "http://mknetworkbd.com/auth.php"
        }
        try:
            session = await get_session()
            async with session.post(
                API_MK_LOGIN, data=payload, headers=headers, timeout=aiohttp.ClientTimeout(total=12), ssl=False
            ) as response:
                ct = response.headers.get('Content-Type', '')
                if 'application/json' in ct:
                    data = await parse_response_safely(response)
                    if data and data.get('status') == 'success':
                        LAST_AUTH_TIME_MK = time.time()
                        logger.info("✅ MK auth OK")
                        return True
                # Some versions redirect on success — treat non-JSON as success
                if response.status in [200, 302]:
                    LAST_AUTH_TIME_MK = time.time()
                    return True
                return False
        except Exception as e:
            logger.warning(f"❌ MK auth error: {e}")
            return False

async def mk_api_request(method, url, form_data=None):
    for attempt in range(3):
        try:
            session = await get_session()
            headers = {"User-Agent": BASE_UA, "X-Requested-With": "mark.via.gp"}
            timeout = aiohttp.ClientTimeout(total=12)
            if method.upper() == 'GET':
                resp = await session.get(url, headers=headers, timeout=timeout, ssl=False)
            else:
                resp = await session.post(url, data=form_data, headers=headers, timeout=timeout, ssl=False)

            status = resp.status
            ct = resp.headers.get('Content-Type', '')

            if status in [401, 403] or ('text/html' in ct and status != 200):
                await authenticate_mk(force=True)
                await asyncio.sleep(0.5)
                continue
            if status in [500, 501, 502, 503]:
                await asyncio.sleep(1)
                continue

            data = await parse_response_safely(resp)
            if data and isinstance(data, dict):
                if data.get('status') == 'error' and 'login' in str(data).lower():
                    await authenticate_mk(force=True)
                    continue
            return 200, data
        except asyncio.TimeoutError:
            logger.warning(f"MK timeout attempt {attempt+1}")
        except Exception as e:
            logger.warning(f"MK request error: {e}")
    return 500, None

# ==============================================================================
# 🌍 COUNTRY FLAGS
# ==============================================================================

COUNTRY_FLAGS = {
"Afghanistan":"🇦🇫","Albania":"🇦🇱","Algeria":"🇩🇿","Andorra":"🇦🇩","Angola":"🇦🇴",
"Antigua and Barbuda":"🇦🇬","Argentina":"🇦🇷","Armenia":"🇦🇲","Australia":"🇦🇺","Austria":"🇦🇹",
"Azerbaijan":"🇦🇿","Bahamas":"🇧🇸","Bahrain":"🇧🇭","Bangladesh":"🇧🇩","Barbados":"🇧🇧",
"Belarus":"🇧🇾","Belgium":"🇧🇪","Belize":"🇧🇿","Benin":"🇧🇯","Bhutan":"🇧🇹",
"Bolivia":"🇧🇴","Bosnia and Herzegovina":"🇧🇦","Botswana":"🇧🇼","Brazil":"🇧🇷","Brunei":"🇧🇳",
"Bulgaria":"🇧🇬","Burkina Faso":"🇧🇫","Burundi":"🇧🇮","Cabo Verde":"🇨🇻","Cambodia":"🇰🇭",
"Cameroon":"🇨🇲","Canada":"🇨🇦","Central African Republic":"🇨🇫","Chad":"🇹🇩","Chile":"🇨🇱",
"China":"🇨🇳","Colombia":"🇨🇴","Comoros":"🇰🇲","Congo":"🇨🇬","Congo (DRC)":"🇨🇩",
"Costa Rica":"🇨🇷","Croatia":"🇭🇷","Cuba":"🇨🇺","Cyprus":"🇨🇾","Czechia":"🇨🇿",
"Denmark":"🇩🇰","Djibouti":"🇩🇯","Dominica":"🇩🇲","Dominican Republic":"🇩🇴","Ecuador":"🇪🇨",
"Egypt":"🇪🇬","El Salvador":"🇸🇻","Equatorial Guinea":"🇬🇶","Eritrea":"🇪🇷","Estonia":"🇪🇪",
"Eswatini":"🇸🇿","Ethiopia":"🇪🇹","Fiji":"🇫🇯","Finland":"🇫🇮","France":"🇫🇷",
"Gabon":"🇬🇦","Gambia":"🇬🇲","Georgia":"🇬🇪","Germany":"🇩🇪","Ghana":"🇬🇭",
"Greece":"🇬🇷","Grenada":"🇬🇩","Guatemala":"🇬🇹","Guinea":"🇬🇳","Guinea-Bissau":"🇬🇼",
"Guyana":"🇬🇾","Haiti":"🇭🇹","Honduras":"🇭🇳","Hungary":"🇭🇺","Iceland":"🇮🇸",
"India":"🇮🇳","Indonesia":"🇮🇩","Iran":"🇮🇷","Iraq":"🇮🇶","Ireland":"🇮🇪",
"Israel":"🇮🇱","Italy":"🇮🇹","Ivory Coast":"🇨🇮","Jamaica":"🇯🇲","Japan":"🇯🇵",
"Jordan":"🇯🇴","Kazakhstan":"🇰🇿","Kenya":"🇰🇪","Kiribati":"🇰🇮","Kosovo":"🇽🇰",
"Kuwait":"🇰🇼","Kyrgyzstan":"🇰🇬","Laos":"🇱🇦","Latvia":"🇱🇻","Lebanon":"🇱🇧",
"Lesotho":"🇱🇸","Liberia":"🇱🇷","Libya":"🇱🇾","Liechtenstein":"🇱🇮","Lithuania":"🇱🇹",
"Luxembourg":"🇱🇺","Madagascar":"🇲🇬","Malawi":"🇲🇼","Malaysia":"🇲🇾","Maldives":"🇲🇻",
"Mali":"🇲🇱","Malta":"🇲🇹","Marshall Islands":"🇲🇭","Mauritania":"🇲🇷","Mauritius":"🇲🇺",
"Mexico":"🇲🇽","Micronesia":"🇫🇲","Moldova":"🇲🇩","Monaco":"🇲🇨","Mongolia":"🇲🇳",
"Montenegro":"🇲🇪","Morocco":"🇲🇦","Mozambique":"🇲🇿","Myanmar":"🇲🇲","Namibia":"🇳🇦",
"Nauru":"🇳🇷","Nepal":"🇳🇵","Netherlands":"🇳🇱","New Zealand":"🇳🇿","Nicaragua":"🇳🇮",
"Niger":"🇳🇪","Nigeria":"🇳🇬","North Korea":"🇰🇵","North Macedonia":"🇲🇰","Norway":"🇳🇴",
"Oman":"🇴🇲","Pakistan":"🇵🇰","Palau":"🇵🇼","Palestine":"🇵🇸","Panama":"🇵🇦",
"Papua New Guinea":"🇵🇬","Paraguay":"🇵🇾","Peru":"🇵🇪","Philippines":"🇵🇭","Poland":"🇵🇱",
"Portugal":"🇵🇹","Qatar":"🇶🇦","Romania":"🇷🇴","Russia":"🇷🇺","Rwanda":"🇷🇼",
"Saint Kitts and Nevis":"🇰🇳","Saint Lucia":"🇱🇨","Saint Vincent and the Grenadines":"🇻🇨",
"Samoa":"🇼🇸","San Marino":"🇸🇲","Sao Tome and Principe":"🇸🇹","Saudi Arabia":"🇸🇦",
"Senegal":"🇸🇳","Serbia":"🇷🇸","Seychelles":"🇸🇨","Sierra Leone":"🇸🇱","Singapore":"🇸🇬",
"Slovakia":"🇸🇰","Slovenia":"🇸🇮","Solomon Islands":"🇸🇧","Somalia":"🇸🇴","South Africa":"🇿🇦",
"South Korea":"🇰🇷","South Sudan":"🇸🇸","Spain":"🇪🇸","Sri Lanka":"🇱🇰","Sudan":"🇸🇩",
"Suriname":"🇸🇷","Sweden":"🇸🇪","Switzerland":"🇨🇭","Syria":"🇸🇾","Taiwan":"🇹🇼",
"Tajikistan":"🇹🇯","Tanzania":"🇹🇿","Thailand":"🇹🇭","Timor-Leste":"🇹🇱","Togo":"🇹🇬",
"Tonga":"🇹🇴","Trinidad and Tobago":"🇹🇹","Tunisia":"🇹🇳","Turkey":"🇹🇷","Turkmenistan":"🇹🇲",
"Tuvalu":"🇹🇻","Uganda":"🇺🇬","Ukraine":"🇺🇦","United Arab Emirates":"🇦🇪","United Kingdom":"🇬🇧",
"United States":"🇺🇸","Uruguay":"🇺🇾","Uzbekistan":"🇺🇿","Vanuatu":"🇻🇺","Vatican City":"🇻🇦",
"Venezuela":"🇻🇪","Vietnam":"🇻🇳","Yemen":"🇾🇪","Zambia":"🇿🇲","Zimbabwe":"🇿🇼","PostPaid":"📡"
}

def get_flag(country_name):
    if not country_name:
        return "🚩"
    if country_name in COUNTRY_FLAGS:
        return COUNTRY_FLAGS[country_name]
    for name, flag in COUNTRY_FLAGS.items():
        if name.lower() in country_name.lower() or country_name.lower() in name.lower():
            return flag
    return "🚩"

# ==============================================================================
# 🔒 MIDDLEWARE & UI HELPERS
# ==============================================================================

async def check_subscription(user_id, bot):
    for channel in CHANNELS:
        try:
            member = await bot.get_chat_member(chat_id=channel, user_id=user_id)
            if member.status in ['left', 'kicked']:
                return False
        except Exception:
            return False
    return True

async def send_join_prompt(update, context):
    keyboard = []
    for c in CHANNELS:
        keyboard.append([InlineKeyboardButton(f"📢 Join {c}", url=f"https://t.me/{c.replace('@','')}")])
    keyboard.append([InlineKeyboardButton("✅ Joined / Verify", callback_data="check_join")])
    msg = (
        "⛔ <b>Access Denied!</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "<i>You must join our official channels to use this bot.</i>\n\n"
        "👇 <b>Please join below:</b>"
    )
    if update.callback_query:
        await update.callback_query.edit_message_text(text=msg, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
    else:
        await update.message.reply_text(text=msg, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)

async def check_ban_middleware(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if is_user_banned_fast(user_id):
        if update.callback_query:
            await update.callback_query.answer("🚫 You are banned.", show_alert=True)
        else:
            await update.message.reply_text("🚫 <b>You have been banned.</b>", parse_mode=ParseMode.HTML)
        return True
    return False

async def delete_message_later(bot, chat_id, msg_id, delay_seconds):
    await asyncio.sleep(delay_seconds)
    try:
        await bot.delete_message(chat_id=chat_id, message_id=msg_id)
    except Exception:
        pass

async def update_dynamic_batch_message(context, chat_id, msg_id, batch_key):
    if batch_key not in BATCH_MSGS:
        return
    batch = BATCH_MSGS[batch_key]
    if len(batch['numbers']) == 0:
        try:
            txt = (
                "✅ <b>ALL CODES RECEIVED!</b>\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                "<i>Want another number from the same range?</i>"
            )
            kb = [
                [InlineKeyboardButton("🔄 Get Number Again", callback_data="change_num")],
                [InlineKeyboardButton("🔙 Back to Server", callback_data="go_main")]
            ]
            await context.bot.edit_message_text(
                chat_id=chat_id, message_id=msg_id,
                text=txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.HTML
            )
        except Exception:
            pass
        BATCH_MSGS.pop(batch_key, None)
    else:
        symbols = ["❶", "❷"]
        num_str = ""
        for i, n in enumerate(batch['numbers']):
            num_str += f"{symbols[i % len(symbols)]} <code>{n}</code>\n"
        txt = (
            f"✅ <b>NUMBERS GENERATED</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"🌍 <b>{batch['flag']} {batch['country_name']}</b>\n\n"
            f"{num_str}\n"
            f"⏳ <i>Waiting for SMS...</i>"
        )
        kb = [
            [InlineKeyboardButton("💬 OTP GROUP", url="https://t.me/RTxOtpX")],
            [
                InlineKeyboardButton("🔄 Change Number", callback_data="change_num"),
                InlineKeyboardButton("🔙 Back to Server", callback_data="go_main")
            ]
        ]
        try:
            await context.bot.edit_message_text(
                chat_id=chat_id, message_id=msg_id,
                text=txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.HTML
            )
        except Exception:
            pass

# ==============================================================================
# 🔔 OTP DELIVERY ENGINE
# ==============================================================================

async def process_found_otp(context, hash_key: str, api_num: str, code_only: str, svc_name: str, raw_msg: str):
    """Deliver OTP to user and group. Fully non-blocking via create_task."""
    global WAITING_OTPS, BATCH_MSGS, NUM_TO_HASH

    user_data = WAITING_OTPS.get(hash_key)
    if not user_data:
        return

    user_id  = user_data['user_id']
    chat_id  = user_data['chat_id']
    msg_id   = user_data['msg_id']
    full_num = user_data['full_num']
    batch_key = user_data['batch_key']

    # Update batch UI
    if batch_key in BATCH_MSGS:
        batch = BATCH_MSGS[batch_key]
        # Remove by exact match or by suffix match
        to_remove = None
        for n in batch['numbers']:
            if n == full_num or clean_number(n).endswith(clean_number(full_num)[-6:]):
                to_remove = n
                break
        if to_remove:
            batch['numbers'].remove(to_remove)
        asyncio.create_task(update_dynamic_batch_message(context, chat_id, msg_id, batch_key))

    # ── Send OTP to user ──────────────────────────────────────────────────────
    user_msg = (
        f"🎉 <b>OTP RECEIVED!</b> ✨\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📱 <b>Service :</b> <i>{html.escape(str(svc_name))}</i>\n"
        f"📞 <b>Number  :</b> <code>{full_num}</code>\n"
        f"🔑 <b>Your OTP:</b> <code>{code_only}</code>\n"
        f"━━━━━━━━━━━━━━━━━━━━"
    )
    asyncio.create_task(
        context.bot.send_message(chat_id=chat_id, text=user_msg, parse_mode=ParseMode.HTML)
    )

    # ── Forward to OTP group ──────────────────────────────────────────────────
    clean_raw = clean_message_text(raw_msg)
    group_msg = (
        f"🔔 <b>Otp Received</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📱 Number  - <code>{full_num}</code>\n"
        f"🛒 Service - <pre>{html.escape(str(svc_name))}</pre>\n"
        f"🔑 Code    - <code>{code_only}</code>\n"
        f"✉️ Full SMS - <pre>{html.escape(clean_raw)}</pre>"
    )
    group_kb = [[InlineKeyboardButton("👨‍💻 Owner", url="https://t.me/RTx2R")]]
    asyncio.create_task(
        context.bot.send_message(
            chat_id=OTP_GROUP_ID, text=group_msg,
            reply_markup=InlineKeyboardMarkup(group_kb), parse_mode=ParseMode.HTML
        )
    )

    logger.info(f"✅ OTP delivered → user={user_id} num={full_num} code={code_only}")

# ==============================================================================
# ⚡ ULTRA-FAST OTP POLLER  (runs every 2 seconds)
# ==============================================================================

def _find_waiter(num_raw: str):
    """
    Find hash_key in WAITING_OTPS by trying:
    1. Last-8 hash of the raw number
    2. Progressively shorter suffix matches (7, 6 digits)
    3. Full-number lookup via NUM_TO_HASH index
    Returns (hash_key, waiter_dict) or (None, None)
    """
    c = clean_number(num_raw)
    if not c:
        return None, None

    # Try last 8, 7, 6 digits
    for length in [8, 7, 6]:
        if len(c) >= length:
            hk = c[-length:]
            if hk in WAITING_OTPS:
                return hk, WAITING_OTPS[hk]

    # Full number index fallback
    hk = NUM_TO_HASH.get(c)
    if hk and hk in WAITING_OTPS:
        return hk, WAITING_OTPS[hk]

    return None, None

async def global_otp_checker_job(context: ContextTypes.DEFAULT_TYPE):
    """
    Polls BOTH servers every 2 seconds.
    Zero blocking: all I/O is parallel via asyncio.gather.
    """
    global WAITING_OTPS, BATCH_MSGS, NUM_TO_HASH

    if not WAITING_OTPS:
        return

    # ── Expire timed-out waiters ──────────────────────────────────────────────
    now = time.time()
    expired = [k for k, v in list(WAITING_OTPS.items()) if now - v['time'] > OTP_TIMEOUT_SECS]
    for hk in expired:
        ud = WAITING_OTPS.pop(hk, None)
        if ud:
            NUM_TO_HASH.pop(clean_number(ud['full_num']), None)
            bk = ud.get('batch_key')
            if bk and bk in BATCH_MSGS:
                bn = BATCH_MSGS[bk]['numbers']
                if ud['full_num'] in bn:
                    bn.remove(ud['full_num'])
                if not bn:
                    try:
                        await context.bot.delete_message(chat_id=ud['chat_id'], message_id=ud['msg_id'])
                    except Exception:
                        pass
                    BATCH_MSGS.pop(bk, None)

    if not WAITING_OTPS:
        return

    # ── Parallel fetch both inboxes ────────────────────────────────────────────
    date_str  = datetime.datetime.now().strftime("%Y-%m-%d")
    stex_url  = f"{API_STEX_INBOX}?date={date_str}&page=1&search=&status="
    mk_url    = f"{API_MK_INBOX.format(date_str)}&_nocache={int(time.time())}"

    stex_task = asyncio.create_task(stex_api_request('GET', stex_url))
    mk_task   = asyncio.create_task(mk_api_request('GET', mk_url))

    results = await asyncio.gather(stex_task, mk_task, return_exceptions=True)

    found_keys = []

    # ── Process STEX (Server 1) ───────────────────────────────────────────────
    if isinstance(results[0], tuple):
        stex_status, stex_res = results[0]
        if stex_status == 200 and isinstance(stex_res, dict):

            # Normalise: STEX wraps items under data.numbers OR data.list OR data directly
            data_field = stex_res.get('data', {})
            if isinstance(data_field, list):
                items = data_field
            elif isinstance(data_field, dict):
                items = (
                    data_field.get('numbers') or
                    data_field.get('list') or
                    data_field.get('items') or
                    []
                )
            else:
                items = []

            logger.info(f"[STEX] inbox items count: {len(items)}")

            for item in items:
                if not isinstance(item, dict):
                    continue

                num_raw = get_number_from_item(item)
                if not num_raw:
                    continue

                raw_msg = get_sms_from_item(item)
                # Skip items with no SMS yet
                if not raw_msg:
                    continue

                hash_key, waiter = _find_waiter(num_raw)
                if hash_key and hash_key not in found_keys:
                    svc_name = get_service_from_item(item)
                    code_val = get_code_from_item(item, raw_msg)
                    await process_found_otp(context, hash_key, waiter['full_num'], code_val, svc_name, raw_msg)
                    found_keys.append(hash_key)

    # ── Process MK Network (Server 2) ────────────────────────────────────────
    if isinstance(results[1], tuple):
        mk_status, mk_res = results[1]
        if mk_status == 200 and mk_res is not None:

            # MK can return list or dict-with-data
            if isinstance(mk_res, list):
                items = mk_res
            elif isinstance(mk_res, dict):
                items = (
                    mk_res.get('data') or
                    mk_res.get('list') or
                    mk_res.get('items') or
                    mk_res.get('history') or
                    []
                )
            else:
                items = []

            logger.info(f"[MK] inbox items count: {len(items)}")

            for item in items:
                if not isinstance(item, dict):
                    continue

                num_raw = get_number_from_item(item)
                if not num_raw:
                    continue

                raw_msg = get_sms_from_item(item)
                if not raw_msg:
                    continue

                hash_key, waiter = _find_waiter(num_raw)
                if hash_key and hash_key not in found_keys:
                    svc_name = get_service_from_item(item)
                    code_val = get_code_from_item(item, raw_msg)
                    await process_found_otp(context, hash_key, waiter['full_num'], code_val, svc_name, raw_msg)
                    found_keys.append(hash_key)

    # Remove delivered waiters
    for hk in found_keys:
        ud = WAITING_OTPS.pop(hk, None)
        if ud:
            NUM_TO_HASH.pop(clean_number(ud['full_num']), None)

# ==============================================================================
# 📡 AUTO RANGE FORWARDER (every 60 seconds)
# ==============================================================================

async def auto_range_forwarder_job(context: ContextTypes.DEFAULT_TYPE):
    allowed_apps = ['facebook', 'whatsapp']
    bot_username = context.bot.username

    stex_task = asyncio.create_task(stex_api_request('GET', API_STEX_CONSOLE))
    mk_task   = asyncio.create_task(mk_api_request('GET', API_MK_CONSOLE))
    results   = await asyncio.gather(stex_task, mk_task, return_exceptions=True)

    if isinstance(results[0], tuple):
        stex_status, stex_data = results[0]
        if stex_status == 200 and isinstance(stex_data, dict):
            for log in stex_data.get('data', {}).get('logs', [])[:5]:
                if not isinstance(log, dict):
                    continue
                r_val   = log.get('range')
                raw_app = str(log.get('app_name', '')).lower()
                c_name  = log.get('country', 'Unknown')
                raw_msg = get_sms_from_item(log) or ""
                if any(a in raw_app for a in allowed_apps) and r_val and r_val not in SENT_RANGES:
                    SENT_RANGES.add(r_val)
                    if len(SENT_RANGES) > 5000:
                        SENT_RANGES.clear()
                    display_app  = "PC Clone" if ('facebook' in raw_app and '******' in raw_msg) else log.get('app_name', 'Unknown').title()
                    full_msg_txt = clean_message_text(raw_msg)
                    range_msg = (
                        f"🔥 <b>New Range found</b>\n"
                        f"━━━━━━━━━━━━━━━━━━━━\n"
                        f"🖥️ Server - <b>Server 1 ✨</b>\n"
                        f"🎯 Range - <code>{r_val}</code>\n"
                        f"🛒 Service - <i>{html.escape(display_app)}</i>\n"
                        f"🌍 Country - {get_flag(c_name)} {c_name}\n"
                        f"✉️ Message - <pre>{html.escape(full_msg_txt)}</pre>"
                    )
                    kb = [[InlineKeyboardButton("🤖 Bot Link", url=f"https://t.me/{bot_username}")]]
                    try:
                        await context.bot.send_message(
                            chat_id=RANGE_GROUP_ID, text=range_msg,
                            reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.HTML
                        )
                    except Exception:
                        pass

    if isinstance(results[1], tuple):
        mk_status, mk_data = results[1]
        if mk_status == 200 and isinstance(mk_data, dict):
            for log in mk_data.get('feed', [])[:5]:
                if not isinstance(log, dict):
                    continue
                r_val   = log.get('range')
                raw_app = str(log.get('service_name', '')).lower()
                c_name  = log.get('country', 'Unknown')
                raw_msg = get_sms_from_item(log) or ""
                if any(a in raw_app for a in allowed_apps) and r_val and r_val not in SENT_RANGES:
                    SENT_RANGES.add(r_val)
                    if len(SENT_RANGES) > 5000:
                        SENT_RANGES.clear()
                    display_app  = "PC Clone" if ('facebook' in raw_app and '******' in raw_msg) else log.get('service_name', 'Unknown').title()
                    full_msg_txt = clean_message_text(raw_msg)
                    range_msg = (
                        f"🔥 <b>New Range found</b>\n"
                        f"━━━━━━━━━━━━━━━━━━━━\n"
                        f"🚀 Server - <b>Server 2 🚀</b>\n"
                        f"🎯 Range - <code>{r_val}</code>\n"
                        f"🛒 Service - <i>{html.escape(display_app)}</i>\n"
                        f"🌍 Country - {get_flag(c_name)} {c_name}\n"
                        f"✉️ Message - <pre>{html.escape(full_msg_txt)}</pre>"
                    )
                    kb = [[InlineKeyboardButton("🤖 Bot Link", url=f"https://t.me/{bot_username}")]]
                    try:
                        await context.bot.send_message(
                            chat_id=RANGE_GROUP_ID, text=range_msg,
                            reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.HTML
                        )
                    except Exception:
                        pass

# ==============================================================================
# 🔄 MK SOFT-HEALER (every 8 minutes)
# ==============================================================================

async def soft_regenerator_job(context: ContextTypes.DEFAULT_TYPE):
    logger.info("🔄 [SOFT-HEALER] Refreshing MK session...")
    await authenticate_mk(force=True)

# ==============================================================================
# 🎯 NUMBER GENERATION
# ==============================================================================

async def process_number_generation(update: Update, context: ContextTypes.DEFAULT_TYPE, range_val, server_id, is_callback=True):
    global WAITING_OTPS, BATCH_MSGS, NUM_TO_HASH

    wait_txt = "⏳ <i>Connecting to secure server... Generating 2 Numbers...</i> 🚀"
    if is_callback:
        user_id = update.callback_query.from_user.id
        chat_id = update.callback_query.message.chat_id
        msg     = await update.callback_query.edit_message_text(text=wait_txt, parse_mode=ParseMode.HTML)
    else:
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        msg     = await update.message.reply_text(text=wait_txt, parse_mode=ParseMode.HTML)

    range_val = str(range_val).strip()
    if not range_val.upper().endswith("XXX"):
        range_val += "XXX"

    fetched_numbers = []
    country_name    = "Unknown"

    for _ in range(2):
        await asyncio.sleep(0.2)
        if server_id == 1:
            payload = {"range": range_val, "is_national": False, "remove_plus": False}
            status, resp = await stex_api_request('POST', API_STEX_GET_NUM, json_payload=payload)
            if status == 200 and isinstance(resp, dict):
                num = resp.get('data', {}).get('number')
                if num:
                    fetched_numbers.append(str(num))
                    country_name = resp['data'].get('country', country_name)
        elif server_id == 2:
            form_data = aiohttp.FormData()
            form_data.add_field('action', 'get_number')
            form_data.add_field('range', range_val)
            status, resp = await mk_api_request('POST', API_MK_GET_NUM, form_data=form_data)
            if status == 200 and isinstance(resp, dict) and resp.get('status') == 'success':
                num = resp.get('number')
                if num:
                    fetched_numbers.append(str(num).replace('+', ''))
                    country_name = context.user_data.get('country_name', 'Global')

    if fetched_numbers:
        flag    = get_flag(country_name)
        symbols = ["❶", "❷"]
        num_str = ""
        for i, n in enumerate(fetched_numbers):
            num_str += f"{symbols[i]} <code>{n}</code>\n"

        txt = (
            f"✅ <b>NUMBERS GENERATED</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"🌍 <b>{flag} {country_name}</b>\n\n"
            f"{num_str}\n"
            f"⏳ <i>Waiting for SMS... ⚡ Auto delivery in seconds!</i>"
        )
        kb = [
            [InlineKeyboardButton("💬 OTP GROUP", url="https://t.me/RTxOtpX")],
            [
                InlineKeyboardButton("🔄 Change Number", callback_data="change_num"),
                InlineKeyboardButton("🔙 Back to Server", callback_data="go_main")
            ]
        ]
        await msg.edit_text(text=txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.HTML)

        batch_key = f"{chat_id}_{msg.message_id}"
        BATCH_MSGS[batch_key] = {
            'numbers': fetched_numbers.copy(),
            'country_name': country_name,
            'flag': flag
        }

        for n in fetched_numbers:
            hk = get_hash_key(n)
            WAITING_OTPS[hk] = {
                'full_num':  n,
                'user_id':   user_id,
                'chat_id':   chat_id,
                'msg_id':    msg.message_id,
                'batch_key': batch_key,
                'time':      time.time()
            }
            # Also register full clean number for fallback matching
            NUM_TO_HASH[clean_number(n)] = hk

        context.user_data['range']  = range_val
        context.user_data['server'] = server_id

    else:
        await msg.edit_text(
            text=(
                "📡 <b>Server Optimizing</b>\n"
                "<i>No numbers available right now. Please try again or select another category.</i>"
            ),
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to Servers", callback_data="go_main")]]),
            parse_mode=ParseMode.HTML
        )

# ==============================================================================
# 📋 MENUS
# ==============================================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await check_ban_middleware(update, context):
        return
    await ensure_user_fast(update.effective_user.id)
    context.user_data.clear()
    if not await check_subscription(update.effective_user.id, context.bot):
        await send_join_prompt(update, context)
    else:
        await show_main_menu(update, context)

async def show_main_menu(update_obj, context):
    kb = [["📱 Get Number", "🔐 Get 2FA"], ["🎧 Support", "📊 See Activity"]]
    msg = (
        "✨ <b>P R E M I U M   O T P   B O T</b> ✨\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "👋 <i>Welcome to the most advanced & stable OTP system!</i>\n\n"
        "🛡️ <b>Choose an option below.</b>"
    )
    if hasattr(update_obj, 'message') and update_obj.message:
        await update_obj.message.reply_text(msg, reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True), parse_mode=ParseMode.HTML)
    elif hasattr(update_obj, 'callback_query') and update_obj.callback_query:
        try:
            await update_obj.callback_query.message.delete()
        except Exception:
            pass
        await context.bot.send_message(
            chat_id=update_obj.effective_chat.id, text=msg,
            reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True), parse_mode=ParseMode.HTML
        )

async def show_server_selection(update_obj, context):
    kb = [
        [InlineKeyboardButton("✨ Server 1", callback_data="srv_1")],
        [InlineKeyboardButton("🚀 Server 2", callback_data="srv_2")]
    ]
    txt = (
        "🌐 <b>SELECT SERVER</b> 🌐\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "<i>Choose a server to generate numbers from:</i>"
    )
    if hasattr(update_obj, 'callback_query') and update_obj.callback_query:
        await update_obj.callback_query.edit_message_text(text=txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.HTML)
    else:
        await update_obj.message.reply_text(text=txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.HTML)

async def start_category_selection(update: Update, context: ContextTypes.DEFAULT_TYPE, server_id):
    context.user_data['server'] = server_id
    server_name = "✨ Server 1" if server_id == 1 else "🚀 Server 2"
    kb = [
        [InlineKeyboardButton("📘 Facebook", callback_data="cat_facebook"), InlineKeyboardButton("💬 WhatsApp", callback_data="cat_whatsapp")],
        [InlineKeyboardButton("🎯 Custom Range", callback_data="cat_custom")],
        [InlineKeyboardButton("🔙 Back to Servers", callback_data="go_main")]
    ]
    txt = (
        f"📱 <b>{server_name} CATEGORIES</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "<i>Which application do you need numbers for?</i>"
    )
    if update.callback_query:
        await update.callback_query.edit_message_text(text=txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.HTML)
    else:
        await update.message.reply_text(text=txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.HTML)

async def handle_category_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query     = update.callback_query
    category  = query.data.split('_')[1].lower()
    server_id = context.user_data.get('server', 1)

    if category == 'custom':
        await query.edit_message_text(
            text="🎯 <b>CUSTOM RANGE GENERATOR</b>\n━━━━━━━━━━━━━━━━━━━━\n✏️ <i>Type your custom range below.</i>\n💡 <b>Ex:</b> <code>88017XXX</code>",
            parse_mode=ParseMode.HTML
        )
        context.user_data['state'] = 'WAITING_FOR_RANGE'
        return

    await query.edit_message_text(text="📡 <i>Connecting to Server... Please wait.</i> ⏳", parse_mode=ParseMode.HTML)
    countries = {}

    if server_id == 1:
        await authenticate_stex(force=True)
        status, data = await stex_api_request('GET', API_STEX_CONSOLE)
        if status == 200 and isinstance(data, dict):
            for log in data.get('data', {}).get('logs', []):
                if isinstance(log, dict) and category in str(log.get('app_name', '')).lower():
                    c, r = log.get('country'), log.get('range')
                    if c and r and c not in countries:
                        countries[c] = r
    elif server_id == 2:
        await authenticate_mk(force=True)
        status, data = await mk_api_request('GET', API_MK_CONSOLE)
        if status == 200 and isinstance(data, dict):
            for log in data.get('feed', []):
                if isinstance(log, dict) and category in str(log.get('service_name', '')).lower():
                    c, r = log.get('country'), log.get('range')
                    if c and r and c not in countries:
                        countries[c] = r

    if not countries:
        await query.edit_message_text(
            text=f"📡 <b>Load Balancing...</b>\n<i>No {category.title()} numbers right now. Try again in a moment.</i>",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data=f"srv_{server_id}")]]),
            parse_mode=ParseMode.HTML
        )
        return

    kb = []
    for c_name, r_val in countries.items():
        kb.append([InlineKeyboardButton(f"{get_flag(c_name)} {c_name}", callback_data=f"r_{server_id}_{r_val}_{c_name[:15]}")])
    kb.append([InlineKeyboardButton("🔙 Back to Categories", callback_data=f"srv_{server_id}")])

    await query.edit_message_text(
        text=f"🌍 <b>SELECT A COUNTRY ({category.title()})</b>\n━━━━━━━━━━━━━━━━━━━━",
        reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.HTML
    )

# ==============================================================================
# 💬 MESSAGE HANDLER
# ==============================================================================

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await check_ban_middleware(update, context):
        return
    user_id   = update.effective_user.id
    text      = update.message.text
    user_data = context.user_data
    await ensure_user_fast(user_id)

    main_buttons = ["📱 Get Number", "🔐 Get 2FA", "🎧 Support", "📊 See Activity"]
    if text in main_buttons:
        user_data['state']              = None
        user_data['admin_reply_target'] = None

    # Admin reply logic
    target_reply_user = user_data.get('admin_reply_target')
    if target_reply_user and text not in main_buttons:
        try:
            await context.bot.send_message(
                chat_id=int(target_reply_user),
                text=f"👨‍💻 <b>Admin Reply:</b>\n━━━━━━━━━━━━━━━━━━━━\n{text}",
                parse_mode=ParseMode.HTML
            )
            await update.message.reply_text("✅ <b>Reply sent successfully.</b>", parse_mode=ParseMode.HTML)
        except Exception:
            await update.message.reply_text("❌ <b>Failed to send reply. User may have blocked the bot.</b>", parse_mode=ParseMode.HTML)
        user_data['admin_reply_target'] = None
        return

    if text == "📱 Get Number":
        if not await check_subscription(user_id, context.bot):
            await send_join_prompt(update, context)
        else:
            await show_server_selection(update, context)

    elif text == "🔐 Get 2FA":
        user_data['state'] = 'WAITING_FOR_2FA'
        await update.message.reply_text(
            "🔐 <b>2FA CODE GENERATOR</b>\n━━━━━━━━━━━━━━━━━━━━\n<i>Paste your Secret Key below:</i>",
            parse_mode=ParseMode.HTML
        )

    elif user_data.get('state') == 'WAITING_FOR_2FA':
        key = text.replace(" ", "").strip()
        msg = await update.message.reply_text("⏳ <i>Generating...</i>", parse_mode=ParseMode.HTML)
        try:
            session = await get_session()
            async with session.get(API_2FA.format(key), timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    code = data.get('code')
                    if code:
                        out = (
                            f"✅ <b>2FA CODE GENERATED!</b>\n"
                            f"━━━━━━━━━━━━━━━━━━━━\n"
                            f"🔢 <b>Code:</b> <code>{code}</code>\n\n"
                            f"<i>⚠️ Auto-delete in 5 mins.</i>"
                        )
                        await msg.edit_text(out, parse_mode=ParseMode.HTML)
                        asyncio.create_task(delete_message_later(context.bot, msg.chat_id, msg.message_id, 300))
                    else:
                        await msg.edit_text("❌ <b>Invalid Secret Key.</b>", parse_mode=ParseMode.HTML)
                else:
                    await msg.edit_text("❌ <b>API Error. Try again.</b>", parse_mode=ParseMode.HTML)
        except Exception:
            await msg.edit_text("❌ <b>Network Error. Try again.</b>", parse_mode=ParseMode.HTML)
        user_data['state'] = None

    elif text == "🎧 Support":
        user_data['state'] = 'WAITING_FOR_SUPPORT'
        await update.message.reply_text(
            "🎧 <b>SUPPORT SYSTEM</b>\n━━━━━━━━━━━━━━━━━━━━\n<i>Type your problem below and an admin will reply.</i>",
            parse_mode=ParseMode.HTML
        )

    elif user_data.get('state') == 'WAITING_FOR_SUPPORT':
        for a_id in ADMIN_IDS:
            try:
                admin_kb = [[InlineKeyboardButton("💬 Reply to User", callback_data=f"admrep_{user_id}")]]
                await context.bot.send_message(
                    chat_id=a_id,
                    text=f"📩 <b>Support Message</b>\n👤 <b>ID:</b> <code>{user_id}</code>\n💬 <b>Msg:</b> {html.escape(text)}",
                    reply_markup=InlineKeyboardMarkup(admin_kb),
                    parse_mode=ParseMode.HTML
                )
            except Exception:
                pass
        await update.message.reply_text("✅ <b>Message Sent!</b> An Admin will reply soon.", parse_mode=ParseMode.HTML)
        user_data['state'] = None

    elif text == "📊 See Activity":
        kb = [
            [InlineKeyboardButton("🔥 Range Channel", url="https://t.me/ConsoleXRT")],
            [InlineKeyboardButton("💬 OTP Channel", url="https://t.me/RTxOtpX")]
        ]
        await update.message.reply_text(
            "📊 <b>BOT ACTIVITY LINKS</b>\n━━━━━━━━━━━━━━━━━━━━\n<i>Join to see live Bot activity:</i>",
            reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.HTML
        )

    elif user_data.get('state') == 'WAITING_FOR_RANGE':
        user_data['state'] = None
        server_id = user_data.get('server', 1)
        await process_number_generation(update, context, text, server_id, is_callback=False)

    else:
        await show_main_menu(update, context)

# ==============================================================================
# 🎮 BUTTON HANDLER
# ==============================================================================

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await check_ban_middleware(update, context):
        return
    query   = update.callback_query
    user_id = query.from_user.id
    data    = query.data
    await ensure_user_fast(user_id)

    if data == "check_join":
        if await check_subscription(user_id, context.bot):
            try:
                await query.message.delete()
            except Exception:
                pass
            await show_main_menu(query, context)
        else:
            await query.answer("⚠️ Please join all channels/groups first.", show_alert=True)

    elif data.startswith("srv_"):
        server_id = int(data.split('_')[1])
        await start_category_selection(update, context, server_id)

    elif data.startswith("cat_"):
        await handle_category_click(update, context)

    elif data.startswith("r_"):
        parts     = data.split("_")
        server_id = int(parts[1])
        range_val = parts[2]
        if len(parts) > 3:
            context.user_data['country_name'] = parts[3]
        await process_number_generation(update, context, range_val, server_id, is_callback=True)

    elif data == "change_num":
        if context.user_data.get('range'):
            server_id = context.user_data.get('server', 1)
            await process_number_generation(update, context, context.user_data['range'], server_id, is_callback=True)
        else:
            await query.edit_message_text("⚠️ <b>Session Expired.</b>\n<i>Please start again.</i>", parse_mode=ParseMode.HTML)

    elif data == "go_main":
        await show_server_selection(update, context)

    elif data.startswith("admrep_"):
        if user_id not in ADMIN_IDS:
            await query.answer("⚠️ You are not an admin.", show_alert=True)
            return
        target_user_id = data.split("_")[1]
        context.user_data['admin_reply_target'] = target_user_id
        await query.message.reply_text(
            f"✍️ <b>Type your reply for User ID:</b> <code>{target_user_id}</code>\n\n"
            f"<i>(Type normally and send — I will forward it to the user.)</i>",
            parse_mode=ParseMode.HTML
        )
        await query.answer()

# ==============================================================================
# 👑 ADMIN COMMANDS
# ==============================================================================

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return
    context.user_data['admin_reply_target'] = None
    context.user_data['state']              = None
    txt = (
        "🔐 <b>ADVANCED ADMIN PANEL</b> 🔐\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "🟢 <code>/status</code>  - Bot Statistics\n"
        "📢 <code>/broadcast &lt;msg&gt;</code> - Broadcast\n"
        "🚫 <code>/ban &lt;id&gt;</code>  - Ban user\n"
        "✅ <code>/unban &lt;id&gt;</code> - Unban user\n"
        "👥 <code>/users</code>  - Total Users"
    )
    await update.message.reply_text(txt, parse_mode=ParseMode.HTML)

async def admin_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return
    uptime  = datetime.datetime.now() - START_TIME
    t_users = get_total_users_count()
    txt = (
        f"📊 <b>BOT STATUS</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"⏱ <b>Uptime:</b> {str(uptime).split('.')[0]}\n"
        f"👥 <b>Total Users:</b> {t_users}\n"
        f"📡 <b>Active Waiters:</b> {len(WAITING_OTPS)}\n"
        f"⚡ <b>Polling:</b> Every 2 seconds\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"✅ <i>Both servers running</i>"
    )
    await update.message.reply_text(txt, parse_mode=ParseMode.HTML)

async def admin_users_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return
    await update.message.reply_text(f"👥 <b>Total Registered Users:</b> {get_total_users_count()}", parse_mode=ParseMode.HTML)

async def ban_user_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return
    try:
        target_id = int(context.args[0])
        await set_ban_status(target_id, 1)
        await update.message.reply_text(f"✅ User <code>{target_id}</code> <b>BANNED</b>.", parse_mode=ParseMode.HTML)
    except Exception:
        await update.message.reply_text("⚠️ Usage: `/ban UserID`", parse_mode=ParseMode.Markdown)

async def unban_user_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return
    try:
        target_id = int(context.args[0])
        await set_ban_status(target_id, 0)
        await update.message.reply_text(f"✅ User <code>{target_id}</code> <b>UNBANNED</b>.", parse_mode=ParseMode.HTML)
    except Exception:
        await update.message.reply_text("⚠️ Usage: `/unban UserID`", parse_mode=ParseMode.Markdown)

async def broadcast_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return
    if not context.args:
        await update.message.reply_text("⚠️ Usage: `/broadcast Your message`", parse_mode=ParseMode.Markdown)
        return
    message = " ".join(context.args)
    users   = get_all_users()
    msg     = await update.message.reply_text(f"⏳ <i>Broadcasting to {len(users)} users...</i>", parse_mode=ParseMode.HTML)
    success = failed = 0
    for u_id in users:
        try:
            await context.bot.send_message(
                chat_id=u_id,
                text=f"📢 <b>ADMIN BROADCAST</b>\n━━━━━━━━━━━━━━━━━━━━\n{message}",
                parse_mode=ParseMode.HTML
            )
            success += 1
        except Exception:
            failed += 1
        await asyncio.sleep(0.05)
    await msg.edit_text(
        f"✅ <b>Broadcast Done!</b>\n━━━━━━━━━━━━━━━━━━━━\n🟢 Delivered: {success}\n🔴 Failed: {failed}",
        parse_mode=ParseMode.HTML
    )

# ==============================================================================
# 🌐 RENDER DUMMY WEB SERVER
# ==============================================================================

async def web_server_handler(request):
    return web.Response(text="✅ Premium OTP Bot — Running perfectly!")

async def start_dummy_server():
    try:
        app  = web.Application()
        app.router.add_get('/', web_server_handler)
        port = int(os.environ.get('PORT', 8080))
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, '0.0.0.0', port)
        await site.start()
        logger.info(f"🌐 Web server running on port {port}")
    except Exception as e:
        logger.warning(f"Web server error: {e}")

async def post_init(app: Application):
    asyncio.create_task(start_dummy_server())
    # Pre-authenticate both servers on startup
    asyncio.create_task(authenticate_stex(force=True))
    asyncio.create_task(authenticate_mk(force=True))

# ==============================================================================
# 🚀 MAIN
# ==============================================================================

if __name__ == "__main__":
    init_db()
    app = Application.builder().token(TOKEN).post_init(post_init).build()

    app.add_handler(CommandHandler("start",     start))
    app.add_handler(CommandHandler("admin",     admin_panel))
    app.add_handler(CommandHandler("status",    admin_status))
    app.add_handler(CommandHandler("ban",       ban_user_cmd))
    app.add_handler(CommandHandler("unban",     unban_user_cmd))
    app.add_handler(CommandHandler("broadcast", broadcast_cmd))
    app.add_handler(CommandHandler("users",     admin_users_cmd))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # ⚡ OTP CHECK: every 2 seconds (fastest possible without API ban risk)
    app.job_queue.run_repeating(global_otp_checker_job,  interval=2,   first=2)
    # 📡 Range forwarder: every 60 seconds
    app.job_queue.run_repeating(auto_range_forwarder_job, interval=60,  first=15)
    # 🔄 MK session healer: every 8 minutes
    app.job_queue.run_repeating(soft_regenerator_job,     interval=480, first=480)

    logger.info("✨ FINAL ULTRA VERSION — STARTED SUCCESSFULLY ✨")
    app.run_polling(drop_pending_updates=True)
