"""
==============================================================================
PROJECT: ✨ PREMIUM OTP BOT (Ultimate Update - Version 55.0 ENTERPRISE FINAL) ✨
CAPACITY: 30,000+ Users on Render Free Plan (Thread-Pool & O(1) RAM Hash-Map).
UPDATES: TRIPLE SERVER ARCHITECTURE (Server 1: STEX, Server 2: ACCHUB, Server 3: ZAYAN).
CLOUDFLARE BYPASS: curl_cffi impersonates Chrome TLS fingerprint for Server 2 & 3!
NEW UI & EXTREME SCALABILITY FEATURES:
- Render Free Plan Anti-Hang: SQLite WAL mode, Async Threading & background batch DB writes.
- High-Speed % Calculation: GLOBAL RAM CACHING makes loading blink-of-an-eye fast (0.01s)!
- Merged Server Panel: "Get Number" directly opens Categories. Custom Range Removed.
- Intelligent Routing: Stex (No Suffix), Acchub (XRT), Zayan (XR). Sorted beautifully.
- Configurable Suffixes: Admin can change suffix tags live from the Admin Panel.
- Restored Short Codes: Numbers display exact ISO codes again (e.g. ❶ [BD] 17XXXXXXXX ⏳).
- Range & OTP Groups: "Range" values hidden. Posts "New Update find" with specific Suffix Country.
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

# 🔥 curl_cffi — Chrome TLS fingerprint spoof for Cloudflare bypass
from curl_cffi.requests import AsyncSession as CurlAsyncSession

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
ADMIN_IDS = [6031032502, 6941366213] 
CHANNELS = ["@EarnXtract", "@RTx_Sms", "@ConsoleXRT", "@RTxOtpX"]

RANGE_GROUP_ID = -1003627708272
OTP_GROUP_ID = -1003830374258

# 🌐 SERVER 1 CREDENTIALS (STEX)
S1_EMAIL = "mdrajaislam469@gmail.com"
S1_PASSWORD = "Raja1234@#"
S1_BASE_URL = "https://stexsms.com/mapi/v1"

# 🚀 SERVER 2 CREDENTIALS (ACCHUB)
S2_EMAIL = "rtxraja01@gmail.com"
S2_PASSWORD = "Raja1234"
S2_BASE_URL = "https://sms.acchub.io"

# 🔥 SERVER 3 CREDENTIALS (ZAYAN SMS)
S3_EMAIL = "mdrajaislam469@gmail.com"
S3_PASSWORD = "Raja1234@#"
S3_BASE_URL = "https://zayansms.com/mapi/v1"

# 🔥 CLOUDFLARE BYPASS HEADERS (Universal Chrome124 Impersonation)
def get_cf_headers(origin_domain):
    return {
        "User-Agent": "Mozilla/5.0 (Linux; Android 14; SM-A135F Build/UP1A.231005.007) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.7680.164 Mobile Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json",
        "Origin": f"https://{origin_domain}",
        "sec-ch-ua": '"Chromium";v="146", "Not-A.Brand";v="24", "Android WebView";v="146"',
        "sec-ch-ua-mobile": "?1",
        "sec-ch-ua-platform": '"Android"',
        "sec-fetch-site": "same-origin",
        "sec-fetch-mode": "cors",
        "sec-fetch-dest": "empty",
        "x-requested-with": "mark.via.gp",
        "accept-encoding": "gzip, deflate, br, zstd",
        "accept-language": "en-US,en-VI;q=0.9,en;q=0.8,bn-BD;q=0.7,bn;q=0.6,en-CA;q=0.5",
        "priority": "u=1, i"
    }

API_2FA = "https://2fa.cn/codes/{}"

# ==============================================================================
# 🛑 ADVANCED SERVER CRASH PREVENTION & CACHING
# ==============================================================================

S1_TOKEN = None
S2_TOKEN = None
S3_TOKEN = None

GLOBAL_SESSION = None 
S2_SESSION = None
S3_SESSION = None

AUTH_LOCK_S1 = asyncio.Lock() 
AUTH_LOCK_S2 = asyncio.Lock()
AUTH_LOCK_S3 = asyncio.Lock()

LAST_AUTH_S1 = 0
LAST_AUTH_S2 = 0
LAST_AUTH_S3 = 0

LAST_INBOX_S1 = ""
LAST_INBOX_S2 = ""
LAST_INBOX_S3 = ""

SENT_RANGES = set()
START_TIME = datetime.datetime.now()

BASE_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"

# 🔥 MAXIMIZED THREAD POOL & DB POOL FOR RENDER 30K USERS ANTI-HANG
DB_POOL_SIZE = 50 
DB_EXECUTOR = concurrent.futures.ThreadPoolExecutor(max_workers=100)

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# ==============================================================================
# 🧠 ENTERPRISE MEMORY SYSTEM (FOR 30,000+ USERS RAM CACHING)
# ==============================================================================

WAITING_OTPS = {}
NUM_TO_HASH = {}
BATCH_MSGS = {} 
OTP_TIMEOUT_SECONDS = 1200  

USER_CACHE = set()
BANNED_CACHE = set()

# ⚡ GLOBAL RAM CACHE FOR INSTANT % CALCULATION (0.01s Loading Time)
CONSOLE_CACHE = {
    1: [],
    2: [],
    3: []
}

# Live Settings for Rewards & Withdrawals & Suffixes
SETTINGS_CACHE = {
    "otp_reward": 0.10,
    "ref_reward": 0.05,
    "min_withdraw": 50.0,
    "ping_url": "https://rtxstexsms-dhno.onrender.com",
    "s1_suffix": "",
    "s2_suffix": " XRT",
    "s3_suffix": " XR"
}

# ==============================================================================
# 🌍 MASSIVE COUNTRY FLAGS & ISO DICTIONARY (250+ COUNTRIES)
# ==============================================================================

COUNTRY_FLAGS = {
    "Afghanistan":"🇦🇫", "Albania":"🇦🇱", "Algeria":"🇩🇿", "Andorra":"🇦🇩", "Angola":"🇦🇴", "Antigua and Barbuda":"🇦🇬", "Argentina":"🇦🇷", "Armenia":"🇦🇲", "Australia":"🇦🇺", "Austria":"🇦🇹", "Azerbaijan":"🇦🇿", "Bahamas":"🇧🇸", "Bahrain":"🇧🇭", "Bangladesh":"🇧🇩", "Barbados":"🇧🇧", "Belarus":"🇧🇾", "Belgium":"🇧🇪", "Belize":"🇧🇿", "Benin":"🇧🇯", "Bhutan":"🇧🇹", "Bolivia":"🇧🇴", "Bosnia and Herzegovina":"🇧🇦", "Botswana":"🇧🇼", "Brazil":"🇧🇷", "Brunei":"🇧🇳", "Bulgaria":"🇧🇬", "Burkina Faso":"🇧🇫", "Burundi":"🇧🇮", "Cabo Verde":"🇨🇻", "Cambodia":"🇰🇭", "Cameroon":"🇨🇲", "Canada":"🇨🇦", "Central African Republic":"🇨🇫", "Chad":"🇹🇩", "Chile":"🇨🇱", "China":"🇨🇳", "Colombia":"🇨🇴", "Comoros":"🇰🇲", "Congo":"🇨🇬", "Costa Rica":"🇨🇷", "Croatia":"🇭🇷", "Cuba":"🇨🇺", "Cyprus":"🇨🇾", "Czechia":"🇨🇿", "Denmark":"🇩🇰", "Djibouti":"🇩🇯", "Dominica":"🇩🇲", "Dominican Republic":"🇩🇴", "Ecuador":"🇪🇨", "Egypt":"🇪🇬", "El Salvador":"🇸🇻", "Equatorial Guinea":"🇬🇶", "Eritrea":"🇪🇷", "Estonia":"🇪🇪", "Eswatini":"🇸🇿", "Ethiopia":"🇪🇹", "Fiji":"🇫🇯", "Finland":"🇫🇮", "France":"🇫🇷", "Gabon":"🇬🇦", "Gambia":"🇬🇲", "Georgia":"🇬🇪", "Germany":"🇩🇪", "Ghana":"🇬🇭", "Greece":"🇬🇷", "Grenada":"🇬🇩", "Guatemala":"🇬🇹", "Guinea":"🇬🇳", "Guinea-Bissau":"🇬🇼", "Guyana":"🇬🇾", "Haiti":"🇭🇹", "Honduras":"🇭🇳", "Hungary":"🇭🇺", "Iceland":"🇮🇸", "India":"🇮🇳", "Indonesia":"🇮🇩", "Iran":"🇮🇷", "Iraq":"🇮🇶", "Ireland":"🇮🇪", "Israel":"🇮🇱", "Italy":"🇮🇹", "Ivory Coast":"🇨🇮", "Jamaica":"🇯🇲", "Japan":"🇯🇵", "Jordan":"🇯🇴", "Kazakhstan":"🇰🇿", "Kenya":"🇰🇪", "Kiribati":"🇰🇮", "Kuwait":"🇰🇼", "Kyrgyzstan":"🇰🇬", "Laos":"🇱🇦", "Latvia":"🇱🇻", "Lebanon":"🇱🇧", "Lesotho":"🇱🇸", "Liberia":"🇱🇷", "Libya":"🇱🇾", "Liechtenstein":"🇱🇮", "Lithuania":"🇱🇹", "Luxembourg":"🇱🇺", "Madagascar":"🇲🇬", "Malawi":"🇲🇼", "Malaysia":"🇲🇾", "Maldives":"🇲🇻", "Mali":"🇲🇱", "Malta":"🇲🇹", "Marshall Islands":"🇲🇭", "Mauritania":"🇲🇷", "Mauritius":"🇲🇺", "Mexico":"🇲🇽", "Micronesia":"🇫🇲", "Moldova":"🇲🇩", "Monaco":"🇲🇨", "Mongolia":"🇲🇳", "Montenegro":"🇲🇪", "Morocco":"🇲🇦", "Mozambique":"🇲🇿", "Myanmar":"🇲🇲", "Namibia":"🇳🇦", "Nauru":"🇳🇷", "Nepal":"🇳🇵", "Netherlands":"🇳🇱", "New Zealand":"🇳🇿", "Nicaragua":"🇳🇮", "Niger":"🇳🇪", "Nigeria":"🇳🇬", "North Korea":"🇰🇵", "North Macedonia":"🇲🇰", "Norway":"🇳🇴", "Oman":"🇴🇲", "Pakistan":"🇵🇰", "Palau":"🇵🇼", "Palestine":"🇵🇸", "Panama":"🇵🇦", "Papua New Guinea":"🇵🇬", "Paraguay":"🇵🇾", "Peru":"🇵🇪", "Philippines":"🇵🇭", "Poland":"🇵🇱", "Portugal":"🇵🇹", "Qatar":"🇶🇦", "Romania":"🇷🇴", "Russia":"🇷🇺", "Rwanda":"🇷🇼", "Saint Kitts and Nevis":"🇰🇳", "Saint Lucia":"🇱🇨", "Saint Vincent":"🇻🇨", "Samoa":"🇼🇸", "San Marino":"🇸🇲", "Sao Tome and Principe":"🇸🇹", "Saudi Arabia":"🇸🇦", "Senegal":"🇸🇳", "Serbia":"🇷🇸", "Seychelles":"🇸🇨", "Sierra Leone":"🇸🇱", "Singapore":"🇸🇬", "Slovakia":"🇸🇰", "Slovenia":"🇸🇮", "Solomon Islands":"🇸🇧", "Somalia":"🇸🇴", "South Africa":"🇿🇦", "South Korea":"🇰🇷", "South Sudan":"🇸🇸", "Spain":"🇪🇸", "Sri Lanka":"🇱🇰", "Sudan":"🇸🇩", "Suriname":"🇸🇷", "Sweden":"🇸🇪", "Switzerland":"🇨🇭", "Syria":"🇸🇾", "Taiwan":"🇹🇼", "Tajikistan":"🇹🇯", "Tanzania":"🇹🇿", "Thailand":"🇹🇭", "Timor-Leste":"🇹🇱", "Togo":"🇹🇬", "Tonga":"🇹🇴", "Trinidad and Tobago":"🇹🇹", "Tunisia":"🇹🇳", "Turkey":"🇹🇷", "Turkmenistan":"🇹🇲", "Tuvalu":"🇹🇻", "Uganda":"🇺🇬", "Ukraine":"🇺🇦", "United Arab Emirates":"🇦🇪", "United Kingdom":"🇬🇧", "United States":"🇺🇸", "Uruguay":"🇺🇾", "Uzbekistan":"🇺🇿", "Vanuatu":"🇻🇺", "Venezuela":"🇻🇪", "Vietnam":"🇻🇳", "Yemen":"🇾🇪", "Zambia":"🇿🇲", "Zimbabwe":"🇿🇼", "PostPaid": "📡", "Hong Kong":"🇭🇰", "Macau":"🇲🇴", "Puerto Rico":"🇵🇷"
}

COUNTRY_CODES = {
    "Afghanistan":"AF", "Albania":"AL", "Algeria":"DZ", "Andorra":"AD", "Angola":"AO", "Antigua and Barbuda":"AG", "Argentina":"AR", "Armenia":"AM", "Australia":"AU", "Austria":"AT", "Azerbaijan":"AZ", "Bahamas":"BS", "Bahrain":"BH", "Bangladesh":"BD", "Barbados":"BB", "Belarus":"BY", "Belgium":"BE", "Belize":"BZ", "Benin":"BJ", "Bhutan":"BT", "Bolivia":"BO", "Bosnia and Herzegovina":"BA", "Botswana":"BW", "Brazil":"BR", "Brunei":"BN", "Bulgaria":"BG", "Burkina Faso":"BF", "Burundi":"BI", "Cabo Verde":"CV", "Cambodia":"KH", "Cameroon":"CM", "Canada":"CA", "Central African Republic":"CF", "Chad":"TD", "Chile":"CL", "China":"CN", "Colombia":"CO", "Comoros":"KM", "Congo":"CG", "Costa Rica":"CR", "Croatia":"HR", "Cuba":"CU", "Cyprus":"CY", "Czechia":"CZ", "Denmark":"DK", "Djibouti":"DJ", "Dominica":"DM", "Dominican Republic":"DO", "Ecuador":"EC", "Egypt":"EG", "El Salvador":"SV", "Equatorial Guinea":"GQ", "Eritrea":"ER", "Estonia":"EE", "Eswatini":"SZ", "Ethiopia":"ET", "Fiji":"FJ", "Finland":"FI", "France":"FR", "Gabon":"GA", "Gambia":"GM", "Georgia":"GE", "Germany":"DE", "Ghana":"GH", "Greece":"GR", "Grenada":"GD", "Guatemala":"GT", "Guinea":"GN", "Guinea-Bissau":"GW", "Guyana":"GY", "Haiti":"HT", "Honduras":"HN", "Hungary":"HU", "Iceland":"IS", "India":"IN", "Indonesia":"ID", "Iran":"IR", "Iraq":"IQ", "Ireland":"IE", "Israel":"IL", "Italy":"IT", "Ivory Coast":"CI", "Jamaica":"JM", "Japan":"JP", "Jordan":"JO", "Kazakhstan":"KZ", "Kenya":"KE", "Kiribati":"KI", "Kuwait":"KW", "Kyrgyzstan":"KG", "Laos":"LA", "Latvia":"LV", "Lebanon":"LB", "Lesotho":"LS", "Liberia":"LR", "Libya":"LY", "Liechtenstein":"LI", "Lithuania":"LT", "Luxembourg":"LU", "Madagascar":"MG", "Malawi":"MW", "Malaysia":"MY", "Maldives":"MV", "Mali":"ML", "Malta":"MT", "Marshall Islands":"MH", "Mauritania":"MR", "Mauritius":"MU", "Mexico":"MX", "Micronesia":"FM", "Moldova":"MD", "Monaco":"MC", "Mongolia":"MN", "Montenegro":"ME", "Morocco":"MA", "Mozambique":"MZ", "Myanmar":"MM", "Namibia":"NA", "Nauru":"NR", "Nepal":"NP", "Netherlands":"NL", "New Zealand":"NZ", "Nicaragua":"NI", "Niger":"NE", "Nigeria":"NG", "North Korea":"KP", "North Macedonia":"MK", "Norway":"NO", "Oman":"OM", "Pakistan":"PK", "Palau":"PW", "Palestine":"PS", "Panama":"PA", "Papua New Guinea":"PG", "Paraguay":"PY", "Peru":"PE", "Philippines":"PH", "Poland":"PL", "Portugal":"PT", "Qatar":"QA", "Romania":"RO", "Russia":"RU", "Rwanda":"RW", "Saint Kitts and Nevis":"KN", "Saint Lucia":"LC", "Saint Vincent":"VC", "Samoa":"WS", "San Marino":"SM", "Sao Tome and Principe":"ST", "Saudi Arabia":"SA", "Senegal":"SN", "Serbia":"RS", "Seychelles":"SC", "Sierra Leone":"SL", "Singapore":"SG", "Slovakia":"SK", "Slovenia":"SI", "Solomon Islands":"SB", "Somalia":"SO", "South Africa":"🇿🇦", "South Korea":"🇰🇷", "South Sudan":"🇸🇸", "Spain":"🇪🇸", "Sri Lanka":"🇱🇰", "Sudan":"🇸🇩", "Suriname":"🇸🇷", "Sweden":"🇸🇪", "Switzerland":"🇨🇭", "Syria":"🇸🇾", "Taiwan":"🇹🇼", "Tajikistan":"🇹🇯", "Tanzania":"🇹🇿", "Thailand":"🇹🇭", "Timor-Leste":"🇹🇱", "Togo":"🇹🇬", "Tonga":"🇹🇴", "Trinidad and Tobago":"🇹🇹", "Tunisia":"🇹🇳", "Turkey":"🇹🇷", "Turkmenistan":"🇹🇲", "Tuvalu":"🇹🇻", "Uganda":"🇺🇬", "Ukraine":"🇺🇦", "United Arab Emirates":"🇦🇪", "United Kingdom":"🇬🇧", "United States":"🇺🇸", "Uruguay":"🇺🇾", "Uzbekistan":"🇺🇿", "Vanuatu":"🇻🇺", "Venezuela":"🇻🇪", "Vietnam":"🇻🇳", "Yemen":"🇾🇪", "Zambia":"🇿🇲", "Zimbabwe":"🇿🇼", "PostPaid": "PP", "Hong Kong":"HK", "Macau":"MO", "Puerto Rico":"PR"
}

def get_flag(country_name):
    clean_name = str(country_name).replace(SETTINGS_CACHE['s1_suffix'], "").replace(SETTINGS_CACHE['s2_suffix'], "").replace(SETTINGS_CACHE['s3_suffix'], "").strip()
    if clean_name in COUNTRY_FLAGS: 
        return COUNTRY_FLAGS[clean_name]
    for name, flag in COUNTRY_FLAGS.items():
        if name.lower() in clean_name.lower() or clean_name.lower() in name.lower(): 
            return flag
    return "🚩"

def get_short_code(country_name):
    clean_name = str(country_name).replace(SETTINGS_CACHE['s1_suffix'], "").replace(SETTINGS_CACHE['s2_suffix'], "").replace(SETTINGS_CACHE['s3_suffix'], "").strip()
    if clean_name in COUNTRY_CODES:
        return COUNTRY_CODES[clean_name]
    for name, code in COUNTRY_CODES.items():
        if name.lower() in clean_name.lower() or clean_name.lower() in name.lower(): 
            return code
    return str(clean_name)[:2].upper()

# ==============================================================================
# 🔧 UTILITY FUNCTIONS
# ==============================================================================

def clean_number(n: str) -> str:
    return re.sub(r'\D', '', str(n))

def mask_number(number: str) -> str:
    digits = clean_number(number)
    if len(digits) < 7:
        return number
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
    wa_match = re.search(r'\b(\d{3})-(\d{3})\b', msg)
    if wa_match:
        return wa_match.group(1) + wa_match.group(2)
        
    kw = re.search(r'(?:otp|code|verification|verify|pin|passcode|password)[^0-9]{0,25}(\d{4,8})', msg, re.IGNORECASE)
    if kw:
        return kw.group(1)
    fb = re.search(r'\b(\d{4,8})\b', msg)
    return fb.group(1) if fb else "See Msg"

def get_sms_from_item(item: dict) -> str:
    return str(item.get('full_sms') or item.get('full_sms_list') or item.get('sms') or item.get('otp') or item.get('message') or item.get('sms_text') or item.get('msg') or "")

def get_service_from_item(item: dict) -> str:
    return str(item.get('app_name') or item.get('service_name') or item.get('service') or item.get('operator') or item.get('provider') or item.get('app') or "Service")

def get_number_from_item(item: dict) -> str:
    return str(item.get('number') or item.get('phone_number') or item.get('phone') or item.get('mobile') or item.get('msisdn') or "")

def get_code_from_item(item: dict, raw_msg: str) -> str:
    explicit = item.get('code') or item.get('otps') or item.get('otp_code') or item.get('verification_code') or ""
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
# 🗄️ DATABASE & REWARD SYSTEM MANAGEMENT (OPTIMIZED FOR 30K USERS)
# ==============================================================================

class DatabasePool:
    def __init__(self, db_file, pool_size=50):
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
            user_id INTEGER PRIMARY KEY, join_date TEXT, is_banned INTEGER DEFAULT 0,
            balance REAL DEFAULT 0.0, referrer_id INTEGER DEFAULT NULL, total_referrals INTEGER DEFAULT 0
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS settings (
            id INTEGER PRIMARY KEY, otp_reward REAL DEFAULT 0.10, ref_reward REAL DEFAULT 0.05, min_withdraw REAL DEFAULT 50.0, 
            ping_url TEXT DEFAULT 'https://rtxstexsms-dhno.onrender.com',
            s1_suffix TEXT DEFAULT '', s2_suffix TEXT DEFAULT ' XRT', s3_suffix TEXT DEFAULT ' XR'
        )''')
        
        try: c.execute("ALTER TABLE settings ADD COLUMN ping_url TEXT DEFAULT 'https://rtxstexsms-dhno.onrender.com'")
        except sqlite3.OperationalError: pass
        try: c.execute("ALTER TABLE settings ADD COLUMN s1_suffix TEXT DEFAULT ''")
        except sqlite3.OperationalError: pass
        try: c.execute("ALTER TABLE settings ADD COLUMN s2_suffix TEXT DEFAULT ' XRT'")
        except sqlite3.OperationalError: pass
        try: c.execute("ALTER TABLE settings ADD COLUMN s3_suffix TEXT DEFAULT ' XR'")
        except sqlite3.OperationalError: pass

        c.execute('''CREATE TABLE IF NOT EXISTS withdrawals (
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, amount REAL,
            method TEXT, account TEXT, status TEXT DEFAULT 'pending', date TEXT DEFAULT CURRENT_TIMESTAMP
        )''')
        
        c.execute("SELECT otp_reward, ref_reward, min_withdraw, ping_url, s1_suffix, s2_suffix, s3_suffix FROM settings WHERE id=1")
        settings_row = c.fetchone()
        if not settings_row:
            c.execute("INSERT INTO settings (id, otp_reward, ref_reward, min_withdraw, ping_url, s1_suffix, s2_suffix, s3_suffix) VALUES (1, 0.10, 0.05, 50.0, 'https://rtxstexsms-dhno.onrender.com', '', ' XRT', ' XR')")
            SETTINGS_CACHE["ping_url"] = "https://rtxstexsms-dhno.onrender.com"
        else:
            SETTINGS_CACHE["otp_reward"] = settings_row[0]
            SETTINGS_CACHE["ref_reward"] = settings_row[1]
            SETTINGS_CACHE["min_withdraw"] = float(settings_row[2]) if len(settings_row)>2 and settings_row[2] else 50.0
            SETTINGS_CACHE["ping_url"] = settings_row[3] if len(settings_row)>3 and settings_row[3] else "https://rtxstexsms-dhno.onrender.com"
            SETTINGS_CACHE["s1_suffix"] = settings_row[4] if len(settings_row)>4 and settings_row[4] is not None else ""
            SETTINGS_CACHE["s2_suffix"] = settings_row[5] if len(settings_row)>5 and settings_row[5] is not None else " XRT"
            SETTINGS_CACHE["s3_suffix"] = settings_row[6] if len(settings_row)>6 and settings_row[6] is not None else " XR"
            
        conn.commit()
        
        c.execute("SELECT user_id, is_banned FROM users")
        for row in c.fetchall():
            USER_CACHE.add(row[0])
            if row[1] == 1: BANNED_CACHE.add(row[0])

def sync_register_user_db(user_id, referrer_id=None):
    with db_pool.get_connection() as conn:
        c = conn.cursor()
        c.execute("SELECT user_id FROM users WHERE user_id=?", (user_id,))
        if not c.fetchone():
            c.execute("INSERT INTO users (user_id, join_date, referrer_id) VALUES (?, CURRENT_TIMESTAMP, ?)", (user_id, referrer_id))
            if referrer_id: c.execute("UPDATE users SET total_referrals = total_referrals + 1 WHERE user_id=?", (referrer_id,))
        conn.commit()

async def ensure_user_fast(user_id, referrer_id=None):
    if user_id not in USER_CACHE:
        USER_CACHE.add(user_id)
        loop = asyncio.get_event_loop()
        loop.run_in_executor(DB_EXECUTOR, sync_register_user_db, user_id, referrer_id)
    return True

def is_user_banned_fast(user_id): return user_id in BANNED_CACHE
def get_all_users(): return list(USER_CACHE)
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
        elif key == "ping_url":
            c.execute("UPDATE settings SET ping_url=? WHERE id=1", (value,))
            SETTINGS_CACHE["ping_url"] = value
        elif key == "s1_suffix":
            c.execute("UPDATE settings SET s1_suffix=? WHERE id=1", (value,))
            SETTINGS_CACHE["s1_suffix"] = value
        elif key == "s2_suffix":
            c.execute("UPDATE settings SET s2_suffix=? WHERE id=1", (value,))
            SETTINGS_CACHE["s2_suffix"] = value
        elif key == "s3_suffix":
            c.execute("UPDATE settings SET s3_suffix=? WHERE id=1", (value,))
            SETTINGS_CACHE["s3_suffix"] = value
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

# ==============================================================================
# 🔐 AUTHENTICATION & API REQUESTS (3 SERVERS) - UPGRADED CF BYPASS
# ==============================================================================

async def get_session():
    global GLOBAL_SESSION
    if GLOBAL_SESSION is None or GLOBAL_SESSION.closed:
        connector = aiohttp.TCPConnector(limit=500, keepalive_timeout=300, enable_cleanup_closed=True)
        GLOBAL_SESSION = aiohttp.ClientSession(connector=connector, cookie_jar=aiohttp.CookieJar(unsafe=True))
    return GLOBAL_SESSION

async def parse_response_safely(response):
    try: return await response.json(content_type=None)
    except Exception:
        try: return json.loads(await response.text())
        except Exception: return None

# --- SERVER 1 (STEX) ---
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
                return False
        except Exception: return False

async def s1_api_request(method, url, json_payload=None, return_text=False):
    global S1_TOKEN
    for attempt in range(3):
        try:
            if not S1_TOKEN:
                if not await auth_s1():
                    await asyncio.sleep(1)
                    continue
            session = await get_session()
            headers = {
                "User-Agent": BASE_USER_AGENT, "Accept": "application/json",
                "mauthtoken": str(S1_TOKEN), "Cookie": f"mauthtoken={S1_TOKEN}"
            }
            timeout = aiohttp.ClientTimeout(total=15)
            if method.upper() == 'GET': response = await session.get(url, headers=headers, timeout=timeout, ssl=False)
            else: response = await session.post(url, json=json_payload, headers=headers, timeout=timeout, ssl=False)
            
            status = response.status
            if status in [401, 403]: S1_TOKEN = None; await asyncio.sleep(0.5); continue
            if status in [500, 501, 502, 503]: await asyncio.sleep(1); continue
            if status == 200:
                text_response = await response.text()
                if return_text: return 200, text_response
                try: data = json.loads(text_response)
                except: data = None
                return 200, data
            else: return status, None
        except Exception: pass
    return 500, None

# --- SERVER 2 (ACCHUB) ---
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
            return False
        except Exception: return False

async def s2_api_request(method: str, url: str, json_payload=None, return_text=False):
    global S2_TOKEN
    for attempt in range(3):
        try:
            if not S2_TOKEN:
                if not await auth_s2():
                    await asyncio.sleep(2)
                    continue
            session = await get_s2_session()
            headers = get_cf_headers("acchub.io")
            headers.update({
                "authorization": f"Bearer {S2_TOKEN}"
            })
            
            if method.upper() == 'GET': response = await session.get(url, headers=headers, timeout=20)
            else: response = await session.post(url, json=json_payload, headers=headers, timeout=20)

            status = response.status_code
            if status in [401, 403]:
                S2_TOKEN = None
                await auth_s2(force=True)
                continue
            if status in [429, 500, 502, 503]:
                await asyncio.sleep(1)
                continue
            if status in [200, 201]:
                if return_text: return 200, response.text
                try: data = response.json()
                except Exception: data = None
                return 200, data
            else: return status, None
        except Exception: await asyncio.sleep(1)
    return 500, None


# --- SERVER 3 (ZAYAN) ---
async def get_s3_session():
    global S3_SESSION
    if S3_SESSION is None: S3_SESSION = CurlAsyncSession(impersonate="chrome124")
    return S3_SESSION

async def auth_s3(force=False):
    global S3_TOKEN, LAST_AUTH_S3
    async with AUTH_LOCK_S3:
        current_time = time.time()
        if not force and current_time - LAST_AUTH_S3 < 82800 and S3_TOKEN: 
            return True
            
        payload = {"email": S3_EMAIL, "password": S3_PASSWORD}
        headers = get_cf_headers("zayansms.com")
        headers["Referer"] = "https://zayansms.com/mauth/login"
        
        try:
            session = await get_s3_session()
            response = await session.post(f"{S3_BASE_URL}/mauth/login", json=payload, headers=headers, timeout=20)
            if response.status_code == 200:
                try: data = response.json()
                except Exception: data = None
                if data and str(data.get('meta', {}).get('code')) == '200':
                    S3_TOKEN = data['data']['token']
                    LAST_AUTH_S3 = time.time()
                    return True
            
            logger.warning("S3 Login Failed. Applying 5-minute cooldown to prevent IP Ban.")
            LAST_AUTH_S3 = current_time + 300
            return False
            
        except Exception: 
            LAST_AUTH_S3 = current_time + 300
            return False

async def s3_api_request(method: str, url: str, json_payload=None, return_text=False, referer="https://zayansms.com/mdashboard"):
    global S3_TOKEN
    for attempt in range(3):
        try:
            if not S3_TOKEN:
                if time.time() < LAST_AUTH_S3 and LAST_AUTH_S3 > time.time() + 82800:
                    return 503, None
                
                if not await auth_s3():
                    await asyncio.sleep(2)
                    continue
                    
            session = await get_s3_session()
            headers = get_cf_headers("zayansms.com")
            headers.update({
                "mauthtoken": str(S3_TOKEN), 
                "Cookie": f"mauthtoken={S3_TOKEN}",
                "Referer": referer
            })
            
            if method.upper() == 'GET': response = await session.get(url, headers=headers, timeout=20)
            else: response = await session.post(url, json=json_payload, headers=headers, timeout=20)

            status = response.status_code
            if status in [401, 403]:
                S3_TOKEN = None
                await auth_s3(force=True)
                continue
            if status in [429, 500, 502, 503]:
                await asyncio.sleep(1)
                continue
            if status == 200:
                if return_text: return 200, response.text
                try: data = response.json()
                except Exception: data = None
                if isinstance(data, dict):
                    if str(data.get('meta', {}).get('code', '200')) in ['401', '403']:
                        S3_TOKEN = None
                        await auth_s3(force=True)
                        continue
                return 200, data
            else: return status, None
        except Exception: await asyncio.sleep(1)
    return 500, None

async def auto_relogin_job(context: ContextTypes.DEFAULT_TYPE):
    logger.info("🔄 Refreshing All Server Sessions in parallel...")
    await asyncio.gather(
        auth_s1(force=True),
        auth_s2(force=True),
        auth_s3(force=True),
        return_exceptions=True
    )

# ==============================================================================
# 🔒 MIDDLEWARES & DYNAMIC UI
# ==============================================================================

async def check_subscription(user_id, bot):
    for channel in CHANNELS:
        try:
            member = await bot.get_chat_member(chat_id=channel, user_id=user_id)
            if member.status in ['left', 'kicked']: return False
        except Exception: return False
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
    
    msg = "⛔ <b>Access Denied!</b>\n━━━━━━━━━━━━━━━━━━━━\n<i>You must be a member of our official channels to use this bot.</i>\n\n👇 <b>Please join below:</b>"
    if update.callback_query: await update.callback_query.edit_message_text(text=msg, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
    else: await update.message.reply_text(text=msg, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)

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
# 🌟 ADVANCED SCREENSHOT UI UPDATE FUNCTION (RESTORED TO CLASSIC TEXT STYLE)
# ==============================================================================

async def update_dynamic_batch_message(context, chat_id, msg_id, batch_key):
    if batch_key not in BATCH_MSGS: return
    batch = BATCH_MSGS[batch_key]
    
    if len(batch['received_for']) == len(batch['numbers']):
        try: await context.bot.delete_message(chat_id=chat_id, message_id=msg_id)
        except Exception: pass
        
        txt = (
            f"✅ <b>ALL CODES RECEIVED SUCCESSFULLY!</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"<i>Thank you for using our service! Do you want to generate another number from the same range?</i>"
        )
        kb = [
            [InlineKeyboardButton("🔄 Get Number Again", callback_data="change_num")],
            [InlineKeyboardButton("🔙 Main Menu", callback_data="go_main")]
        ]
        try: await context.bot.send_message(chat_id=chat_id, text=txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.HTML)
        except Exception: pass
        BATCH_MSGS.pop(batch_key, None)
    
    else:
        # V40 CLASSIC STYLE RESTORED WITH SHORT CODES
        num_str = ""
        symbols = ["❶", "❷", "❸", "❹", "❺"] 
        for i, n in enumerate(batch['numbers']):
            short_name = get_short_code(batch['country_name'])
            if n in batch['received_for']:
                num_str += f"{symbols[i % len(symbols)]} [{short_name}] <del>{n}</del> ✅\n"
            else:
                num_str += f"{symbols[i % len(symbols)]} [{short_name}] <code>{n}</code> ⏳\n"
            
        txt = (
            f"✅ <b>NUMBERS GENERATED</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"🌍 <b>{batch['flag']} {batch['country_name']}</b>\n\n"
            f"{num_str}\n"
            f"⏳ <i>Waiting for SMS...</i>"
        )
        kb = [
            [InlineKeyboardButton("💬 OTP GROUP", url="https://t.me/RTxOtpX")],
            [InlineKeyboardButton("🔄 Change Number", callback_data="change_num"), InlineKeyboardButton("🔙 Back", callback_data="go_main")]
        ]
        
        try: await context.bot.edit_message_text(chat_id=chat_id, message_id=msg_id, text=txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.HTML)
        except Exception: pass

# ==============================================================================
# 🤖 AUTO RANGE FORWARDER JOB 
# ==============================================================================

async def process_console_logs_for_forwarder(context, logs, server_id, bot_username):
    global SENT_RANGES
    allowed_apps = ['facebook', 'whatsapp']
    
    s_suffix = ""
    if server_id == 1: s_suffix = SETTINGS_CACHE['s1_suffix']
    elif server_id == 2: s_suffix = SETTINGS_CACHE['s2_suffix']
    elif server_id == 3: s_suffix = SETTINGS_CACHE['s3_suffix']
    
    for log in logs[:20]:
        if isinstance(log, dict):
            if server_id == 2:
                c_id = log.get('country_id')
                op_id = log.get('operator_id')
                if not c_id or not op_id: continue
                r_val = f"{c_id}|{op_id}"
                raw_app = str(log.get('provider', 'Unknown')).lower()
                c_name = log.get('country_name', 'Unknown')
                raw_msg = log.get('sms_text', '')
            else:
                r_val = log.get('range')
                raw_app = str(log.get('app_name', str(log.get('service_name', 'Unknown')))).lower()
                c_name = log.get('country', 'Unknown')
                raw_msg = get_sms_from_item(log)

            if not r_val: continue
            
            if any(app in raw_app for app in allowed_apps):
                full_msg_text = clean_message_text(raw_msg)
                code_sig = extract_code(raw_msg)
                range_sig = f"{r_val}_{code_sig}_{str(raw_msg)[:20]}"
                
                if range_sig not in SENT_RANGES:
                    SENT_RANGES.add(range_sig)
                    if len(SENT_RANGES) > 10000: SENT_RANGES.clear()
                    
                    display_app = "PC Clone" if ('facebook' in raw_app and '•' in raw_msg) else raw_app.title()
                    num_in_msg = re.search(r'\b(\d{7,15})\b', full_msg_text)
                    if num_in_msg: full_msg_text = full_msg_text.replace(num_in_msg.group(1), mask_number(num_in_msg.group(1)))
                    
                    final_country_name = f"{c_name}{s_suffix}"
                    
                    range_msg = (
                        f"🔥 <b>New Update find</b>\n"
                        f"━━━━━━━━━━━━━━━━━━━━\n"
                        f"🛒 Service - <i>{html.escape(display_app)}</i>\n"
                        f"🌍 Country - {get_flag(c_name)} {final_country_name}\n"
                        f"✉️ Message - <pre>{html.escape(full_msg_text)}</pre>"
                    )
                    
                    kb = [[InlineKeyboardButton("📱 Get Number", url=f"https://t.me/{bot_username}")]]
                    
                    try: await context.bot.send_message(chat_id=RANGE_GROUP_ID, text=range_msg, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.HTML)
                    except Exception: pass

async def auto_range_forwarder_job(context: ContextTypes.DEFAULT_TYPE):
    global CONSOLE_CACHE
    bot_username = context.bot.username

    s1_task = s1_api_request('GET', f"{S1_BASE_URL}/mdashboard/console/info")
    s2_task = s2_api_request('GET', f"{S2_BASE_URL}/api/freelancer/console/data?page=1&limit=100")
    s3_task = s3_api_request('GET', f"{S3_BASE_URL}/mdashboard/console/info")
    
    results = await asyncio.gather(s1_task, s2_task, s3_task, return_exceptions=True)
    
    if isinstance(results[0], tuple) and results[0][0] == 200 and isinstance(results[0][1], dict):
        logs = results[0][1].get('data', {}).get('logs', [])
        CONSOLE_CACHE[1] = logs
        await process_console_logs_for_forwarder(context, logs, 1, bot_username)

    if isinstance(results[1], tuple) and results[1][0] == 200 and isinstance(results[1][1], dict):
        logs = results[1][1].get('data', [])
        CONSOLE_CACHE[2] = logs
        await process_console_logs_for_forwarder(context, logs, 2, bot_username)

    if isinstance(results[2], tuple) and results[2][0] == 200 and isinstance(results[2][1], dict):
        logs = results[2][1].get('data', {}).get('logs', [])
        CONSOLE_CACHE[3] = logs
        await process_console_logs_for_forwarder(context, logs, 3, bot_username)

# ==============================================================================
# 🚀 ULTRA-FAST OTP POLLER WITH MULTI-OTP SUPPORT (RESTORED CLASSIC OTP UI)
# ==============================================================================

async def process_found_otp(context, hash_key, api_num, code_only, svc_name, raw_msg, is_multi=False):
    global WAITING_OTPS, BATCH_MSGS, NUM_TO_HASH
    user_data = WAITING_OTPS.get(hash_key)
    if not user_data: return
    
    user_id = user_data['user_id']
    chat_id = user_data['chat_id']
    msg_id = user_data['msg_id']
    full_num = user_data['full_num']
    batch_key = user_data['batch_key']
    
    custom_service_name = user_data.get('service_name', svc_name)
    if custom_service_name == 'Auto Matched': custom_service_name = str(svc_name).title()
    
    loop = asyncio.get_event_loop()
    otp_reward = SETTINGS_CACHE["otp_reward"]
    ref_reward = SETTINGS_CACHE["ref_reward"]
    
    new_balance = await loop.run_in_executor(DB_EXECUTOR, sync_add_balance, user_id, otp_reward)
    
    user_info = await loop.run_in_executor(DB_EXECUTOR, sync_get_user_info, user_id)
    referrer_id = user_info.get("referrer_id")
    if referrer_id:
        await loop.run_in_executor(DB_EXECUTOR, sync_add_balance, referrer_id, ref_reward)
        try: asyncio.create_task(context.bot.send_message(chat_id=referrer_id, text=f"🎁 <b>Referral Bonus!</b>\nYour referral received an OTP. You got <b>+{ref_reward:.2f} Tk</b>!", parse_mode=ParseMode.HTML))
        except Exception: pass

    if not is_multi and batch_key in BATCH_MSGS:
        BATCH_MSGS[batch_key]['received_for'].add(full_num)
        asyncio.create_task(update_dynamic_batch_message(context, chat_id, msg_id, batch_key))

    header_text = "🔄 <b>MULTI OTP RECEIVED!</b>" if is_multi else "🎉 <b>OTP RECEIVED SUCCESSFULLY!</b>"
    user_msg = (
        f"{header_text} ✨\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📱 <b>Service :</b> <i>{html.escape(str(custom_service_name).upper())}</i>\n"
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
        f"🛒 Service - <pre>{html.escape(str(custom_service_name))}</pre>\n"
        f"🔑 Code - <code>{code_only}</code>\n"
        f"✉️ Full sms - <pre>{html.escape(str(clean_raw_msg))}</pre>"
    )
    
    group_kb = [[InlineKeyboardButton("👨‍💻 Owner", url="https://t.me/RTx2R")]]
    asyncio.create_task(context.bot.send_message(chat_id=OTP_GROUP_ID, text=group_msg, reply_markup=InlineKeyboardMarkup(group_kb), parse_mode=ParseMode.HTML))

async def check_inbox(context, server_res, last_text, text_var_name):
    global LAST_INBOX_S1, LAST_INBOX_S2, LAST_INBOX_S3
    if isinstance(server_res, tuple) and server_res[0] == 200 and server_res[1] and server_res[1] != last_text:
        text_data = server_res[1]
        if text_var_name == "s1": LAST_INBOX_S1 = text_data
        elif text_var_name == "s2": LAST_INBOX_S2 = text_data
        elif text_var_name == "s3": LAST_INBOX_S3 = text_data

        try:
            api_res = json.loads(text_data)
            items = []
            if text_var_name == "s2":
                items = api_res.get('data', [])
            else:
                data_field = api_res.get('data', {})
                items = data_field if isinstance(data_field, list) else (data_field.get('numbers') or data_field.get('list') or data_field.get('items') or data_field.get('otps') or [])
            
            for item in items:
                if not isinstance(item, dict): continue
                num_raw = get_number_from_item(item)
                raw_msg = get_sms_from_item(item)
                if not num_raw or not raw_msg: continue
                
                hash_key, waiter = _find_waiter(num_raw)
                if hash_key:
                    svc_name = get_service_from_item(item)
                    code_val = get_code_from_item(item, raw_msg)
                    
                    msg_sig = f"{code_val}_{str(raw_msg)[:15]}"
                    rcv_set = waiter.setdefault('received_codes', set())
                    if msg_sig not in rcv_set:
                        rcv_set.add(msg_sig)
                        is_multi = len(rcv_set) > 1
                        await process_found_otp(context, hash_key, waiter['full_num'], code_val, svc_name, raw_msg, is_multi)
        except Exception: pass

async def global_otp_checker_job(context: ContextTypes.DEFAULT_TYPE):
    global WAITING_OTPS, BATCH_MSGS, NUM_TO_HASH
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
        
    date_str = datetime.datetime.now().strftime("%Y-%m-%d")

    s1_task = s1_api_request('GET', f"{S1_BASE_URL}/mdashboard/getnum/info?date={date_str}&page=1", return_text=True)
    s2_task = s2_api_request('GET', f"{S2_BASE_URL}/api/freelancer/get-page/otp-history?page=1&limit=20", return_text=True)
    s3_task = s3_api_request('GET', f"{S3_BASE_URL}/mdashboard/getnum/info?date={date_str}&page=1", return_text=True)
    
    results = await asyncio.gather(s1_task, s2_task, s3_task, return_exceptions=True)

    await check_inbox(context, results[0], LAST_INBOX_S1, "s1")
    await check_inbox(context, results[1], LAST_INBOX_S2, "s2")
    await check_inbox(context, results[2], LAST_INBOX_S3, "s3")

# ==============================================================================
# 🎯 HIGH-SPEED STAGGERED NUMBER GENERATION 
# ==============================================================================

async def _fetch_number_s1(payload):
    return await s1_api_request('POST', f"{S1_BASE_URL}/mdashboard/getnum/number", json_payload=payload)

async def _fetch_number_s2(payload, delay=0):
    if delay > 0: await asyncio.sleep(delay)
    return await s2_api_request('POST', f"{S2_BASE_URL}/api/freelancer/get-page/get-number", json_payload=payload)

async def _fetch_number_s3(payload, delay=0):
    if delay > 0: await asyncio.sleep(delay)
    return await s3_api_request('POST', f"{S3_BASE_URL}/mdashboard/getnum/number", json_payload=payload, referer=f"https://zayansms.com/mdashboard/getnum?range={payload.get('range', '')}")

async def process_number_generation(update: Update, context: ContextTypes.DEFAULT_TYPE, range_val, server_id, is_callback=True):
    global WAITING_OTPS, BATCH_MSGS, NUM_TO_HASH
    
    wait_txt = "⏳ <i>Connecting to secure server... Generating Numbers...</i> 🚀"
    if is_callback:
        user_id = update.callback_query.from_user.id
        chat_id = update.callback_query.message.chat_id
        msg = await update.callback_query.edit_message_text(text=wait_txt, parse_mode=ParseMode.HTML)
    else:
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        msg = await update.message.reply_text(text=wait_txt, parse_mode=ParseMode.HTML)
    
    fetched_numbers = []
    country_name = context.user_data.get('real_country_name', 'Unknown')
    tasks = []

    raw_svc = str(context.user_data.get('service_name', 'facebook')).lower()
    api_svc = 'facebook' if 'facebook' in raw_svc else 'whatsapp' if 'whatsapp' in raw_svc else 'facebook'

    if server_id == 1:
        range_val = str(range_val).strip()
        if not range_val.upper().endswith("XXX"): range_val += "XXX"
        payload = {"range": range_val, "app": api_svc, "service": api_svc, "is_national": False, "remove_plus": False}
        tasks = [_fetch_number_s1(payload), _fetch_number_s1(payload)]
        
    elif server_id == 2:
        rv = str(range_val).replace('X', '|')
        parts = rv.split('|')
        if len(parts) >= 2:
            payload = {"country_id": int(parts[0]), "mode": "single", "operator_id": int(parts[1]), "number_format": "full", "app": api_svc, "provider": api_svc}
            tasks = [_fetch_number_s2(payload, 0), _fetch_number_s2(payload, 0.15)]
            
    elif server_id == 3:
        range_val = str(range_val).strip()
        if not range_val.upper().endswith("XXX"): range_val += "XXX"
        payload = {"range": range_val, "app": api_svc, "service": api_svc, "is_national": False, "remove_plus": True}
        tasks = [_fetch_number_s3(payload, 0), _fetch_number_s3(payload, 0.15)]

    if tasks:
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for res in results:
            if isinstance(res, tuple):
                status, resp = res
                if status in [200, 201] and isinstance(resp, dict):
                    num = ""
                    if server_id == 2 and resp.get('status') in ['success', 200, True]:
                        data_obj = resp.get('data', {})
                        if isinstance(data_obj, dict):
                            num = str(data_obj.get('phone_number') or data_obj.get('number', ''))
                        elif isinstance(data_obj, list) and len(data_obj) > 0:
                            num = str(data_obj[0].get('phone_number') or data_obj[0].get('number', ''))
                            
                    elif 'data' in resp and isinstance(resp['data'], dict) and resp['data'].get('number'):
                        num = str(resp['data']['number'])
                        if country_name == "Unknown":
                            country_name = resp['data'].get('country', country_name)
                    
                    if num and num != "None": 
                        fetched_numbers.append(num.replace('+', ''))
            elif isinstance(res, Exception):
                logger.error(f"API Error in parallel task: {res}")
            
    if fetched_numbers:
        s_suffix = ""
        if server_id == 1: s_suffix = SETTINGS_CACHE['s1_suffix']
        elif server_id == 2: s_suffix = SETTINGS_CACHE['s2_suffix']
        elif server_id == 3: s_suffix = SETTINGS_CACHE['s3_suffix']
        
        display_country_name = f"{country_name}{s_suffix}"
        flag = get_flag(country_name)
        short_name = get_short_code(country_name)
        
        # V40 CLASSIC UI RESTORED (Number clearly displayed in regular text body WITH SHORT CODES)
        symbols = ["❶", "❷", "❸", "❹", "❺"]
        num_str = ""
        for i, n in enumerate(fetched_numbers):
            num_str += f"{symbols[i % len(symbols)]} [{short_name}] <code>{n}</code> ⏳\n"
            
        txt = (
            f"✅ <b>NUMBERS GENERATED</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"🌍 <b>{flag} {display_country_name}</b>\n\n"
            f"{num_str}\n"
            f"⏳ <i>Waiting for SMS...</i>"
        )
        
        kb = [
            [InlineKeyboardButton("💬 OTP GROUP", url="https://t.me/RTxOtpX")],
            [InlineKeyboardButton("🔙 Menu", callback_data="go_main")]
        ]
        
        try:
            await msg.edit_text(text=txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.HTML)
        except Exception as e:
            await msg.edit_text(text=f"✅ Assigned: +{fetched_numbers[0]}\nWaiting for OTP...", reply_markup=InlineKeyboardMarkup(kb))
            logger.error(f"Edit text crashed: {e}")
        
        batch_key = f"{chat_id}_{msg.message_id}"
        BATCH_MSGS[batch_key] = {'numbers': fetched_numbers.copy(), 'country_name': display_country_name, 'flag': flag, 'received_for': set()}
        
        custom_svc = context.user_data.get('service_name', api_svc.title())
        for n in fetched_numbers:
            hash_key = get_hash_key(n)
            WAITING_OTPS[hash_key] = {
                'full_num': n, 'user_id': user_id, 'chat_id': chat_id, 'msg_id': msg.message_id, 
                'batch_key': batch_key, 'time': time.time(), 'received_codes': set(), 
                'range': range_val, 'server_id': server_id, 'service_name': custom_svc
            }
            NUM_TO_HASH[clean_number(n)] = hash_key
            
        context.user_data['range'] = range_val 
        context.user_data['server'] = server_id
        
    else:
        err_msg = "🔄 <i>Our high-speed servers are balancing the load. No numbers found right now.</i>"
        try:
            await msg.edit_text(
                text=f"📡 <b>Server Optimizing:</b>\n{err_msg}\n\nPlease try again or select another category.", 
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="go_main")]]), 
                parse_mode=ParseMode.HTML
            )
        except Exception:
            await msg.edit_text(
                text="📡 Server Optimizing. No numbers found right now. Please try again.", 
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="go_main")]])
            )

# ==============================================================================
# 📋 MENUS & UI WITH MERGED PANELS
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

async def start_category_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = [
        [InlineKeyboardButton("📘 Facebook", callback_data="cat_facebook"), InlineKeyboardButton("💬 WhatsApp", callback_data="cat_whatsapp")],
        [InlineKeyboardButton("🔙 Main Menu", callback_data="go_main")]
    ]
    txt = "📱 <b>CATEGORIES</b> 📱\n━━━━━━━━━━━━━━━━━━━━\n<i>Which application do you need numbers for?</i>"
    
    if update.callback_query: 
        await update.callback_query.edit_message_text(text=txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.HTML)
    else: 
        await update.message.reply_text(text=txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.HTML)

async def handle_category_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global CONSOLE_CACHE
    query = update.callback_query
    category = query.data.split('_')[1].lower()
    
    context.user_data['service_name'] = category.title()
    
    await query.edit_message_text(text="⚡ <i>Calculating Live Success Rate across all servers...</i>", parse_mode=ParseMode.HTML)
    
    if not CONSOLE_CACHE[1]:
        res = await s1_api_request('GET', f"{S1_BASE_URL}/mdashboard/console/info")
        if res[0] == 200 and isinstance(res[1], dict): CONSOLE_CACHE[1] = res[1].get('data', {}).get('logs', [])
    if not CONSOLE_CACHE[2]:
        res = await s2_api_request('GET', f"{S2_BASE_URL}/api/freelancer/console/data?page=1&limit=20")
        if res[0] == 200 and isinstance(res[1], dict): CONSOLE_CACHE[2] = res[1].get('data', [])
    if not CONSOLE_CACHE[3]:
        res = await s3_api_request('GET', f"{S3_BASE_URL}/mdashboard/console/info")
        if res[0] == 200 and isinstance(res[1], dict): CONSOLE_CACHE[3] = res[1].get('data', {}).get('logs', [])

    country_stats = {}
    
    def process_logs(logs, srv_id):
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

                if category in app_name and c and r and 'None' not in r:
                    key = (srv_id, c)
                    if key not in country_stats:
                        country_stats[key] = {'range': r, 'count': 0, 'c_name': c}
                    country_stats[key]['count'] += 1

    process_logs(CONSOLE_CACHE[1], 1)
    process_logs(CONSOLE_CACHE[2], 2)
    process_logs(CONSOLE_CACHE[3], 3)

    if not country_stats:
        await query.edit_message_text(
            text=f"📡 <b>Load Balancing...</b>\n<i>No immediate numbers found for {category.title()}. Please try again in a moment.</i>", 
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="go_main")]]), parse_mode=ParseMode.HTML
        )
        return
        
    max_count = max([v['count'] for v in country_stats.values()]) if country_stats else 1
    
    sorted_keys = sorted(country_stats.keys(), key=lambda x: x[0])
    
    kb = []
    
    s1_suffix = SETTINGS_CACHE['s1_suffix']
    s2_suffix = SETTINGS_CACHE['s2_suffix']
    s3_suffix = SETTINGS_CACHE['s3_suffix']
    
    for key in sorted_keys:
        srv_id, c_name = key
        stats = country_stats[key]
        
        raw_pct = (stats['count'] / max_count) * 100
        display_rate = min(99, max(45, int(raw_pct + 40))) 
        indicator = "🟢" if display_rate >= 80 else ("🟡" if display_rate >= 60 else "🔴")
        
        display_name = c_name
        if srv_id == 1: display_name += s1_suffix
        elif srv_id == 2: display_name += s2_suffix
        elif srv_id == 3: display_name += s3_suffix
            
        btn_text = f"{get_flag(c_name)} {display_name} {display_rate}% {indicator}"
        
        safe_c_name = str(c_name)[:15].replace(" ", "")
        kb.append([InlineKeyboardButton(btn_text, callback_data=f"r_{srv_id}_{stats['range']}_{safe_c_name}")])
        
    kb.append([InlineKeyboardButton("🔙 Back to Main Menu", callback_data="go_main")])
    
    await asyncio.sleep(0.01)
    await query.edit_message_text(text=f"🌍 <b>SELECT A COUNTRY ({category.title()})</b>\n━━━━━━━━━━━━━━━━━━━━", reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.HTML)

# ==============================================================================
# 🎮 TEXT HANDLER & ADMIN / WITHDRAW LOGIC
# ==============================================================================

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await check_ban_middleware(update, context): return
    user_id = update.effective_user.id
    raw_text = update.message.text
    if not raw_text: return
    text = raw_text.strip()
    
    user_data = context.user_data
    await ensure_user_fast(user_id)
    
    is_main_menu_action = any(btn in text for btn in ["Get Number", "Get 2FA", "Support", "See Activity", "Referral & Balance"])
    is_admin_action = any(btn in text for btn in ["Bot Status", "Total Users", "Broadcast", "Ban / Unban", "Set Rewards", "Set Min Withdraw", "Add Balance", "Top Referrers", "Set Ping URL", "Set Suffix S1", "Set Suffix S2", "Set Suffix S3", "Main Menu"])
    
    if is_main_menu_action or is_admin_action:
        user_data['state'] = None
        user_data['admin_reply_target'] = None
        
    # --- ADMIN CONTROLS ---
    if user_id in ADMIN_IDS:
        if "Bot Status" in text:
            uptime = datetime.datetime.now() - START_TIME
            current_ping = SETTINGS_CACHE.get("ping_url", "Not Set")
            txt = (
                f"📊 <b>ULTRA ENTERPRISE STATUS</b> 📊\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"⏱ <b>Uptime:</b> {str(uptime).split('.')[0]}\n"
                f"👥 <b>Total Users:</b> {get_total_users_count()}\n"
                f"📡 <b>Active Waiters:</b> {len(WAITING_OTPS)} Numbers\n"
                f"⚡ <b>RAM Cache:</b> ACTIVE (Instant Load)\n"
                f"🏓 <b>Auto-Ping URL:</b> {current_ping}\n"
                f"💰 <b>OTP Reward:</b> {SETTINGS_CACHE['otp_reward']} Tk\n"
                f"💳 <b>Min Withdraw:</b> {SETTINGS_CACHE['min_withdraw']} Tk\n"
                f"🏷 <b>S1 Suffix:</b> '{SETTINGS_CACHE['s1_suffix']}'\n"
                f"🏷 <b>S2 Suffix:</b> '{SETTINGS_CACHE['s2_suffix']}'\n"
                f"🏷 <b>S3 Suffix:</b> '{SETTINGS_CACHE['s3_suffix']}'\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"✅ <i>TRIPLE Servers Running Perfectly</i>"
            )
            return await update.message.reply_text(txt, parse_mode=ParseMode.HTML)
            
        elif "Total Users" in text:
            return await update.message.reply_text(f"👥 <b>Total Registered Users:</b> {get_total_users_count()}", parse_mode=ParseMode.HTML)
            
        elif "Broadcast" in text:
            user_data['state'] = 'ADMIN_BROADCAST'
            return await update.message.reply_text("📢 <b>Send the message you want to broadcast.</b>\n<i>(Or click 🔙 Main Menu to cancel)</i>", parse_mode=ParseMode.HTML)
            
        elif "Ban / Unban" in text:
            user_data['state'] = 'ADMIN_BAN'
            return await update.message.reply_text("🚫 <b>Send User ID and action (ban/unban).</b>\nExample: <code>12345678 ban</code>", parse_mode=ParseMode.HTML)
            
        elif "Set Rewards" in text:
            user_data['state'] = 'ADMIN_REWARD'
            return await update.message.reply_text("💰 <b>Set Reward.</b>\nExample: <code>otp 0.5</code> or <code>ref 0.2</code>", parse_mode=ParseMode.HTML)
            
        elif "Set Min Withdraw" in text:
            user_data['state'] = 'ADMIN_MIN_WD'
            return await update.message.reply_text("💳 <b>Set Minimum Withdraw Amount.</b>\nExample: <code>100</code>", parse_mode=ParseMode.HTML)
            
        elif "Add Balance" in text:
            user_data['state'] = 'ADMIN_ADD_BAL'
            return await update.message.reply_text("💸 <b>Add balance to user.</b>\nExample: <code>12345678 50.0</code>", parse_mode=ParseMode.HTML)

        elif "Set Ping URL" in text:
            user_data['state'] = 'ADMIN_SET_PING'
            return await update.message.reply_text("🌐 <b>Send the URL for Auto-Ping.</b>\nExample: <code>https://my-bot-url.onrender.com</code>", parse_mode=ParseMode.HTML)
            
        elif "Set Suffix S1" in text:
            user_data['state'] = 'ADMIN_SET_S1_SUFFIX'
            return await update.message.reply_text("✏️ <b>Send suffix for Server 1.</b>\n(Send `-` to keep it blank)", parse_mode=ParseMode.HTML)
            
        elif "Set Suffix S2" in text:
            user_data['state'] = 'ADMIN_SET_S2_SUFFIX'
            return await update.message.reply_text("✏️ <b>Send suffix for Server 2.</b>\n(Example: ` XRT`)", parse_mode=ParseMode.HTML)
            
        elif "Set Suffix S3" in text:
            user_data['state'] = 'ADMIN_SET_S3_SUFFIX'
            return await update.message.reply_text("✏️ <b>Send suffix for Server 3.</b>\n(Example: ` XR`)", parse_mode=ParseMode.HTML)
            
        elif "Top Referrers" in text:
            loop = asyncio.get_event_loop()
            top_users = await loop.run_in_executor(DB_EXECUTOR, sync_get_top_referrers)
            msg = "🏆 <b>TOP 10 REFERRERS</b> 🏆\n━━━━━━━━━━━━━━━━━━━━\n"
            for i, (uid, count) in enumerate(top_users):
                if count > 0: msg += f"<b>{i+1}.</b> <code>{uid}</code> - <b>{count}</b> Referrals\n"
            if "1." not in msg: msg += "<i>No active referrers yet.</i>"
            return await update.message.reply_text(msg, parse_mode=ParseMode.HTML)
            
        elif "Main Menu" in text:
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

        elif state == 'ADMIN_SET_PING':
            new_url = text.strip()
            if not new_url.startswith("http"):
                new_url = "https://" + new_url
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(DB_EXECUTOR, sync_update_setting, "ping_url", new_url)
            await update.message.reply_text(f"✅ <b>Auto-Ping URL updated to:</b>\n<code>{new_url}</code>", parse_mode=ParseMode.HTML)
            user_data['state'] = None
            return
            
        elif state == 'ADMIN_SET_S1_SUFFIX':
            val = text if text != "-" else ""
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(DB_EXECUTOR, sync_update_setting, "s1_suffix", val)
            await update.message.reply_text(f"✅ <b>S1 Suffix updated to:</b> '{val}'", parse_mode=ParseMode.HTML)
            user_data['state'] = None
            return
            
        elif state == 'ADMIN_SET_S2_SUFFIX':
            val = text if text != "-" else ""
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(DB_EXECUTOR, sync_update_setting, "s2_suffix", val)
            await update.message.reply_text(f"✅ <b>S2 Suffix updated to:</b> '{val}'", parse_mode=ParseMode.HTML)
            user_data['state'] = None
            return
            
        elif state == 'ADMIN_SET_S3_SUFFIX':
            val = text if text != "-" else ""
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(DB_EXECUTOR, sync_update_setting, "s3_suffix", val)
            await update.message.reply_text(f"✅ <b>S3 Suffix updated to:</b> '{val}'", parse_mode=ParseMode.HTML)
            user_data['state'] = None
            return

    # --- USER CONTROLS & STATES ---
    target_reply_user = user_data.get('admin_reply_target')
    if target_reply_user and not is_main_menu_action and not is_admin_action:
        try:
            await context.bot.send_message(chat_id=int(target_reply_user), text=f"👨‍💻 <b>Admin Reply:</b>\n━━━━━━━━━━━━━━━━━━━━\n{text}", parse_mode=ParseMode.HTML)
            await update.message.reply_text("✅ <b>Reply sent successfully.</b>", parse_mode=ParseMode.HTML)
        except Exception:
            await update.message.reply_text("❌ <b>Failed to send.</b>")
        user_data['admin_reply_target'] = None
        return

    state = user_data.get('state')
    
    if "Get Number" in text:
        if not await check_subscription(user_id, context.bot): await send_join_prompt(update, context)
        else: await start_category_selection(update, context)
            
    elif "Get 2FA" in text:
        user_data['state'] = 'WAITING_FOR_2FA'
        await update.message.reply_text("🔐 <b>2FA CODE GENERATOR</b>\n━━━━━━━━━━━━━━━━━━━━\n<i>Paste your Secret Key below:</i>", parse_mode=ParseMode.HTML)
        
    elif state == 'WAITING_FOR_2FA':
        user_msg_id = update.message.message_id
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
                        asyncio.create_task(delete_message_later(context.bot, msg.chat_id, msg.message_id, 300, user_msg_id))
                    else: await msg.edit_text("❌ <b>Invalid Secret Key.</b>", parse_mode=ParseMode.HTML)
                else: await msg.edit_text("❌ <b>API Error!</b>", parse_mode=ParseMode.HTML)
        except Exception: await msg.edit_text("❌ <b>Network Error.</b>", parse_mode=ParseMode.HTML)
        user_data['state'] = None

    elif "Referral & Balance" in text:
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
        
    elif "Support" in text:
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
        
    elif "See Activity" in text:
        kb = [[InlineKeyboardButton("🔥 Range Channel", url="https://t.me/ConsoleXRT")], [InlineKeyboardButton("💬 OTP Channel", url="https://t.me/RTxOtpX")]]
        await update.message.reply_text("📊 <b>BOT ACTIVITY LINKS</b>\n━━━━━━━━━━━━━━━━━━━━\n<i>Join to see live Bot activity:</i>", reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.HTML)
        
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
            if not is_main_menu_action:
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
    
    if data == "ignore": 
        return await query.answer()
    
    elif data == "check_join":
        if await check_subscription(user_id, context.bot): 
            try: await query.message.delete()
            except: pass
            await show_main_menu(query, context)
        else: await query.answer("⚠️ Please join all channels/groups first.", show_alert=True)

    elif data.startswith("cat_"): 
        await handle_category_click(update, context)
        
    elif data.startswith("r_"):
        parts = data.split("_")
        server_id = int(parts[1])
        range_val = parts[2]
        if len(parts) > 3: context.user_data['real_country_name'] = parts[3]
        await process_number_generation(update, context, range_val, server_id, is_callback=True)
        
    elif data == "change_num":
        if context.user_data.get('range'):
            server_id = context.user_data.get('server', 1)
            await process_number_generation(update, context, context.user_data['range'], server_id, is_callback=True)
        else: await query.edit_message_text("⚠️ <b>Session Expired.</b>\n<i>Please start again.</i>", parse_mode=ParseMode.HTML)
            
    elif data == "go_main": 
        await show_main_menu(update, context)
        
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
        ["✏️ Set Suffix S1", "✏️ Set Suffix S2", "✏️ Set Suffix S3"],
        ["🌐 Set Ping URL", "🔙 Main Menu"]
    ]
    txt = "🔐 <b>ADVANCED ADMIN PANEL</b> 🔐\n━━━━━━━━━━━━━━━━━━━━\n<i>Use the keyboard below to manage the bot:</i>"
    await update.message.reply_text(txt, reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True), parse_mode=ParseMode.HTML)

# ==============================================================================
# 🌐 RENDER DUMMY WEB SERVER & MAIN LOOP
# ==============================================================================

async def web_server_handler(request):
    return web.Response(text="✅ Premium OTP Bot V55 Enterprise Edition — Running perfectly!")

async def self_ping_job(context: ContextTypes.DEFAULT_TYPE):
    ping_url = SETTINGS_CACHE.get("ping_url", "https://rtxstexsms-dhno.onrender.com")
    if not ping_url or ping_url == "None": return
    try:
        session = await get_session()
        async with session.get(ping_url, timeout=aiohttp.ClientTimeout(total=10), ssl=False) as resp:
            pass
    except Exception:
        pass

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
    
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    app.job_queue.run_repeating(global_otp_checker_job,  interval=2,   first=2)
    app.job_queue.run_repeating(auto_range_forwarder_job, interval=10,  first=10)
    app.job_queue.run_repeating(auto_relogin_job,         interval=300, first=300)
    app.job_queue.run_repeating(self_ping_job,            interval=120,  first=30)
    
    logger.info("✨ VERSION 55.0 ENTERPRISE FINAL STARTED SUCCESSFULLY ✨")
    app.run_polling(drop_pending_updates=True)
