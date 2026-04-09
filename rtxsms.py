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
import gc
import urllib.parse
from contextlib import contextmanager
import concurrent.futures

# 🔥 UVLOOP FOR EXTREME SPEED
try:
    import uvloop
    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
except ImportError:
    pass

# 🔥 curl_cffi for CF bypass
from curl_cffi.requests import AsyncSession as CurlAsyncSession

from telegram import (
    Update, 
    InlineKeyboardButton, 
    InlineKeyboardMarkup, 
    ReplyKeyboardMarkup, 
    ReplyKeyboardRemove,
    CopyTextButton
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

OTP_GROUP_ID = -1003830374258

S1_EMAIL = "mdrajaislam469@gmail.com"
S1_PASSWORD = "Raja1234@#"
S1_BASE_URL = "https://stexsms.com/mapi/v1"

S2_EMAIL = "rtxraja01@gmail.com"
S2_PASSWORD = "Raja1234"
S2_BASE_URL = "https://sms.acchub.io"

S3_EMAIL = "mdrajaislam469@gmail.com"
S3_STATIC_TOKEN = "ed49e203-6618-45ec-980d-21aaab1cfe45"
S3_BASE_URL = "https://crackerjacksms.com"

def get_cf_headers(origin_domain):
    return {
        "User-Agent": "Mozilla/5.0 (Linux; Android 14; SM-A135F Build/UP1A.231005.007) AppleWebKit/537.36",
        "Accept": "application/json, text/plain, */*",
        "Origin": f"https://{origin_domain}",
        "sec-fetch-site": "same-origin",
        "sec-fetch-mode": "cors",
        "sec-fetch-dest": "empty",
        "Referer": f"https://{origin_domain}/"
    }

API_2FA = "https://2fa.cn/codes/{}"

# ==============================================================================
# 🛑 CACHING & MEMORY
# ==============================================================================

S1_TOKEN = None
S2_TOKEN = None
S3_TOKEN = None

GLOBAL_SESSION = None 
S2_SESSION = None

AUTH_LOCK_S1 = asyncio.Lock() 
AUTH_LOCK_S2 = asyncio.Lock()
AUTH_LOCK_S3 = asyncio.Lock()

LAST_AUTH_S1 = 0
LAST_AUTH_S2 = 0
LAST_AUTH_S3 = 0

LAST_INBOX_S1 = ""
LAST_INBOX_S2 = ""
LAST_INBOX_S3 = ""

START_TIME = datetime.datetime.now()
BASE_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

DB_POOL_SIZE = 15 
DB_EXECUTOR = concurrent.futures.ThreadPoolExecutor(max_workers=15)

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

WAITING_OTPS = {}
NUM_TO_HASH = {}
BATCH_MSGS = {} 
OTP_TIMEOUT_SECONDS = 1200  

USER_CACHE = set()
BANNED_CACHE = set()
USER_INFO_CACHE = {} 
CHANNELS_CACHE = set()

CONSOLE_CACHE = {1: [], 2: []}

SETTINGS_CACHE = {
    "otp_reward": 0.10,
    "ref_reward": 0.05,
    "min_withdraw": 50.0,
    "ping_url": "https://rtxstexsms-qf5h.onrender.com",
    "s1_suffix": "",
    "s2_suffix": " XRT",
    "s3_suffix": " CJ"
}

# Extensive Flag & Code Mapping
COUNTRY_FLAGS = {
    "Afghanistan":"🇦🇫", "Albania":"🇦🇱", "Algeria":"🇩🇿", "Andorra":"🇦🇩", "Angola":"🇦🇴", "Antigua and Barbuda":"🇦🇬", "Argentina":"🇦🇷", "Armenia":"🇦🇲", "Australia":"🇦🇺", "Austria":"🇦🇹", "Azerbaijan":"🇦🇿", "Bahamas":"🇧🇸", "Bahrain":"🇧🇭", "Bangladesh":"🇧🇩", "Barbados":"🇧🇧", "Belarus":"🇧🇾", "Belgium":"🇧🇪", "Belize":"🇧🇿", "Benin":"🇧🇯", "Bhutan":"🇧🇹", "Bolivia":"🇧🇴", "Bosnia and Herzegovina":"🇧🇦", "Botswana":"🇧🇼", "Brazil":"🇧🇷", "Brunei":"🇧🇳", "Bulgaria":"🇧🇬", "Burkina Faso":"🇧🇫", "Burundi":"🇧🇮", "Cabo Verde":"🇨🇻", "Cambodia":"🇰🇭", "Cameroon":"🇨🇲", "Canada":"🇨🇦", "Central African Republic":"🇨🇫", "Central Africa":"🇨🇫", "Chad":"🇹🇩", "Chile":"🇨🇱", "China":"🇨🇳", "Colombia":"🇨🇴", "Comoros":"🇰🇲", "Congo":"🇨🇬", "Democratic Republic of the Congo":"🇨🇩", "Costa Rica":"🇨🇷", "Croatia":"🇭🇷", "Cuba":"🇨🇺", "Cyprus":"🇨🇾", "Czechia":"🇨🇿", "Denmark":"🇩🇰", "Djibouti":"🇩🇯", "Dominica":"🇩🇲", "Dominican Republic":"🇩🇴", "East Timor":"🇹🇱", "Ecuador":"🇪🇨", "Egypt":"🇪🇬", "El Salvador":"🇸🇻", "Equatorial Guinea":"🇬🇶", "Eritrea":"🇪🇷", "Estonia":"🇪🇪", "Eswatini":"🇸🇿", "Ethiopia":"🇪🇹", "Fiji":"🇫🇯", "Finland":"🇫🇮", "France":"🇫🇷", "Gabon":"🇬🇦", "Gambia":"🇬🇲", "Georgia":"🇬🇪", "Germany":"🇩🇪", "Ghana":"🇬🇭", "Greece":"🇬🇷", "Grenada":"🇬🇩", "Guatemala":"🇬🇹", "Guinea":"🇬🇳", "Guinea-Bissau":"🇬🇼", "Guyana":"🇬🇾", "Haiti":"🇭🇹", "Honduras":"🇭🇳", "Hungary":"🇭🇺", "Iceland":"🇮🇸", "India":"🇮🇳", "Indonesia":"🇮🇩", "Iran":"🇮🇷", "Iraq":"🇮🇶", "Ireland":"🇮🇪", "Israel":"🇮🇱", "Italy":"🇮🇹", "Ivory Coast":"🇨🇮", "Jamaica":"🇯🇲", "Japan":"🇯🇵", "Jordan":"🇯🇴", "Kazakhstan":"🇰🇿", "Kenya":"🇰🇪", "Kiribati":"🇰🇮", "Kuwait":"🇰🇼", "Kyrgyzstan":"🇰🇬", "Laos":"🇱🇦", "Latvia":"🇱🇻", "Lebanon":"🇱🇧", "Lesotho":"🇱🇸", "Liberia":"🇱🇷", "Libya":"🇱🇾", "Liechtenstein":"🇱🇮", "Lithuania":"🇱🇹", "Luxembourg":"🇱🇺", "Madagascar":"🇲🇬", "Malawi":"🇲🇼", "Malaysia":"🇲🇾", "Maldives":"🇲🇻", "Mali":"🇲🇱", "Malta":"🇲🇹", "Marshall Islands":"🇲🇭", "Mauritania":"🇲🇷", "Mauritius":"🇲🇺", "Mexico":"🇲🇽", "Micronesia":"🇫🇲", "Moldova":"🇲🇩", "Monaco":"🇲🇨", "Mongolia":"🇲🇳", "Montenegro":"🇲🇪", "Morocco":"🇲🇦", "Mozambique":"🇲🇿", "Myanmar":"🇲🇲", "Namibia":"🇳🇦", "Nauru":"🇳🇷", "Nepal":"🇳🇵", "Netherlands":"🇳🇱", "New Zealand":"🇳🇿", "Nicaragua":"🇳🇮", "Niger":"🇳🇪", "Nigeria":"🇳🇬", "North Korea":"🇰🇵", "North Macedonia":"🇲🇰", "Norway":"🇳🇴", "Oman":"🇴🇲", "Pakistan":"🇵🇰", "Palau":"🇵🇼", "Palestine":"🇵🇸", "Panama":"🇵🇦", "Papua New Guinea":"🇵🇬", "Paraguay":"🇵🇾", "Peru":"🇵🇪", "Philippines":"🇵🇭", "Poland":"🇵🇱", "Portugal":"🇵🇹", "Qatar":"🇶🇦", "Romania":"🇷🇴", "Russia":"🇷🇺", "Rwanda":"🇷🇼", "Saint Kitts and Nevis":"🇰🇳", "Saint Lucia":"🇱🇨", "Saint Vincent and the Grenadines":"🇻🇨", "Samoa":"🇼🇸", "San Marino":"🇸🇲", "Sao Tome and Principe":"🇸🇹", "Saudi Arabia":"🇸🇦", "Senegal":"🇸🇳", "Serbia":"🇷🇸", "Seychelles":"🇸🇨", "Sierra Leone":"🇸🇱", "Singapore":"🇸🇬", "Slovakia":"🇸🇰", "Slovenia":"🇸🇮", "Solomon Islands":"🇸🇧", "Somalia":"🇸🇴", "South Africa":"🇿🇦", "South Korea":"🇰🇷", "South Sudan":"🇸🇸", "Spain":"🇪🇸", "Sri Lanka":"🇱🇰", "Sudan":"🇸🇩", "Suriname":"🇸🇷", "Sweden":"🇸🇪", "Switzerland":"🇨🇭", "Syria":"🇸🇾", "Taiwan":"🇹🇼", "Tajikistan":"🇹🇯", "Tanzania":"🇹🇿", "Thailand":"🇹🇭", "Togo":"🇹🇬", "Tonga":"🇹🇴", "Trinidad and Tobago":"🇹🇹", "Tunisia":"🇹🇳", "Turkey":"🇹🇷", "Turkmenistan":"🇹🇲", "Tuvalu":"🇹🇻", "Uganda":"🇺🇬", "Ukraine":"🇺🇦", "United Arab Emirates":"🇦🇪", "United Kingdom":"🇬🇧", "United States":"🇺🇸", "Uruguay":"🇺🇾", "Uzbekistan":"🇺🇿", "Vanuatu":"🇻🇺", "Venezuela":"🇻🇪", "Vietnam":"🇻🇳", "Yemen":"🇾🇪", "Zambia":"🇿🇲", "Zimbabwe":"🇿🇼"
}

COUNTRY_CODES = {
    "Afghanistan":"AF", "Albania":"AL", "Algeria":"DZ", "Andorra":"AD", "Angola":"AO", "Argentina":"AR", "Armenia":"AM", "Australia":"AU", "Austria":"AT", "Azerbaijan":"AZ", "Bahamas":"BS", "Bahrain":"BH", "Bangladesh":"BD", "Barbados":"BB", "Belarus":"BY", "Belgium":"BE", "Belize":"BZ", "Benin":"BJ", "Bhutan":"BT", "Bolivia":"BO", "Botswana":"BW", "Brazil":"BR", "Brunei":"BN", "Bulgaria":"BG", "Burkina Faso":"BF", "Burundi":"BI", "Cambodia":"KH", "Cameroon":"CM", "Canada":"CA", "Central African Republic":"CF", "Chad":"TD", "Chile":"CL", "China":"CN", "Colombia":"CO", "Comoros":"KM", "Congo":"CG", "Costa Rica":"CR", "Croatia":"HR", "Cuba":"CU", "Cyprus":"CY", "Czechia":"CZ", "Denmark":"DK", "Djibouti":"DJ", "Dominican Republic":"DO", "Ecuador":"EC", "Egypt":"EG", "El Salvador":"SV", "Equatorial Guinea":"GQ", "Eritrea":"ER", "Estonia":"EE", "Eswatini":"SZ", "Ethiopia":"ET", "Fiji":"FJ", "Finland":"FI", "France":"FR", "Gabon":"GA", "Gambia":"GM", "Georgia":"GE", "Germany":"DE", "Ghana":"GH", "Greece":"GR", "Grenada":"GD", "Guatemala":"GT", "Guinea":"GN", "Guinea-Bissau":"GW", "Guyana":"GY", "Haiti":"HT", "Honduras":"HN", "Hungary":"HU", "Iceland":"IS", "India":"IN", "Indonesia":"ID", "Iran":"IR", "Iraq":"IQ", "Ireland":"IE", "Israel":"IL", "Italy":"IT", "Jamaica":"JM", "Japan":"JP", "Jordan":"JO", "Kazakhstan":"KZ", "Kenya":"KE", "Kuwait":"KW", "Kyrgyzstan":"KG", "Laos":"LA", "Latvia":"LV", "Lebanon":"LB", "Lesotho":"LS", "Liberia":"LR", "Libya":"LY", "Lithuania":"LT", "Luxembourg":"LU", "Madagascar":"MG", "Malawi":"MW", "Malaysia":"MY", "Maldives":"MV", "Mali":"ML", "Malta":"MT", "Mauritania":"MR", "Mauritius":"MU", "Mexico":"MX", "Moldova":"MD", "Monaco":"MC", "Mongolia":"MN", "Montenegro":"ME", "Morocco":"MA", "Mozambique":"MZ", "Myanmar":"MM", "Namibia":"NA", "Nepal":"NP", "Netherlands":"NL", "New Zealand":"NZ", "Nicaragua":"NI", "Niger":"NE", "Nigeria":"NG", "North Korea":"KP", "Norway":"NO", "Oman":"OM", "Pakistan":"PK", "Palau":"PW", "Palestine":"PS", "Panama":"PA", "Paraguay":"PY", "Peru":"PE", "Philippines":"PH", "Poland":"PL", "Portugal":"PT", "Qatar":"QA", "Romania":"RO", "Russia":"RU", "Rwanda":"RW", "Saudi Arabia":"SA", "Senegal":"SN", "Serbia":"RS", "Seychelles":"SC", "Sierra Leone":"SL", "Singapore":"SG", "Slovakia":"SK", "Slovenia":"SI", "Somalia":"SO", "South Africa":"ZA", "South Korea":"KR", "South Sudan":"SS", "Spain":"ES", "Sri Lanka":"LK", "Sudan":"SD", "Suriname":"SR", "Sweden":"SE", "Switzerland":"CH", "Syria":"SY", "Taiwan":"TW", "Tajikistan":"TJ", "Tanzania":"TZ", "Thailand":"TH", "Togo":"TG", "Tunisia":"TN", "Turkey":"TR", "Turkmenistan":"TM", "Uganda":"UG", "Ukraine":"UA", "United Arab Emirates":"AE", "United Kingdom":"GB", "United States":"US", "Uruguay":"UY", "Uzbekistan":"UZ", "Vanuatu":"VU", "Venezuela":"VE", "Vietnam":"VN", "Yemen":"YE", "Zambia":"ZM", "Zimbabwe":"ZW"
}

def get_flag(country_name):
    clean_name = str(country_name).replace(SETTINGS_CACHE['s1_suffix'], "").replace(SETTINGS_CACHE['s2_suffix'], "").replace(SETTINGS_CACHE['s3_suffix'], "")
    clean_name = re.sub(r'(?i)\bpostpaid\b', '', clean_name).strip()
    if clean_name in COUNTRY_FLAGS: return COUNTRY_FLAGS[clean_name]
    clean_no_space = clean_name.replace(" ", "").lower()
    for name, flag in COUNTRY_FLAGS.items():
        if name.replace(" ", "").lower() in clean_no_space or clean_no_space in name.replace(" ", "").lower(): 
            return flag
    return "🚩"

def get_short_code(country_name):
    clean_name = str(country_name).replace(SETTINGS_CACHE['s1_suffix'], "").replace(SETTINGS_CACHE['s2_suffix'], "").replace(SETTINGS_CACHE['s3_suffix'], "")
    clean_name = re.sub(r'(?i)\bpostpaid\b', '', clean_name).strip()
    if clean_name in COUNTRY_CODES: return COUNTRY_CODES[clean_name]
    clean_no_space = clean_name.replace(" ", "").lower()
    for name, code in COUNTRY_CODES.items():
        if name.replace(" ", "").lower() in clean_no_space or clean_no_space in name.replace(" ", "").lower(): 
            return code
    return str(clean_name)[:2].upper()

def clean_number(n: str) -> str:
    return re.sub(r'\D', '', str(n))

def mask_number_group(number: str) -> str:
    digits = clean_number(number)
    if len(digits) <= 6: return digits
    first = digits[:2]
    last = digits[-4:]
    middle = 'X' * (len(digits) - 6)
    return first + middle + last

def extract_code(message):
    msg = str(message)
    wa_match = re.search(r'\b(\d{3})-(\d{3})\b', msg)
    if wa_match: return wa_match.group(1) + wa_match.group(2)
    kw = re.search(r'(?:otp|code|verification|verify|pin|passcode|password)[^0-9]{0,25}(\d{4,8})', msg, re.IGNORECASE)
    if kw: return kw.group(1)
    fb = re.search(r'\b(\d{4,8})\b', msg)
    return fb.group(1) if fb else "See Msg"

def get_sms_from_item(item: dict) -> str: return str(item.get('full_sms') or item.get('sms') or item.get('otp') or item.get('message') or item.get('sms_text') or "")
def get_service_from_item(item: dict) -> str: return str(item.get('app_name') or item.get('service_name') or item.get('service') or item.get('provider') or "Service")
def get_number_from_item(item: dict) -> str: return str(item.get('number') or item.get('phone_number') or item.get('phone') or item.get('msisdn') or item.get('did') or "").replace("+", "")

def get_code_from_item(item: dict, raw_msg: str) -> str:
    explicit = item.get('code') or item.get('otps') or item.get('otp_code') or item.get('verification_code') or ""
    if explicit and re.match(r'^\d{4,8}$', str(explicit).strip()): return str(explicit).strip()
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

def get_hash_key(number_str):
    clean_str = re.sub(r'\D', '', str(number_str))
    return clean_str[-8:] if clean_str else "UNKNOWN"

# ==============================================================================
# 🗄️ DATABASE
# ==============================================================================

DB_FILE = "bot_v83_enterprise.db"

class DatabasePool:
    def __init__(self, db_file, pool_size=10):
        self.db_file = db_file
        self.pool_size = pool_size
    @contextmanager
    def get_connection(self):
        conn = sqlite3.connect(self.db_file, timeout=60.0, check_same_thread=False)
        conn.execute('PRAGMA journal_mode=DELETE;') 
        conn.execute('PRAGMA synchronous=NORMAL;')
        conn.execute('PRAGMA temp_store=MEMORY;')
        conn.execute('PRAGMA mmap_size=300000000;') 
        try: yield conn
        finally: conn.close()

db_pool = DatabasePool(DB_FILE, DB_POOL_SIZE)

def init_db():
    global USER_CACHE, BANNED_CACHE, SETTINGS_CACHE, USER_INFO_CACHE, CHANNELS_CACHE
    with db_pool.get_connection() as conn:
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY, join_date TEXT, is_banned INTEGER DEFAULT 0,
            balance REAL DEFAULT 0.0, referrer_id INTEGER DEFAULT NULL, total_referrals INTEGER DEFAULT 0,
            ref_earnings REAL DEFAULT 0.0
        )''')
        
        try: c.execute("ALTER TABLE users ADD COLUMN ref_earnings REAL DEFAULT 0.0")
        except: pass
        
        c.execute('''CREATE TABLE IF NOT EXISTS settings (
            id INTEGER PRIMARY KEY, otp_reward REAL DEFAULT 0.10, ref_reward REAL DEFAULT 0.05, min_withdraw REAL DEFAULT 50.0, 
            ping_url TEXT DEFAULT 'https://rtxstexsms-qf5h.onrender.com',
            s1_suffix TEXT DEFAULT '', s2_suffix TEXT DEFAULT ' XRT', s3_suffix TEXT DEFAULT ' CJ'
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS channels (
            id INTEGER PRIMARY KEY AUTOINCREMENT, channel_username TEXT UNIQUE
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS s3_ranges (
            id INTEGER PRIMARY KEY AUTOINCREMENT, category TEXT, carrier_id TEXT, country_name TEXT
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS withdrawals (
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, amount REAL,
            method TEXT, account TEXT, status TEXT DEFAULT 'pending', date TEXT DEFAULT CURRENT_TIMESTAMP
        )''')
        
        c.execute("SELECT otp_reward, ref_reward, min_withdraw, ping_url, s1_suffix, s2_suffix, s3_suffix FROM settings WHERE id=1")
        settings_row = c.fetchone()
        if not settings_row:
            c.execute("INSERT INTO settings (id, otp_reward, ref_reward, min_withdraw, ping_url, s1_suffix, s2_suffix, s3_suffix) VALUES (1, 0.10, 0.05, 50.0, 'https://rtxstexsms-qf5h.onrender.com', '', ' XRT', ' CJ')")
        else:
            SETTINGS_CACHE["otp_reward"] = settings_row[0]
            SETTINGS_CACHE["ref_reward"] = settings_row[1]
            SETTINGS_CACHE["min_withdraw"] = float(settings_row[2]) if settings_row[2] else 50.0
            SETTINGS_CACHE["ping_url"] = settings_row[3] if settings_row[3] else "https://rtxstexsms-qf5h.onrender.com"
            SETTINGS_CACHE["s1_suffix"] = settings_row[4] if settings_row[4] else ""
            SETTINGS_CACHE["s2_suffix"] = settings_row[5] if settings_row[5] else " XRT"
            SETTINGS_CACHE["s3_suffix"] = settings_row[6] if settings_row[6] else " CJ"
            
        c.execute("SELECT channel_username FROM channels")
        rows = c.fetchall()
        CHANNELS_CACHE.clear()
        if not rows:
            default_channels = ["@EarnXtract", "@RTx_Sms", "@ConsoleXRT", "@RTxOtpX"]
            for ch in default_channels:
                c.execute("INSERT OR IGNORE INTO channels (channel_username) VALUES (?)", (ch,))
                CHANNELS_CACHE.add(ch)
        else:
            for r in rows: CHANNELS_CACHE.add(r[0])
            
        conn.commit()
        
        c.execute("SELECT user_id, is_banned, balance, referrer_id, total_referrals, ref_earnings FROM users")
        USER_CACHE.clear(); BANNED_CACHE.clear(); USER_INFO_CACHE.clear()
        for row in c.fetchall():
            USER_CACHE.add(row[0])
            if row[1] == 1: BANNED_CACHE.add(row[0])
            USER_INFO_CACHE[row[0]] = {"balance": row[2], "referrer_id": row[3], "total_referrals": row[4], "ref_earnings": row[5]}

def sync_register_user_db(user_id, referrer_id=None):
    with db_pool.get_connection() as conn:
        c = conn.cursor()
        c.execute("SELECT user_id FROM users WHERE user_id=?", (user_id,))
        if not c.fetchone():
            c.execute("INSERT INTO users (user_id, join_date, referrer_id) VALUES (?, CURRENT_TIMESTAMP, ?)", (user_id, referrer_id))
            USER_INFO_CACHE[user_id] = {"balance": 0.0, "referrer_id": referrer_id, "total_referrals": 0, "ref_earnings": 0.0}
            if referrer_id: 
                c.execute("UPDATE users SET total_referrals = total_referrals + 1 WHERE user_id=?", (referrer_id,))
                if referrer_id in USER_INFO_CACHE: USER_INFO_CACHE[referrer_id]["total_referrals"] += 1
        conn.commit()

async def ensure_user_fast(user_id, referrer_id=None):
    if user_id not in USER_CACHE:
        USER_CACHE.add(user_id)
        loop = asyncio.get_event_loop()
        loop.run_in_executor(DB_EXECUTOR, sync_register_user_db, user_id, referrer_id)
    return True

def sync_add_channel(username):
    with db_pool.get_connection() as conn:
        c = conn.cursor()
        c.execute("INSERT OR IGNORE INTO channels (channel_username) VALUES (?)", (username,))
        conn.commit()

def sync_del_channel(username):
    with db_pool.get_connection() as conn:
        c = conn.cursor()
        c.execute("DELETE FROM channels WHERE channel_username=?", (username,))
        conn.commit()

def is_user_banned_fast(user_id): return user_id in BANNED_CACHE
def get_total_users_count(): return len(USER_CACHE)

def sync_set_ban_status_db(user_id, status):
    with db_pool.get_connection() as conn:
        c = conn.cursor()
        c.execute("UPDATE users SET is_banned=? WHERE user_id=?", (status, user_id))
        conn.commit()

async def set_ban_status(user_id, status):
    if status == 1: BANNED_CACHE.add(user_id)
    else: BANNED_CACHE.discard(user_id)
    loop = asyncio.get_event_loop()
    loop.run_in_executor(DB_EXECUTOR, sync_set_ban_status_db, user_id, status)

def sync_get_user_info(user_id):
    if user_id in USER_INFO_CACHE: return USER_INFO_CACHE[user_id]
    with db_pool.get_connection() as conn:
        c = conn.cursor()
        c.execute("SELECT balance, total_referrals, referrer_id, ref_earnings FROM users WHERE user_id=?", (user_id,))
        row = c.fetchone()
        if row: 
            data = {"balance": row[0], "total_referrals": row[1], "referrer_id": row[2], "ref_earnings": row[3]}
            USER_INFO_CACHE[user_id] = data
            return data
        return {"balance": 0.0, "total_referrals": 0, "referrer_id": None, "ref_earnings": 0.0}

def sync_add_balance(user_id, amount):
    with db_pool.get_connection() as conn:
        c = conn.cursor()
        c.execute("UPDATE users SET balance = balance + ? WHERE user_id=?", (amount, user_id))
        c.execute("SELECT balance FROM users WHERE user_id=?", (user_id,))
        new_bal = c.fetchone()[0]
        if user_id in USER_INFO_CACHE: USER_INFO_CACHE[user_id]["balance"] = new_bal
        conn.commit()
        return new_bal

def sync_update_setting(key, value):
    with db_pool.get_connection() as conn:
        c = conn.cursor()
        settings_map = {"otp": "otp_reward", "ref": "ref_reward", "min_withdraw": "min_withdraw", "ping_url": "ping_url", "s1_suffix": "s1_suffix", "s2_suffix": "s2_suffix", "s3_suffix": "s3_suffix"}
        if key in settings_map:
            c.execute(f"UPDATE settings SET {settings_map[key]}=? WHERE id=1", (value,))
            SETTINGS_CACHE[settings_map[key]] = value
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
        if user_id in USER_INFO_CACHE: USER_INFO_CACHE[user_id]["balance"] -= amount
        return wid

def sync_update_withdraw_status(wd_id, status):
    with db_pool.get_connection() as conn:
        c = conn.cursor()
        c.execute("SELECT user_id, amount, status FROM withdrawals WHERE id=?", (wd_id,))
        row = c.fetchone()
        if not row or row[2] != 'pending': return False, None, None, None, None
        
        user_id, amount = row[0], row[1]
        c.execute("UPDATE withdrawals SET status=? WHERE id=?", (status, wd_id))
        
        referrer_id = None
        ref_bonus = 0.0
        
        if status == 'rejected':
            c.execute("UPDATE users SET balance = balance + ? WHERE user_id=?", (amount, user_id))
            if user_id in USER_INFO_CACHE: USER_INFO_CACHE[user_id]["balance"] += amount
        elif status == 'approved':
            c.execute("SELECT referrer_id FROM users WHERE user_id=?", (user_id,))
            ref_row = c.fetchone()
            if ref_row and ref_row[0]:
                referrer_id = ref_row[0]
                ref_bonus = amount * 0.10
                c.execute("UPDATE users SET balance = balance + ?, ref_earnings = ref_earnings + ? WHERE user_id=?", (ref_bonus, ref_bonus, referrer_id))
                if referrer_id in USER_INFO_CACHE: 
                    USER_INFO_CACHE[referrer_id]["balance"] += ref_bonus
                    USER_INFO_CACHE[referrer_id]["ref_earnings"] += ref_bonus

        conn.commit()
        return True, user_id, amount, referrer_id, ref_bonus

def sync_add_s3_range(category, carrier_id, country_name):
    with db_pool.get_connection() as conn:
        c = conn.cursor()
        c.execute("INSERT INTO s3_ranges (category, carrier_id, country_name) VALUES (?, ?, ?)", (category, carrier_id, country_name))
        conn.commit()

def sync_get_s3_ranges(category=None):
    with db_pool.get_connection() as conn:
        c = conn.cursor()
        if category: c.execute("SELECT id, category, carrier_id, country_name FROM s3_ranges WHERE LOWER(category) = LOWER(?)", (category,))
        else: c.execute("SELECT id, category, carrier_id, country_name FROM s3_ranges")
        return c.fetchall()

def sync_delete_s3_range(range_id):
    with db_pool.get_connection() as conn:
        c = conn.cursor()
        c.execute("DELETE FROM s3_ranges WHERE id=?", (range_id,))
        conn.commit()

def sync_checkpoint():
    with db_pool.get_connection() as conn:
        conn.execute("PRAGMA wal_checkpoint(TRUNCATE);")

# ==============================================================================
# 🔐 AUTHENTICATION
# ==============================================================================

async def get_session():
    global GLOBAL_SESSION
    if GLOBAL_SESSION is None or GLOBAL_SESSION.closed:
        connector = aiohttp.TCPConnector(limit=1000, keepalive_timeout=600, enable_cleanup_closed=True)
        GLOBAL_SESSION = aiohttp.ClientSession(connector=connector, cookie_jar=aiohttp.CookieJar(unsafe=True))
    return GLOBAL_SESSION

async def parse_response_safely(response):
    try: return await response.json(content_type=None)
    except Exception:
        try: return json.loads(await response.text())
        except Exception: return None

async def auth_s1(force=False):
    global S1_TOKEN, LAST_AUTH_S1
    async with AUTH_LOCK_S1:
        if not force and time.time() - LAST_AUTH_S1 < 300 and S1_TOKEN: return True
        payload = {"email": S1_EMAIL, "password": S1_PASSWORD}
        headers = {
            "User-Agent": BASE_USER_AGENT, "Accept": "application/json, text/plain, */*",
            "Content-Type": "application/json", "Origin": "https://stexsms.com", "Referer": "https://stexsms.com/"
        }
        try:
            session = await get_session()
            async with session.post(f"{S1_BASE_URL}/mauth/login", json=payload, headers=headers, timeout=15, ssl=False) as response:
                if response.status == 200:
                    data = await parse_response_safely(response)
                    if data and str(data.get('meta', {}).get('code')) == '200':
                        S1_TOKEN = data['data']['token']
                        LAST_AUTH_S1 = time.time()
                        return True
        except Exception: pass
        return False

async def s1_api_request(method, url, json_payload=None, return_text=False):
    global S1_TOKEN
    for attempt in range(3):
        try:
            if not S1_TOKEN and not await auth_s1(): continue
            session = await get_session()
            headers = {"User-Agent": BASE_USER_AGENT, "Accept": "application/json", "mauthtoken": str(S1_TOKEN), "Cookie": f"mauthtoken={S1_TOKEN}"}
            timeout = aiohttp.ClientTimeout(total=15)
            if method.upper() == 'GET': response = await session.get(url, headers=headers, timeout=timeout, ssl=False)
            else: response = await session.post(url, json=json_payload, headers=headers, timeout=timeout, ssl=False)
            
            status = response.status
            if status in [401, 403]: S1_TOKEN = None; await asyncio.sleep(0.5); continue
            if status == 200:
                text_response = await response.text()
                if return_text: return 200, text_response
                try: return 200, json.loads(text_response)
                except: return 200, None
            return status, None
        except Exception: pass
    return 500, None

async def get_s2_session():
    global S2_SESSION
    if S2_SESSION is None: S2_SESSION = CurlAsyncSession(impersonate="chrome124")
    return S2_SESSION

async def auth_s2(force=False):
    global S2_TOKEN, LAST_AUTH_S2
    async with AUTH_LOCK_S2:
        if not force and time.time() - LAST_AUTH_S2 < 300 and S2_TOKEN: return True
        payload = {"email": S2_EMAIL, "password": S2_PASSWORD}
        headers = get_cf_headers("acchub.io")
        try:
            session = await get_s2_session()
            response = await session.post(f"{S2_BASE_URL}/auth/login", json=payload, headers=headers, timeout=20)
            if response.status_code in [200, 201]:
                try: data = response.json()
                except Exception: data = None
                if data and 'access_token' in data:
                    S2_TOKEN = data['access_token']
                    LAST_AUTH_S2 = time.time()
                    return True
        except Exception: pass
        return False

async def s2_api_request(method: str, url: str, json_payload=None, return_text=False):
    global S2_TOKEN
    for attempt in range(3):
        try:
            if not S2_TOKEN and not await auth_s2(): continue
            session = await get_s2_session()
            headers = get_cf_headers("acchub.io")
            headers.update({"authorization": f"Bearer {S2_TOKEN}"})
            if method.upper() == 'GET': response = await session.get(url, headers=headers, timeout=20)
            else: response = await session.post(url, json=json_payload, headers=headers, timeout=20)

            status = response.status_code
            if status in [401, 403]: S2_TOKEN = None; await auth_s2(force=True); continue
            if status in [200, 201]:
                if return_text: return 200, response.text
                try: return 200, response.json()
                except: return 200, None
            return status, None
        except Exception: await asyncio.sleep(1)
    return 500, None

async def auth_s3(force=False):
    global S3_TOKEN, LAST_AUTH_S3
    async with AUTH_LOCK_S3:
        if not force and time.time() - LAST_AUTH_S3 < 3600 and S3_TOKEN: return True
        try:
            session = await get_session()
            data = aiohttp.FormData()
            data.add_field('email', S3_EMAIL); data.add_field('auth-token', S3_STATIC_TOKEN)
            headers = {"User-Agent": BASE_USER_AGENT, "Origin": "https://crackerjacksms.com", "Referer": "https://crackerjacksms.com/"}
            async with session.post(f"{S3_BASE_URL}/api/authentication/", data=data, headers=headers, timeout=15, ssl=False) as response:
                if response.status == 200:
                    S3_TOKEN = S3_STATIC_TOKEN 
                    LAST_AUTH_S3 = time.time()
                    return True
        except Exception: pass
        return False

async def s3_api_request(method: str, url: str, json_payload=None, return_text=False):
    global S3_TOKEN
    for attempt in range(3):
        try:
            if not S3_TOKEN and not await auth_s3(): continue
            session = await get_session()
            headers = {"User-Agent": BASE_USER_AGENT, "auth-token": S3_TOKEN, "Origin": "https://crackerjacksms.com"}
            timeout = aiohttp.ClientTimeout(total=15)
            if method.upper() == 'GET': response = await session.get(url, headers=headers, timeout=timeout, ssl=False)
            else: response = await session.post(url, json=json_payload, headers=headers, timeout=timeout, ssl=False)
            
            status = response.status
            if status == 200:
                text_response = await response.text()
                if return_text: return 200, text_response
                try: return 200, json.loads(text_response)
                except: return 200, None
            return status, None
        except Exception: await asyncio.sleep(1)
    return 500, None

async def auto_relogin_job(context: ContextTypes.DEFAULT_TYPE):
    await asyncio.gather(auth_s1(force=True), auth_s2(force=True), auth_s3(force=True), return_exceptions=True)

# ==============================================================================
# 🔒 MIDDLEWARES & UI
# ==============================================================================

async def check_subscription(user_id, bot):
    if not CHANNELS_CACHE: return True
    for channel in CHANNELS_CACHE:
        try:
            member = await bot.get_chat_member(chat_id=channel, user_id=user_id)
            if member.status in ['left', 'kicked']: return False
        except Exception: return False
    return True

async def send_join_prompt(update, context):
    keyboard = []
    row = []
    for i, c in enumerate(CHANNELS_CACHE):
        row.append({"text": f"🔗 Join {i+1}", "url": f"https://t.me/{c.replace('@', '')}", "style": "primary"})
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row: keyboard.append(row)
    keyboard.append([{"text": "✅ Join Done", "callback_data": "check_join", "style": "success"}])
    
    msg = "⛔ <b>You must join our channels to use this bot!</b>"
    reply_markup = {"inline_keyboard": keyboard}
    
    if update.callback_query: await update.callback_query.edit_message_text(text=msg, reply_markup=reply_markup, parse_mode=ParseMode.HTML)
    else: await update.message.reply_text(text=msg, reply_markup=reply_markup, parse_mode=ParseMode.HTML)

async def check_ban_middleware(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if is_user_banned_fast(update.effective_user.id):
        if update.callback_query: await update.callback_query.answer("🚫 You are banned.", show_alert=True)
        else: await update.message.reply_text("🚫 <b>You have been banned.</b>", parse_mode=ParseMode.HTML)
        return True
    return False

async def delete_message_later(bot, chat_id, msg_id, delay_seconds, user_msg_id=None):
    await asyncio.sleep(delay_seconds)
    try: await bot.delete_message(chat_id=chat_id, message_id=msg_id)
    except Exception: pass
    if user_msg_id:
        try: await bot.delete_message(chat_id=chat_id, message_id=user_msg_id)
        except Exception: pass

# ==============================================================================
# 🚀 ULTRA-FAST OTP POLLER & NEW UI INJECTION
# ==============================================================================

async def process_found_otp(context, hash_key, api_num, code_only, svc_name, raw_msg, is_multi=False, display_country_name="Unknown"):
    global WAITING_OTPS, NUM_TO_HASH
    user_data = WAITING_OTPS.get(hash_key)
    if not user_data: return
    
    user_id = user_data['user_id']
    chat_id = user_data['chat_id']
    full_num = user_data['full_num']
    c_name = user_data.get('country_name', display_country_name)
    
    custom_service_name = user_data.get('service_name', svc_name)
    if custom_service_name == 'Auto Matched': custom_service_name = str(svc_name).title()
    
    loop = asyncio.get_event_loop()
    otp_reward = SETTINGS_CACHE["otp_reward"]
    
    user_info_before = await loop.run_in_executor(DB_EXECUTOR, sync_get_user_info, user_id)
    old_bal = user_info_before['balance']
    new_bal = await loop.run_in_executor(DB_EXECUTOR, sync_add_balance, user_id, otp_reward)

    flag = get_flag(c_name)
    short_name = get_short_code(c_name)
    
    svc_name_display = "Facebook" if "facebook" in custom_service_name.lower() else ("Whatsapp" if "whatsapp" in custom_service_name.lower() else custom_service_name.title())
    stylish_svc = "𝐹𝑏" if "facebook" in custom_service_name.lower() else ("𝑊𝑠" if "whatsapp" in custom_service_name.lower() else custom_service_name[:2].title())
    
    # 🌟 NEW OTP LAYOUT (INBOX) 🌟
    user_msg = (
        f"💬 <b>ɴᴇᴡ Oᴛᴘ Rᴇᴄɪᴠᴇᴅ</b>\n"
        f"╭─────────────────╮\n"
        f"│  <b>+{full_num}</b>\n"
        f"╰─────────────────╯\n"
        f"🟢 <b>Sᴇʀᴠɪᴄᴇ » {svc_name_display}</b>\n"
        f"💰 <b>Bᴀʟᴀɴᴄᴇ - {old_bal:.2f} » {new_bal:.2f}</b>"
    )
    
    user_markup = {
        "inline_keyboard": [
            [
                {
                    "text": str(code_only),
                    "copy_text": {"text": str(code_only)},
                    "style": "primary"
                }
            ]
        ]
    }
    
    try: await context.bot.send_message(chat_id=chat_id, text=user_msg, reply_markup=user_markup, parse_mode=ParseMode.HTML)
    except: pass
    
    # 🌟 MASSIVE PREMIUM OTP GROUP FORMAT 🌟
    masked_num = mask_number_group(full_num)
    
    group_msg = (
        f"╭─────────────────╮\n"
        f"│  <b>{flag} #{short_name} » {stylish_svc} {masked_num}</b>\n"
        f"╰─────────────────╯"
    )
    
    group_markup = {
        "inline_keyboard": [
            [
                {
                    "text": str(code_only),
                    "copy_text": {"text": str(code_only)},
                    "style": "primary"
                }
            ],
            [
                {
                    "text": "📢 Main Channel",
                    "url": "https://t.me/EarnXtract",
                    "style": "danger"
                },
                {
                    "text": "🤖 Bot Link",
                    "url": f"https://t.me/{(await context.bot.get_me()).username}",
                    "style": "success"
                }
            ]
        ]
    }
    
    try: await context.bot.send_message(chat_id=OTP_GROUP_ID, text=group_msg, reply_markup=group_markup, parse_mode=ParseMode.HTML)
    except: pass

async def check_inbox(context, server_res, last_text, text_var_name):
    global LAST_INBOX_S1, LAST_INBOX_S2, LAST_INBOX_S3
    if isinstance(server_res, tuple) and server_res[0] == 200 and server_res[1] and server_res[1] != last_text:
        text_data = server_res[1]
        if text_var_name == "s1": LAST_INBOX_S1 = text_data
        elif text_var_name == "s2": LAST_INBOX_S2 = text_data
        elif text_var_name == "s3": LAST_INBOX_S3 = text_data

        try:
            api_res = json.loads(text_data) if isinstance(text_data, str) else text_data
            items = []
            if text_var_name in ["s2", "s3"]: items = api_res.get('data', [])
            else:
                data_field = api_res.get('data', {})
                items = data_field if isinstance(data_field, list) else (data_field.get('numbers') or data_field.get('otps') or [])
            
            for item in items:
                if not isinstance(item, dict): continue
                
                if text_var_name == "s3":
                    if item.get('status') != 'Success' or not item.get('otp'): continue
                    num_raw = str(item.get('did', '')).replace('+', '')
                    raw_msg = str(item.get('otp', ''))
                    svc_name = "Service" 
                else:
                    num_raw = get_number_from_item(item)
                    raw_msg = get_sms_from_item(item)
                    svc_name = get_service_from_item(item)
                    
                if not num_raw or not raw_msg: continue
                
                hash_key, waiter = _find_waiter(num_raw)
                if hash_key:
                    code_val = extract_code(raw_msg) if text_var_name == "s3" else get_code_from_item(item, raw_msg)
                    msg_sig = f"{code_val}_{str(raw_msg)[:15]}"
                    rcv_set = waiter.setdefault('received_codes', set())
                    
                    if msg_sig not in rcv_set:
                        rcv_set.add(msg_sig)
                        is_multi = len(rcv_set) > 1
                        await process_found_otp(context, hash_key, waiter['full_num'], code_val, svc_name, raw_msg, is_multi, waiter.get('country_name', 'Unknown'))
        except Exception: pass

async def global_otp_checker_job(context: ContextTypes.DEFAULT_TYPE):
    global WAITING_OTPS, NUM_TO_HASH
    gc.collect()
    if not WAITING_OTPS: return 
    
    current_time = time.time()
    expired_keys = [hk for hk, d in list(WAITING_OTPS.items()) if current_time - d['time'] > OTP_TIMEOUT_SECONDS]
            
    for h_key in expired_keys:
        u_data = WAITING_OTPS.pop(h_key, None)
        if u_data:
            NUM_TO_HASH.pop(clean_number(u_data['full_num']), None)
            try: await context.bot.delete_message(chat_id=u_data['chat_id'], message_id=u_data['msg_id'])
            except: pass

    if not WAITING_OTPS: return 
        
    date_str = datetime.datetime.now().strftime("%Y-%m-%d")

    s1_task = s1_api_request('GET', f"{S1_BASE_URL}/mdashboard/getnum/info?date={date_str}&page=1", return_text=True)
    s2_task = s2_api_request('GET', f"{S2_BASE_URL}/api/freelancer/get-page/otp-history?page=1&limit=20", return_text=True)
    s3_url = f"{S3_BASE_URL}/api/?page_no=1&filter%5B0%5D%5Bname%5D=status&filter%5B0%5D%5Bvalue%5D=All&filter%5B1%5D%5Bname%5D=length&filter%5B1%5D%5Bvalue%5D=30"
    s3_task = s3_api_request('GET', s3_url, return_text=True)
    
    results = await asyncio.gather(s1_task, s2_task, s3_task, return_exceptions=True)

    await check_inbox(context, results[0], LAST_INBOX_S1, "s1")
    await check_inbox(context, results[1], LAST_INBOX_S2, "s2")
    await check_inbox(context, results[2], LAST_INBOX_S3, "s3")

# ==============================================================================
# 🎯 HIGH-SPEED NUMBER GENERATION
# ==============================================================================

async def _fetch_number_s1(payload): return await s1_api_request('POST', f"{S1_BASE_URL}/mdashboard/getnum/number", json_payload=payload)
async def _fetch_number_s2(payload): return await s2_api_request('POST', f"{S2_BASE_URL}/api/freelancer/get-page/get-number", json_payload=payload)
async def _fetch_number_s3(url): return await s3_api_request('GET', url)

async def safe_delayed_fetch(delay, func, *args, **kwargs):
    if delay > 0: await asyncio.sleep(delay)
    return await func(*args, **kwargs)

async def process_number_generation(update: Update, context: ContextTypes.DEFAULT_TYPE, range_val, server_id, is_callback=True):
    global WAITING_OTPS, NUM_TO_HASH
    
    wait_txt = "<b>⏳ 𝗖𝗼𝗻𝗻𝗲𝗰𝘁𝗶𝗻𝗴... 𝗚𝗲𝗻𝗲𝗿𝗮𝘁𝗶𝗻𝗴 𝗡𝘂𝗺𝗯𝗲𝗿𝘀... 🚀</b>"
    if is_callback:
        user_id = update.callback_query.from_user.id
        chat_id = update.callback_query.message.chat_id
        msg = await update.callback_query.edit_message_text(text=wait_txt, parse_mode=ParseMode.HTML)
    else:
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        msg = await update.message.reply_text(text=wait_txt, parse_mode=ParseMode.HTML)
    
    await asyncio.sleep(0.01)
    
    fetched_numbers = []
    country_name = context.user_data.get('real_country_name', 'Unknown')
    country_name = re.sub(r'(?i)\bpostpaid\b', '', country_name).strip()
    
    raw_svc = str(context.user_data.get('service_name', 'facebook')).lower()
    api_svc = 'facebook' if 'facebook' in raw_svc else 'whatsapp' if 'whatsapp' in raw_svc else 'facebook'

    results = []
    
    if server_id == 1:
        range_val = str(range_val).strip()
        if not range_val.upper().endswith("XXX"): range_val += "XXX"
        payload = {"range": range_val, "app": api_svc, "service": api_svc, "is_national": False, "remove_plus": False}
        tasks = [_fetch_number_s1(payload), safe_delayed_fetch(0.15, _fetch_number_s1, payload), safe_delayed_fetch(0.30, _fetch_number_s1, payload)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
    elif server_id == 2:
        rv = str(range_val).replace('X', '|')
        parts = rv.split('|')
        if len(parts) >= 2:
            payload = {"country_id": int(parts[0]), "mode": "single", "operator_id": int(parts[1]), "number_format": "full", "app": api_svc, "provider": api_svc}
            tasks = [_fetch_number_s2(payload), safe_delayed_fetch(0.15, _fetch_number_s2, payload), safe_delayed_fetch(0.30, _fetch_number_s2, payload)]
            results = await asyncio.gather(*tasks, return_exceptions=True)

    elif server_id == 3:
        url = f"{S3_BASE_URL}/api/sms/?carrier={range_val}&auth-token={S3_TOKEN or S3_STATIC_TOKEN}"
        tasks = [_fetch_number_s3(url), safe_delayed_fetch(0.5, _fetch_number_s3, url), safe_delayed_fetch(1.0, _fetch_number_s3, url)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

    if results:
        for res in results:
            if isinstance(res, tuple):
                status, resp = res
                if status in [200, 201] and isinstance(resp, dict):
                    num = ""
                    if server_id == 2 and resp.get('status') in ['success', 200, True]:
                        data_obj = resp.get('data', {})
                        if isinstance(data_obj, dict): num = str(data_obj.get('phone_number') or data_obj.get('number', ''))
                        elif isinstance(data_obj, list) and len(data_obj) > 0: num = str(data_obj[0].get('phone_number') or data_obj[0].get('number', ''))
                            
                    elif server_id == 3 and str(resp.get('meta')) == '200':
                        data_obj = resp.get('data', {})
                        if isinstance(data_obj, dict): num = str(data_obj.get('did', ''))
                            
                    elif 'data' in resp and isinstance(resp['data'], dict) and resp['data'].get('number'):
                        num = str(resp['data']['number'])
                        if country_name == "Unknown": country_name = resp['data'].get('country', country_name)
                        country_name = re.sub(r'(?i)\bpostpaid\b', '', country_name).strip()
                    
                    if num and num != "None": 
                        clean_n = num.replace('+', '')
                        if clean_n not in fetched_numbers: 
                            fetched_numbers.append(clean_n)
                            if len(fetched_numbers) == 2: break
            elif isinstance(res, Exception): logger.error(f"API Error in fetch task: {res}")
            
    if fetched_numbers:
        s_suffix = ""
        if server_id == 1: s_suffix = SETTINGS_CACHE['s1_suffix']
        elif server_id == 2: s_suffix = SETTINGS_CACHE['s2_suffix']
        elif server_id == 3: s_suffix = SETTINGS_CACHE['s3_suffix']
        
        display_country_name = f"{country_name}{s_suffix}".strip()
        flag = get_flag(country_name)
        custom_svc = context.user_data.get('service_name', api_svc.title())
        
        txt = (
            f"<b>{flag} {display_country_name} Number Assigned:</b>\n"
            f"╭─────────────────╮\n"
            f"│  ⏳ <b>Waiting for OTP...</b>\n"
            f"╰─────────────────╯"
        )
        
        num_kb = {"inline_keyboard": []}
        for n in fetched_numbers:
            num_kb["inline_keyboard"].append([{"text": f"⎘ +{n}", "copy_text": {"text": str(n)}, "style": "primary"}])
            
        num_kb["inline_keyboard"].append([{"text": "🔄 Change Number", "callback_data": "change_num", "style": "danger"}])
        num_kb["inline_keyboard"].append([{"text": "🌍 Change Country", "callback_data": "go_cat", "style": "primary"}])
        num_kb["inline_keyboard"].append([{"text": "🗝️ Get OTP", "url": "https://t.me/RTxOtpX", "style": "success"}])
        
        try: await msg.edit_text(text=txt, reply_markup=num_kb, parse_mode=ParseMode.HTML)
        except Exception: pass
        
        for n in fetched_numbers:
            hash_key = get_hash_key(n)
            WAITING_OTPS[hash_key] = {
                'full_num': n, 'user_id': user_id, 'chat_id': chat_id, 'msg_id': msg.message_id, 
                'time': time.time(), 'received_codes': set(), 
                'range': range_val, 'server_id': server_id, 'service_name': custom_svc, 'country_name': display_country_name
            }
            NUM_TO_HASH[clean_number(n)] = hash_key
            
        context.user_data['range'] = range_val 
        context.user_data['server'] = server_id
        
    else:
        err_msg = "🔄 <i>Our high-speed servers are balancing the load. No numbers found right now.</i>"
        btn_back = {"inline_keyboard": [[{"text": "🔙 Back", "callback_data": "go_cat", "style": "danger"}]]}
        try:
            await msg.edit_text(
                text=f"📡 <b>𝗦𝗲𝗿𝘃𝗲𝗿 𝗢𝗽𝘁𝗶𝗺𝗶𝘇𝗶𝗻𝗴:</b>\n{err_msg}\n\nPlease try again.", 
                reply_markup=btn_back, parse_mode=ParseMode.HTML
            )
        except Exception: pass

# ==============================================================================
# 📋 MENUS & UI
# ==============================================================================

async def show_live_traffic(update, context):
    logs = CONSOLE_CACHE[1] + CONSOLE_CACHE[2]
    if not logs:
        return await update.message.reply_text("<b>⏳ Processing live traffic data. Please try again soon.</b>", parse_mode=ParseMode.HTML)
        
    counts = {}
    for log in logs:
        if isinstance(log, dict):
            c = log.get('country_name') or log.get('country') or 'Unknown'
            c = re.sub(r'(?i)\bpostpaid\b', '', c).strip()
            app = log.get('provider') or log.get('app_name') or log.get('service') or 'Unknown'
            app = str(app).title()
            
            if 'Facebook' in app: app = 'Facebook'
            elif 'Whatsapp' in app: app = 'WhatsApp'
            
            if app in ['Facebook', 'WhatsApp'] and c != 'Unknown':
                counts[(app, c)] = counts.get((app, c), 0) + 1
                
    total = sum(counts.values())
    if total == 0:
        return await update.message.reply_text("<b>⏳ No Facebook/WhatsApp live traffic currently recorded.</b>", parse_mode=ParseMode.HTML)
        
    sorted_traffic = sorted(counts.items(), key=lambda x: x[1], reverse=True)[:15]
    
    txt = "📁 <b>LIVE-STOCK STATUS</b>\n\n"
    for (app, c), count in sorted_traffic:
        flag = get_flag(c)
        pct = (count / total) * 100
        icon = "𒊹︎" if app == 'Facebook' else "💌"
        txt += f"• {icon} <b>{app}</b> | {flag} <b>{c}</b> - <b>{pct:.1f}%</b>\n"
        
    await update.message.reply_text(txt, parse_mode=ParseMode.HTML)

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
    
    if not await check_subscription(user_id, context.bot): await send_join_prompt(update, context)
    else: await show_main_menu(update, context)

async def show_main_menu(update_obj, context):
    kb = [
        ["📱 GET NUMBER", "📊 LIVE TRAFFIC"], 
        ["💳 BALANCE", "🎁 REFER"],
        ["🎧 LIVE SUPPORT"]
    ]
    msg = f"👋 <b>Wᴇᴄʟᴏᴍᴇ {html.escape(update_obj.effective_user.full_name)} Tᴏ Oᴜʀ ʙᴏᴛ</b>\n<b>Sᴇʟᴇᴄᴛ Aɴ Oᴘᴛɪᴏɴ Fᴏʀ ᴄᴏɴᴛɪɴᴜᴇ </b>"
    
    if hasattr(update_obj, 'message') and update_obj.message: 
        await update_obj.message.reply_text(msg, reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True), parse_mode=ParseMode.HTML)
    elif hasattr(update_obj, 'callback_query') and update_obj.callback_query:
        try: await update_obj.callback_query.message.delete()
        except: pass
        await context.bot.send_message(chat_id=update_obj.effective_chat.id, text=msg, reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True), parse_mode=ParseMode.HTML)

async def cmd_2fa(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['state'] = 'WAITING_FOR_2FA'
    await update.message.reply_text("🔐 <b>2FA CODE GENERATOR</b>\n━━━━━━━━━━━━━━━━━━━━\n<i>Paste your Secret Key below:</i>", parse_mode=ParseMode.HTML)

async def start_category_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cat_kb = {
        "inline_keyboard": [
            [{"text": "⚙️Fᴀᴄᴇʙᴏᴏᴋ", "callback_data": "cat_facebook", "style": "primary"}],
            [{"text": "Wʜᴀᴛsᴀᴘᴘ 𒊹︎︎", "callback_data": "cat_whatsapp", "style": "success"}],
            [{"text": "🔙 Mᴀɪɴ Mᴇɴᴜ ", "callback_data": "go_main", "style": "danger"}]
        ]
    }
    txt = "<b>Sᴇʟᴇᴄᴛ Yᴏᴜ ᴄᴀᴛᴀɢᴏʀʏ </b>"
    
    if update and hasattr(update, 'callback_query') and update.callback_query: 
        await update.callback_query.edit_message_text(text=txt, reply_markup=cat_kb, parse_mode=ParseMode.HTML)
    else: 
        if update and hasattr(update, 'message') and update.message:
            await update.message.reply_text(text=txt, reply_markup=cat_kb, parse_mode=ParseMode.HTML)

async def handle_category_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global CONSOLE_CACHE
    query = update.callback_query
    category = query.data.split('_')[1].lower()
    context.user_data['service_name'] = category.title()
    
    await query.edit_message_text(text="<b>⚡ 𝗖𝗮𝗹𝗰𝘂𝗹𝗮𝘁𝗶𝗻𝗴 𝗟𝗶𝘃𝗲 𝗦𝘂𝗰𝗰𝗲𝘀𝘀 𝗥𝗮𝘁𝗲...</b>", parse_mode=ParseMode.HTML)
    await asyncio.sleep(0.01)
    
    country_stats = {}
    
    def process_logs(logs, srv_id):
        if not logs: return
        for log in logs:
            if isinstance(log, dict):
                if srv_id == 2:
                    c = log.get('country_name', 'Unknown')
                    r = f"{log.get('country_id')}|{log.get('operator_id')}"
                    app_name = str(log.get('provider', '')).lower()
                else:
                    c = log.get('country', 'Unknown')
                    r = log.get('range')
                    app_name = str(log.get('app_name', '')).lower()

                c = re.sub(r'(?i)\bpostpaid\b', '', c).strip()

                if category in app_name and c and r and 'None' not in r:
                    key = (srv_id, c)
                    if key not in country_stats: country_stats[key] = {'range': r, 'count': 0, 'c_name': c}
                    country_stats[key]['count'] += 1

    process_logs(CONSOLE_CACHE[1], 1)
    process_logs(CONSOLE_CACHE[2], 2)

    loop = asyncio.get_event_loop()
    s3_ranges = await loop.run_in_executor(DB_EXECUTOR, sync_get_s3_ranges, category)
    for s3r in s3_ranges:
        r_id, r_cat, carrier_id, c_name = s3r
        c_name = re.sub(r'(?i)\bpostpaid\b', '', c_name).strip()
        key = (3, c_name)
        if key not in country_stats: country_stats[key] = {'range': carrier_id, 'count': 100, 'c_name': c_name}

    if not country_stats:
        btn_kb = {"inline_keyboard": [[{"text": "🔙 Back", "callback_data": "go_cat", "style": "danger"}]]}
        await query.edit_message_text(
            text=f"𝗡𝗼 𝗡𝘂𝗺𝗯𝗲𝗿 𝗙𝗶𝗻𝗱 𝗥𝗶𝗴𝗵𝘁 𝗡𝗼𝘄 𝗙𝗼𝗿 𝗧𝗵𝗶𝘀 𝗖𝗮𝘁𝗮𝗴𝗼𝗿𝘆 💣", 
            reply_markup=btn_kb, parse_mode=ParseMode.HTML
        )
        return
        
    sorted_keys = sorted(country_stats.keys(), key=lambda x: x[0])
    
    kb = []
    s1_suffix = SETTINGS_CACHE['s1_suffix']
    s2_suffix = SETTINGS_CACHE['s2_suffix']
    s3_suffix = SETTINGS_CACHE['s3_suffix']
    
    for key in sorted_keys:
        srv_id, c_name = key
        stats = country_stats[key]
        
        display_name = c_name
        if srv_id == 1: display_name += s1_suffix
        elif srv_id == 2: display_name += s2_suffix
        elif srv_id == 3: display_name += s3_suffix
            
        btn_text = f"{get_flag(c_name)} {display_name}"
        safe_c_name = str(c_name)[:15].replace(" ", "")
        
        kb.append([{"text": btn_text, "callback_data": f"r_{srv_id}_{stats['range']}_{safe_c_name}", "style": "primary"}])
        
    kb.append([{"text": "🔙 Back", "callback_data": "go_cat", "style": "danger"}])
    
    await query.edit_message_text(
        text=f"🌍 <b> Sᴇʟᴇᴄᴛ A Cᴏᴜɴᴛʀʏ Fᴏʀ {category.title()}</b>", 
        reply_markup={"inline_keyboard": kb}, parse_mode=ParseMode.HTML
    )

# ==============================================================================
# 🎮 TEXT HANDLER & ADMIN LOGIC
# ==============================================================================

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await check_ban_middleware(update, context): return
    user_id = update.effective_user.id
    raw_text = update.message.text
    if not raw_text: return
    text = raw_text.strip()
    
    user_data = context.user_data
    await ensure_user_fast(user_id)
    
    menu_actions = ["📱 GET NUMBER", "📊 LIVE TRAFFIC", "💳 BALANCE", "🎁 REFER", "🎧 LIVE SUPPORT"]
    admin_actions = ["Bot Status", "𝗕𝗼𝘁 𝗦𝘁𝗮𝘁𝘂𝘀", "Total Users", "𝗧𝗼𝘁𝗮𝗹 𝗨𝘀𝗲𝗿𝘀", "Broadcast", "𝗕𝗿𝗼𝗮𝗱𝗰𝗮𝘀𝘁", "Ban / Unban", "𝗕𝗮𝗻 / 𝗨𝗻𝗯𝗮𝗻", "Set Rewards", "𝗦𝗲𝘁 𝗥𝗲𝘄𝗮𝗿𝗱𝘀", "Set Min Withdraw", "𝗦𝗲𝘁 𝗠𝗶𝗻 𝗪𝗶𝘁𝗵𝗱𝗿𝗮𝘄", "Add Balance", "𝗔𝗱𝗱 𝗕𝗮𝗹𝗮𝗻𝗰𝗲", "Top Referrers", "𝗧𝗼𝗽 𝗥𝗲𝗳𝗲𝗿𝗿𝗲𝗿𝘀", "Set Ping URL", "𝗦𝗲𝘁 𝗣𝗶𝗻𝗴 𝗨𝗥𝗟", "Set Suffix S1", "𝗦𝗲𝘁 𝗦𝘂𝗳𝗳𝗶𝘅 𝗦𝟭", "Set Suffix S2", "𝗦𝗲𝘁 𝗦𝘂𝗳𝗳𝗶𝘅 𝗦𝟮", "Set Suffix S3", "𝗦𝗲𝘁 𝗦𝘂𝗳𝗳𝗶𝘅 𝗦𝟯", "➕ 𝗔𝗱𝗱 𝗦𝟯 𝗥𝗮𝗻𝗴𝗲", "🗑️ 𝗗𝗲𝗹 𝗦𝟯 𝗥𝗮𝗻𝗴𝗲", "Main Menu", "𝗠𝗮𝗶𝗻 𝗠𝗲𝗻𝘂", "➕ 𝗔𝗱𝗱 𝗖𝗵𝗮𝗻𝗻𝗲𝗹", "🗑️ 𝗗𝗲𝗹 𝗖𝗵𝗮𝗻𝗻𝗲𝗹"]
    
    is_main_menu_action = any(btn == text for btn in menu_actions)
    is_admin_action = any(btn in text for btn in admin_actions)
    
    if is_main_menu_action or is_admin_action:
        user_data['state'] = None
        user_data['admin_reply_target'] = None
        
    if user_id in ADMIN_IDS:
        if "𝗕𝗼𝘁 𝗦𝘁𝗮𝘁𝘂𝘀" in text or "Bot Status" in text:
            uptime = datetime.datetime.now() - START_TIME
            txt = (
                f"📊 <b>𝗨𝗟𝗧𝗥𝗔 𝗘𝗡𝗧𝗘𝗥𝗣𝗥𝗜𝗦𝗘 𝗦𝗧𝗔𝗧𝗨𝗦</b> 📊\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"⏱ <b>𝗨𝗽𝘁𝗶𝗺𝗲:</b> {str(uptime).split('.')[0]}\n"
                f"👥 <b>𝗧𝗼𝘁𝗮𝗹 𝗨𝘀𝗲𝗿𝘀:</b> {get_total_users_count()}\n"
                f"📡 <b>𝗔𝗰𝘁𝗶𝘃𝗲 𝗪𝗮𝗶𝘁𝗲𝗿𝘀:</b> {len(WAITING_OTPS)} Numbers\n"
                f"💰 <b>𝗢𝗧𝗣 𝗥𝗲𝘄𝗮𝗿𝗱:</b> {SETTINGS_CACHE['otp_reward']} ৳\n"
                f"💳 <b>𝗠𝗶𝗻 𝗪𝗶𝘁𝗵𝗱𝗿𝗮𝘄:</b> {SETTINGS_CACHE['min_withdraw']} ৳\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"✅ <i>𝗧𝗥𝗜𝗣𝗟𝗘 𝗦𝗲𝗿𝘃𝗲𝗿𝘀 𝗥𝘂𝗻𝗻𝗶𝗻𝗴 𝗣𝗲𝗿𝗳𝗲𝗰𝘁𝗹𝘆</i>"
            )
            return await update.message.reply_text(txt, parse_mode=ParseMode.HTML)
            
        elif "𝗧𝗼𝘁𝗮𝗹 𝗨𝘀𝗲𝗿𝘀" in text or "Total Users" in text:
            return await update.message.reply_text(f"👥 <b>𝗧𝗼𝘁𝗮𝗹 𝗥𝗲𝗴𝗶𝘀𝘁𝗲𝗿𝗲𝗱 𝗨𝘀𝗲𝗿𝘀:</b> {get_total_users_count()}", parse_mode=ParseMode.HTML)
            
        elif "𝗕𝗿𝗼𝗮𝗱𝗰𝗮𝘀𝘁" in text or "Broadcast" in text:
            user_data['state'] = 'ADMIN_BROADCAST'
            return await update.message.reply_text("📢 <b>𝗦𝗲𝗻𝗱 𝘁𝗵𝗲 𝗺𝗲𝘀𝘀𝗮𝗴𝗲 𝘆𝗼𝘂 𝘄𝗮𝗻𝘁 𝘁𝗼 𝗯𝗿𝗼𝗮𝗱𝗰𝗮𝘀𝘁.</b>", parse_mode=ParseMode.HTML)
            
        elif "𝗕𝗮𝗻 / 𝗨𝗻𝗯𝗮𝗻" in text or "Ban / Unban" in text:
            user_data['state'] = 'ADMIN_BAN'
            return await update.message.reply_text("🚫 <b>𝗦𝗲𝗻𝗱 𝗨𝘀𝗲𝗿 𝗜𝗗 𝗮𝗻𝗱 𝗮𝗰𝘁𝗶𝗼𝗻 (𝗯𝗮𝗻/𝘂𝗻𝗯𝗮𝗻).</b>\nExample: <code>12345678 ban</code>", parse_mode=ParseMode.HTML)
            
        elif "𝗦𝗲𝘁 𝗥𝗲𝘄𝗮𝗿𝗱𝘀" in text or "Set Rewards" in text:
            user_data['state'] = 'ADMIN_REWARD'
            return await update.message.reply_text("💰 <b>𝗦𝗲𝘁 𝗥𝗲𝘄𝗮𝗿𝗱.</b>\nExample: <code>otp 0.5</code>", parse_mode=ParseMode.HTML)
            
        elif "𝗦𝗲𝘁 𝗠𝗶𝗻 𝗪𝗶𝘁𝗵𝗱𝗿𝗮𝘄" in text or "Set Min Withdraw" in text:
            user_data['state'] = 'ADMIN_MIN_WD'
            return await update.message.reply_text("💳 <b>𝗦𝗲𝘁 𝗠𝗶𝗻𝗶𝗺𝘂𝗺 𝗪𝗶𝘁𝗵𝗱𝗿𝗮𝘄 𝗔𝗺𝗼𝘂𝗻𝘁.</b>\nExample: <code>100</code>", parse_mode=ParseMode.HTML)
            
        elif "𝗔𝗱𝗱 𝗕𝗮𝗹𝗮𝗻𝗰𝗲" in text or "Add Balance" in text:
            user_data['state'] = 'ADMIN_ADD_BAL'
            return await update.message.reply_text("💸 <b>𝗔𝗱𝗱 𝗯𝗮𝗹𝗮𝗻𝗰𝗲 𝘁𝗼 𝘂𝘀𝗲𝗿.</b>\nExample: <code>12345678 50.0</code>", parse_mode=ParseMode.HTML)

        elif "𝗦𝗲𝘁 𝗣𝗶𝗻𝗴 𝗨𝗥𝗟" in text or "Set Ping URL" in text:
            user_data['state'] = 'ADMIN_SET_PING'
            return await update.message.reply_text("🌐 <b>𝗦𝗲𝗻𝗱 𝘁𝗵𝗲 𝗨𝗥𝗟 𝗳𝗼𝗿 𝗔𝘂𝘁𝗼-𝗣𝗶𝗻𝗴.</b>", parse_mode=ParseMode.HTML)
            
        elif "𝗦𝗲𝘁 𝗦𝘂𝗳𝗳𝗶𝘅" in text or "Set Suffix" in text:
            if "S1" in text or "𝗦𝟭" in text: user_data['state'] = 'ADMIN_SET_S1_SUFFIX'
            elif "S2" in text or "𝗦𝟮" in text: user_data['state'] = 'ADMIN_SET_S2_SUFFIX'
            elif "S3" in text or "𝗦𝟯" in text: user_data['state'] = 'ADMIN_SET_S3_SUFFIX'
            return await update.message.reply_text("✏️ <b>𝗦𝗲𝗻𝗱 𝘀𝘂𝗳𝗳𝗶𝘅.</b>\n(Send `-` to keep it blank)", parse_mode=ParseMode.HTML)
            
        elif "➕ 𝗔𝗱𝗱 𝗦𝟯 𝗥𝗮𝗻𝗴𝗲" in text:
            user_data['state'] = 'ADMIN_S3_ADD_CAT'
            return await update.message.reply_text("➕ <b>𝗔𝗱𝗱 𝗦𝟯 𝗥𝗮𝗻𝗴𝗲</b>\nSend Category (<code>facebook</code> or <code>whatsapp</code>):", parse_mode=ParseMode.HTML)
            
        elif "🗑️ 𝗗𝗲𝗹 𝗦𝟯 𝗥𝗮𝗻𝗴𝗲" in text:
            loop = asyncio.get_event_loop()
            ranges = await loop.run_in_executor(DB_EXECUTOR, sync_get_s3_ranges, None)
            if not ranges: return await update.message.reply_text("📭 <i>No S3 Ranges found.</i>", parse_mode=ParseMode.HTML)
            kb = [[InlineKeyboardButton(f"❌ {r[1].title()} | {r[3]} ({r[2]})", callback_data=f"dels3_{r[0]}")] for r in ranges]
            return await update.message.reply_text("🗑️ <b>𝗖𝗹𝗶𝗰𝗸 𝗮 𝗿𝗮𝗻𝗴𝗲 𝗯𝗲𝗹𝗼𝘄 𝘁𝗼 𝗱𝗲𝗹𝗲𝘁𝗲 𝗶𝘁:</b>", reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.HTML)

        elif "➕ 𝗔𝗱𝗱 𝗖𝗵𝗮𝗻𝗻𝗲𝗹" in text:
            user_data['state'] = 'ADMIN_ADD_CHANNEL'
            return await update.message.reply_text("➕ <b>𝗦𝗲𝗻𝗱 𝗖𝗵𝗮𝗻𝗻𝗲𝗹 𝗨𝘀𝗲𝗿𝗻𝗮𝗺𝗲.</b>\nExample: `@RTx_Sms`", parse_mode=ParseMode.HTML)

        elif "🗑️ 𝗗𝗲𝗹 𝗖𝗵𝗮𝗻𝗻𝗲𝗹" in text:
            if not CHANNELS_CACHE: return await update.message.reply_text("📭 <i>No channels found.</i>", parse_mode=ParseMode.HTML)
            kb = [[InlineKeyboardButton(f"❌ {ch}", callback_data=f"delch_{ch}")] for ch in CHANNELS_CACHE]
            return await update.message.reply_text("🗑️ <b>𝗖𝗹𝗶𝗰𝗸 𝗮 𝗰𝗵𝗮𝗻𝗻𝗲𝗹 𝘁𝗼 𝗿𝗲𝗺𝗼𝘃𝗲:</b>", reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.HTML)

        elif "𝗧𝗼𝗽 𝗥𝗲𝗳𝗲𝗿𝗿𝗲𝗿𝘀" in text or "Top Referrers" in text:
            loop = asyncio.get_event_loop()
            top_users = await loop.run_in_executor(DB_EXECUTOR, sync_get_top_referrers)
            msg = "🏆 <b>𝗧𝗢𝗣 𝟭𝟬 𝗥𝗘𝗙𝗘𝗥𝗥𝗘𝗥𝗦</b> 🏆\n━━━━━━━━━━━━━━━━━━━━\n"
            for i, (uid, count) in enumerate(top_users):
                if count > 0: msg += f"<b>{i+1}.</b> <code>{uid}</code> - <b>{count}</b> Referrals\n"
            if "1." not in msg: msg += "<i>No active referrers yet.</i>"
            return await update.message.reply_text(msg, parse_mode=ParseMode.HTML)
            
        elif "𝗠𝗮𝗶𝗻 𝗠𝗲𝗻𝘂" in text or "Main Menu" in text:
            await show_main_menu(update, context)
            return

        state = user_data.get('state')
        if state == 'ADMIN_BROADCAST':
            users = list(USER_CACHE)
            msg = await update.message.reply_text(f"⏳ <i>Broadcasting to {len(users)} users...</i>", parse_mode=ParseMode.HTML)
            success, failed = 0, 0
            for u_id in users:
                try:
                    await context.bot.send_message(chat_id=u_id, text=f"📢 <b>𝗔𝗗𝗠𝗜𝗡 𝗕𝗥𝗢𝗔𝗗𝗖𝗔𝗦𝗧</b>\n━━━━━━━━━━━━━━━━━━━━\n{text}", parse_mode=ParseMode.HTML)
                    success += 1
                except: failed += 1
                await asyncio.sleep(0.05) 
            await msg.edit_text(f"✅ <b>𝗕𝗿𝗼𝗮𝗱𝗰𝗮𝘀𝘁 𝗖𝗼𝗺plete𝗱!</b>\n🟢 Delivered: {success}\n🔴 Failed: {failed}", parse_mode=ParseMode.HTML)
            user_data['state'] = None
            return
            
        elif state == 'ADMIN_ADD_CHANNEL':
            ch = text.strip()
            if not ch.startswith("@"): ch = "@" + ch
            CHANNELS_CACHE.add(ch)
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(DB_EXECUTOR, sync_add_channel, ch)
            await update.message.reply_text(f"✅ <b>𝗖𝗵𝗮𝗻𝗻𝗲𝗹 {ch} 𝗔𝗱𝗱𝗲𝗱 𝗦𝘂𝗰𝗰𝗲𝘀𝘀𝗳𝘂𝗹𝗹𝘆!</b>", parse_mode=ParseMode.HTML)
            user_data['state'] = None
            return
            
        elif state == 'ADMIN_BAN':
            try:
                parts = text.split(); uid, action = int(parts[0]), parts[1].lower()
                await set_ban_status(uid, 1 if action == 'ban' else 0)
                await update.message.reply_text(f"✅ User <code>{uid}</code> has been <b>{action.upper()}NED</b>.", parse_mode=ParseMode.HTML)
            except: await update.message.reply_text("⚠️ Invalid format.")
            user_data['state'] = None
            return
            
        elif state == 'ADMIN_REWARD':
            try:
                parts = text.split(); r_type, amount = parts[0].lower(), float(parts[1])
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(DB_EXECUTOR, sync_update_setting, r_type, amount)
                await update.message.reply_text(f"✅ {r_type.upper()} reward updated to <b>{amount:.2f} ৳</b>.", parse_mode=ParseMode.HTML)
            except: await update.message.reply_text("⚠️ Invalid format.")
            user_data['state'] = None
            return
            
        elif state == 'ADMIN_MIN_WD':
            try:
                amount = float(text)
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(DB_EXECUTOR, sync_update_setting, "min_withdraw", amount)
                await update.message.reply_text(f"✅ Min Withdraw updated to <b>{amount:.2f} ৳</b>.", parse_mode=ParseMode.HTML)
            except: await update.message.reply_text("⚠️ Invalid format.")
            user_data['state'] = None
            return
            
        elif state == 'ADMIN_ADD_BAL':
            try:
                parts = text.split(); uid, amount = int(parts[0]), float(parts[1])
                loop = asyncio.get_event_loop()
                new_bal = await loop.run_in_executor(DB_EXECUTOR, sync_add_balance, uid, amount)
                await update.message.reply_text(f"✅ Added <b>{amount} ৳</b> to <code>{uid}</code>.\nNew Balance: <b>{new_bal:.2f} ৳</b>", parse_mode=ParseMode.HTML)
                try: await context.bot.send_message(chat_id=uid, text=f"💰 <b>𝗔𝗱𝗺𝗶𝗻 𝗔𝗱𝗱𝗲𝗱 𝗕𝗮𝗹𝗮𝗻𝗰𝗲!</b>\n+{amount:.2f} ৳ has been added.", parse_mode=ParseMode.HTML)
                except: pass
            except: await update.message.reply_text("⚠️ Invalid format.")
            user_data['state'] = None
            return

        elif state == 'ADMIN_SET_PING':
            new_url = text.strip()
            if not new_url.startswith("http"): new_url = "https://" + new_url
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(DB_EXECUTOR, sync_update_setting, "ping_url", new_url)
            await update.message.reply_text(f"✅ <b>𝗔𝘂𝘁𝗼-𝗣𝗶𝗻𝗴 𝗨𝗥𝗟 𝘂𝗽𝗱𝗮𝘁𝗲𝗱 𝘁𝗼:</b>\n<code>{new_url}</code>", parse_mode=ParseMode.HTML)
            user_data['state'] = None; return
            
        elif state in ['ADMIN_SET_S1_SUFFIX', 'ADMIN_SET_S2_SUFFIX', 'ADMIN_SET_S3_SUFFIX']:
            val = text if text != "-" else ""
            key = "s1_suffix" if state == 'ADMIN_SET_S1_SUFFIX' else ("s2_suffix" if state == 'ADMIN_SET_S2_SUFFIX' else "s3_suffix")
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(DB_EXECUTOR, sync_update_setting, key, val)
            await update.message.reply_text(f"✅ <b>𝗦𝘂𝗳𝗳𝗶𝘅 𝘂𝗽𝗱𝗮𝘁𝗲𝗱 𝘁𝗼:</b> '{val}'", parse_mode=ParseMode.HTML)
            user_data['state'] = None; return
            
        elif state == 'ADMIN_S3_ADD_CAT':
            cat = text.strip().lower()
            if cat not in ['facebook', 'whatsapp']: return await update.message.reply_text("⚠️ Please send either `facebook` or `whatsapp`.", parse_mode=ParseMode.HTML)
            user_data['s3_tmp_cat'] = cat; user_data['state'] = 'ADMIN_S3_ADD_CARRIER'
            return await update.message.reply_text("✅ Category Set.\nNow send the <b>𝗖𝗮𝗿𝗿𝗶𝗲𝗿 𝗜𝗗</b> (e.g. `95-1324`):", parse_mode=ParseMode.HTML)

        elif state == 'ADMIN_S3_ADD_CARRIER':
            user_data['s3_tmp_car'] = text.strip(); user_data['state'] = 'ADMIN_S3_ADD_COUNTRY'
            return await update.message.reply_text("✅ Carrier ID Set.\nNow send the <b>𝗖𝗼𝘂𝗻𝘁𝗿𝘆 𝗡𝗮𝗺𝗲</b> (e.g. `Myanmar`):", parse_mode=ParseMode.HTML)

        elif state == 'ADMIN_S3_ADD_COUNTRY':
            c_name = text.strip().title(); cat = user_data.get('s3_tmp_cat'); car = user_data.get('s3_tmp_car')
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(DB_EXECUTOR, sync_add_s3_range, cat, car, c_name)
            await update.message.reply_text(f"✅ <b>𝗦𝟯 𝗥𝗮𝗻𝗴𝗲 𝗔𝗱𝗱𝗲𝗱 𝗦𝘂𝗰𝗰𝗲𝘀𝘀𝗳𝘂𝗹𝗹𝘆!</b>\n\n🌍 {get_flag(c_name)} {c_name}\n🛒 {cat.title()}\n🆔 {car}", parse_mode=ParseMode.HTML)
            user_data['state'] = None; return

    # --- USER CONTROLS & STATES ---
    target_reply_user = user_data.get('admin_reply_target')
    if target_reply_user and not is_main_menu_action and not is_admin_action:
        try:
            await context.bot.send_message(chat_id=int(target_reply_user), text=f"👨‍💻 <b>Admin Reply:</b>\n━━━━━━━━━━━━━━━━━━━━\n<b>{text}</b>", parse_mode=ParseMode.HTML)
            await update.message.reply_text("✅ <b>Reply sent successfully.</b>", parse_mode=ParseMode.HTML)
        except Exception: await update.message.reply_text("❌ <b>Failed to send.</b>")
        user_data['admin_reply_target'] = None; return

    state = user_data.get('state')
    
    if text == "📱 GET NUMBER":
        if not await check_subscription(user_id, context.bot): await send_join_prompt(update, context)
        else: await start_category_selection(update, context)
            
    elif state == 'WAITING_FOR_2FA':
        user_msg_id = update.message.message_id
        key = text.replace(" ", "").strip()
        msg = await update.message.reply_text("<b>⏳ Generating...</b>", parse_mode=ParseMode.HTML)
        try:
            session = await get_session()
            async with session.get(API_2FA.format(key), timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    code = data.get('code')
                    if code: 
                        out = f"✅ <b>2FA CODE GENERATED!</b>\n🔢 <b>Code:</b> <code>{code}</code>\n<b>⚠️ Auto-delete in 5 mins.</b>"
                        await msg.edit_text(out, parse_mode=ParseMode.HTML)
                        asyncio.create_task(delete_message_later(context.bot, msg.chat_id, msg.message_id, 300, user_msg_id))
                    else: await msg.edit_text("❌ <b>Invalid Secret Key.</b>", parse_mode=ParseMode.HTML)
                else: await msg.edit_text("❌ <b>API Error!</b>", parse_mode=ParseMode.HTML)
        except Exception: await msg.edit_text("❌ <b>Network Error.</b>", parse_mode=ParseMode.HTML)
        user_data['state'] = None

    elif text == "🎁 REFER":
        loop = asyncio.get_event_loop()
        user_info = await loop.run_in_executor(DB_EXECUTOR, sync_get_user_info, user_id)
        bot_username = context.bot.username
        ref_link = f"https://t.me/{bot_username}?start=ref_{user_id}"
        share_url = f"https://t.me/share/url?url={urllib.parse.quote(ref_link)}&text=Join%20Now!"
        
        msg = (
            f"🟢 <b>Your Referral Dashboard</b>\n\n"
            f"🖲️ <b>You Referred:</b> {user_info['total_referrals']} users\n"
            f"💸 <b>Total Commission:</b> {user_info.get('ref_earnings', 0.0):.4f} ৳\n\n"
            f"<b>You will get 10% commission when your referral withdraws money!</b>\n\n"
            f"🔗 <b>Referral Link:</b>\n<code>{ref_link}</code>"
        )
        
        markup = {
            "inline_keyboard": [
                [
                    {"text": "🚀 Refer Now", "url": share_url, "style": "success"}
                ]
            ]
        }
        await update.message.reply_text(msg, reply_markup=markup, parse_mode=ParseMode.HTML)

    elif text == "💳 BALANCE":
        loop = asyncio.get_event_loop()
        user_info = await loop.run_in_executor(DB_EXECUTOR, sync_get_user_info, user_id)
        
        msg = (
            f"💳 <b>Balance:</b> {user_info['balance']:.2f} ৳\n"
            f"<b>Minimum Withdraw:</b> {SETTINGS_CACHE['min_withdraw']} ৳"
        )
        
        markup = {
            "inline_keyboard": [
                [
                    {"text": "💳 Withdraw Balance", "callback_data": "req_withdraw", "style": "success"}
                ]
            ]
        }
        await update.message.reply_text(msg, reply_markup=markup, parse_mode=ParseMode.HTML)
        
    elif text == "🎧 LIVE SUPPORT":
        user_data['state'] = 'WAITING_FOR_SUPPORT'
        await update.message.reply_text("<b>আপনার সমস্যাটি বলুন:</b>", parse_mode=ParseMode.HTML)
        
    elif state == 'WAITING_FOR_SUPPORT':
        for a_id in ADMIN_IDS:
            try: 
                markup = {
                    "inline_keyboard": [
                        [
                            {"text": "💬 Reply", "callback_data": f"admrep_{user_id}", "style": "primary"}
                        ]
                    ]
                }
                await context.bot.send_message(chat_id=a_id, text=f"📩 <b>Support Message</b>\n👤 <b>ID:</b> <code>{user_id}</code>\n💬 <b>Msg:</b> {html.escape(text)}", parse_mode=ParseMode.HTML, reply_markup=markup)
            except: pass
        await update.message.reply_text("✅ <b>Message Sent!</b> An Admin will reply soon.", parse_mode=ParseMode.HTML)
        user_data['state'] = None
        
    elif text == "📊 LIVE TRAFFIC":
        await show_live_traffic(update, context)
        
    elif state == 'WAIT_WITHDRAW_ACC':
        user_data['wd_account'] = text; user_data['state'] = 'WAIT_WITHDRAW_AMT'
        await update.message.reply_text(f"💳 <b>Enter Amount to Withdraw:</b>\n<i>(Minimum {SETTINGS_CACHE['min_withdraw']} ৳)</i>", parse_mode=ParseMode.HTML)
        
    elif state == 'WAIT_WITHDRAW_AMT':
        try: amount = float(text)
        except: return await update.message.reply_text("<b>⚠️ Invalid amount. Try again.</b>", parse_mode=ParseMode.HTML)
        
        if amount < SETTINGS_CACHE['min_withdraw']: return await update.message.reply_text(f"<b>⚠️ Minimum withdraw is {SETTINGS_CACHE['min_withdraw']} ৳.</b>", parse_mode=ParseMode.HTML)
            
        loop = asyncio.get_event_loop()
        user_info = await loop.run_in_executor(DB_EXECUTOR, sync_get_user_info, user_id)
        if user_info['balance'] < amount:
            user_data['state'] = None
            return await update.message.reply_text("<b>❌ Insufficient balance.</b>", parse_mode=ParseMode.HTML)
            
        method = user_data.get('wd_method', 'Unknown')
        account = user_data.get('wd_account', 'Unknown')
        
        wd_id = await loop.run_in_executor(DB_EXECUTOR, sync_create_withdraw, user_id, amount, method, account)
        await update.message.reply_text("<b>✅ Withdrawal Request Sent!</b>\n<i>Please wait for Admin approval.</i>", parse_mode=ParseMode.HTML)
        
        admin_txt = (
            f"💳 <b>NEW WITHDRAW REQUEST</b> 💳\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"👤 <b>User:</b> <code>{user_id}</code>\n"
            f"💰 <b>Amount:</b> {amount} ৳\n"
            f"🏦 <b>Method:</b> {method}\n"
            f"📱 <b>Account:</b> <code>{account}</code>\n"
        )
        kb = [[InlineKeyboardButton("✅ Approve", callback_data=f"wd_app_{wd_id}"), InlineKeyboardButton("❌ Reject", callback_data=f"wd_rej_{wd_id}")]]
        for a_id in ADMIN_IDS:
            try: await context.bot.send_message(chat_id=a_id, text=admin_txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.HTML)
            except: pass
            
        user_data['state'] = None
        
    else:
        if user_id not in ADMIN_IDS and not is_main_menu_action: await show_main_menu(update, context)

# ==============================================================================
# 🎮 BUTTON HANDLER
# ==============================================================================

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await check_ban_middleware(update, context): return
    query = update.callback_query
    user_id = query.from_user.id
    data = query.data
    await ensure_user_fast(user_id)
    
    if data == "ignore": return await query.answer()
    elif data == "check_join":
        if await check_subscription(user_id, context.bot): 
            try: await query.message.delete()
            except: pass
            await show_main_menu(query, context)
        else: await query.answer("⚠️ Please join all channels first.", show_alert=True)

    elif data.startswith("cat_"): await handle_category_click(update, context)
        
    elif data.startswith("r_"):
        parts = data.split("_")
        server_id, range_val = int(parts[1]), parts[2]
        if len(parts) > 3: context.user_data['real_country_name'] = parts[3]
        await process_number_generation(update, context, range_val, server_id, is_callback=True)
        
    elif data == "change_num":
        if context.user_data.get('range'):
            server_id = context.user_data.get('server', 1)
            await process_number_generation(update, context, context.user_data['range'], server_id, is_callback=True)
        else: await query.edit_message_text("<b>⚠️ Session Expired.</b>\n<i>Please start again.</i>", parse_mode=ParseMode.HTML)
            
    elif data == "go_main": await show_main_menu(update, context)
    elif data == "go_cat": await start_category_selection(update, context)
        
    elif data.startswith("dels3_"):
        if user_id not in ADMIN_IDS: return await query.answer("⚠️ Admin only.", show_alert=True)
        r_id = int(data.split("_")[1])
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(DB_EXECUTOR, sync_delete_s3_range, r_id)
        await query.answer("✅ S3 Range Deleted!")
        ranges = await loop.run_in_executor(DB_EXECUTOR, sync_get_s3_ranges, None)
        if not ranges: await query.edit_message_text("📭 <i>All S3 Ranges deleted.</i>", parse_mode=ParseMode.HTML)
        else:
            kb = [[InlineKeyboardButton(f"❌ {r[1].title()} | {r[3]} ({r[2]})", callback_data=f"dels3_{r[0]}")] for r in ranges]
            await query.edit_message_text("🗑️ <b>Click a range below to delete it:</b>", reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.HTML)

    elif data.startswith("delch_"):
        if user_id not in ADMIN_IDS: return await query.answer("⚠️ Admin only.", show_alert=True)
        ch = data.replace("delch_", "")
        CHANNELS_CACHE.discard(ch)
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(DB_EXECUTOR, sync_del_channel, ch)
        await query.answer(f"✅ Removed {ch}")
        if not CHANNELS_CACHE: await query.edit_message_text("📭 <i>All Channels deleted.</i>", parse_mode=ParseMode.HTML)
        else:
            kb = [[InlineKeyboardButton(f"❌ {c}", callback_data=f"delch_{c}")] for c in CHANNELS_CACHE]
            await query.edit_message_text("🗑️ <b>Click a channel to remove:</b>", reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.HTML)

    elif data.startswith("admrep_"):
        if user_id not in ADMIN_IDS: return await query.answer("⚠️ Admin only.", show_alert=True)
        target_user_id = data.split("_")[1]
        context.user_data['admin_reply_target'] = target_user_id
        await query.message.reply_text(f"✍️ <b>Type reply for:</b> <code>{target_user_id}</code>\n<i>(Type message normally)</i>", parse_mode=ParseMode.HTML)
        await query.answer()

    elif data == "req_withdraw":
        loop = asyncio.get_event_loop()
        u_info = await loop.run_in_executor(DB_EXECUTOR, sync_get_user_info, user_id)
        min_wd = SETTINGS_CACHE["min_withdraw"]
        if u_info['balance'] < min_wd: return await query.answer(f"⚠️ Minimum withdraw is {min_wd} ৳.", show_alert=True)
            
        markup = {
            "inline_keyboard": [
                [{"text": "Bᴋᴀsʜ ", "callback_data": "wdm_Bkash", "style": "primary"}],
                [{"text": "Nᴀɢᴀᴅ ", "callback_data": "wdm_Nagad", "style": "success"}],
                [{"text": "Rᴇᴄʜᴀʀɢᴇ ", "callback_data": "wdm_Mobile_Recharge", "style": "danger"}]
            ]
        }
        
        await query.edit_message_text("🏦 <b>Sᴇʟᴇᴄᴛ Yᴏᴜʀ Wɪᴛʜᴅʀᴀᴡ Mᴀᴛʜᴏᴅ :</b>", parse_mode=ParseMode.HTML, reply_markup=markup)
        
    elif data.startswith("wdm_"):
        method = data.replace("wdm_", "").replace("_", " ")
        context.user_data['wd_method'] = method; context.user_data['state'] = 'WAIT_WITHDRAW_ACC'
        await query.edit_message_text(f"📱 <b>Method: {method}</b>\n\n✍️ <i>Please type your {method} Account Number:</i>", parse_mode=ParseMode.HTML)

    elif data.startswith("wd_app_") or data.startswith("wd_rej_"):
        if user_id not in ADMIN_IDS: return await query.answer("⚠️ Admin only.", show_alert=True)
        wd_id = int(data.split("_")[2])
        is_approve = data.startswith("wd_app_")
        status_txt = "approved" if is_approve else "rejected"
        
        loop = asyncio.get_event_loop()
        success, tgt_user, amount, ref_id, bonus = await loop.run_in_executor(DB_EXECUTOR, sync_update_withdraw_status, wd_id, status_txt)
        
        if success:
            await query.edit_message_text(f"✅ <b>Request {status_txt.upper()}!</b> (ID: {wd_id})", parse_mode=ParseMode.HTML)
            try:
                if is_approve: 
                    await context.bot.send_message(chat_id=tgt_user, text=f"✅ <b>WITHDRAW APPROVED!</b>\nYour request for {amount} ৳ has been successfully processed.", parse_mode=ParseMode.HTML)
                    if ref_id and bonus > 0:
                        try: await context.bot.send_message(chat_id=ref_id, text=f"🎉 <b>Referral Bonus!</b>\nYour referral withdrew money. You received <b>{bonus:.2f} ৳</b> (10% commission).", parse_mode=ParseMode.HTML)
                        except: pass
                else: 
                    await context.bot.send_message(chat_id=tgt_user, text=f"❌ <b>WITHDRAW REJECTED!</b>\nYour request for {amount} ৳ was rejected. Balance refunded.", parse_mode=ParseMode.HTML)
            except: pass
        else: await query.edit_message_text(f"⚠️ Request already processed or not found. (ID: {wd_id})", parse_mode=ParseMode.HTML)

# ==============================================================================
# 👑 FULLY FUNCTIONAL ADMIN KEYBOARD
# ==============================================================================

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS: return
    context.user_data['admin_reply_target'] = None
    context.user_data['state'] = None
    kb = [
        ["📊 𝗕𝗼𝘁 𝗦𝘁𝗮𝘁𝘂𝘀", "👥 𝗧𝗼𝘁𝗮𝗹 𝗨𝘀𝗲𝗿𝘀"],
        ["📢 𝗕𝗿𝗼𝗮𝗱𝗰𝗮𝘀𝘁", "🚫 𝗕𝗮𝗻 / 𝗨𝗻𝗯𝗮𝗻"],
        ["💰 𝗦𝗲𝘁 𝗥𝗲𝘄𝗮𝗿𝗱𝘀", "💳 𝗦𝗲𝘁 𝗠𝗶𝗻 𝗪𝗶𝘁𝗵𝗱𝗿𝗮𝘄"],
        ["💸 𝗔𝗱𝗱 𝗕𝗮𝗹𝗮𝗻𝗰𝗲", "🏆 𝗧𝗼𝗽 𝗥𝗲𝗳𝗲𝗿𝗿𝗲𝗿𝘀"],
        ["➕ 𝗔𝗱𝗱 𝗖𝗵𝗮𝗻𝗻𝗲𝗹", "🗑️ 𝗗𝗲𝗹 𝗖𝗵𝗮𝗻𝗻𝗲𝗹"],
        ["✏️ 𝗦𝗲𝘁 𝗦𝘂𝗳𝗳𝗶𝘅 𝗦𝟭", "✏️ 𝗦𝗲𝘁 𝗦𝘂𝗳𝗳𝗶𝘅 𝗦𝟮"],
        ["✏️ 𝗦𝗲𝘁 𝗦𝘂𝗳𝗳𝗶𝘅 𝗦𝟯", "🌐 𝗦𝗲𝘁 𝗣𝗶𝗻𝗴 𝗨𝗥𝗟"],
        ["➕ 𝗔𝗱𝗱 𝗦𝟯 𝗥𝗮𝗻𝗴𝗲", "🗑️ 𝗗𝗲𝗹 𝗦𝟯 𝗥𝗮𝗻𝗴𝗲"],
        ["Main Menu"]
    ]
    txt = "🔐 <b>𝗔𝗗𝗩𝗔𝗡𝗖𝗘𝗗 𝗔𝗗𝗠𝗜𝗡 𝗣𝗔𝗡𝗘𝗟</b> 🔐\n━━━━━━━━━━━━━━━━━━━━\n<i>Use the keyboard below to manage the bot:</i>"
    await update.message.reply_text(txt, reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True), parse_mode=ParseMode.HTML)

# ==============================================================================
# ☁️ INVISIBLE TELEGRAM CLOUD BACKUP & RESTORE SYSTEM
# ==============================================================================

LAST_BACKUP_MSG_ID = None

async def cmd_backup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS: return
    try:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(DB_EXECUTOR, sync_checkpoint)
        if os.path.exists(DB_FILE): await update.message.reply_document(document=open(DB_FILE, 'rb'), filename=DB_FILE, caption="☁️ <b>𝗠𝗮𝗻𝘂𝗮𝗹 𝗗𝗮𝘁𝗮𝗯𝗮𝘀𝗲 𝗕𝗮𝗰𝗸𝘂𝗽</b>\n\n<i>To restore, reply to this file with /restore</i>", parse_mode=ParseMode.HTML)
        else: await update.message.reply_text("⚠️ No database file found yet.")
    except Exception as e: await update.message.reply_text(f"❌ Backup failed: {e}")

async def cmd_restore(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS: return
    if not update.message.reply_to_message or not update.message.reply_to_message.document: return await update.message.reply_text("⚠️ <b>Please reply to a .db backup file with /restore</b>", parse_mode=ParseMode.HTML)
        
    doc = update.message.reply_to_message.document
    if not doc.file_name.endswith('.db'): return await update.message.reply_text("⚠️ <b>Invalid file format. Must be a .db file.</b>", parse_mode=ParseMode.HTML)
        
    msg = await update.message.reply_text("⏳ <i>𝗗𝗼𝘄𝗻𝗹𝗼𝗮𝗱𝗶𝗻𝗴 𝗮𝗻𝗱 𝗿𝗲𝘀𝘁𝗼𝗿𝗶𝗻𝗴 𝗱𝗮𝘁𝗮𝗯𝗮𝘀𝗲...</i>", parse_mode=ParseMode.HTML)
    
    try:
        if os.path.exists(f"{DB_FILE}-wal"): os.remove(f"{DB_FILE}-wal")
        if os.path.exists(f"{DB_FILE}-shm"): os.remove(f"{DB_FILE}-shm")
        file = await context.bot.get_file(doc.file_id)
        await file.download_to_drive(DB_FILE)
        init_db()
        await msg.edit_text("✅ <b>𝗗𝗮𝘁𝗮𝗯𝗮𝘀𝗲 𝗥𝗲𝘀𝘁𝗼𝗿𝗲𝗱 𝗦𝘂𝗰𝗰𝗲𝘀𝘀𝗳𝘂𝗹𝗹𝘆!</b>\n<i>All user balances and data have been completely recovered.</i>", parse_mode=ParseMode.HTML)
    except Exception as e: await msg.edit_text(f"❌ <b>𝗥𝗲𝘀𝘁𝗼𝗿𝗲 𝗳𝗮𝗶𝗹𝗲𝗱:</b> {e}", parse_mode=ParseMode.HTML)

async def auto_backup_job(context: ContextTypes.DEFAULT_TYPE):
    global LAST_BACKUP_MSG_ID
    if not os.path.exists(DB_FILE): return
    try:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(DB_EXECUTOR, sync_checkpoint)
        
        main_admin = ADMIN_IDS[0] 
        with open(DB_FILE, 'rb') as f:
            msg = await context.bot.send_document(
                chat_id=main_admin, document=f, filename=f"Silent_Backup_{datetime.datetime.now().strftime('%Y%m%d_%H%M')}.db",
                caption="☁️ <b>Silent Auto Cloud Backup (20 Min)</b>\n\n<i>Render safe-guard. To restore, reply to this file with /restore</i>",
                parse_mode=ParseMode.HTML, disable_notification=True 
            )
        if LAST_BACKUP_MSG_ID:
            try: await context.bot.delete_message(chat_id=main_admin, message_id=LAST_BACKUP_MSG_ID)
            except Exception: pass
        LAST_BACKUP_MSG_ID = msg.message_id
    except Exception as e: logger.error(f"Auto Backup Failed: {e}")

# ==============================================================================
# 🌐 BACKGROUND CACHE UPDATER
# ==============================================================================

async def update_cache_job(context: ContextTypes.DEFAULT_TYPE):
    global CONSOLE_CACHE
    try:
        gc.collect()
        s1_tasks = [s1_api_request('GET', f"{S1_BASE_URL}/mdashboard/console/info?page={i}") for i in range(1, 4)]
        s2_tasks = [s2_api_request('GET', f"{S2_BASE_URL}/api/freelancer/console/data?page={i}&limit=50") for i in range(1, 4)]
        results = await asyncio.gather(*s1_tasks, *s2_tasks, return_exceptions=True)
        
        s1_logs = []
        for res in results[:3]:
            if isinstance(res, tuple) and res[0] == 200 and isinstance(res[1], dict):
                s1_logs.extend(res[1].get('data', {}).get('logs', []))
        s2_logs = []
        for res in results[3:]:
            if isinstance(res, tuple) and res[0] == 200 and isinstance(res[1], dict):
                s2_logs.extend(res[1].get('data', []))
                
        if s1_logs: CONSOLE_CACHE[1] = s1_logs[:150]
        if s2_logs: CONSOLE_CACHE[2] = s2_logs[:150]
    except Exception: pass

# ==============================================================================
# 🌐 RENDER LONG-POLLING ANTI-SLEEP
# ==============================================================================

async def web_server_handler(request):
    if request.query.get('keepalive') == 'true':
        await asyncio.sleep(60) 
        return web.Response(text="✅ Long-poll successful. Stayed for 60s.")
    return web.Response(text="✅ Premium OTP Bot Running perfectly!")

async def self_ping_job(context: ContextTypes.DEFAULT_TYPE):
    ping_url = SETTINGS_CACHE.get("ping_url", "https://rtxstexsms-qf5h.onrender.com")
    if not ping_url or ping_url == "None": return
    url = f"{ping_url}&keepalive=true" if "?" in ping_url else f"{ping_url}?keepalive=true"
    try:
        session = await get_session()
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=75), ssl=False) as resp: pass
    except Exception: pass

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
    asyncio.create_task(auth_s1(force=True))
    asyncio.create_task(auth_s2(force=True))
    asyncio.create_task(auth_s3(force=True))

if __name__ == "__main__":
    init_db()
    app = Application.builder().token(TOKEN).post_init(post_init).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin_panel))
    app.add_handler(CommandHandler("backup", cmd_backup))
    app.add_handler(CommandHandler("restore", cmd_restore))
    app.add_handler(CommandHandler("2fa", cmd_2fa))
    
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    app.job_queue.run_repeating(global_otp_checker_job,  interval=2,    first=2)
    app.job_queue.run_repeating(update_cache_job,         interval=15,   first=2)
    app.job_queue.run_repeating(auto_relogin_job,         interval=300,  first=300)
    app.job_queue.run_repeating(self_ping_job,            interval=120,  first=10)
    app.job_queue.run_repeating(auto_backup_job,          interval=1200, first=1200)
    
    logger.info("✨ VERSION 83 ENTERPRISE RUNNING ✨")
    app.run_polling(drop_pending_updates=True)
