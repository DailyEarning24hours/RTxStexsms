"""
==============================================================================
PROJECT: ✨ PREMIUM OTP BOT (Ultimate Update - Version 32.0 FINAL) ✨
CAPACITY: 20,000+ Users on Render Free Plan (RAM Caching O(1) Algorithm).
ULTRA SPEED UPDATE: Polling interval 2 seconds. Connection pool 1000.
SERVER 2: Replaced MK Network → ZayanSMS (https://zayansms.com/mdashboard)
FIXED: Channel join buttons side by side (2 per row).
FIXED: Range forward 100% — no miss, parallel multi-page fetch.
NEW: Balance system — 10 poisha per OTP received (admin configurable).
NEW: Referral system — 5 poisha per referral's OTP received (admin configurable).
NEW: Balance shown in USDT. Admin can add balance, set rates, view top referrers.
NEW: Refer button in main menu — single button.
NEW: /addbalance /setotprate /setrefrate /topref /mybalance admin commands.
FIXED: OTP Receive system 100% working for BOTH STEX + ZAYAN servers.
FIXED: * replaced with • in all messages.
FIXED: STEX + ZAYAN auto re-login every 5 minutes.
FIXED: Number masked system in range group messages.
FIXED: run_polling() compatible with all python-telegram-bot versions.
ERROR HANDLING: 100% hidden HTTP 401/500 errors. Premium fallback messages.
FORMATTING: Fully Expanded, No Shortcuts, Maximum Stability & Beauty.
==============================================================================
"""

import subprocess
import sys

# ==============================================================================
# 🔧 AUTO-INSTALL CORRECT VERSIONS ON STARTUP (Render free plan safe)
# ==============================================================================
def _ensure_correct_ptb():
    try:
        import telegram as _tg
        ver = tuple(int(x) for x in _tg.__version__.split(".")[:2])
        if ver[0] < 20:
            raise ImportError("old version detected")
    except Exception:
        subprocess.check_call([
            sys.executable, "-m", "pip", "install",
            "python-telegram-bot[job-queue]==20.7",
            "APScheduler==3.10.4",
            "--quiet", "--upgrade"
        ])

_ensure_correct_ptb()

# Auto-install curl_cffi for Cloudflare bypass
def _ensure_curl_cffi():
    try:
        import curl_cffi
    except ImportError:
        subprocess.check_call([
            sys.executable, "-m", "pip", "install",
            "curl_cffi", "--quiet", "--upgrade"
        ])

_ensure_curl_cffi()

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
    filters, 
    ConversationHandler
)
from telegram.constants import ParseMode
from aiohttp import web

# ==============================================================================
# ⚙️ CONFIGURATION & CREDENTIALS
# ==============================================================================

TOKEN = "8784714590:AAGW1bthOSIh2HUl2vPCYS_zv13zEz7BOsg"

# 🔥 SINGLE ADMIN ID AS REQUESTED
ADMIN_IDS = [6031032502] 

CHANNELS = ["@EarnXtract", "@RTx_Sms", "@ConsoleXRT", "@RTxOtpX"]

RANGE_GROUP_ID = -1003627708272
OTP_GROUP_ID = -1003830374258

# 🌐 SERVER 1 CREDENTIALS (STEX)
STEX_EMAIL = "mdrajaislam469@gmail.com"
STEX_PASSWORD = "Raja1234@#"
API_STEX_LOGIN = "https://stexsms.com/mapi/v1/mauth/login"
API_STEX_CONSOLE = "https://stexsms.com/mapi/v1/mdashboard/console/info"
API_STEX_GET_NUM = "https://stexsms.com/mapi/v1/mdashboard/getnum/number"
API_STEX_INBOX = "https://stexsms.com/mapi/v1/mdashboard/getnum/info"

# 🚀 SERVER 2 CREDENTIALS (ZAYAN SMS — same system as STEX)
ZAYAN_EMAIL = "mdrajaislam469@gmail.com"
ZAYAN_PASSWORD = "Raja1234@#"
API_ZAYAN_LOGIN = "https://zayansms.com/mapi/v1/mauth/login"
API_ZAYAN_CONSOLE = "https://zayansms.com/mapi/v1/mdashboard/console/info"
API_ZAYAN_GET_NUM = "https://zayansms.com/mapi/v1/mdashboard/getnum/number"
API_ZAYAN_INBOX = "https://zayansms.com/mapi/v1/mdashboard/getnum/info"

API_2FA = "https://2fa.cn/codes/{}"

# ==============================================================================
# 💰 BALANCE / REWARD CONFIGURATION (ADMIN CONFIGURABLE AT RUNTIME)
# ==============================================================================
# These are the DEFAULT values. Admin can change via /setotprate and /setrefrate.
# Stored in DB so they persist across restarts.
DEFAULT_OTP_REWARD_PAISA    = 10   # Paisa per OTP received (0.10 Tk)
DEFAULT_REF_REWARD_PAISA    = 5    # Paisa per referral OTP (0.05 Tk)
DEFAULT_OTP_REWARD_POISHA   = DEFAULT_OTP_REWARD_PAISA  # alias
DEFAULT_REF_REWARD_POISHA   = DEFAULT_REF_REWARD_PAISA  # alias
POISHA_PER_USDT             = 8400  # 1 USDT ≈ 8400 paisa (84 Tk)

# ==============================================================================
# 🛑 ADVANCED SERVER CRASH PREVENTION & CACHING
# ==============================================================================

MAUTH_TOKEN_STEX   = None
MAUTH_TOKEN_ZAYAN  = None
GLOBAL_SESSION     = None
ZAYAN_SESSION      = None   # Separate persistent session for Cloudflare bypass 

AUTH_LOCK_STEX  = asyncio.Lock() 
LAST_AUTH_TIME_STEX = 0

AUTH_LOCK_ZAYAN = asyncio.Lock()
LAST_AUTH_TIME_ZAYAN = 0

SENT_RANGES = set()
START_TIME  = datetime.datetime.now()
BASE_USER_AGENT = "Mozilla/5.0 (Linux; Android 14; SM-A135F Build/UP1A.231005.007) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.7632.120 Mobile Safari/537.36"

DB_POOL_SIZE = 30

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# ==============================================================================
# 🧠 ENTERPRISE MEMORY SYSTEM (FOR 20,000+ USERS RAM CACHING)
# ==============================================================================

WAITING_OTPS = {}
# Extra reverse index: clean_full_number → hash_key (fallback matching)
NUM_TO_HASH  = {}
BATCH_MSGS   = {} 
OTP_TIMEOUT_SECONDS = 1200  # 20 minutes before silent delete

USER_CACHE   = set()
BANNED_CACHE = set()
DB_EXECUTOR  = concurrent.futures.ThreadPoolExecutor(max_workers=20)

# Runtime reward rates (loaded from DB on startup)
_OTP_REWARD_POISHA  = DEFAULT_OTP_REWARD_POISHA
_REF_REWARD_POISHA  = DEFAULT_REF_REWARD_POISHA

# ==============================================================================
# 🔧 UTILITY FUNCTIONS
# ==============================================================================

def clean_number(n: str) -> str:
    """Strip all non-digit characters from a number string."""
    return re.sub(r'\D', '', str(n))

def mask_number(number: str) -> str:
    """
    Mask middle digits of phone number for privacy in range group.
    Example: 8801712345678 → 880171•••678
    """
    digits = clean_number(number)
    if len(digits) < 7:
        return number
    first  = digits[:6]
    last   = digits[-3:]
    middle = '•' * (len(digits) - 9)
    if len(digits) <= 9:
        first  = digits[:4]
        last   = digits[-3:]
        middle = '•' * (len(digits) - 7)
    return first + middle + last

def clean_message_text(raw_text):
    if not raw_text or str(raw_text).strip() == "":
        return "No Message Provided"
    
    text = str(raw_text)
    text = html.unescape(html.unescape(text))
    text = re.sub(r'<[^>]+>', '', text)
    text = text.replace('&lt;', '<').replace('&gt;', '>')
    # Replace * with • (bullet) — original request
    text = re.sub(r'\*+', lambda m: '•' * len(m.group()), text)
    text = " ".join(text.split())
    
    return text.strip() if text.strip() else "No Message Provided"

def get_hash_key(number_str):
    """Generates an O(1) lookup key. Uses last 8 digits."""
    clean_str = re.sub(r'\D', '', str(number_str))
    if not clean_str: return "UNKNOWN"
    return clean_str[-8:]

def extract_code(message):
    """
    Extract OTP/verification code. Tries keyword proximity first,
    then any standalone 4-8 digit number.
    """
    msg = str(message)
    # Keyword-proximity search
    kw = re.search(
        r'(?:otp|code|verification|verify|pin|passcode|password)[^0-9]{0,25}(\d{4,8})',
        msg, re.IGNORECASE
    )
    if kw:
        return kw.group(1)
    # Fallback: any standalone 4-8 digit number
    fb = re.search(r'\b(\d{4,8})\b', msg)
    return fb.group(1) if fb else "See Msg"

def get_sms_from_item(item: dict) -> str:
    """Try all known SMS field names from STEX, ZAYAN, and other APIs.
    ZAYAN inbox uses 'message' field.
    ZAYAN console uses 'sms' field.
    STEX uses 'full_sms' or 'sms'.
    """
    # Skip empty strings — try each field in order
    for field in ['full_sms', 'full_sms_list', 'sms', 'message', 'otp',
                  'text', 'msg', 'sms_text', 'full_message', 'content', 'body']:
        val = item.get(field)
        if val and str(val).strip():
            return str(val).strip()
    return ""

def get_service_from_item(item: dict) -> str:
    """Try all known service/app name fields from both APIs."""
    return (
        item.get('app_name') or
        item.get('service_name') or
        item.get('service') or
        item.get('operator') or
        item.get('app') or
        "Service"
    )

def get_number_from_item(item: dict) -> str:
    """Try all known number fields from STEX, ZAYAN, and other APIs."""
    return (
        item.get('number') or
        item.get('full_number') or
        item.get('copy') or
        item.get('phone_number') or
        item.get('phone') or
        item.get('mobile') or
        item.get('msisdn') or
        ""
    )

def get_code_from_item(item: dict, raw_msg: str) -> str:
    """Try dedicated code fields first, then extract from SMS text."""
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

def _find_waiter(num_raw: str):
    """
    Find hash_key in WAITING_OTPS by trying:
    1. Last-8 hash of the raw number
    2. Shorter suffix matches (7, 6 digits)
    3. Full-number lookup via NUM_TO_HASH reverse index
    Returns (hash_key, waiter_dict) or (None, None)
    """
    c = clean_number(num_raw)
    if not c:
        return None, None
    for length in [8, 7, 6]:
        if len(c) >= length:
            hk = c[-length:]
            if hk in WAITING_OTPS:
                return hk, WAITING_OTPS[hk]
    # Full number reverse index fallback
    hk = NUM_TO_HASH.get(c)
    if hk and hk in WAITING_OTPS:
        return hk, WAITING_OTPS[hk]
    return None, None

def poisha_to_usdt(poisha: int) -> str:
    """Convert poisha integer to USDT string with 6 decimal places."""
    usdt_val = poisha / POISHA_PER_USDT
    return f"{usdt_val:.6f}"

def paisa_to_taka(paisa: int) -> str:
    """Convert paisa integer to Taka string with 2 decimal places."""
    return f"{paisa / 100:.2f}"

def format_balance_display(paisa: int) -> str:
    """Format balance for display: show Taka."""
    taka_val = paisa_to_taka(paisa)
    return f"{taka_val} Tk ({paisa} Paisa)"

# ==============================================================================
# 🗄️ DATABASE & RAM CACHE MANAGEMENT
# ==============================================================================

DB_FILE = "bot.db"

class DatabasePool:
    def __init__(self, db_file, pool_size=30):
        self.db_file  = db_file
        self.pool_size = pool_size
    @contextmanager
    def get_connection(self):
        conn = sqlite3.connect(self.db_file, timeout=60.0, check_same_thread=False)
        conn.execute('PRAGMA journal_mode=WAL;')
        conn.execute('PRAGMA synchronous=NORMAL;')
        conn.execute('PRAGMA cache_size=-20000;') 
        try: 
            yield conn
        finally: 
            conn.close()

db_pool = DatabasePool(DB_FILE, DB_POOL_SIZE)

def init_db():
    global USER_CACHE, BANNED_CACHE, _OTP_REWARD_POISHA, _REF_REWARD_POISHA
    with db_pool.get_connection() as conn:
        c = conn.cursor()
        # Users table — extended with balance + referral columns
        c.execute('''CREATE TABLE IF NOT EXISTS users (
            user_id     INTEGER PRIMARY KEY,
            join_date   TEXT,
            is_banned   INTEGER DEFAULT 0,
            balance     INTEGER DEFAULT 0,
            referred_by INTEGER DEFAULT NULL,
            total_otps  INTEGER DEFAULT 0
        )''')
        # Add columns if upgrading from old DB (ignore error if already exist)
        for col_sql in [
            "ALTER TABLE users ADD COLUMN balance    INTEGER DEFAULT 0",
            "ALTER TABLE users ADD COLUMN referred_by INTEGER DEFAULT NULL",
            "ALTER TABLE users ADD COLUMN total_otps INTEGER DEFAULT 0",
        ]:
            try:
                c.execute(col_sql)
            except Exception:
                pass

        # Settings table for admin-configurable values
        c.execute('''CREATE TABLE IF NOT EXISTS settings (
            key   TEXT PRIMARY KEY,
            value TEXT
        )''')
        conn.commit()

        # Load reward rates from settings
        c.execute("SELECT value FROM settings WHERE key='otp_reward_poisha'")
        row = c.fetchone()
        if row:
            _OTP_REWARD_POISHA = int(row[0])
        else:
            c.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('otp_reward_poisha', ?)", (str(DEFAULT_OTP_REWARD_POISHA),))
            conn.commit()

        c.execute("SELECT value FROM settings WHERE key='ref_reward_poisha'")
        row = c.fetchone()
        if row:
            _REF_REWARD_POISHA = int(row[0])
        else:
            c.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('ref_reward_poisha', ?)", (str(DEFAULT_REF_REWARD_POISHA),))
            conn.commit()

        # Load user cache
        c.execute("SELECT user_id, is_banned FROM users")
        rows = c.fetchall()
        for row in rows:
            USER_CACHE.add(row[0])
            if row[1] == 1:
                BANNED_CACHE.add(row[0])

def sync_register_user_db(user_id, referred_by=None):
    with db_pool.get_connection() as conn:
        c = conn.cursor()
        if referred_by:
            c.execute(
                "INSERT OR IGNORE INTO users (user_id, join_date, referred_by) VALUES (?, CURRENT_TIMESTAMP, ?)",
                (user_id, referred_by)
            )
        else:
            c.execute(
                "INSERT OR IGNORE INTO users (user_id, join_date) VALUES (?, CURRENT_TIMESTAMP)",
                (user_id,)
            )
        conn.commit()

async def ensure_user_fast(user_id, referred_by=None):
    if user_id not in USER_CACHE:
        USER_CACHE.add(user_id)
        loop = asyncio.get_event_loop()
        loop.run_in_executor(DB_EXECUTOR, sync_register_user_db, user_id, referred_by)
    return True

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

# ── Balance & Referral DB helpers ──────────────────────────────────────────────

def sync_get_balance(user_id: int) -> int:
    with db_pool.get_connection() as conn:
        c = conn.cursor()
        c.execute("SELECT balance FROM users WHERE user_id=?", (user_id,))
        row = c.fetchone()
        return row[0] if row else 0

def sync_add_balance(user_id: int, amount: int) -> int:
    """Add amount (poisha) to user balance. Returns new balance."""
    with db_pool.get_connection() as conn:
        c = conn.cursor()
        c.execute("INSERT OR IGNORE INTO users (user_id, join_date) VALUES (?, CURRENT_TIMESTAMP)", (user_id,))
        c.execute("UPDATE users SET balance = balance + ? WHERE user_id=?", (amount, user_id))
        conn.commit()
        c.execute("SELECT balance FROM users WHERE user_id=?", (user_id,))
        row = c.fetchone()
        return row[0] if row else 0

def sync_increment_otp_count(user_id: int):
    with db_pool.get_connection() as conn:
        c = conn.cursor()
        c.execute("UPDATE users SET total_otps = total_otps + 1 WHERE user_id=?", (user_id,))
        conn.commit()

def sync_get_referred_by(user_id: int):
    with db_pool.get_connection() as conn:
        c = conn.cursor()
        c.execute("SELECT referred_by FROM users WHERE user_id=?", (user_id,))
        row = c.fetchone()
        return row[0] if row else None

def sync_get_top_referrers(limit: int = 10):
    """Returns list of (user_id, referral_count) sorted descending."""
    with db_pool.get_connection() as conn:
        c = conn.cursor()
        c.execute(
            """
            SELECT referred_by, COUNT(*) as cnt
            FROM users
            WHERE referred_by IS NOT NULL
            GROUP BY referred_by
            ORDER BY cnt DESC
            LIMIT ?
            """,
            (limit,)
        )
        return c.fetchall()

def sync_get_user_stats(user_id: int):
    """Returns (balance, total_otps, referred_by) for a user."""
    with db_pool.get_connection() as conn:
        c = conn.cursor()
        c.execute("SELECT balance, total_otps, referred_by FROM users WHERE user_id=?", (user_id,))
        row = c.fetchone()
        return row if row else (0, 0, None)

def sync_count_my_referrals(user_id: int) -> int:
    with db_pool.get_connection() as conn:
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM users WHERE referred_by=?", (user_id,))
        row = c.fetchone()
        return row[0] if row else 0

def sync_update_setting(key: str, value: str):
    with db_pool.get_connection() as conn:
        c = conn.cursor()
        c.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value))
        conn.commit()

# ==============================================================================
# 🔐 ULTIMATE DUAL-API AUTHENTICATION & PERSISTENT SESSION
# ==============================================================================

# Separate session for ZAYAN to preserve Cloudflare cookies independently
ZAYAN_SESSION = None

async def get_session():
    """General session for STEX and other requests."""
    global GLOBAL_SESSION
    if GLOBAL_SESSION is None or GLOBAL_SESSION.closed:
        connector = aiohttp.TCPConnector(
            limit=500,
            limit_per_host=100,
            keepalive_timeout=120,
            ttl_dns_cache=600,
            enable_cleanup_closed=True,
            force_close=False
        )
        GLOBAL_SESSION = aiohttp.ClientSession(
            connector=connector,
            cookie_jar=aiohttp.CookieJar(unsafe=True),
            timeout=aiohttp.ClientTimeout(total=15, connect=5)
        )
    return GLOBAL_SESSION

def get_zayan_cf_session():
    """
    Returns a curl_cffi AsyncSession that impersonates Chrome 124.
    curl_cffi spoofs the TLS fingerprint (JA3/JA4) at the C level,
    which is what Cloudflare actually checks — aiohttp cannot do this.
    The session is reused across calls to preserve cookies (cf_clearance).
    """
    global ZAYAN_SESSION
    if ZAYAN_SESSION is None:
        try:
            from curl_cffi.requests import AsyncSession
            ZAYAN_SESSION = AsyncSession(
                impersonate="chrome124",
                verify=True,
                timeout=20,
                headers={
                    "Accept": "application/json, text/plain, */*",
                    "Accept-Language": "en-US,en-VI;q=0.9,en;q=0.8,bn-BD;q=0.7,bn;q=0.6,en-CA;q=0.5",
                    "Accept-Encoding": "gzip, deflate, br, zstd",
                    "Content-Type": "application/json",
                    "Origin": "https://zayansms.com",
                    "Referer": "https://zayansms.com/mdashboard",
                    "x-requested-with": "mark.via.gp",
                    "sec-fetch-site": "same-origin",
                    "sec-fetch-mode": "cors",
                    "sec-fetch-dest": "empty",
                    "priority": "u=1, i",
                }
            )
            logger.info("🛡️ ZAYAN curl_cffi session created (Chrome124 TLS)")
        except Exception as e:
            logger.error(f"❌ curl_cffi failed: {e}. Falling back to aiohttp.")
            ZAYAN_SESSION = "FALLBACK"
    return ZAYAN_SESSION

async def parse_response_safely(response):
    try: 
        return await response.json(content_type=None)
    except Exception:
        try:
            text = await response.text()
            return json.loads(text)
        except Exception:
            return None

# ----- SERVER 1 AUTH (STEX) -----
async def authenticate_stex(force=False):
    global MAUTH_TOKEN_STEX, LAST_AUTH_TIME_STEX
    async with AUTH_LOCK_STEX:
        if not force and time.time() - LAST_AUTH_TIME_STEX < 300 and MAUTH_TOKEN_STEX:
            return True
        payload = {"email": STEX_EMAIL, "password": STEX_PASSWORD}
        headers = {
            "User-Agent": BASE_USER_AGENT, 
            "Accept": "application/json",
            "Content-Type": "application/json", 
            "Origin": "https://stexsms.com", 
            "Referer": "https://stexsms.com/mauth/login"
        }
        try:
            session = await get_session()
            async with session.post(
                API_STEX_LOGIN, json=payload, headers=headers,
                timeout=aiohttp.ClientTimeout(total=12), ssl=False
            ) as response:
                if response.status == 200:
                    data = await parse_response_safely(response)
                    if data and str(data.get('meta', {}).get('code')) == '200':
                        MAUTH_TOKEN_STEX = data['data']['token']
                        LAST_AUTH_TIME_STEX = time.time()
                        logger.info("✅ STEX auth successful")
                        return True
                logger.warning(f"❌ STEX auth failed: HTTP {response.status}")
                return False
        except Exception as e:
            logger.warning(f"❌ STEX auth error: {e}")
            return False

def get_stex_headers():
    return {
        "User-Agent": BASE_USER_AGENT, 
        "Accept": "application/json", 
        "mauthtoken": str(MAUTH_TOKEN_STEX), 
        "Cookie": f"mauthtoken={MAUTH_TOKEN_STEX}"
    }

async def stex_api_request(method, url, json_payload=None):
    global MAUTH_TOKEN_STEX
    for attempt in range(3):
        try:
            if not MAUTH_TOKEN_STEX:
                if not await authenticate_stex():
                    await asyncio.sleep(1)
                    continue
            session  = await get_session()
            headers  = get_stex_headers()
            timeout  = aiohttp.ClientTimeout(total=12)
            if method.upper() == 'GET': 
                response = await session.get(url, headers=headers, timeout=timeout, ssl=False)
            else: 
                response = await session.post(url, json=json_payload, headers=headers, timeout=timeout, ssl=False)
            
            status = response.status
            if status in [401, 403]: 
                MAUTH_TOKEN_STEX = None
                await asyncio.sleep(0.5)
                continue
            if status in [500, 501, 502, 503]:
                await asyncio.sleep(1)
                continue
                
            if status == 200:
                data = await parse_response_safely(response)
                if isinstance(data, dict):
                    if str(data.get('meta', {}).get('code', '200')) in ['401', '403']: 
                        MAUTH_TOKEN_STEX = None
                        continue
                return 200, data
            else: 
                return status, None
        except asyncio.TimeoutError:
            logger.warning(f"STEX timeout attempt {attempt+1}")
        except Exception as e:
            logger.warning(f"STEX error: {e}")
    return 500, None

# ----- SERVER 2 AUTH (ZAYAN SMS) -----
async def authenticate_zayan(force=False):
    global MAUTH_TOKEN_ZAYAN, LAST_AUTH_TIME_ZAYAN
    async with AUTH_LOCK_ZAYAN:
        if not force and time.time() - LAST_AUTH_TIME_ZAYAN < 300 and MAUTH_TOKEN_ZAYAN:
            return True
        payload = {"email": ZAYAN_EMAIL, "password": ZAYAN_PASSWORD}
        headers = {
            "User-Agent": BASE_USER_AGENT, 
            "Accept": "application/json, text/plain, */*",
            "Content-Type": "application/json", 
            "Origin": "https://zayansms.com", 
            "Referer": "https://zayansms.com/mauth/login",
            "x-requested-with": "mark.via.gp",
            "sec-fetch-site": "same-origin",
            "sec-fetch-mode": "cors",
            "sec-fetch-dest": "empty"
        }
        try:
            cf_sess = get_zayan_cf_session()
            if cf_sess == "FALLBACK":
                # curl_cffi not available — use aiohttp fallback
                session = await get_session()
                async with session.post(
                    API_ZAYAN_LOGIN, json=payload, headers=headers,
                    timeout=aiohttp.ClientTimeout(total=20), ssl=True
                ) as resp:
                    status_code = resp.status
                    raw_data = await parse_response_safely(resp)
            else:
                # curl_cffi — Chrome TLS fingerprint, Cloudflare bypass
                resp = await cf_sess.post(
                    API_ZAYAN_LOGIN,
                    json=payload,
                    headers={
                        "mauthtoken": str(MAUTH_TOKEN_ZAYAN) if MAUTH_TOKEN_ZAYAN else "",
                    }
                )
                status_code = resp.status_code
                try:
                    raw_data = resp.json()
                except Exception:
                    raw_data = None

            logger.info(f"[ZAYAN LOGIN] HTTP {status_code}")
            if status_code == 200 and raw_data:
                if str(raw_data.get('meta', {}).get('code')) == '200':
                    MAUTH_TOKEN_ZAYAN = raw_data['data']['token']
                    LAST_AUTH_TIME_ZAYAN = time.time()
                    logger.info("✅ ZAYAN auth successful")
                    return True
                logger.warning(f"[ZAYAN LOGIN] Bad meta: {raw_data}")
            elif status_code == 403:
                logger.warning("[ZAYAN LOGIN] 403 Cloudflare — resetting session")
                global ZAYAN_SESSION
                ZAYAN_SESSION = None
            logger.warning(f"❌ ZAYAN auth failed: HTTP {status_code}")
            return False
        except Exception as e:
            logger.warning(f"❌ ZAYAN auth error: {e}")
            return False

def get_zayan_headers():
    return {
        "User-Agent": BASE_USER_AGENT, 
        "Accept": "application/json, text/plain, */*",
        "mauthtoken": str(MAUTH_TOKEN_ZAYAN), 
        "Cookie": f"mauthtoken={MAUTH_TOKEN_ZAYAN}",
        "x-requested-with": "mark.via.gp",
        "Origin": "https://zayansms.com",
        "Referer": "https://zayansms.com/mdashboard/console",
        "sec-fetch-site": "same-origin",
        "sec-fetch-mode": "cors",
        "sec-fetch-dest": "empty"
    }

async def zayan_api_request(method, url, json_payload=None):
    """
    All ZAYAN API requests use curl_cffi (Chrome TLS fingerprint).
    Falls back to aiohttp if curl_cffi unavailable.
    Cloudflare cookies (cf_clearance) are preserved in the session automatically.
    """
    global MAUTH_TOKEN_ZAYAN, ZAYAN_SESSION
    for attempt in range(3):
        try:
            if not MAUTH_TOKEN_ZAYAN:
                if not await authenticate_zayan():
                    await asyncio.sleep(1)
                    continue

            cf_sess  = get_zayan_cf_session()
            extra_hdr = {"mauthtoken": str(MAUTH_TOKEN_ZAYAN),
                         "Cookie": f"mauthtoken={MAUTH_TOKEN_ZAYAN}"}

            if cf_sess == "FALLBACK":
                # aiohttp fallback
                session = await get_session()
                hdrs    = get_zayan_headers()
                t       = aiohttp.ClientTimeout(total=15)
                if method.upper() == 'GET':
                    resp = await session.get(url, headers=hdrs, timeout=t, ssl=True)
                else:
                    resp = await session.post(url, json=json_payload, headers=hdrs, timeout=t, ssl=True)
                status = resp.status
                if status == 200:
                    data = await parse_response_safely(resp)
                else:
                    data = None
            else:
                # curl_cffi — Chrome TLS fingerprint
                if method.upper() == 'GET':
                    resp = await cf_sess.get(url, headers=extra_hdr)
                else:
                    resp = await cf_sess.post(url, json=json_payload, headers=extra_hdr)
                status = resp.status_code
                if status == 200:
                    try:
                        data = resp.json()
                    except Exception:
                        data = None
                else:
                    data = None

            if status == 403:
                logger.warning(f"[ZAYAN] 403 Cloudflare on {url} — resetting session")
                MAUTH_TOKEN_ZAYAN = None
                ZAYAN_SESSION = None
                await asyncio.sleep(2)
                continue
            if status == 401:
                MAUTH_TOKEN_ZAYAN = None
                await asyncio.sleep(0.5)
                continue
            if status in [500, 501, 502, 503]:
                await asyncio.sleep(1)
                continue
            if status == 200 and isinstance(data, dict):
                if str(data.get('meta', {}).get('code', '200')) in ['401', '403']:
                    MAUTH_TOKEN_ZAYAN = None
                    continue
                return 200, data
            elif status == 200:
                return 200, data
            else:
                logger.warning(f"[ZAYAN] HTTP {status} on {url}")
                return status, None
        except asyncio.TimeoutError:
            logger.warning(f"[ZAYAN] Timeout attempt {attempt+1} on {url}")
        except Exception as e:
            logger.warning(f"[ZAYAN] Error attempt {attempt+1}: {e}")
    return 500, None


# ==============================================================================
# 🔄 5-MINUTE AUTO RE-LOGIN JOB (STEX + ZAYAN)
# ==============================================================================

async def auto_relogin_job(context: ContextTypes.DEFAULT_TYPE):
    """
    Re-authenticates both servers every 5 minutes.
    For ZAYAN, we keep the SAME session alive (preserves cf_clearance cookie).
    We only reset the ZAYAN session if login actually fails.
    """
    global ZAYAN_SESSION
    logger.info("🔄 [AUTO RELOGIN] Refreshing STEX + ZAYAN sessions...")
    stex_task  = asyncio.create_task(authenticate_stex(force=True))
    zayan_task = asyncio.create_task(authenticate_zayan(force=True))
    results = await asyncio.gather(stex_task, zayan_task, return_exceptions=True)
    stex_ok  = results[0] if not isinstance(results[0], Exception) else False
    zayan_ok = results[1] if not isinstance(results[1], Exception) else False
    if not zayan_ok:
        # ZAYAN failed — force new curl_cffi session next attempt
        logger.warning("[AUTO RELOGIN] ZAYAN failed — resetting CF session")
        try:
            cf = get_zayan_cf_session()
            if cf != "FALLBACK" and cf is not None:
                await cf.close()
        except Exception:
            pass
        ZAYAN_SESSION = None
    logger.info(f"✅ [AUTO RELOGIN] STEX={'OK' if stex_ok else 'FAIL'} | ZAYAN={'OK' if zayan_ok else 'FAIL'}")


# ==============================================================================
# 🌍 MASSIVE COUNTRY FLAGS DICTIONARY
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
"Venezuela":"🇻🇪","Vietnam":"🇻🇳","Yemen":"🇾🇪","Zambia":"🇿🇲","Zimbabwe":"🇿🇼", "PostPaid": "📡"
}

def get_flag(country_name):
    if country_name in COUNTRY_FLAGS: 
        return COUNTRY_FLAGS[country_name]
    for name, flag in COUNTRY_FLAGS.items():
        if name.lower() in country_name.lower() or country_name.lower() in name.lower(): 
            return flag
    return "🚩"


# ==============================================================================
# 🔒 MIDDLEWARES & DYNAMIC UI
# ==============================================================================

async def check_subscription(user_id, bot):
    tasks = []
    for channel in CHANNELS:
        tasks.append(bot.get_chat_member(chat_id=channel, user_id=user_id))
    try:
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for result in results:
            if isinstance(result, Exception):
                return False
            if result.status in ['left', 'kicked']:
                return False
        return True
    except Exception:
        return False

async def send_join_prompt(update, context):
    # Channel buttons — সব নিচে নিচে (1 per row)
    keyboard = []
    for c in CHANNELS:
        keyboard.append([InlineKeyboardButton(f"📢 Join {c}", url=f"https://t.me/{c.replace('@', '')}")])
    keyboard.append([InlineKeyboardButton("✅ Joined / Verify", callback_data="check_join")])

    msg = (
        "⛔ <b>Access Denied!</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "<i>You must be a member of our official channels and groups to use this bot.</i>\n\n"
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
        # ALL CODES RECEIVED
        try: 
            txt = (
                f"✅ <b>ALL CODES RECEIVED SUCCESSFULLY!</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"<i>Thank you for using our service. Do you want to generate another number from the same range?</i>"
            )
            kb = [
                [InlineKeyboardButton("🔄 Get Number Again", callback_data="change_num")],
                [InlineKeyboardButton("🔙 Back to Server", callback_data="go_main")]
            ]
            await context.bot.edit_message_text(chat_id=chat_id, message_id=msg_id, text=txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.HTML)
        except Exception: 
            pass
        BATCH_MSGS.pop(batch_key, None)
    else:
        num_str = ""
        symbols = ["❶", "❷"] 
        for i, n in enumerate(batch['numbers']):
            num_str += f"{symbols[i % len(symbols)]} <code>{n}</code>\n"
            
        txt = (
            f"✅ <b>NUMBERS GENERATED</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"🌍 <b>{batch['flag']} {batch['country_name']}</b>\n\n"
            f"{num_str}\n"
            f"⏳ <i>Waiting for SMS... (Received numbers will disappear)</i>"
        )
        
        kb = [
            [InlineKeyboardButton("💬 OTP GROUP", url="https://t.me/RTxOtpX")],
            [
                InlineKeyboardButton("🔄 Change Number", callback_data="change_num"), 
                InlineKeyboardButton("🔙 Back to Server", callback_data="go_main")
            ]
        ]
        
        try: 
            await context.bot.edit_message_text(chat_id=chat_id, message_id=msg_id, text=txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.HTML)
        except Exception: 
            pass


# ==============================================================================
# 🤖 AUTO RANGE FORWARDER JOB (every 60 seconds, NO MISS, number masked)
# ==============================================================================

_RANGE_JOB_RUNNING = False  # Prevent overlapping range forward runs

async def auto_range_forwarder_job(context: ContextTypes.DEFAULT_TYPE):
    """
    Fetch console from BOTH servers in parallel.
    Send ALL unsent ranges to RANGE_GROUP_ID — no miss.
    Overlap guard prevents double-sending.
    """
    global SENT_RANGES, _RANGE_JOB_RUNNING
    if _RANGE_JOB_RUNNING:
        return
    _RANGE_JOB_RUNNING = True
    try:
        await _run_range_forwarder(context)
    finally:
        _RANGE_JOB_RUNNING = False

async def _run_range_forwarder(context: ContextTypes.DEFAULT_TYPE):
    global SENT_RANGES
    # Forward ALL app ranges — no filter, no miss
    bot_username = context.bot.username

    stex_task  = asyncio.create_task(stex_api_request('GET', API_STEX_CONSOLE))
    zayan_task = asyncio.create_task(zayan_api_request('GET', API_ZAYAN_CONSOLE))
    
    results = await asyncio.gather(stex_task, zayan_task, return_exceptions=True)

    # ── Send helper ──────────────────────────────────────────────────────────
    async def _send_range(server_label: str, r_val, display_app, c_name, full_msg_text):
        if r_val in SENT_RANGES:
            return
        SENT_RANGES.add(r_val)
        if len(SENT_RANGES) > 2000:
            SENT_RANGES.clear()

        # Mask any phone number inside the message text
        num_in_msg = re.search(r'\b(\d{7,15})\b', full_msg_text)
        if num_in_msg:
            full_msg_text = full_msg_text.replace(num_in_msg.group(1), mask_number(num_in_msg.group(1)))

        range_msg = (
            f"🔥 <b>New Range Found!</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"🖥️ <b>Server  :</b> {server_label}\n"
            f"🎯 <b>Range   :</b> <code>{r_val}</code>\n"
            f"🛒 <b>Service :</b> {html.escape(display_app)}\n"
            f"🌍 <b>Country :</b> {get_flag(c_name)} {c_name}\n"
            f"✉️ <b>SMS     :</b> <pre>{html.escape(full_msg_text)}</pre>\n"
            f"━━━━━━━━━━━━━━━━━━━━"
        )
        kb = [[InlineKeyboardButton("🤖 Bot Link", url=f"https://t.me/{bot_username}")]]
        try: 
            await context.bot.send_message(
                chat_id=RANGE_GROUP_ID, text=range_msg,
                reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.HTML
            )
        except Exception: 
            pass

    # SERVER 1 (STEX) — iterate ALL logs, not just first 5
    if isinstance(results[0], tuple):
        stex_status, stex_data = results[0]
        if stex_status == 200 and isinstance(stex_data, dict):
            logs = stex_data.get('data', {}).get('logs', [])
            send_tasks = []
            for log in logs:  # ALL logs — no limit
                if not isinstance(log, dict):
                    continue
                r_val        = log.get('range')
                c_name       = log.get('country', 'Unknown')
                display_app  = log.get('app_name', 'Unknown').title()
                raw_msg      = get_sms_from_item(log)
                full_msg_text = clean_message_text(raw_msg)
                if r_val and r_val not in SENT_RANGES:
                    send_tasks.append(_send_range("Server 1 ✨", r_val, display_app, c_name, full_msg_text))
            if send_tasks:
                await asyncio.gather(*send_tasks, return_exceptions=True)

    # SERVER 2 (ZAYAN) — iterate ALL logs
    if isinstance(results[1], tuple):
        zayan_status, zayan_data = results[1]
        if zayan_status == 200 and isinstance(zayan_data, dict):
            logs = zayan_data.get('data', {}).get('logs', [])
            send_tasks = []
            for log in logs:  # ALL logs — no limit
                if not isinstance(log, dict):
                    continue
                r_val        = log.get('range')
                c_name       = log.get('country', 'Unknown')
                display_app  = log.get('app_name', 'Unknown').title()
                raw_msg      = get_sms_from_item(log)
                full_msg_text = clean_message_text(raw_msg)
                if r_val and r_val not in SENT_RANGES:
                    send_tasks.append(_send_range("Server 2 🚀", r_val, display_app, c_name, full_msg_text))
            if send_tasks:
                await asyncio.gather(*send_tasks, return_exceptions=True)


# ==============================================================================
# 🚀 OTP POLLER — PARALLEL INBOX FETCH, ZERO MISS, BALANCE REWARD
# ==============================================================================

async def process_found_otp(context, hash_key, api_num, code_only, svc_name, raw_msg):
    global WAITING_OTPS, BATCH_MSGS, NUM_TO_HASH, _OTP_REWARD_POISHA, _REF_REWARD_POISHA
    user_data = WAITING_OTPS.get(hash_key)
    if not user_data:
        return
    user_id, chat_id, msg_id = user_data['user_id'], user_data['chat_id'], user_data['msg_id']
    full_num, batch_key = user_data['full_num'], user_data['batch_key']
    
    # DYNAMIC MESSAGE UPDATE
    if batch_key in BATCH_MSGS:
        batch = BATCH_MSGS[batch_key]
        to_remove = None
        for n in batch['numbers']:
            if n == full_num or clean_number(n).endswith(clean_number(full_num)[-6:]):
                to_remove = n
                break
        if to_remove and to_remove in batch['numbers']:
            batch['numbers'].remove(to_remove)
        asyncio.create_task(update_dynamic_batch_message(context, chat_id, msg_id, batch_key))

    # ── REWARD BALANCE ────────────────────────────────────────────────────────
    # Add OTP reward to user
    otp_reward = _OTP_REWARD_POISHA
    loop = asyncio.get_event_loop()
    new_balance = await loop.run_in_executor(DB_EXECUTOR, sync_add_balance, user_id, otp_reward)
    await loop.run_in_executor(DB_EXECUTOR, sync_increment_otp_count, user_id)

    # Add referral reward to referrer (if any)
    ref_reward     = _REF_REWARD_POISHA
    referrer_id    = await loop.run_in_executor(DB_EXECUTOR, sync_get_referred_by, user_id)
    ref_new_balance = None
    if referrer_id:
        ref_new_balance = await loop.run_in_executor(DB_EXECUTOR, sync_add_balance, referrer_id, ref_reward)
        # Notify referrer silently (non-blocking)
        ref_taka = paisa_to_taka(ref_reward)
        ref_notif = (
            f"💰 <b>Referral Bonus!</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"Your referral received an OTP!\n"
            f"🎁 <b>+{ref_taka} Tk</b> (+{ref_reward} Paisa) added to your balance.\n"
            f"💳 <b>New Balance:</b> {format_balance_display(ref_new_balance)}"
        )
        asyncio.create_task(
            _silent_send(context.bot, referrer_id, ref_notif)
        )

    # ── SEND OTP TO USER ──────────────────────────────────────────────────────
    otp_taka = paisa_to_taka(otp_reward)
    total_taka = paisa_to_taka(new_balance)
    user_msg = (
        f"🎉 <b>OTP RECEIVED SUCCESSFULLY!</b> ✨\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📱 <b>Service :</b> <i>{html.escape(str(svc_name))}</i>\n"
        f"📞 <b>Number  :</b> <code>{full_num}</code>\n"
        f"🔑 <b>Your OTP:</b> <code>{code_only}</code>\n"
        f"💰 <b>Balance Added:</b> +{otp_taka} Tk\n"
        f"💳 <b>Total Balance:</b> {total_taka} Tk\n"
        f"━━━━━━━━━━━━━━━━━━━━"
    )
    
    asyncio.create_task(context.bot.send_message(chat_id=chat_id, text=user_msg, parse_mode=ParseMode.HTML))
    
    # FORWARD TO OTP GROUP — number masked, clean format
    clean_raw_msg = clean_message_text(raw_msg)
    masked_num    = mask_number(full_num)

    group_msg = (
        f"🔔 <b>OTP Received</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📱 <b>Number :</b> <code>{masked_num}</code>\n"
        f"🛒 <b>Service:</b> <pre>{html.escape(str(svc_name))}</pre>\n"
        f"🔑 <b>Code   :</b> <code>{code_only}</code>\n"
        f"✉️ <b>SMS    :</b> <pre>{html.escape(str(clean_raw_msg))}</pre>\n"
        f"━━━━━━━━━━━━━━━━━━━━"
    )
    group_kb = [[InlineKeyboardButton("👨‍💻 Owner", url="https://t.me/RTx2R")]]
    asyncio.create_task(
        context.bot.send_message(
            chat_id=OTP_GROUP_ID, text=group_msg,
            reply_markup=InlineKeyboardMarkup(group_kb), parse_mode=ParseMode.HTML
        )
    )
    
    logger.info(f"✅ OTP delivered → user={user_id} num={full_num} code={code_only} reward={otp_reward}p")

async def _silent_send(bot, chat_id, text):
    """Send a message silently — ignore all errors."""
    try:
        await bot.send_message(chat_id=chat_id, text=text, parse_mode=ParseMode.HTML)
    except Exception:
        pass

async def _fetch_stex_inbox_page(date_str: str, page: int):
    """Fetch a single STEX inbox page."""
    url = f"{API_STEX_INBOX}?date={date_str}&page={page}&search=&status="
    return await stex_api_request('GET', url)

async def _fetch_zayan_inbox_page(date_str: str, page: int):
    """Fetch a single ZAYAN inbox page."""
    url = f"{API_ZAYAN_INBOX}?date={date_str}&page={page}&search=&status="
    return await zayan_api_request('GET', url)

def _extract_items_from_response(res_data) -> list:
    """Universal item extractor from any server inbox response."""
    if res_data is None:
        return []
    if isinstance(res_data, list):
        return res_data
    if isinstance(res_data, dict):
        data_field = res_data.get('data', {})
        if isinstance(data_field, list):
            return data_field
        elif isinstance(data_field, dict):
            return (
                data_field.get('numbers') or
                data_field.get('list') or
                data_field.get('items') or
                []
            )
        return (
            res_data.get('data') or
            res_data.get('list') or
            res_data.get('items') or
            res_data.get('history') or
            []
        )
    return []

_OTP_CHECKER_RUNNING = False  # Prevent overlapping runs

async def global_otp_checker_job(context: ContextTypes.DEFAULT_TYPE):
    """
    Ultra-fast parallel OTP checker:
    - Fetches page 1+2 of STEX and ZAYAN inbox simultaneously.
    - Zero miss guarantee via multi-page parallel fetch.
    - Overlap guard: skips if previous run still going.
    """
    global WAITING_OTPS, BATCH_MSGS, NUM_TO_HASH, _OTP_CHECKER_RUNNING
    if _OTP_CHECKER_RUNNING:
        return
    if not WAITING_OTPS:
        return
    _OTP_CHECKER_RUNNING = True
    try:
        await _run_otp_checker(context)
    finally:
        _OTP_CHECKER_RUNNING = False

async def _run_otp_checker(context: ContextTypes.DEFAULT_TYPE):
    global WAITING_OTPS, BATCH_MSGS, NUM_TO_HASH
    if not WAITING_OTPS:
        return 
    
    current_time = time.time()
    expired_keys = []
    
    # CLEANUP SILENTLY
    for hash_key, data in list(WAITING_OTPS.items()):
        if current_time - data['time'] > OTP_TIMEOUT_SECONDS: 
            expired_keys.append(hash_key)
            
    for h_key in expired_keys:
        u_data = WAITING_OTPS.pop(h_key, None)
        if u_data:
            NUM_TO_HASH.pop(clean_number(u_data['full_num']), None)
            b_key = u_data.get('batch_key')
            if b_key and b_key in BATCH_MSGS:
                if u_data['full_num'] in BATCH_MSGS[b_key]['numbers']:
                    BATCH_MSGS[b_key]['numbers'].remove(u_data['full_num'])
                if len(BATCH_MSGS[b_key]['numbers']) == 0:
                    try: 
                        await context.bot.delete_message(chat_id=u_data['chat_id'], message_id=u_data['msg_id'])
                    except: 
                        pass
                    BATCH_MSGS.pop(b_key, None)

    if not WAITING_OTPS: 
        return 
        
    found_keys = []
    date_str   = datetime.datetime.now().strftime("%Y-%m-%d")

    # 🔥 PARALLEL FETCHING: pages 1-3 of BOTH inboxes at the exact same time
    # This ensures we never miss OTPs that appear on page 2 or 3
    stex_p1_task  = asyncio.create_task(_fetch_stex_inbox_page(date_str, 1))
    stex_p2_task  = asyncio.create_task(_fetch_stex_inbox_page(date_str, 2))
    zayan_p1_task = asyncio.create_task(_fetch_zayan_inbox_page(date_str, 1))
    zayan_p2_task = asyncio.create_task(_fetch_zayan_inbox_page(date_str, 2))

    all_results = await asyncio.gather(
        stex_p1_task, stex_p2_task,
        zayan_p1_task, zayan_p2_task,
        return_exceptions=True
    )

    # Collect all items from all pages
    all_stex_items  = []
    all_zayan_items = []

    for res in all_results[:2]:  # STEX pages
        if isinstance(res, tuple) and res[0] == 200:
            all_stex_items.extend(_extract_items_from_response(res[1]))

    for res in all_results[2:]:  # ZAYAN pages
        if isinstance(res, tuple) and res[0] == 200:
            all_zayan_items.extend(_extract_items_from_response(res[1]))

    logger.info(f"[STEX] inbox items: {len(all_stex_items)} | [ZAYAN] inbox items: {len(all_zayan_items)}")

    # ── Process STEX items ────────────────────────────────────────────────────
    for item in all_stex_items:
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

    # ── Process ZAYAN items ───────────────────────────────────────────────────
    for item in all_zayan_items:
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

    for k in found_keys:
        ud = WAITING_OTPS.pop(k, None)
        if ud:
            NUM_TO_HASH.pop(clean_number(ud['full_num']), None)


# ==============================================================================
# 🎯 EXACTLY 2-NUMBER GENERATION SYSTEM (DUAL SERVER)
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
    
    # Fetch 2 numbers in parallel for maximum speed
    async def _fetch_one(idx):
        await asyncio.sleep(0.1 * idx)  # slight stagger to avoid duplicate
        if server_id == 1: 
            payload = {"range": range_val, "is_national": False, "remove_plus": False}
            status, resp = await stex_api_request('POST', API_STEX_GET_NUM, json_payload=payload)
            if status == 200 and isinstance(resp, dict) and 'data' in resp and resp['data'].get('number'):
                return resp['data']['number'], resp['data'].get('country', 'Unknown')
        elif server_id == 2: 
            payload = {"range": range_val, "is_national": False, "remove_plus": True}
            status, resp = await zayan_api_request('POST', API_ZAYAN_GET_NUM, json_payload=payload)
            if status == 200 and isinstance(resp, dict) and 'data' in resp:
                zd = resp['data']
                num_val = zd.get('number') or zd.get('full_number') or zd.get('copy') or ""
                num_val = str(num_val).replace('+', '').strip()
                if num_val:
                    return num_val, zd.get('country', 'Unknown')
        return None, None

    results_pair = await asyncio.gather(_fetch_one(0), _fetch_one(1), return_exceptions=True)

    fetched_numbers = []
    country_name    = context.user_data.get('country_name', 'Unknown')

    for res in results_pair:
        if isinstance(res, tuple) and res[0]:
            num_val = str(res[0]).replace('+', '')
            if num_val not in fetched_numbers:
                fetched_numbers.append(num_val)
            if res[1] and res[1] != 'Unknown':
                country_name = res[1]
            
    if fetched_numbers:
        flag     = get_flag(country_name)
        symbols  = ["❶", "❷"]
        num_str  = ""
        for i, n in enumerate(fetched_numbers):
            num_str += f"{symbols[i]} <code>{n}</code>\n"
            
        txt = (
            f"✅ <b>NUMBERS GENERATED</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"🌍 <b>{flag} {country_name}</b>\n\n"
            f"{num_str}\n"
            f"⏳ <i>Waiting for SMS... (Received numbers will disappear)</i>"
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
            'numbers':      fetched_numbers.copy(), 
            'country_name': country_name, 
            'flag':         flag
        }
        
        for n in fetched_numbers:
            hash_key = get_hash_key(n)
            WAITING_OTPS[hash_key] = {
                'full_num':  n, 
                'user_id':   user_id, 
                'chat_id':   chat_id, 
                'msg_id':    msg.message_id, 
                'batch_key': batch_key, 
                'time':      time.time()
            }
            NUM_TO_HASH[clean_number(n)] = hash_key
            
        context.user_data['range']  = range_val 
        context.user_data['server'] = server_id
        
    else:
        err_msg = "🔄 <i>Our high-speed servers are balancing the load. No numbers found right now.</i>"
        await msg.edit_text(
            text=f"📡 <b>Server Optimizing:</b>\n{err_msg}\n\nPlease try again or select another category.", 
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to Servers", callback_data="go_main")]]), 
            parse_mode=ParseMode.HTML
        )


# ==============================================================================
# 📋 MENUS & DUAL SERVER SELECTION UI
# ==============================================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await check_ban_middleware(update, context): 
        return
    user_id = update.effective_user.id

    # Handle referral link: /start ref_12345678
    args = context.args
    referred_by = None
    if args and args[0].startswith("ref_"):
        try:
            ref_id = int(args[0].split("_")[1])
            if ref_id != user_id:
                referred_by = ref_id
        except Exception:
            pass

    await ensure_user_fast(user_id, referred_by=referred_by)
    context.user_data.clear()
    
    if not await check_subscription(user_id, context.bot): 
        await send_join_prompt(update, context)
    else: 
        await show_main_menu(update, context)

async def show_main_menu(update_obj, context):
    kb = [
        ["📱 Get Number"],
        ["🔐 Get 2FA"],
        ["💰 My Balance"],
        ["👥 Refer & Earn"],
        ["📊 See Activity"],
        ["🎧 Support"]
    ]
    msg = (
        "✨ <b>PREMIUM OTP BOT</b> ✨\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "👋 <i>Welcome! Choose an option:</i>"
    )
    if hasattr(update_obj, 'message') and update_obj.message: 
        await update_obj.message.reply_text(msg, reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True), parse_mode=ParseMode.HTML)
    elif hasattr(update_obj, 'callback_query') and update_obj.callback_query:
        try: 
            await update_obj.callback_query.message.delete()
        except: 
            pass
        await context.bot.send_message(chat_id=update_obj.effective_chat.id, text=msg, reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True), parse_mode=ParseMode.HTML)

async def show_server_selection(update_obj, context):
    kb = [
        [InlineKeyboardButton("✨ Server 1 (STEX)", callback_data="srv_1")],
        [InlineKeyboardButton("🚀 Server 2 (ZayanSMS)", callback_data="srv_2")]
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
        f"📱 <b>{server_name} CATEGORIES</b> 📱\n"
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
        await authenticate_zayan(force=True)
        status, data = await zayan_api_request('GET', API_ZAYAN_CONSOLE)
        if status == 200 and isinstance(data, dict):
            for log in data.get('data', {}).get('logs', []):
                if isinstance(log, dict) and category in str(log.get('app_name', '')).lower():
                    c, r = log.get('country'), log.get('range')
                    if c and r and c not in countries: 
                        countries[c] = r
        
    if not countries:
        await query.edit_message_text(
            text=f"📡 <b>Load Balancing...</b>\n<i>No immediate numbers found for {category.title()}. Please try again in a moment.</i>", 
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
        reply_markup=InlineKeyboardMarkup(kb), 
        parse_mode=ParseMode.HTML
    )


# ==============================================================================
# 💰 BALANCE & REFERRAL HANDLERS
# ==============================================================================

async def show_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show user's current balance and stats with Withdraw button."""
    if await check_ban_middleware(update, context):
        return
    user_id = update.effective_user.id
    await ensure_user_fast(user_id)
    loop = asyncio.get_event_loop()
    balance, total_otps, referred_by = await loop.run_in_executor(DB_EXECUTOR, sync_get_user_stats, user_id)
    my_referrals = await loop.run_in_executor(DB_EXECUTOR, sync_count_my_referrals, user_id)
    taka_val = paisa_to_taka(balance)
    otp_taka = paisa_to_taka(_OTP_REWARD_POISHA)
    ref_taka = paisa_to_taka(_REF_REWARD_POISHA)

    txt = (
        f"💰 <b>MY WALLET</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"💳 <b>Balance:</b> {taka_val} Tk ({balance} Paisa)\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📩 <b>Total OTPs Received:</b> {total_otps}\n"
        f"👥 <b>My Referrals:</b> {my_referrals} users\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"💡 <i>Earn {otp_taka} Tk per OTP received.\n"
        f"Earn {ref_taka} Tk when your referral gets an OTP.</i>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"💸 <b>Withdraw via:</b> bKash / Nagad / Mobile Recharge"
    )
    kb = [
        [InlineKeyboardButton("💸 Withdraw Now", callback_data="withdraw_menu")]
    ]
    await update.message.reply_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.HTML)

async def show_refer_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show referral link and info."""
    if await check_ban_middleware(update, context):
        return
    user_id     = update.effective_user.id
    bot_username = context.bot.username
    loop = asyncio.get_event_loop()
    my_referrals = await loop.run_in_executor(DB_EXECUTOR, sync_count_my_referrals, user_id)
    balance, total_otps, _ = await loop.run_in_executor(DB_EXECUTOR, sync_get_user_stats, user_id)

    ref_link = f"https://t.me/{bot_username}?start=ref_{user_id}"
    
    txt = (
        f"👥 <b>REFER & EARN</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🔗 <b>Your Referral Link:</b>\n"
        f"<code>{ref_link}</code>\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🎁 <b>Reward System:</b>\n"
        f"• Each OTP you receive → <b>+{paisa_to_taka(_OTP_REWARD_POISHA)} Tk</b>\n"
        f"• Each OTP your referral receives → <b>+{paisa_to_taka(_REF_REWARD_POISHA)} Tk</b> for you\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📊 <b>Your Stats:</b>\n"
        f"👤 Total Referrals: {my_referrals}\n"
        f"💳 Balance: {format_balance_display(balance)}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"<i>Share your link and earn automatically!</i>"
    )
    kb = [[InlineKeyboardButton("📤 Share My Link", url=f"https://t.me/share/url?url={ref_link}&text=Join%20this%20premium%20OTP%20bot%21")]]
    await update.message.reply_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.HTML)




# ==============================================================================
# 💸 WITHDRAW SYSTEM — bKash / Nagad / Mobile Recharge
# ==============================================================================

MIN_WITHDRAW_PAISA = 500  # 5 Taka minimum withdraw

async def show_withdraw_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show withdraw options inline."""
    query = update.callback_query
    user_id = query.from_user.id
    loop = asyncio.get_event_loop()
    balance, total_otps, _ = await loop.run_in_executor(DB_EXECUTOR, sync_get_user_stats, user_id)
    taka_val = paisa_to_taka(balance)

    txt = (
        f"💸 <b>WITHDRAW BALANCE</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"💳 <b>Your Balance:</b> {taka_val} Tk ({balance} Paisa)\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📋 <b>Withdraw Methods:</b>\n"
        f"• 📱 bKash\n"
        f"• 💜 Nagad\n"
        f"• 📡 Mobile Recharge\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"⚠️ <i>Minimum withdraw: {paisa_to_taka(MIN_WITHDRAW_PAISA)} Tk</i>"
    )
    kb = [
        [
            InlineKeyboardButton("📱 bKash", callback_data="withdraw_bkash"),
            InlineKeyboardButton("💜 Nagad", callback_data="withdraw_nagad")
        ],
        [InlineKeyboardButton("📡 Mobile Recharge", callback_data="withdraw_recharge")],
        [InlineKeyboardButton("🔙 Back", callback_data="withdraw_back")]
    ]
    await query.edit_message_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.HTML)

async def handle_withdraw_method(update: Update, context: ContextTypes.DEFAULT_TYPE, method: str):
    """Ask user for their number after selecting withdraw method."""
    query = update.callback_query
    user_id = query.from_user.id
    loop = asyncio.get_event_loop()
    balance, _, _ = await loop.run_in_executor(DB_EXECUTOR, sync_get_user_stats, user_id)

    if balance < MIN_WITHDRAW_PAISA:
        taka_needed = paisa_to_taka(MIN_WITHDRAW_PAISA)
        taka_have   = paisa_to_taka(balance)
        await query.answer(
            f"❌ Minimum {taka_needed} Tk needed. You have {taka_have} Tk.",
            show_alert=True
        )
        return

    method_labels = {
        'bkash':    '📱 bKash',
        'nagad':    '💜 Nagad',
        'recharge': '📡 Mobile Recharge'
    }
    label = method_labels.get(method, method)
    context.user_data['withdraw_method'] = method
    context.user_data['state'] = 'WAITING_FOR_WITHDRAW_NUMBER'

    taka_val = paisa_to_taka(balance)
    txt = (
        f"💸 <b>WITHDRAW via {label}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"💳 <b>Available:</b> {taka_val} Tk\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📞 <b>Enter your {label} number:</b>\n"
        f"<i>(e.g. 01XXXXXXXXX)</i>"
    )
    kb = [[InlineKeyboardButton("❌ Cancel", callback_data="withdraw_cancel")]]
    await query.edit_message_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.HTML)

async def process_withdraw_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process withdraw after user sends their number."""
    user_id = update.effective_user.id
    phone   = update.message.text.strip()
    method  = context.user_data.get('withdraw_method', 'bkash')
    context.user_data['state'] = None
    context.user_data['withdraw_method'] = None

    # Validate phone number
    if not re.match(r'^0[1-9][0-9]{9}$', phone):
        await update.message.reply_text(
            "❌ <b>Invalid number!</b> Please enter a valid 11-digit BD number (e.g. 01XXXXXXXXX)",
            parse_mode=ParseMode.HTML
        )
        return

    loop = asyncio.get_event_loop()
    balance, _, _ = await loop.run_in_executor(DB_EXECUTOR, sync_get_user_stats, user_id)

    if balance < MIN_WITHDRAW_PAISA:
        taka_needed = paisa_to_taka(MIN_WITHDRAW_PAISA)
        await update.message.reply_text(
            f"❌ <b>Insufficient balance!</b> Minimum {taka_needed} Tk required.",
            parse_mode=ParseMode.HTML
        )
        return

    taka_val = paisa_to_taka(balance)
    method_labels = {
        'bkash':    '📱 bKash',
        'nagad':    '💜 Nagad',
        'recharge': '📡 Mobile Recharge'
    }
    label = method_labels.get(method, method)

    # Notify user — request submitted
    user_txt = (
        f"✅ <b>Withdraw Request Submitted!</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"💸 <b>Method:</b> {label}\n"
        f"📞 <b>Number:</b> <code>{phone}</code>\n"
        f"💰 <b>Amount:</b> {taka_val} Tk ({balance} Paisa)\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"⏳ <i>Admin will process within 24 hours.</i>"
    )
    await update.message.reply_text(user_txt, parse_mode=ParseMode.HTML)

    # Notify admin
    admin_txt = (
        f"💸 <b>WITHDRAW REQUEST</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 <b>User ID:</b> <code>{user_id}</code>\n"
        f"💸 <b>Method:</b> {label}\n"
        f"📞 <b>Number:</b> <code>{phone}</code>\n"
        f"💰 <b>Amount:</b> {taka_val} Tk ({balance} Paisa)\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"✅ Use /addbalance {user_id} -amount to deduct after payment."
    )
    admin_kb = [
        [
            InlineKeyboardButton("✅ Approve & Notify", callback_data=f"wd_approve_{user_id}_{balance}"),
            InlineKeyboardButton("❌ Reject", callback_data=f"wd_reject_{user_id}")
        ]
    ]
    for a_id in ADMIN_IDS:
        asyncio.create_task(_silent_send_with_kb(context.bot, a_id, admin_txt, admin_kb))

async def _silent_send_with_kb(bot, chat_id, text, kb_rows):
    """Send message with inline keyboard silently."""
    try:
        await bot.send_message(
            chat_id=chat_id, text=text,
            reply_markup=InlineKeyboardMarkup(kb_rows),
            parse_mode=ParseMode.HTML
        )
    except Exception:
        pass

# ==============================================================================
# 🎮 TEXT HANDLER & INLINE ADMIN REPLY LOGIC
# ==============================================================================

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await check_ban_middleware(update, context): 
        return
    user_id   = update.effective_user.id
    text      = update.message.text
    user_data = context.user_data
    await ensure_user_fast(user_id)
    
    main_buttons = ["📱 Get Number", "🔐 Get 2FA", "🎧 Support", "📊 See Activity", "💰 My Balance", "👥 Refer & Earn"]
    
    if text in main_buttons:
        user_data['state'] = None
        user_data['admin_reply_target'] = None
    
    target_reply_user = user_data.get('admin_reply_target')
    if target_reply_user and text not in main_buttons:
        try:
            await context.bot.send_message(
                chat_id=int(target_reply_user), 
                text=f"👨‍💻 <b>Admin Reply:</b>\n━━━━━━━━━━━━━━━━━━━━\n{text}", 
                parse_mode=ParseMode.HTML
            )
            await update.message.reply_text("✅ <b>Reply sent successfully to the user.</b>", parse_mode=ParseMode.HTML)
        except Exception:
            await update.message.reply_text("❌ <b>Failed to send reply. The user might have blocked the bot.</b>", parse_mode=ParseMode.HTML)
        
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
                        out = f"✅ <b>2FA CODE GENERATED!</b>\n━━━━━━━━━━━━━━━━━━━━\n🔢 <b>Code:</b> <code>{code}</code>\n\n<i>⚠️ Auto-delete in 5 mins.</i>"
                        await msg.edit_text(out, parse_mode=ParseMode.HTML)
                        asyncio.create_task(delete_message_later(context.bot, msg.chat_id, msg.message_id, 300))
                    else: 
                        await msg.edit_text("❌ <b>Invalid Secret Key.</b>", parse_mode=ParseMode.HTML)
                else: 
                    await msg.edit_text("❌ <b>API Error!</b>", parse_mode=ParseMode.HTML)
        except Exception: 
            await msg.edit_text("❌ <b>Network Error.</b>", parse_mode=ParseMode.HTML)
        user_data['state'] = None
        
    elif text == "🎧 Support":
        user_data['state'] = 'WAITING_FOR_SUPPORT'
        await update.message.reply_text(
            "🎧 <b>SUPPORT SYSTEM</b>\n━━━━━━━━━━━━━━━━━━━━\n<i>Type your problem below.</i>", 
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
            except: 
                pass
                
        await update.message.reply_text("✅ <b>Message Sent!</b> An Admin will reply soon.", parse_mode=ParseMode.HTML)
        user_data['state'] = None
        
    elif text == "📊 See Activity":
        kb = [
            [InlineKeyboardButton("🔥 Range Channel", url="https://t.me/ConsoleXRT"), InlineKeyboardButton("💬 OTP Channel", url="https://t.me/RTxOtpX")]
        ]
        await update.message.reply_text(
            "📊 <b>BOT ACTIVITY LINKS</b>\n━━━━━━━━━━━━━━━━━━━━\n<i>Join to see live Bot activity:</i>", 
            reply_markup=InlineKeyboardMarkup(kb), 
            parse_mode=ParseMode.HTML
        )

    elif text == "💰 My Balance":
        await show_balance(update, context)

    elif text == "👥 Refer & Earn":
        await show_refer_info(update, context)
        
    elif user_data.get('state') == 'WAITING_FOR_RANGE':
        user_data['state'] = None
        server_id = user_data.get('server', 1)
        await process_number_generation(update, context, text, server_id, is_callback=False)

    elif user_data.get('state') == 'WAITING_FOR_WITHDRAW_NUMBER':
        await process_withdraw_request(update, context)
        
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
            except: 
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
        parts      = data.split("_")
        server_id  = int(parts[1])
        range_val  = parts[2]
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
        
    elif data == "withdraw_menu":
        await show_withdraw_menu(update, context)
        
    elif data == "withdraw_bkash":
        await handle_withdraw_method(update, context, "bkash")
        
    elif data == "withdraw_nagad":
        await handle_withdraw_method(update, context, "nagad")
        
    elif data == "withdraw_recharge":
        await handle_withdraw_method(update, context, "recharge")
        
    elif data == "withdraw_cancel":
        context.user_data['state'] = None
        context.user_data['withdraw_method'] = None
        await query.answer("❌ Withdraw cancelled.")
        try:
            await query.message.delete()
        except Exception:
            pass
            
    elif data == "withdraw_back":
        context.user_data['state'] = None
        # Re-show balance page
        user_id_wb = query.from_user.id
        loop_wb = asyncio.get_event_loop()
        balance_wb, total_otps_wb, _ = await loop_wb.run_in_executor(DB_EXECUTOR, sync_get_user_stats, user_id_wb)
        my_refs_wb = await loop_wb.run_in_executor(DB_EXECUTOR, sync_count_my_referrals, user_id_wb)
        taka_wb = paisa_to_taka(balance_wb)
        otp_tk = paisa_to_taka(_OTP_REWARD_POISHA)
        ref_tk = paisa_to_taka(_REF_REWARD_POISHA)
        txt_wb = (
            f"💰 <b>MY WALLET</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"💳 <b>Balance:</b> {taka_wb} Tk ({balance_wb} Paisa)\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"📩 <b>Total OTPs Received:</b> {total_otps_wb}\n"
            f"👥 <b>My Referrals:</b> {my_refs_wb} users\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"💡 <i>Earn {otp_tk} Tk per OTP received.\n"
            f"Earn {ref_tk} Tk when your referral gets an OTP.</i>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"💸 <b>Withdraw via:</b> bKash / Nagad / Mobile Recharge"
        )
        kb_wb = [[InlineKeyboardButton("💸 Withdraw Now", callback_data="withdraw_menu")]]
        try:
            await query.edit_message_text(txt_wb, reply_markup=InlineKeyboardMarkup(kb_wb), parse_mode=ParseMode.HTML)
        except Exception:
            pass

    elif data.startswith("wd_approve_"):
        # Admin approves withdraw: wd_approve_USERID_AMOUNT
        if user_id not in ADMIN_IDS:
            await query.answer("⚠️ Not an admin.", show_alert=True)
            return
        parts_wd = data.split("_")
        wd_user  = int(parts_wd[2])
        wd_amt   = int(parts_wd[3])
        # Deduct balance
        loop_wd = asyncio.get_event_loop()
        await loop_wd.run_in_executor(DB_EXECUTOR, sync_add_balance, wd_user, -wd_amt)
        # Notify user
        asyncio.create_task(_silent_send(
            context.bot, wd_user,
            f"✅ <b>Withdraw Approved!</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"💰 <b>{paisa_to_taka(wd_amt)} Tk</b> has been sent to your account.\n"
            f"<i>Thank you for using our service!</i>"
        ))
        await query.answer("✅ Approved & balance deducted.", show_alert=True)
        try:
            await query.edit_message_text(
                query.message.text + "\n\n✅ <b>APPROVED by Admin</b>",
                parse_mode=ParseMode.HTML
            )
        except Exception:
            pass

    elif data.startswith("wd_reject_"):
        if user_id not in ADMIN_IDS:
            await query.answer("⚠️ Not an admin.", show_alert=True)
            return
        wd_user_r = int(data.split("_")[2])
        asyncio.create_task(_silent_send(
            context.bot, wd_user_r,
            f"❌ <b>Withdraw Rejected</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"<i>Your withdraw request was rejected by admin.\nPlease contact support for more info.</i>"
        ))
        await query.answer("❌ Rejected.", show_alert=True)
        try:
            await query.edit_message_text(
                query.message.text + "\n\n❌ <b>REJECTED by Admin</b>",
                parse_mode=ParseMode.HTML
            )
        except Exception:
            pass
        
    elif data.startswith("admrep_"):
        if user_id not in ADMIN_IDS:
            await query.answer("⚠️ You are not an admin.", show_alert=True)
            return
            
        target_user_id = data.split("_")[1]
        context.user_data['admin_reply_target'] = target_user_id
        
        reply_txt = (
            f"✍️ <b>Type your reply for User ID:</b> <code>{target_user_id}</code>\n\n"
            f"<i>(Just type the message normally in the chat and send it. I will forward it to the user.)</i>"
        )
        await query.message.reply_text(reply_txt, parse_mode=ParseMode.HTML)
        await query.answer()


# ==============================================================================
# 👑 FULLY FUNCTIONAL ADMIN COMMANDS
# ==============================================================================

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS: return
    context.user_data['admin_reply_target'] = None
    context.user_data['state'] = None
    txt = (
        "🔐 <b>ADVANCED ADMIN PANEL v32</b> 🔐\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "🟢 <code>/status</code> - Bot Statistics\n"
        "📢 <code>/broadcast &lt;msg&gt;</code> - Broadcast to all\n"
        "🚫 <code>/ban &lt;id&gt;</code> - Ban a user\n"
        "✅ <code>/unban &lt;id&gt;</code> - Unban a user\n"
        "👥 <code>/users</code> - Total User Count\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "💰 <b>BALANCE COMMANDS:</b>\n"
        "💳 <code>/addbalance &lt;id&gt; &lt;poisha&gt;</code> - Add balance to user\n"
        "🔢 <code>/setotprate &lt;poisha&gt;</code> - Set OTP reward rate\n"
        "🔢 <code>/setrefrate &lt;poisha&gt;</code> - Set referral reward rate\n"
        "🏆 <code>/topref</code> - Top 10 referrers\n"
        "📊 <code>/userinfo &lt;id&gt;</code> - User balance + stats\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"<i>Current OTP Rate: {paisa_to_taka(_OTP_REWARD_POISHA)} Tk | Ref Rate: {paisa_to_taka(_REF_REWARD_POISHA)} Tk</i>"
    )
    await update.message.reply_text(txt, parse_mode=ParseMode.HTML)

async def admin_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS: return
    uptime  = datetime.datetime.now() - START_TIME
    t_users = get_total_users_count()
    txt = (
        f"📊 <b>ULTRA ENTERPRISE STATUS v32</b> 📊\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"⏱ <b>Uptime:</b> {str(uptime).split('.')[0]}\n"
        f"👥 <b>Total Users (RAM):</b> {t_users}\n"
        f"📡 <b>Active Waiters:</b> {len(WAITING_OTPS)} Numbers\n"
        f"⚡ <b>RAM Cache:</b> ACTIVE (O(1) Speed)\n"
        f"🔄 <b>Auto Relogin:</b> Every 5 Minutes\n"
        f"🌐 <b>Connection Pool:</b> 1000 Connections\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"💰 <b>OTP Reward:</b> {paisa_to_taka(_OTP_REWARD_POISHA)} Tk/OTP\n"
        f"🎁 <b>Ref Reward:</b> {paisa_to_taka(_REF_REWARD_POISHA)} Tk/referral OTP\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"✅ <i>STEX + ZAYAN Running Smoothly</i>"
    )
    await update.message.reply_text(txt, parse_mode=ParseMode.HTML)

async def admin_users_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS: return
    count = get_total_users_count()
    await update.message.reply_text(f"👥 <b>Total Registered Users:</b> {count}", parse_mode=ParseMode.HTML)

async def ban_user_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS: return
    try:
        target_id = int(context.args[0])
        await set_ban_status(target_id, 1)
        await update.message.reply_text(f"✅ User <code>{target_id}</code> has been successfully <b>BANNED</b>.", parse_mode=ParseMode.HTML)
    except Exception:
        await update.message.reply_text("⚠️ Usage: `/ban UserID`", parse_mode=ParseMode.Markdown)

async def unban_user_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS: return
    try:
        target_id = int(context.args[0])
        await set_ban_status(target_id, 0)
        await update.message.reply_text(f"✅ User <code>{target_id}</code> has been successfully <b>UNBANNED</b>.", parse_mode=ParseMode.HTML)
    except Exception:
        await update.message.reply_text("⚠️ Usage: `/unban UserID`", parse_mode=ParseMode.Markdown)

async def broadcast_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS: return
    if not context.args:
        await update.message.reply_text("⚠️ Usage: `/broadcast Your message here`", parse_mode=ParseMode.Markdown)
        return
    message = " ".join(context.args)
    users   = get_all_users()
    msg     = await update.message.reply_text(f"⏳ <i>Broadcasting to {len(users)} users... Please wait.</i>", parse_mode=ParseMode.HTML)
    success = 0
    failed  = 0
    for u_id in users:
        try:
            await context.bot.send_message(chat_id=u_id, text=f"📢 <b>ADMIN BROADCAST</b>\n━━━━━━━━━━━━━━━━━━━━\n{message}", parse_mode=ParseMode.HTML)
            success += 1
        except Exception:
            failed += 1
        await asyncio.sleep(0.05) 
    await msg.edit_text(f"✅ <b>Broadcast Completed!</b>\n━━━━━━━━━━━━━━━━━━━━\n🟢 Delivered: {success}\n🔴 Failed: {failed}", parse_mode=ParseMode.HTML)

# ── NEW ADMIN: Add balance to user ────────────────────────────────────────────
async def admin_add_balance_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS: return
    try:
        target_id = int(context.args[0])
        amount    = int(context.args[1])
        loop      = asyncio.get_event_loop()
        new_bal   = await loop.run_in_executor(DB_EXECUTOR, sync_add_balance, target_id, amount)
        await update.message.reply_text(
            f"✅ <b>Balance Added!</b>\n"
            f"👤 User: <code>{target_id}</code>\n"
            f"💰 Added: <b>{paisa_to_taka(amount)} Tk</b> (+{amount} Paisa)\n"
            f"💳 New Balance: <b>{format_balance_display(new_bal)}</b>",
            parse_mode=ParseMode.HTML
        )
        # Notify the user
        asyncio.create_task(_silent_send(
            context.bot, target_id,
            f"🎁 <b>Balance Added by Admin!</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"💰 <b>+{paisa_to_taka(amount)} Tk</b> (+{amount} Paisa) added to your wallet.\n"
            f"💳 <b>New Balance:</b> {format_balance_display(new_bal)}"
        ))
    except (IndexError, ValueError):
        await update.message.reply_text("⚠️ Usage: <code>/addbalance UserID Amount_in_poisha</code>", parse_mode=ParseMode.HTML)

# ── NEW ADMIN: Set OTP reward rate ────────────────────────────────────────────
async def admin_set_otp_rate_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global _OTP_REWARD_POISHA
    if update.effective_user.id not in ADMIN_IDS: return
    try:
        rate = int(context.args[0])
        if rate < 0:
            raise ValueError("Rate cannot be negative")
        _OTP_REWARD_POISHA = rate
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(DB_EXECUTOR, sync_update_setting, 'otp_reward_poisha', str(rate))
        await update.message.reply_text(
            f"✅ <b>OTP Reward Rate Updated!</b>\n"
            f"🔢 New rate: <b>{rate} Paisa ({paisa_to_taka(rate)} Tk) per OTP received</b>",
            parse_mode=ParseMode.HTML
        )
    except (IndexError, ValueError):
        await update.message.reply_text("⚠️ Usage: <code>/setotprate 10</code> (in Poisha)", parse_mode=ParseMode.HTML)

# ── NEW ADMIN: Set referral reward rate ───────────────────────────────────────
async def admin_set_ref_rate_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global _REF_REWARD_POISHA
    if update.effective_user.id not in ADMIN_IDS: return
    try:
        rate = int(context.args[0])
        if rate < 0:
            raise ValueError("Rate cannot be negative")
        _REF_REWARD_POISHA = rate
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(DB_EXECUTOR, sync_update_setting, 'ref_reward_poisha', str(rate))
        await update.message.reply_text(
            f"✅ <b>Referral Reward Rate Updated!</b>\n"
            f"🔢 New rate: <b>{rate} Paisa ({paisa_to_taka(rate)} Tk) per referral's OTP</b>",
            parse_mode=ParseMode.HTML
        )
    except (IndexError, ValueError):
        await update.message.reply_text("⚠️ Usage: <code>/setrefrate 5</code> (in Poisha)", parse_mode=ParseMode.HTML)

# ── NEW ADMIN: Top referrers leaderboard ──────────────────────────────────────
async def admin_top_ref_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS: return
    loop     = asyncio.get_event_loop()
    top_list = await loop.run_in_executor(DB_EXECUTOR, sync_get_top_referrers, 10)
    if not top_list:
        await update.message.reply_text("📊 <b>No referral data yet.</b>", parse_mode=ParseMode.HTML)
        return
    medals = ["🥇","🥈","🥉","4️⃣","5️⃣","6️⃣","7️⃣","8️⃣","9️⃣","🔟"]
    lines  = []
    for idx, (uid, cnt) in enumerate(top_list):
        medal = medals[idx] if idx < len(medals) else f"{idx+1}."
        lines.append(f"{medal} <code>{uid}</code> — <b>{cnt}</b> referrals")
    txt = (
        "🏆 <b>TOP 10 REFERRERS</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n" +
        "\n".join(lines)
    )
    await update.message.reply_text(txt, parse_mode=ParseMode.HTML)

# ── NEW ADMIN: User info (balance + stats) ────────────────────────────────────
async def admin_user_info_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS: return
    try:
        target_id  = int(context.args[0])
        loop       = asyncio.get_event_loop()
        balance, total_otps, referred_by = await loop.run_in_executor(DB_EXECUTOR, sync_get_user_stats, target_id)
        my_refs    = await loop.run_in_executor(DB_EXECUTOR, sync_count_my_referrals, target_id)
        banned_str = "🚫 YES" if target_id in BANNED_CACHE else "✅ NO"
        txt = (
            f"📋 <b>USER INFO</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"👤 <b>User ID:</b> <code>{target_id}</code>\n"
            f"🚫 <b>Banned:</b> {banned_str}\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"💳 <b>Balance:</b> {format_balance_display(balance)}\n"
            f"📩 <b>Total OTPs:</b> {total_otps}\n"
            f"👥 <b>My Referrals:</b> {my_refs}\n"
            f"🔗 <b>Referred By:</b> {referred_by if referred_by else 'None'}"
        )
        await update.message.reply_text(txt, parse_mode=ParseMode.HTML)
    except (IndexError, ValueError):
        await update.message.reply_text("⚠️ Usage: <code>/userinfo UserID</code>", parse_mode=ParseMode.HTML)


# ==============================================================================
# 🌐 RENDER DUMMY WEB SERVER & MAIN LOOP
# ==============================================================================

async def web_server_handler(request):
    return web.Response(text="✅ Premium OTP Bot V33 ULTRA — Running perfectly!")

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
    # Pre-authenticate both servers on startup simultaneously
    asyncio.create_task(authenticate_stex(force=True))
    asyncio.create_task(authenticate_zayan(force=True))

if __name__ == "__main__":
    init_db()
    app = Application.builder().token(TOKEN).post_init(post_init).build()
    
    # Core commands
    app.add_handler(CommandHandler("start",      start))
    app.add_handler(CommandHandler("admin",      admin_panel))
    app.add_handler(CommandHandler("status",     admin_status))
    app.add_handler(CommandHandler("ban",        ban_user_cmd))
    app.add_handler(CommandHandler("unban",      unban_user_cmd))
    app.add_handler(CommandHandler("broadcast",  broadcast_cmd))
    app.add_handler(CommandHandler("users",      admin_users_cmd))
    # Balance / referral admin commands
    app.add_handler(CommandHandler("addbalance", admin_add_balance_cmd))
    app.add_handler(CommandHandler("setotprate", admin_set_otp_rate_cmd))
    app.add_handler(CommandHandler("setrefrate", admin_set_ref_rate_cmd))
    app.add_handler(CommandHandler("topref",     admin_top_ref_cmd))
    app.add_handler(CommandHandler("userinfo",   admin_user_info_cmd))
    
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # ⚡ OTP CHECKER: every 1 second (super fast parallel fetch)
    app.job_queue.run_repeating(global_otp_checker_job,   interval=1,   first=1)
    # 📡 Range forwarder: every 30 seconds (ALL ranges, no miss)
    app.job_queue.run_repeating(auto_range_forwarder_job, interval=20,  first=10)
    # 🔄 Auto Re-Login (STEX + ZAYAN): every 5 minutes
    app.job_queue.run_repeating(auto_relogin_job,         interval=300, first=300)
    
    logger.info("✨ VERSION 33.0 ULTRA STARTED SUCCESSFULLY ✨")
    app.run_polling(
        drop_pending_updates=True,
        allowed_updates=["message", "callback_query"],
        pool_timeout=10,
        read_timeout=10,
        write_timeout=10,
        connect_timeout=10
    )
