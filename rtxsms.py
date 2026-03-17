"""
==============================================================================
PROJECT: ✨ PREMIUM OTP BOT (Ultimate Update - Version 33.0 FINAL) ✨
CAPACITY: 20,000+ Users on Render Free Plan (RAM Caching & Text Diff Algorithm).
UPDATES: Single Server (STEX), Advanced Withdrawal System, Full Admin Keyboard.
FIXED: WhatsApp Hyphen Codes (123-456), 100% Range Catching, 250+ Country Flags.
FORMATTING: Fully Expanded, No Shortcuts, Maximum Stability & Beauty.
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
    filters, 
    ConversationHandler
)
from telegram.constants import ParseMode
from aiohttp import web

# ==============================================================================
# ⚙️ CONFIGURATION & CREDENTIALS
# ==============================================================================

TOKEN = "8784714590:AAGW1bthOSIh2HUl2vPCYS_zv13zEz7BOsg"
ADMIN_IDS = [6031032502] 
CHANNELS = ["@EarnXtract", "@RTx_Sms", "@ConsoleXRT", "@RTxOtpX"]

RANGE_GROUP_ID = -1003627708272
OTP_GROUP_ID = -1003830374258

# 🌐 SERVER CREDENTIALS (STEX ONLY)
STEX_EMAIL = "mdrajaislam469@gmail.com"
STEX_PASSWORD = "Raja1234@#"
API_STEX_LOGIN = "https://stexsms.com/mapi/v1/mauth/login"
API_STEX_CONSOLE = "https://stexsms.com/mapi/v1/mdashboard/console/info"
API_STEX_GET_NUM = "https://stexsms.com/mapi/v1/mdashboard/getnum/number"
API_STEX_INBOX = "https://stexsms.com/mapi/v1/mdashboard/getnum/info"

API_2FA = "https://2fa.cn/codes/{}"

# ==============================================================================
# 🛑 ADVANCED SERVER CRASH PREVENTION & CACHING
# ==============================================================================

MAUTH_TOKEN_STEX = None
GLOBAL_SESSION = None 
AUTH_LOCK_STEX = asyncio.Lock() 
LAST_AUTH_TIME_STEX = 0
LAST_INBOX_TEXT_STEX = ""

SENT_RANGES = set()
START_TIME = datetime.datetime.now()

BASE_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
DB_POOL_SIZE = 30

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# ==============================================================================
# 🧠 ENTERPRISE MEMORY SYSTEM (FOR 20,000+ USERS RAM CACHING)
# ==============================================================================

WAITING_OTPS = {}
NUM_TO_HASH = {}
BATCH_MSGS = {} 
OTP_TIMEOUT_SECONDS = 1200  

USER_CACHE = set()
BANNED_CACHE = set()

# Live Settings for Rewards & Withdrawals
SETTINGS_CACHE = {
    "otp_reward": 0.10,
    "ref_reward": 0.05,
    "min_withdraw": 50.0
}

DB_EXECUTOR = concurrent.futures.ThreadPoolExecutor(max_workers=20)

# ==============================================================================
# 🌍 MASSIVE COUNTRY FLAGS DICTIONARY (250+ COUNTRIES)
# ==============================================================================

COUNTRY_FLAGS = {
    "Afghanistan":"🇦🇫", "Albania":"🇦🇱", "Algeria":"🇩🇿", "Andorra":"🇦🇩", "Angola":"🇦🇴", "Antigua and Barbuda":"🇦🇬", "Argentina":"🇦🇷", "Armenia":"🇦🇲", "Australia":"🇦🇺", "Austria":"🇦🇹", "Azerbaijan":"🇦🇿", "Bahamas":"🇧🇸", "Bahrain":"🇧🇭", "Bangladesh":"🇧🇩", "Barbados":"🇧🇧", "Belarus":"🇧🇾", "Belgium":"🇧🇪", "Belize":"🇧🇿", "Benin":"🇧🇯", "Bhutan":"🇧🇹", "Bolivia":"🇧🇴", "Bosnia and Herzegovina":"🇧🇦", "Botswana":"🇧🇼", "Brazil":"🇧🇷", "Brunei":"🇧🇳", "Bulgaria":"🇧🇬", "Burkina Faso":"🇧🇫", "Burundi":"🇧🇮", "Cabo Verde":"🇨🇻", "Cambodia":"🇰🇭", "Cameroon":"🇨🇲", "Canada":"🇨🇦", "Central African Republic":"🇨🇫", "Chad":"🇹🇩", "Chile":"🇨🇱", "China":"🇨🇳", "Colombia":"🇨🇴", "Comoros":"🇰🇲", "Congo":"🇨🇬", "Costa Rica":"🇨🇷", "Croatia":"🇭🇷", "Cuba":"🇨🇺", "Cyprus":"🇨🇾", "Czechia":"🇨🇿", "Denmark":"🇩🇰", "Djibouti":"🇩🇯", "Dominica":"🇩🇲", "Dominican Republic":"🇩🇴", "Ecuador":"🇪🇨", "Egypt":"🇪🇬", "El Salvador":"🇸🇻", "Equatorial Guinea":"🇬🇶", "Eritrea":"🇪🇷", "Estonia":"🇪🇪", "Eswatini":"🇸🇿", "Ethiopia":"🇪🇹", "Fiji":"🇫🇯", "Finland":"🇫🇮", "France":"🇫🇷", "Gabon":"🇬🇦", "Gambia":"🇬🇲", "Georgia":"🇬🇪", "Germany":"🇩🇪", "Ghana":"🇬🇭", "Greece":"🇬🇷", "Grenada":"🇬🇩", "Guatemala":"🇬🇹", "Guinea":"🇬🇳", "Guinea-Bissau":"🇬🇼", "Guyana":"🇬🇾", "Haiti":"🇭🇹", "Honduras":"🇭🇳", "Hungary":"🇭🇺", "Iceland":"🇮🇸", "India":"🇮🇳", "Indonesia":"🇮🇩", "Iran":"🇮🇷", "Iraq":"🇮🇶", "Ireland":"🇮🇪", "Israel":"🇮🇱", "Italy":"🇮🇹", "Ivory Coast":"🇨🇮", "Jamaica":"🇯🇲", "Japan":"🇯🇵", "Jordan":"🇯🇴", "Kazakhstan":"🇰🇿", "Kenya":"🇰🇪", "Kiribati":"🇰🇮", "Kuwait":"🇰🇼", "Kyrgyzstan":"🇰🇬", "Laos":"🇱🇦", "Latvia":"🇱🇻", "Lebanon":"🇱🇧", "Lesotho":"🇱🇸", "Liberia":"🇱🇷", "Libya":"🇱🇾", "Liechtenstein":"🇱🇮", "Lithuania":"🇱🇹", "Luxembourg":"🇱🇺", "Madagascar":"🇲🇬", "Malawi":"🇲🇼", "Malaysia":"🇲🇾", "Maldives":"🇲🇻", "Mali":"🇲🇱", "Malta":"🇲🇹", "Marshall Islands":"🇲🇭", "Mauritania":"🇲🇷", "Mauritius":"🇲🇺", "Mexico":"🇲🇽", "Micronesia":"🇫🇲", "Moldova":"🇲🇩", "Monaco":"🇲🇨", "Mongolia":"🇲🇳", "Montenegro":"🇲🇪", "Morocco":"🇲🇦", "Mozambique":"🇲🇿", "Myanmar":"🇲🇲", "Namibia":"🇳🇦", "Nauru":"🇳🇷", "Nepal":"🇳🇵", "Netherlands":"🇳🇱", "New Zealand":"🇳🇿", "Nicaragua":"🇳🇮", "Niger":"🇳🇪", "Nigeria":"🇳🇬", "North Korea":"🇰🇵", "North Macedonia":"🇲🇰", "Norway":"🇳🇴", "Oman":"🇴🇲", "Pakistan":"🇵🇰", "Palau":"🇵🇼", "Palestine":"🇵🇸", "Panama":"🇵🇦", "Papua New Guinea":"🇵🇬", "Paraguay":"🇵🇾", "Peru":"🇵🇪", "Philippines":"🇵🇭", "Poland":"🇵🇱", "Portugal":"🇵🇹", "Qatar":"🇶🇦", "Romania":"🇷🇴", "Russia":"🇷🇺", "Rwanda":"🇷🇼", "Saint Kitts and Nevis":"🇰🇳", "Saint Lucia":"🇱🇨", "Saint Vincent":"🇻🇨", "Samoa":"🇼🇸", "San Marino":"🇸🇲", "Sao Tome and Principe":"🇸🇹", "Saudi Arabia":"🇸🇦", "Senegal":"🇸🇳", "Serbia":"🇷🇸", "Seychelles":"🇸🇨", "Sierra Leone":"🇸🇱", "Singapore":"🇸🇬", "Slovakia":"🇸🇰", "Slovenia":"🇸🇮", "Solomon Islands":"🇸🇧", "Somalia":"🇸🇴", "South Africa":"🇿🇦", "South Korea":"🇰🇷", "South Sudan":"🇸🇸", "Spain":"🇪🇸", "Sri Lanka":"🇱🇰", "Sudan":"🇸🇩", "Suriname":"🇸🇷", "Sweden":"🇸🇪", "Switzerland":"🇨🇭", "Syria":"🇸🇾", "Taiwan":"🇹🇼", "Tajikistan":"🇹🇯", "Tanzania":"🇹🇿", "Thailand":"🇹🇭", "Timor-Leste":"🇹🇱", "Togo":"🇹🇬", "Tonga":"🇹🇴", "Trinidad and Tobago":"🇹🇹", "Tunisia":"🇹🇳", "Turkey":"🇹🇷", "Turkmenistan":"🇹🇲", "Tuvalu":"🇹🇻", "Uganda":"🇺🇬", "Ukraine":"🇺🇦", "United Arab Emirates":"🇦🇪", "United Kingdom":"🇬🇧", "United States":"🇺🇸", "Uruguay":"🇺🇾", "Uzbekistan":"🇺🇿", "Vanuatu":"🇻🇺", "Venezuela":"🇻🇪", "Vietnam":"🇻🇳", "Yemen":"🇾🇪", "Zambia":"🇿🇲", "Zimbabwe":"🇿🇼", "PostPaid": "📡", "Hong Kong":"🇭🇰", "Macau":"🇲🇴", "Puerto Rico":"🇵🇷"
}

def get_flag(country_name):
    if country_name in COUNTRY_FLAGS: 
        return COUNTRY_FLAGS[country_name]
    for name, flag in COUNTRY_FLAGS.items():
        if name.lower() in country_name.lower() or country_name.lower() in name.lower(): 
            return flag
    return "🚩"

# ==============================================================================
# 🔧 UTILITY FUNCTIONS
# ==============================================================================

def clean_number(n: str) -> str:
    return re.sub(r'\D', '', str(n))

def mask_number(number: str) -> str:
    digits = clean_number(number)
    if len(digits) < 7:
        return number
    show_start = max(6, len(digits) - 6)
    first  = digits[:6]
    last   = digits[-3:]
    middle = '•' * (len(digits) - 9)
    if len(digits) <= 9:
        first = digits[:4]
        last  = digits[-3:]
        middle = '•' * (len(digits) - 7)
    return first + middle + last

def clean_message_text(raw_text):
    if not raw_text or str(raw_text).strip() == "":
        return "No Message Provided"
    text = str(raw_text)
    text = html.unescape(html.unescape(text))
    text = re.sub(r'<[^>]+>', '', text)
    text = text.replace('&lt;', '<').replace('&gt;', '>')
    text = re.sub(r'\*+', lambda m: '•' * len(m.group()), text)
    text = " ".join(text.split())
    return text.strip() if text.strip() else "No Message Provided"

def get_hash_key(number_str):
    clean_str = re.sub(r'\D', '', str(number_str))
    if not clean_str: return "UNKNOWN"
    return clean_str[-8:]

def extract_code(message):
    msg = str(message)
    # FIX: Catch WhatsApp format 123-456 and strip hyphen
    wa_match = re.search(r'\b(\d{3})-(\d{3})\b', msg)
    if wa_match:
        return wa_match.group(1) + wa_match.group(2)
        
    kw = re.search(r'(?:otp|code|verification|verify|pin|passcode|password)[^0-9]{0,25}(\d{4,8})', msg, re.IGNORECASE)
    if kw:
        return kw.group(1)
    fb = re.search(r'\b(\d{4,8})\b', msg)
    return fb.group(1) if fb else "See Msg"

def get_sms_from_item(item: dict) -> str:
    return item.get('full_sms') or item.get('full_sms_list') or item.get('sms') or item.get('otp') or item.get('message') or item.get('text') or item.get('msg') or ""

def get_service_from_item(item: dict) -> str:
    return item.get('app_name') or item.get('service_name') or item.get('service') or item.get('operator') or item.get('app') or "Service"

def get_number_from_item(item: dict) -> str:
    return item.get('number') or item.get('phone_number') or item.get('phone') or item.get('mobile') or item.get('msisdn') or ""

def get_code_from_item(item: dict, raw_msg: str) -> str:
    explicit = item.get('otps') or item.get('otp_code') or item.get('verification_code') or item.get('code') or ""
    if explicit and re.match(r'^\d{4,8}$', str(explicit).strip()):
        return str(explicit).strip()
    return extract_code(raw_msg)

def _find_waiter(num_raw: str):
    c = clean_number(num_raw)
    if not c: return None, None
    for length in [8, 7, 6]:
        if len(c) >= length:
            hk = c[-length:]
            if hk in WAITING_OTPS: return hk, WAITING_OTPS[hk]
    hk = NUM_TO_HASH.get(c)
    if hk and hk in WAITING_OTPS: return hk, WAITING_OTPS[hk]
    return None, None

# ==============================================================================
# 🗄️ DATABASE & REWARD SYSTEM MANAGEMENT
# ==============================================================================

DB_FILE = "bot_v33.db"

class DatabasePool:
    def __init__(self, db_file, pool_size=30):
        self.db_file = db_file
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
    global USER_CACHE, BANNED_CACHE, SETTINGS_CACHE
    with db_pool.get_connection() as conn:
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            join_date TEXT,
            is_banned INTEGER DEFAULT 0,
            balance REAL DEFAULT 0.0,
            referrer_id INTEGER DEFAULT NULL,
            total_referrals INTEGER DEFAULT 0
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS settings (
            id INTEGER PRIMARY KEY,
            otp_reward REAL DEFAULT 0.10,
            ref_reward REAL DEFAULT 0.05,
            min_withdraw REAL DEFAULT 50.0
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS withdrawals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            amount REAL,
            method TEXT,
            account TEXT,
            status TEXT DEFAULT 'pending',
            date TEXT DEFAULT CURRENT_TIMESTAMP
        )''')
        
        c.execute("SELECT otp_reward, ref_reward, min_withdraw FROM settings WHERE id=1")
        settings_row = c.fetchone()
        if not settings_row:
            c.execute("INSERT INTO settings (id, otp_reward, ref_reward, min_withdraw) VALUES (1, 0.10, 0.05, 50.0)")
            SETTINGS_CACHE["otp_reward"] = 0.10
            SETTINGS_CACHE["ref_reward"] = 0.05
            SETTINGS_CACHE["min_withdraw"] = 50.0
        else:
            SETTINGS_CACHE["otp_reward"] = settings_row[0]
            SETTINGS_CACHE["ref_reward"] = settings_row[1]
            SETTINGS_CACHE["min_withdraw"] = float(settings_row[2]) if len(settings_row)>2 and settings_row[2] else 50.0
            
        conn.commit()
        
        c.execute("SELECT user_id, is_banned FROM users")
        rows = c.fetchall()
        for row in rows:
            USER_CACHE.add(row[0])
            if row[1] == 1:
                BANNED_CACHE.add(row[0])

def sync_register_user_db(user_id, referrer_id=None):
    with db_pool.get_connection() as conn:
        c = conn.cursor()
        c.execute("SELECT user_id FROM users WHERE user_id=?", (user_id,))
        if not c.fetchone():
            c.execute("INSERT INTO users (user_id, join_date, referrer_id) VALUES (?, CURRENT_TIMESTAMP, ?)", (user_id, referrer_id))
            if referrer_id:
                c.execute("UPDATE users SET total_referrals = total_referrals + 1 WHERE user_id=?", (referrer_id,))
        conn.commit()

async def ensure_user_fast(user_id, referrer_id=None):
    if user_id not in USER_CACHE:
        USER_CACHE.add(user_id)
        loop = asyncio.get_event_loop()
        loop.run_in_executor(DB_EXECUTOR, sync_register_user_db, user_id, referrer_id)
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

def sync_get_user_info(user_id):
    with db_pool.get_connection() as conn:
        c = conn.cursor()
        c.execute("SELECT balance, total_referrals, referrer_id FROM users WHERE user_id=?", (user_id,))
        row = c.fetchone()
        if row: return {"balance": row[0], "total_referrals": row[1], "referrer_id": row[2]}
        return {"balance": 0.0, "total_referrals": 0, "referrer_id": None}

def sync_add_balance(user_id, amount):
    with db_pool.get_connection() as conn:
        c = conn.cursor()
        c.execute("UPDATE users SET balance = balance + ? WHERE user_id=?", (amount, user_id))
        c.execute("SELECT balance FROM users WHERE user_id=?", (user_id,))
        new_bal = c.fetchone()[0]
        conn.commit()
        return new_bal

def sync_update_setting(key, value):
    with db_pool.get_connection() as conn:
        c = conn.cursor()
        if key == "otp":
            c.execute("UPDATE settings SET otp_reward=? WHERE id=1", (value,))
            SETTINGS_CACHE["otp_reward"] = value
        elif key == "ref":
            c.execute("UPDATE settings SET ref_reward=? WHERE id=1", (value,))
            SETTINGS_CACHE["ref_reward"] = value
        elif key == "min_withdraw":
            c.execute("UPDATE settings SET min_withdraw=? WHERE id=1", (value,))
            SETTINGS_CACHE["min_withdraw"] = value
        conn.commit()

def sync_get_top_referrers():
    with db_pool.get_connection() as conn:
        c = conn.cursor()
        c.execute("SELECT user_id, total_referrals FROM users ORDER BY total_referrals DESC LIMIT 10")
        return c.fetchall()

def sync_create_withdraw(user_id, amount, method, account):
    with db_pool.get_connection() as conn:
        c = conn.cursor()
        c.execute("UPDATE users SET balance = balance - ? WHERE user_id=?", (amount, user_id))
        c.execute("INSERT INTO withdrawals (user_id, amount, method, account, status) VALUES (?, ?, ?, ?, 'pending')", (user_id, amount, method, account))
        wid = c.lastrowid
        conn.commit()
        return wid

def sync_update_withdraw_status(wd_id, status):
    with db_pool.get_connection() as conn:
        c = conn.cursor()
        c.execute("SELECT user_id, amount, status FROM withdrawals WHERE id=?", (wd_id,))
        row = c.fetchone()
        if not row or row[2] != 'pending': return False, None, None
        
        user_id, amount = row[0], row[1]
        c.execute("UPDATE withdrawals SET status=? WHERE id=?", (status, wd_id))
        
        if status == 'rejected':
            c.execute("UPDATE users SET balance = balance + ? WHERE user_id=?", (amount, user_id))
            
        conn.commit()
        return True, user_id, amount

def sync_get_withdraw_info(wd_id):
    with db_pool.get_connection() as conn:
        c = conn.cursor()
        c.execute("SELECT user_id, amount, method, account, status FROM withdrawals WHERE id=?", (wd_id,))
        return c.fetchone()

# ==============================================================================
# 🔐 AUTHENTICATION & API REQUESTS (STEX ONLY)
# ==============================================================================

async def get_session():
    global GLOBAL_SESSION
    if GLOBAL_SESSION is None or GLOBAL_SESSION.closed:
        connector = aiohttp.TCPConnector(limit=500, keepalive_timeout=300, enable_cleanup_closed=True)
        GLOBAL_SESSION = aiohttp.ClientSession(connector=connector, cookie_jar=aiohttp.CookieJar(unsafe=True))
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

def get_cf_headers():
    return {
        "User-Agent": BASE_USER_AGENT,
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9",
        "Origin": "https://stexsms.com",
        "Referer": "https://stexsms.com/",
        "Sec-Ch-Ua": '"Chromium";v="122", "Not(A:Brand";v="24", "Google Chrome";v="122"',
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": '"Windows"',
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin"
    }

async def authenticate_stex(force=False):
    global MAUTH_TOKEN_STEX, LAST_AUTH_TIME_STEX
    async with AUTH_LOCK_STEX:
        if not force and time.time() - LAST_AUTH_TIME_STEX < 300 and MAUTH_TOKEN_STEX: return True
        payload = {"email": STEX_EMAIL, "password": STEX_PASSWORD}
        headers = get_cf_headers()
        headers["Content-Type"] = "application/json"
        try:
            session = await get_session()
            async with session.post(API_STEX_LOGIN, json=payload, headers=headers, timeout=12, ssl=False) as response:
                if response.status == 200:
                    data = await parse_response_safely(response)
                    if data and str(data.get('meta', {}).get('code')) == '200':
                        MAUTH_TOKEN_STEX = data['data']['token']
                        LAST_AUTH_TIME_STEX = time.time()
                        logger.info("✅ STEX auth successful")
                        return True
                return False
        except Exception as e:
            return False

async def stex_api_request(method, url, json_payload=None, return_text=False):
    global MAUTH_TOKEN_STEX
    for attempt in range(3):
        try:
            if not MAUTH_TOKEN_STEX:
                if not await authenticate_stex():
                    await asyncio.sleep(1)
                    continue
            session = await get_session()
            headers = get_cf_headers()
            headers["mauthtoken"] = str(MAUTH_TOKEN_STEX)
            headers["Cookie"] = f"mauthtoken={MAUTH_TOKEN_STEX}"
            
            timeout = aiohttp.ClientTimeout(total=12)
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
                text_response = await response.text()
                if return_text: return 200, text_response
                try: data = json.loads(text_response)
                except: data = None
                return 200, data
            else: 
                return status, None
        except Exception: pass
    return 500, None

async def auto_relogin_job(context: ContextTypes.DEFAULT_TYPE):
    logger.info("🔄 Refreshing Session...")
    await authenticate_stex(force=True)

# ==============================================================================
# 🔒 MIDDLEWARES & DYNAMIC UI
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
    row = []
    for c in CHANNELS:
        row.append(InlineKeyboardButton(f"📢 Join {c}", url=f"https://t.me/{c.replace('@', '')}"))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row: keyboard.append(row)
        
    keyboard.append([InlineKeyboardButton("✅ Joined / Verify", callback_data="check_join")])
    
    msg = (
        "⛔ <b>Access Denied!</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "<i>You must be a member of our official channels to use this bot.</i>\n\n"
        "👇 <b>Please join below:</b>"
    )
    if update.callback_query: 
        await update.callback_query.edit_message_text(text=msg, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
    else: 
        await update.message.reply_text(text=msg, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)

async def check_ban_middleware(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if is_user_banned_fast(user_id):
        if update.callback_query: await update.callback_query.answer("🚫 You are banned.", show_alert=True)
        else: await update.message.reply_text("🚫 <b>You have been banned.</b>", parse_mode=ParseMode.HTML)
        return True
    return False

async def delete_message_later(bot, chat_id, msg_id, delay_seconds):
    await asyncio.sleep(delay_seconds)
    try: await bot.delete_message(chat_id=chat_id, message_id=msg_id)
    except Exception: pass

async def update_dynamic_batch_message(context, chat_id, msg_id, batch_key):
    if batch_key not in BATCH_MSGS: return
    batch = BATCH_MSGS[batch_key]
    
    if len(batch['numbers']) == 0:
        try: 
            txt = (
                f"✅ <b>ALL CODES RECEIVED SUCCESSFULLY!</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"<i>Thank you for using our service. Do you want to generate another number from the same range?</i>"
            )
            kb = [
                [InlineKeyboardButton("🔄 Get Number Again", callback_data="change_num")],
                [InlineKeyboardButton("🔙 Menu", callback_data="go_main")]
            ]
            await context.bot.edit_message_text(chat_id=chat_id, message_id=msg_id, text=txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.HTML)
        except Exception: pass
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
            f"⏳ <i>Waiting for SMS... (Received numbers disappear)</i>"
        )
        kb = [
            [InlineKeyboardButton("💬 OTP GROUP", url="https://t.me/RTxOtpX")],
            [InlineKeyboardButton("🔄 Change Number", callback_data="change_num"), InlineKeyboardButton("🔙 Back", callback_data="go_main")]
        ]
        try: 
            await context.bot.edit_message_text(chat_id=chat_id, message_id=msg_id, text=txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.HTML)
        except Exception: pass

# ==============================================================================
# 🤖 AUTO RANGE FORWARDER JOB (10s interval, Top 50 Logs, 100% Capture)
# ==============================================================================

async def auto_range_forwarder_job(context: ContextTypes.DEFAULT_TYPE):
    global SENT_RANGES
    allowed_apps = ['facebook', 'whatsapp']
    bot_username = context.bot.username

    status, data = await stex_api_request('GET', API_STEX_CONSOLE)
    if status == 200 and isinstance(data, dict):
        # Fetching top 50 logs to guarantee NO RANGE is missed
        logs = data.get('data', {}).get('logs', [])[:50]
        for log in logs:
            if isinstance(log, dict):
                r_val = log.get('range')
                raw_app = str(log.get('app_name', 'Unknown')).lower()
                c_name = log.get('country', 'Unknown')
                
                raw_msg = get_sms_from_item(log)
                msg_text = str(raw_msg)
                
                if any(app in raw_app for app in allowed_apps) and r_val and r_val not in SENT_RANGES:
                    SENT_RANGES.add(r_val)
                    if len(SENT_RANGES) > 5000: SENT_RANGES.clear()
                    
                    display_app = "PC Clone" if ('facebook' in raw_app and '•' in msg_text) else log.get('app_name', 'Unknown').title()
                    full_msg_text = clean_message_text(raw_msg)
                    
                    num_in_msg = re.search(r'\b(\d{7,15})\b', full_msg_text)
                    if num_in_msg:
                        full_msg_text = full_msg_text.replace(num_in_msg.group(1), mask_number(num_in_msg.group(1)))
                    
                    range_msg = (
                        f"🔥 <b>New Range find</b>\n"
                        f"━━━━━━━━━━━━━━━━━━━━\n"
                        f"🎯 Range - <code>{r_val}</code>\n"
                        f"🛒 Service - <i>{html.escape(display_app)}</i>\n"
                        f"🌍 Country - {get_flag(c_name)} {c_name}\n"
                        f"✉️ Message - <pre>{html.escape(full_msg_text)}</pre>"
                    )
                    kb = [[InlineKeyboardButton("🤖 Bot Link", url=f"https://t.me/{bot_username}")]]
                    try: await context.bot.send_message(chat_id=RANGE_GROUP_ID, text=range_msg, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.HTML)
                    except Exception: pass

# ==============================================================================
# 🚀 ULTRA-FAST OTP POLLER WITH TEXT-CACHE ALGORITHM
# ==============================================================================

async def process_found_otp(context, hash_key, api_num, code_only, svc_name, raw_msg):
    global WAITING_OTPS, BATCH_MSGS, NUM_TO_HASH
    user_data = WAITING_OTPS.get(hash_key)
    if not user_data: return
    
    user_id = user_data['user_id']
    chat_id = user_data['chat_id']
    msg_id = user_data['msg_id']
    full_num = user_data['full_num']
    batch_key = user_data['batch_key']
    
    loop = asyncio.get_event_loop()
    otp_reward = SETTINGS_CACHE["otp_reward"]
    ref_reward = SETTINGS_CACHE["ref_reward"]
    
    new_balance = await loop.run_in_executor(DB_EXECUTOR, sync_add_balance, user_id, otp_reward)
    
    user_info = await loop.run_in_executor(DB_EXECUTOR, sync_get_user_info, user_id)
    referrer_id = user_info.get("referrer_id")
    if referrer_id:
        await loop.run_in_executor(DB_EXECUTOR, sync_add_balance, referrer_id, ref_reward)
        try:
            ref_msg = f"🎁 <b>Referral Bonus!</b>\nYour referral received an OTP. You got <b>+{ref_reward:.2f} Tk</b>!"
            asyncio.create_task(context.bot.send_message(chat_id=referrer_id, text=ref_msg, parse_mode=ParseMode.HTML))
        except Exception: pass

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

    user_msg = (
        f"🎉 <b>OTP RECEIVED SUCCESSFULLY!</b> ✨\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📱 <b>Service :</b> <i>{html.escape(str(svc_name).upper())}</i>\n"
        f"📞 <b>Number  :</b> <code>{full_num}</code>\n"
        f"🔑 <b>Your OTP:</b> <code>{code_only}</code>\n"
        f"💰 <b>Balance Added:</b> +{otp_reward:.2f} Tk\n"
        f"💳 <b>Total Balance:</b> {new_balance:.2f} Tk\n"
        f"━━━━━━━━━━━━━━━━━━━━"
    )
    
    asyncio.create_task(context.bot.send_message(chat_id=chat_id, text=user_msg, parse_mode=ParseMode.HTML))
    
    clean_raw_msg = clean_message_text(raw_msg) 
    masked_num = mask_number(full_num)
    
    group_msg = (
        f"🔔 <b>Otp Received</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📱 Number - <code>{masked_num}</code>\n"
        f"🛒 Service - <pre>{html.escape(str(svc_name))}</pre>\n"
        f"🔑 Code - <code>{code_only}</code>\n"
        f"✉️ Full sms - <pre>{html.escape(str(clean_raw_msg))}</pre>"
    )
    group_kb = [[InlineKeyboardButton("👨‍💻 Owner", url="https://t.me/RTx2R")]]
    asyncio.create_task(context.bot.send_message(chat_id=OTP_GROUP_ID, text=group_msg, reply_markup=InlineKeyboardMarkup(group_kb), parse_mode=ParseMode.HTML))

async def global_otp_checker_job(context: ContextTypes.DEFAULT_TYPE):
    global WAITING_OTPS, BATCH_MSGS, NUM_TO_HASH, LAST_INBOX_TEXT_STEX
    if not WAITING_OTPS: return 
    
    current_time = time.time()
    expired_keys = [hk for hk, d in list(WAITING_OTPS.items()) if current_time - d['time'] > OTP_TIMEOUT_SECONDS]
            
    for h_key in expired_keys:
        u_data = WAITING_OTPS.pop(h_key, None)
        if u_data:
            NUM_TO_HASH.pop(clean_number(u_data['full_num']), None)
            b_key = u_data.get('batch_key')
            if b_key and b_key in BATCH_MSGS:
                if u_data['full_num'] in BATCH_MSGS[b_key]['numbers']:
                    BATCH_MSGS[b_key]['numbers'].remove(u_data['full_num'])
                if len(BATCH_MSGS[b_key]['numbers']) == 0:
                    try: await context.bot.delete_message(chat_id=u_data['chat_id'], message_id=u_data['msg_id'])
                    except: pass
                    BATCH_MSGS.pop(b_key, None)

    if not WAITING_OTPS: return 
        
    found_keys = []
    date_str = datetime.datetime.now().strftime("%Y-%m-%d")

    stex_url = f"{API_STEX_INBOX}?date={date_str}&page=1&search=&status="
    stex_status, stex_text = await stex_api_request('GET', stex_url, return_text=True)

    if stex_status == 200 and stex_text and stex_text != LAST_INBOX_TEXT_STEX:
        LAST_INBOX_TEXT_STEX = stex_text
        try:
            api_res = json.loads(stex_text)
            data_field = api_res.get('data', {})
            items = data_field if isinstance(data_field, list) else (data_field.get('numbers') or data_field.get('list') or data_field.get('items') or [])
            
            for item in items:
                if not isinstance(item, dict): continue
                num_raw = get_number_from_item(item)
                raw_msg = get_sms_from_item(item)
                if not num_raw or not raw_msg: continue
                
                hash_key, waiter = _find_waiter(num_raw)
                if hash_key and hash_key not in found_keys:
                    svc_name = get_service_from_item(item)
                    code_val = get_code_from_item(item, raw_msg)
                    await process_found_otp(context, hash_key, waiter['full_num'], code_val, svc_name, raw_msg)
                    found_keys.append(hash_key)
        except Exception: pass

    for k in found_keys: 
        ud = WAITING_OTPS.pop(k, None)
        if ud: NUM_TO_HASH.pop(clean_number(ud['full_num']), None)

# ==============================================================================
# 🎯 EXACTLY 2-NUMBER GENERATION SYSTEM
# ==============================================================================

async def process_number_generation(update: Update, context: ContextTypes.DEFAULT_TYPE, range_val, is_callback=True):
    global WAITING_OTPS, BATCH_MSGS, NUM_TO_HASH
    
    wait_txt = "⏳ <i>Connecting to secure server... Generating 2 Numbers...</i> 🚀"
    if is_callback:
        user_id = update.callback_query.from_user.id
        chat_id = update.callback_query.message.chat_id
        msg = await update.callback_query.edit_message_text(text=wait_txt, parse_mode=ParseMode.HTML)
    else:
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        msg = await update.message.reply_text(text=wait_txt, parse_mode=ParseMode.HTML)
    
    range_val = str(range_val).strip()
    if not range_val.upper().endswith("XXX"): range_val += "XXX"
        
    fetched_numbers = []
    country_name = "Unknown"
    
    for _ in range(2):
        await asyncio.sleep(0.3) 
        payload = {"range": range_val, "is_national": False, "remove_plus": False}
        status, resp = await stex_api_request('POST', API_STEX_GET_NUM, json_payload=payload)
            
        if status == 200 and isinstance(resp, dict) and 'data' in resp and resp['data'].get('number'):
            fetched_numbers.append(resp['data']['number'])
            country_name = resp['data'].get('country', country_name)
            
    if fetched_numbers:
        flag = get_flag(country_name)
        symbols = ["❶", "❷"]
        num_str = ""
        for i, n in enumerate(fetched_numbers):
            num_str += f"{symbols[i]} <code>{n}</code>\n"
            
        txt = (
            f"✅ <b>NUMBERS GENERATED</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"🌍 <b>{flag} {country_name}</b>\n\n"
            f"{num_str}\n"
            f"⏳ <i>Waiting for SMS... (Received numbers disappear)</i>"
        )
        
        kb = [
            [InlineKeyboardButton("💬 OTP GROUP", url="https://t.me/RTxOtpX")],
            [InlineKeyboardButton("🔄 Change Number", callback_data="change_num"), InlineKeyboardButton("🔙 Menu", callback_data="go_main")]
        ]
        
        await msg.edit_text(text=txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.HTML)
        
        batch_key = f"{chat_id}_{msg.message_id}"
        BATCH_MSGS[batch_key] = {'numbers': fetched_numbers.copy(), 'country_name': country_name, 'flag': flag}
        
        for n in fetched_numbers:
            hash_key = get_hash_key(n)
            WAITING_OTPS[hash_key] = {'full_num': n, 'user_id': user_id, 'chat_id': chat_id, 'msg_id': msg.message_id, 'batch_key': batch_key, 'time': time.time()}
            NUM_TO_HASH[clean_number(n)] = hash_key
            
        context.user_data['range'] = range_val 
        
    else:
        err_msg = "🔄 <i>Our high-speed servers are balancing the load. No numbers found right now.</i>"
        await msg.edit_text(
            text=f"📡 <b>Server Optimizing:</b>\n{err_msg}\n\nPlease try again or select another category.", 
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="go_main")]]), 
            parse_mode=ParseMode.HTML
        )

# ==============================================================================
# 📋 MENUS & UI
# ==============================================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await check_ban_middleware(update, context): return
    user_id = update.effective_user.id
    
    referrer_id = None
    if context.args and context.args[0].startswith("ref_"):
        try: referrer_id = int(context.args[0].replace("ref_", ""))
        except: pass
        if referrer_id == user_id: referrer_id = None
        
    await ensure_user_fast(user_id, referrer_id)
    context.user_data.clear()
    
    if not await check_subscription(user_id, context.bot): 
        await send_join_prompt(update, context)
    else: 
        await show_main_menu(update, context)

async def show_main_menu(update_obj, context):
    kb = [
        ["📱 Get Number", "🔐 Get 2FA"], 
        ["🎁 Referral & Balance", "📊 See Activity"],
        ["🎧 Support"]
    ]
    msg = (
        "✨ <b>P R E M I U M   O T P   B O T</b> ✨\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "👋 <i>Welcome to the most advanced & stable OTP system!</i>\n\n"
        "🛡️ <b>Choose an option below.</b>"
    )
    if hasattr(update_obj, 'message') and update_obj.message: 
        await update_obj.message.reply_text(msg, reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True), parse_mode=ParseMode.HTML)
    elif hasattr(update_obj, 'callback_query') and update_obj.callback_query:
        try: await update_obj.callback_query.message.delete()
        except: pass
        await context.bot.send_message(chat_id=update_obj.effective_chat.id, text=msg, reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True), parse_mode=ParseMode.HTML)

async def start_category_selection(update_obj, context):
    kb = [
        [InlineKeyboardButton("📘 Facebook", callback_data="cat_facebook"), InlineKeyboardButton("💬 WhatsApp", callback_data="cat_whatsapp")],
        [InlineKeyboardButton("🎯 Custom Range", callback_data="cat_custom")]
    ]
    txt = "📱 <b>SELECT CATEGORY</b> 📱\n━━━━━━━━━━━━━━━━━━━━\n<i>Which application do you need numbers for?</i>"
    if hasattr(update_obj, 'callback_query') and update_obj.callback_query: 
        await update_obj.callback_query.edit_message_text(text=txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.HTML)
    else: 
        await update_obj.message.reply_text(text=txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.HTML)

async def handle_category_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    category = query.data.split('_')[1].lower()
    
    if category == 'custom':
        await query.edit_message_text(text="🎯 <b>CUSTOM RANGE GENERATOR</b>\n━━━━━━━━━━━━━━━━━━━━\n✏️ <i>Type your custom range below.</i>\n💡 <b>Ex:</b> <code>88017XXX</code>", parse_mode=ParseMode.HTML)
        context.user_data['state'] = 'WAITING_FOR_RANGE'
        return
    
    await query.edit_message_text(text="📡 <i>Connecting to Server... Please wait.</i> ⏳", parse_mode=ParseMode.HTML)
    countries = {}

    await authenticate_stex(force=True)
    status, data = await stex_api_request('GET', API_STEX_CONSOLE)

    if status == 200 and isinstance(data, dict):
        for log in data.get('data', {}).get('logs', []):
            if isinstance(log, dict) and category in str(log.get('app_name', '')).lower():
                c, r = log.get('country'), log.get('range')
                if c and r and c not in countries: countries[c] = r
        
    if not countries:
        await query.edit_message_text(
            text=f"📡 <b>Load Balancing...</b>\n<i>No immediate numbers found for {category.title()}. Please try again in a moment.</i>", 
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="go_main")]]), parse_mode=ParseMode.HTML
        )
        return
        
    kb = []
    for c_name, r_val in countries.items(): 
        kb.append([InlineKeyboardButton(f"{get_flag(c_name)} {c_name}", callback_data=f"r_{r_val}_{c_name[:15]}")])
    kb.append([InlineKeyboardButton("🔙 Back to Categories", callback_data="go_main")])
    
    await query.edit_message_text(text=f"🌍 <b>SELECT A COUNTRY ({category.title()})</b>\n━━━━━━━━━━━━━━━━━━━━", reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.HTML)

# ==============================================================================
# 🎮 TEXT HANDLER & ADMIN / WITHDRAW LOGIC
# ==============================================================================

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await check_ban_middleware(update, context): return
    user_id = update.effective_user.id
    text = update.message.text
    user_data = context.user_data
    await ensure_user_fast(user_id)
    
    main_buttons = ["📱 Get Number", "🔐 Get 2FA", "🎧 Support", "📊 See Activity", "🎁 Referral & Balance"]
    admin_buttons = ["📊 Bot Status", "👥 Total Users", "📢 Broadcast", "🚫 Ban / Unban", "💰 Set Rewards", "💳 Set Min Withdraw", "💸 Add Balance", "🏆 Top Referrers", "🔙 Main Menu"]
    
    if text in main_buttons or text in admin_buttons:
        user_data['state'] = None
        user_data['admin_reply_target'] = None
        
    # --- ADMIN CONTROLS ---
    if user_id in ADMIN_IDS:
        if text == "📊 Bot Status":
            uptime = datetime.datetime.now() - START_TIME
            txt = (
                f"📊 <b>ULTRA ENTERPRISE STATUS</b> 📊\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"⏱ <b>Uptime:</b> {str(uptime).split('.')[0]}\n"
                f"👥 <b>Total Users:</b> {get_total_users_count()}\n"
                f"📡 <b>Active Waiters:</b> {len(WAITING_OTPS)} Numbers\n"
                f"⚡ <b>RAM Cache:</b> ACTIVE\n"
                f"💰 <b>OTP Reward:</b> {SETTINGS_CACHE['otp_reward']} Tk\n"
                f"🔗 <b>Ref Reward:</b> {SETTINGS_CACHE['ref_reward']} Tk\n"
                f"💳 <b>Min Withdraw:</b> {SETTINGS_CACHE['min_withdraw']} Tk\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"✅ <i>Server Running Perfectly</i>"
            )
            return await update.message.reply_text(txt, parse_mode=ParseMode.HTML)
            
        elif text == "👥 Total Users":
            return await update.message.reply_text(f"👥 <b>Total Registered Users:</b> {get_total_users_count()}", parse_mode=ParseMode.HTML)
            
        elif text == "📢 Broadcast":
            user_data['state'] = 'ADMIN_BROADCAST'
            return await update.message.reply_text("📢 <b>Send the message you want to broadcast.</b>\n<i>(Or click 🔙 Main Menu to cancel)</i>", parse_mode=ParseMode.HTML)
            
        elif text == "🚫 Ban / Unban":
            user_data['state'] = 'ADMIN_BAN'
            return await update.message.reply_text("🚫 <b>Send User ID and action (ban/unban).</b>\nExample: <code>12345678 ban</code>", parse_mode=ParseMode.HTML)
            
        elif text == "💰 Set Rewards":
            user_data['state'] = 'ADMIN_REWARD'
            return await update.message.reply_text("💰 <b>Set Reward.</b>\nExample: <code>otp 0.5</code> or <code>ref 0.2</code>", parse_mode=ParseMode.HTML)
            
        elif text == "💳 Set Min Withdraw":
            user_data['state'] = 'ADMIN_MIN_WD'
            return await update.message.reply_text("💳 <b>Set Minimum Withdraw Amount.</b>\nExample: <code>100</code>", parse_mode=ParseMode.HTML)
            
        elif text == "💸 Add Balance":
            user_data['state'] = 'ADMIN_ADD_BAL'
            return await update.message.reply_text("💸 <b>Add balance to user.</b>\nExample: <code>12345678 50.0</code>", parse_mode=ParseMode.HTML)
            
        elif text == "🏆 Top Referrers":
            loop = asyncio.get_event_loop()
            top_users = await loop.run_in_executor(DB_EXECUTOR, sync_get_top_referrers)
            msg = "🏆 <b>TOP 10 REFERRERS</b> 🏆\n━━━━━━━━━━━━━━━━━━━━\n"
            for i, (uid, count) in enumerate(top_users):
                if count > 0: msg += f"<b>{i+1}.</b> <code>{uid}</code> - <b>{count}</b> Referrals\n"
            if "1." not in msg: msg += "<i>No active referrers yet.</i>"
            return await update.message.reply_text(msg, parse_mode=ParseMode.HTML)
            
        elif text == "🔙 Main Menu":
            await show_main_menu(update, context)
            return

        state = user_data.get('state')
        if state == 'ADMIN_BROADCAST':
            users = get_all_users()
            msg = await update.message.reply_text(f"⏳ <i>Broadcasting to {len(users)} users...</i>", parse_mode=ParseMode.HTML)
            success, failed = 0, 0
            for u_id in users:
                try:
                    await context.bot.send_message(chat_id=u_id, text=f"📢 <b>ADMIN BROADCAST</b>\n━━━━━━━━━━━━━━━━━━━━\n{text}", parse_mode=ParseMode.HTML)
                    success += 1
                except: failed += 1
                await asyncio.sleep(0.05) 
            await msg.edit_text(f"✅ <b>Broadcast Completed!</b>\n🟢 Delivered: {success}\n🔴 Failed: {failed}", parse_mode=ParseMode.HTML)
            user_data['state'] = None
            return
            
        elif state == 'ADMIN_BAN':
            try:
                parts = text.split()
                uid, action = int(parts[0]), parts[1].lower()
                status = 1 if action == 'ban' else 0
                await set_ban_status(uid, status)
                await update.message.reply_text(f"✅ User <code>{uid}</code> has been <b>{action.upper()}NED</b>.", parse_mode=ParseMode.HTML)
            except: await update.message.reply_text("⚠️ Invalid format.")
            user_data['state'] = None
            return
            
        elif state == 'ADMIN_REWARD':
            try:
                parts = text.split()
                r_type, amount = parts[0].lower(), float(parts[1])
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(DB_EXECUTOR, sync_update_setting, r_type, amount)
                await update.message.reply_text(f"✅ {r_type.upper()} reward updated to <b>{amount:.2f} Tk</b>.", parse_mode=ParseMode.HTML)
            except: await update.message.reply_text("⚠️ Invalid format.")
            user_data['state'] = None
            return
            
        elif state == 'ADMIN_MIN_WD':
            try:
                amount = float(text)
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(DB_EXECUTOR, sync_update_setting, "min_withdraw", amount)
                await update.message.reply_text(f"✅ Min Withdraw updated to <b>{amount:.2f} Tk</b>.", parse_mode=ParseMode.HTML)
            except: await update.message.reply_text("⚠️ Invalid format.")
            user_data['state'] = None
            return
            
        elif state == 'ADMIN_ADD_BAL':
            try:
                parts = text.split()
                uid, amount = int(parts[0]), float(parts[1])
                loop = asyncio.get_event_loop()
                new_bal = await loop.run_in_executor(DB_EXECUTOR, sync_add_balance, uid, amount)
                await update.message.reply_text(f"✅ Added <b>{amount} Tk</b> to <code>{uid}</code>.\nNew Balance: <b>{new_bal:.2f} Tk</b>", parse_mode=ParseMode.HTML)
                try: await context.bot.send_message(chat_id=uid, text=f"💰 <b>Admin Added Balance!</b>\n+{amount:.2f} Tk has been added.", parse_mode=ParseMode.HTML)
                except: pass
            except: await update.message.reply_text("⚠️ Invalid format.")
            user_data['state'] = None
            return

    # --- USER CONTROLS & STATES ---
    target_reply_user = user_data.get('admin_reply_target')
    if target_reply_user and text not in main_buttons:
        try:
            await context.bot.send_message(chat_id=int(target_reply_user), text=f"👨‍💻 <b>Admin Reply:</b>\n━━━━━━━━━━━━━━━━━━━━\n{text}", parse_mode=ParseMode.HTML)
            await update.message.reply_text("✅ <b>Reply sent successfully.</b>", parse_mode=ParseMode.HTML)
        except Exception:
            await update.message.reply_text("❌ <b>Failed to send.</b>")
        user_data['admin_reply_target'] = None
        return

    state = user_data.get('state')
    
    if text == "📱 Get Number":
        if not await check_subscription(user_id, context.bot): await send_join_prompt(update, context)
        else: await start_category_selection(update, context)
            
    elif text == "🔐 Get 2FA":
        user_data['state'] = 'WAITING_FOR_2FA'
        await update.message.reply_text("🔐 <b>2FA CODE GENERATOR</b>\n━━━━━━━━━━━━━━━━━━━━\n<i>Paste your Secret Key below:</i>", parse_mode=ParseMode.HTML)
        
    elif state == 'WAITING_FOR_2FA':
        key = text.replace(" ", "").strip()
        msg = await update.message.reply_text("⏳ <i>Generating...</i>", parse_mode=ParseMode.HTML)
        try:
            session = await get_session()
            async with session.get(API_2FA.format(key), timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    code = data.get('code')
                    if code: 
                        out = f"✅ <b>2FA CODE GENERATED!</b>\n━━━━━━━━━━━━━━━━━━━━\n🔢 <b>Code:</b> <code>{code}</code>\n\n<i>⚠️ Auto-delete in 5 mins.</i>"
                        await msg.edit_text(out, parse_mode=ParseMode.HTML)
                        asyncio.create_task(delete_message_later(context.bot, msg.chat_id, msg.message_id, 300))
                    else: await msg.edit_text("❌ <b>Invalid Secret Key.</b>", parse_mode=ParseMode.HTML)
                else: await msg.edit_text("❌ <b>API Error!</b>", parse_mode=ParseMode.HTML)
        except Exception: await msg.edit_text("❌ <b>Network Error.</b>", parse_mode=ParseMode.HTML)
        user_data['state'] = None

    elif text == "🎁 Referral & Balance":
        loop = asyncio.get_event_loop()
        user_info = await loop.run_in_executor(DB_EXECUTOR, sync_get_user_info, user_id)
        bot_username = context.bot.username
        ref_link = f"https://t.me/{bot_username}?start=ref_{user_id}"
        
        msg = (
            f"🎁 <b>REFERRAL & BALANCE</b> 🎁\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"💰 <b>Your Balance:</b> {user_info['balance']:.2f} Tk\n"
            f"👥 <b>Total Referrals:</b> {user_info['total_referrals']}\n\n"
            f"⚡ <b>Earn Per OTP:</b> {SETTINGS_CACHE['otp_reward']:.2f} Tk\n"
            f"🔗 <b>Earn Per Referral OTP:</b> {SETTINGS_CACHE['ref_reward']:.2f} Tk\n\n"
            f"🚀 <b>Your Referral Link:</b>\n<code>{ref_link}</code>\n\n"
            f"<i>Share this link with friends. When they receive an OTP, you get a bonus automatically!</i>"
        )
        kb = [[InlineKeyboardButton("💳 Withdraw Balance", callback_data="req_withdraw")]]
        await update.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.HTML)
        
    elif text == "🎧 Support":
        user_data['state'] = 'WAITING_FOR_SUPPORT'
        await update.message.reply_text("🎧 <b>SUPPORT SYSTEM</b>\n━━━━━━━━━━━━━━━━━━━━\n<i>Type your problem below.</i>", parse_mode=ParseMode.HTML)
        
    elif state == 'WAITING_FOR_SUPPORT':
        for a_id in ADMIN_IDS:
            try: 
                admin_kb = [[InlineKeyboardButton("💬 Reply", callback_data=f"admrep_{user_id}")]]
                await context.bot.send_message(
                    chat_id=a_id, 
                    text=f"📩 <b>Support Message</b>\n👤 <b>ID:</b> <code>{user_id}</code>\n💬 <b>Msg:</b> {html.escape(text)}", 
                    reply_markup=InlineKeyboardMarkup(admin_kb), parse_mode=ParseMode.HTML
                )
            except: pass
        await update.message.reply_text("✅ <b>Message Sent!</b> An Admin will reply soon.", parse_mode=ParseMode.HTML)
        user_data['state'] = None
        
    elif text == "📊 See Activity":
        kb = [[InlineKeyboardButton("🔥 Range Channel", url="https://t.me/ConsoleXRT")], [InlineKeyboardButton("💬 OTP Channel", url="https://t.me/RTxOtpX")]]
        await update.message.reply_text("📊 <b>BOT ACTIVITY LINKS</b>\n━━━━━━━━━━━━━━━━━━━━\n<i>Join to see live Bot activity:</i>", reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.HTML)
        
    elif state == 'WAITING_FOR_RANGE':
        user_data['state'] = None
        await process_number_generation(update, context, text, is_callback=False)
        
    # --- WITHDRAWAL STATES ---
    elif state == 'WAIT_WITHDRAW_ACC':
        user_data['wd_account'] = text
        user_data['state'] = 'WAIT_WITHDRAW_AMT'
        await update.message.reply_text(f"💳 <b>Enter Amount to Withdraw:</b>\n<i>(Minimum {SETTINGS_CACHE['min_withdraw']} Tk)</i>", parse_mode=ParseMode.HTML)
        
    elif state == 'WAIT_WITHDRAW_AMT':
        try: amount = float(text)
        except: return await update.message.reply_text("⚠️ Invalid amount. Try again.")
        
        if amount < SETTINGS_CACHE['min_withdraw']:
            return await update.message.reply_text(f"⚠️ Minimum withdraw is {SETTINGS_CACHE['min_withdraw']} Tk.")
            
        loop = asyncio.get_event_loop()
        user_info = await loop.run_in_executor(DB_EXECUTOR, sync_get_user_info, user_id)
        if user_info['balance'] < amount:
            user_data['state'] = None
            return await update.message.reply_text("❌ Insufficient balance.", parse_mode=ParseMode.HTML)
            
        method = user_data.get('wd_method', 'Unknown')
        account = user_data.get('wd_account', 'Unknown')
        
        wd_id = await loop.run_in_executor(DB_EXECUTOR, sync_create_withdraw, user_id, amount, method, account)
        
        await update.message.reply_text("✅ <b>Withdrawal Request Sent!</b>\n<i>Please wait for Admin approval.</i>", parse_mode=ParseMode.HTML)
        
        admin_txt = (
            f"💳 <b>NEW WITHDRAW REQUEST</b> 💳\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"👤 <b>User:</b> <code>{user_id}</code>\n"
            f"💰 <b>Amount:</b> {amount} Tk\n"
            f"🏦 <b>Method:</b> {method}\n"
            f"📱 <b>Account:</b> <code>{account}</code>\n"
        )
        kb = [
            [InlineKeyboardButton("✅ Approve", callback_data=f"wd_app_{wd_id}"), InlineKeyboardButton("❌ Reject", callback_data=f"wd_rej_{wd_id}")]
        ]
        for a_id in ADMIN_IDS:
            try: await context.bot.send_message(chat_id=a_id, text=admin_txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.HTML)
            except: pass
            
        user_data['state'] = None
        
    else:
        if user_id not in ADMIN_IDS:
            await show_main_menu(update, context)

# ==============================================================================
# 🎮 BUTTON HANDLER
# ==============================================================================

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await check_ban_middleware(update, context): return
    query = update.callback_query
    user_id = query.from_user.id
    data = query.data
    await ensure_user_fast(user_id)
    
    if data == "check_join":
        if await check_subscription(user_id, context.bot): 
            try: await query.message.delete()
            except: pass
            await show_main_menu(query, context)
        else: await query.answer("⚠️ Please join all channels/groups first.", show_alert=True)
        
    elif data.startswith("cat_"): 
        await handle_category_click(update, context)
        
    elif data.startswith("r_"):
        parts = data.split("_")
        if len(parts) > 2: context.user_data['country_name'] = parts[2]
        await process_number_generation(update, context, parts[1], is_callback=True)
        
    elif data == "change_num":
        if context.user_data.get('range'): await process_number_generation(update, context, context.user_data['range'], is_callback=True)
        else: await query.edit_message_text("⚠️ <b>Session Expired.</b>\n<i>Please start again.</i>", parse_mode=ParseMode.HTML)
            
    elif data == "go_main": 
        await start_category_selection(update, context)
        
    elif data.startswith("admrep_"):
        if user_id not in ADMIN_IDS: return await query.answer("⚠️ Admin only.", show_alert=True)
        target_user_id = data.split("_")[1]
        context.user_data['admin_reply_target'] = target_user_id
        await query.message.reply_text(f"✍️ <b>Type reply for:</b> <code>{target_user_id}</code>\n<i>(Type message normally)</i>", parse_mode=ParseMode.HTML)
        await query.answer()
        
    # --- WITHDRAW FLOW ---
    elif data == "req_withdraw":
        loop = asyncio.get_event_loop()
        u_info = await loop.run_in_executor(DB_EXECUTOR, sync_get_user_info, user_id)
        min_wd = SETTINGS_CACHE["min_withdraw"]
        
        if u_info['balance'] < min_wd:
            return await query.answer(f"⚠️ Minimum withdraw is {min_wd} Tk.", show_alert=True)
            
        kb = [
            [InlineKeyboardButton("Bkash", callback_data="wdm_Bkash")],
            [InlineKeyboardButton("Nagad", callback_data="wdm_Nagad")],
            [InlineKeyboardButton("Mobile Recharge", callback_data="wdm_Mobile_Recharge")]
        ]
        await query.edit_message_text("🏦 <b>Select Withdraw Method:</b>", reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.HTML)
        
    elif data.startswith("wdm_"):
        method = data.replace("wdm_", "").replace("_", " ")
        context.user_data['wd_method'] = method
        context.user_data['state'] = 'WAIT_WITHDRAW_ACC'
        await query.edit_message_text(f"📱 <b>Method: {method}</b>\n\n✍️ <i>Please type your {method} Account Number:</i>", parse_mode=ParseMode.HTML)

    # --- ADMIN WITHDRAWAL APPROVAL ---
    elif data.startswith("wd_app_") or data.startswith("wd_rej_"):
        if user_id not in ADMIN_IDS: return await query.answer("⚠️ Admin only.", show_alert=True)
        
        wd_id = int(data.split("_")[2])
        is_approve = data.startswith("wd_app_")
        status_txt = "approved" if is_approve else "rejected"
        
        loop = asyncio.get_event_loop()
        success, tgt_user, amount = await loop.run_in_executor(DB_EXECUTOR, sync_update_withdraw_status, wd_id, status_txt)
        
        if success:
            await query.edit_message_text(f"✅ <b>Request {status_txt.upper()}!</b> (ID: {wd_id})", parse_mode=ParseMode.HTML)
            try:
                if is_approve:
                    await context.bot.send_message(chat_id=tgt_user, text=f"✅ <b>WITHDRAW APPROVED!</b>\nYour request for {amount} Tk has been successfully processed.", parse_mode=ParseMode.HTML)
                else:
                    await context.bot.send_message(chat_id=tgt_user, text=f"❌ <b>WITHDRAW REJECTED!</b>\nYour request for {amount} Tk was rejected. Balance has been refunded.", parse_mode=ParseMode.HTML)
            except: pass
        else:
            await query.edit_message_text(f"⚠️ Request already processed or not found. (ID: {wd_id})", parse_mode=ParseMode.HTML)


# ==============================================================================
# 👑 FULLY FUNCTIONAL ADMIN KEYBOARD
# ==============================================================================

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS: return
    context.user_data['admin_reply_target'] = None
    context.user_data['state'] = None
    kb = [
        ["📊 Bot Status", "👥 Total Users"],
        ["📢 Broadcast", "🚫 Ban / Unban"],
        ["💰 Set Rewards", "💳 Set Min Withdraw"],
        ["💸 Add Balance", "🏆 Top Referrers"],
        ["🔙 Main Menu"]
    ]
    txt = "🔐 <b>ADVANCED ADMIN PANEL</b> 🔐\n━━━━━━━━━━━━━━━━━━━━\n<i>Use the keyboard below to manage the bot:</i>"
    await update.message.reply_text(txt, reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True), parse_mode=ParseMode.HTML)

# ==============================================================================
# 🌐 RENDER DUMMY WEB SERVER & MAIN LOOP
# ==============================================================================

async def web_server_handler(request):
    return web.Response(text="✅ Premium OTP Bot V33 (Single Server + Auto Withdraw) — Running perfectly!")

async def start_dummy_server():
    try:
        app = web.Application()
        app.router.add_get('/', web_server_handler)
        port = int(os.environ.get('PORT', 8080))
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, '0.0.0.0', port)
        await site.start()
        logger.info(f"🌐 Web server running on port {port}")
    except Exception as e: logger.warning(f"Web server error: {e}")

async def post_init(app: Application):
    asyncio.create_task(start_dummy_server())
    asyncio.create_task(authenticate_stex(force=True))

if __name__ == "__main__":
    init_db()
    app = Application.builder().token(TOKEN).post_init(post_init).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin_panel))
    
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    app.job_queue.run_repeating(global_otp_checker_job,  interval=2,   first=2)
    # Range forwarder: Every 10 Seconds for Maximum Reliability (Fetching top 50 logs)
    app.job_queue.run_repeating(auto_range_forwarder_job, interval=10,  first=15)
    app.job_queue.run_repeating(auto_relogin_job,         interval=300, first=300)
    
    logger.info("✨ VERSION 33.0 FINAL STARTED SUCCESSFULLY ✨")
    app.run_polling(drop_pending_updates=True)
