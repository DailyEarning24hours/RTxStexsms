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

# 🔥 UVLOOP FOR EXTREME SPEED (VPS OPTIMIZATION)
try:
    import uvloop
    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
except ImportError:
    pass

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

# ==============================================================================
# ⚙️ CONFIGURATION & CREDENTIALS
# ==============================================================================

TOKEN = "8784714590:AAGW1bthOSIh2HUl2vPCYS_zv13zEz7BOsg"
ADMIN_IDS = [6031032502] 

OTP_GROUP_ID = -1003830374258

# SERVER 1 (STEX SMS)
S1_EMAIL = "mdrajaislam469@gmail.com"
S1_PASSWORD = "Raja1234@#"
S1_BASE_URL = "https://stexsms.com/mapi/v1"

# SERVER 2 (CRACKERJACK SMS - NEW PANEL)
S2_EMAIL = "rtx.raja.rt@gmail.com"
S2_STATIC_TOKEN = "e7f26541-bded-4138-b0ac-0d9cff7b1838"
S2_BASE_URL = "https://crackerjacksms.com"

API_2FA = "https://2fa.cn/codes/{}"

# ==============================================================================
# 🛑 CACHING & MEMORY (VPS ENTERPRISE LEVEL)
# ==============================================================================

S1_TOKEN = None

GLOBAL_SESSION = None 
AUTH_LOCK_S1 = asyncio.Lock() 
LAST_AUTH_S1 = 0

LAST_INBOX_S1 = ""
LAST_INBOX_S2 = ""

START_TIME = datetime.datetime.now()
BASE_USER_AGENT = "Mozilla/5.0 (Linux; Android 14; SM-A135F Build/UP1A.231005.007) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.7727.55 Mobile Safari/537.36"

# 🔥 OPTIMIZED FOR VPS & MASSIVE TRAFFIC
DB_POOL_SIZE = 30
DB_EXECUTOR = concurrent.futures.ThreadPoolExecutor(max_workers=30, thread_name_prefix="db_worker")

# Max 100 concurrent number generation tasks
GENERATION_SEMAPHORE = asyncio.Semaphore(100)

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# ==============================================================================
# 🧠 SMART LRU CACHE 
# ==============================================================================

class BoundedTTLCache:
    __slots__ = ('_cache', '_max_size', '_ttl')
    def __init__(self, max_size: int, ttl: float):
        self._cache = {}
        self._max_size = max_size
        self._ttl = ttl
    def get(self, key, default=None):
        entry = self._cache.get(key)
        if entry is None: return default
        value, exp = entry
        if time.time() > exp:
            del self._cache[key]
            return default
        self._cache[key] = (value, exp)
        return value
    def set(self, key, value):
        if key in self._cache: del self._cache[key]
        elif len(self._cache) >= self._max_size:
            try:
                oldest = next(iter(self._cache))
                del self._cache[oldest]
            except StopIteration: pass
        self._cache[key] = (value, time.time() + self._ttl)
    def delete(self, key):
        self._cache.pop(key, None)
    def __contains__(self, key):
        return self.get(key) is not None
    def purge_expired(self):
        now = time.time()
        expired = [k for k, (_, exp) in self._cache.items() if now > exp]
        for k in expired: del self._cache[k]
        return len(expired)

WAITING_OTPS = {}
NUM_TO_HASH = {}
OTP_TIMEOUT_SECONDS = 1200 # 20 Mins

USER_CACHE = set()
BANNED_CACHE = set()
CHANNELS_CACHE = set()

# Increased Size for 50,000+ Users
USER_INFO_CACHE      = BoundedTTLCache(max_size=100_000, ttl=3600)
SUBSCRIPTION_CACHE   = BoundedTTLCache(max_size=100_000, ttl=43200) # 12 Hours

CONSOLE_CACHE = {1: [], 2: []}
PRECOMPUTED_MENUS = {"facebook": None, "whatsapp": None, "telegram": None} 

SETTINGS_CACHE = {
    "otp_reward": 0.10,
    "ref_reward": 0.05,
    "min_withdraw": 50.0,
    "s1_suffix": "",
    "s2_suffix": " CJ",
}

# ==============================================================================
# 🌍 FULL COUNTRY FLAGS & CODES (RESTORED COMPLETELY)
# ==============================================================================

COUNTRY_FLAGS = {
    "Afghanistan":"🇦🇫", "Albania":"🇦🇱", "Algeria":"🇩🇿", "Andorra":"🇦🇩", "Angola":"🇦🇴", "Antigua and Barbuda":"🇦🇬", "Argentina":"🇦🇷", "Armenia":"🇦🇲", "Australia":"🇦🇺", "Austria":"🇦🇹", "Azerbaijan":"🇦🇿", "Bahamas":"🇧🇸", "Bahrain":"🇧🇭", "Bangladesh":"🇧🇩", "Barbados":"🇧🇧", "Belarus":"🇧🇾", "Belgium":"🇧🇪", "Belize":"🇧🇿", "Benin":"🇧🇯", "Bhutan":"🇧🇹", "Bolivia":"🇧🇴", "Bosnia and Herzegovina":"🇧🇦", "Bosnia":"🇧🇦", "Botswana":"🇧🇼", "Brazil":"🇧🇷", "Brunei":"🇧🇳", "Bulgaria":"🇧🇬", "Burkina Faso":"🇧🇫", "Burundi":"🇧🇮", "Cabo Verde":"🇨🇻", "Cambodia":"🇰🇭", "Cameroon":"🇨🇲", "Canada":"🇨🇦", "Central African Republic":"🇨🇫", "Central Africa":"🇨🇫", "Chad":"🇹🇩", "Chile":"🇨🇱", "China":"🇨🇳", "Colombia":"🇨🇴", "Comoros":"🇰🇲", "Congo":"🇨🇬", "Democratic Republic of the Congo":"🇨🇩", "Costa Rica":"🇨🇷", "Croatia":"🇭🇷", "Cuba":"🇨🇺", "Cyprus":"🇨🇾", "Czechia":"🇨🇿", "Denmark":"🇩🇰", "Djibouti":"🇩🇯", "Dominica":"🇩🇲", "Dominican Republic":"🇩🇴", "East Timor":"🇹🇱", "Ecuador":"🇪🇨", "Egypt":"🇪🇬", "El Salvador":"🇸🇻", "Equatorial Guinea":"🇬🇶", "Eritrea":"🇪🇷", "Estonia":"🇪🇪", "Eswatini":"🇸🇿", "Ethiopia":"🇪🇹", "Fiji":"🇫🇯", "Finland":"🇫🇮", "France":"🇫🇷", "Gabon":"🇬🇦", "Gambia":"🇬🇲", "Georgia":"🇬🇪", "Germany":"🇩🇪", "Ghana":"🇬🇭", "Greece":"🇬🇷", "Grenada":"🇬🇩", "Guatemala":"🇬🇹", "Guinea":"🇬🇳", "Guinea-Bissau":"🇬🇼", "Guyana":"🇬🇾", "Haiti":"🇭🇹", "Honduras":"🇭🇳", "Hungary":"🇭🇺", "Iceland":"🇮🇸", "India":"🇮🇳", "Indonesia":"🇮🇩", "Iran":"🇮🇷", "Iraq":"🇮🇶", "Ireland":"🇮🇪", "Israel":"🇮🇱", "Italy":"🇮🇹", "Ivory Coast":"🇨🇮", "Jamaica":"🇯🇲", "Japan":"🇯🇵", "Jordan":"🇯🇴", "Kazakhstan":"🇰🇿", "Kenya":"🇰🇪", "Kiribati":"🇰🇮", "Kuwait":"🇰🇼", "Kyrgyzstan":"🇰🇬", "Laos":"🇱🇦", "Latvia":"🇱🇻", "Lebanon":"🇱🇧", "Lesotho":"🇱🇸", "Liberia":"🇱🇷", "Libya":"🇱🇾", "Liechtenstein":"🇱🇮", "Lithuania":"🇱🇹", "Luxembourg":"🇱🇺", "Madagascar":"🇲🇬", "Malawi":"🇲🇼", "Malaysia":"🇲🇾", "Maldives":"🇲🇻", "Mali":"🇲🇱", "Malta":"🇲🇹", "Marshall Islands":"🇲🇭", "Mauritania":"🇲🇷", "Mauritius":"🇲🇺", "Mexico":"🇲🇽", "Micronesia":"🇫🇲", "Moldova":"🇲🇩", "Monaco":"🇲🇨", "Mongolia":"🇲🇳", "Montenegro":"🇲🇪", "Morocco":"🇲🇦", "Mozambique":"🇲🇿", "Myanmar":"🇲🇲", "Namibia":"🇳🇦", "Nauru":"🇳🇷", "Nepal":"🇳🇵", "Netherlands":"🇳🇱", "New Zealand":"🇳🇿", "Nicaragua":"🇳🇮", "Niger":"🇳🇪", "Nigeria":"🇳🇬", "North Korea":"🇰🇵", "North Macedonia":"🇲🇰", "Norway":"🇳🇴", "Oman":"🇴🇲", "Pakistan":"🇵🇰", "Palau":"🇵🇼", "Palestine":"🇵🇸", "Panama":"🇵🇦", "Papua New Guinea":"🇵🇬", "Paraguay":"🇵🇾", "Peru":"🇵🇪", "Philippines":"🇵🇭", "Poland":"🇵🇱", "Portugal":"🇵🇹", "Qatar":"🇶🇦", "Romania":"🇷🇴", "Russia":"🇷🇺", "Rwanda":"🇷🇼", "Saint Kitts and Nevis":"🇰🇳", "Saint Lucia":"🇱🇨", "Saint Vincent and the Grenadines":"🇻🇨", "Samoa":"🇼🇸", "San Marino":"🇸🇲", "Sao Tome and Principe":"🇸🇹", "Saudi Arabia":"🇸🇦", "Senegal":"🇸🇳", "Serbia":"🇷🇸", "Seychelles":"🇸🇨", "Sierra Leone":"🇸🇱", "Singapore":"🇸🇬", "Slovakia":"🇸🇰", "Slovenia":"🇸🇮", "Solomon Islands":"🇸🇧", "Somalia":"🇸🇴", "South Africa":"🇿🇦", "South Korea":"🇰🇷", "South Sudan":"🇸🇸", "Spain":"🇪🇸", "Sri Lanka":"🇱🇰", "Sudan":"🇸🇩", "Suriname":"🇸🇷", "Sweden":"🇸🇪", "Switzerland":"🇨🇭", "Syria":"🇸🇾", "Taiwan":"🇹🇼", "Tajikistan":"🇹🇯", "Tanzania":"🇹🇿", "Thailand":"🇹🇭", "Togo":"🇹🇬", "Tunisia":"🇹🇳", "Turkey":"🇹🇷", "Turkmenistan":"TM", "Uganda":"🇺🇬", "Ukraine":"🇺🇦", "United Arab Emirates":"🇦🇪", "United Kingdom":"🇬🇧", "United States":"🇺🇸", "Uruguay":"🇺🇾", "Uzbekistan":"🇺🇿", "Vanuatu":"🇻🇺", "Venezuela":"🇻🇪", "Vietnam":"🇻🇳", "Yemen":"🇾🇪", "Zambia":"🇿🇲", "Zimbabwe":"🇿🇼"
}

COUNTRY_CODES = {
    "Afghanistan":"AF", "Albania":"AL", "Algeria":"DZ", "Andorra":"AD", "Angola":"AO", "Argentina":"AR", "Armenia":"AM", "Australia":"AU", "Austria":"AT", "Azerbaijan":"AZ", "Bahamas":"BS", "Bahrain":"BH", "Bangladesh":"BD", "Barbados":"BB", "Belarus":"BY", "Belgium":"BE", "Belize":"BZ", "Benin":"BJ", "Bhutan":"BT", "Bolivia":"BO", "Bosnia":"BA", "Botswana":"BW", "Brazil":"BR", "Brunei":"BN", "Bulgaria":"BG", "Burkina Faso":"BF", "Burundi":"BI", "Cambodia":"KH", "Cameroon":"CM", "Canada":"CA", "Central African Republic":"CF", "Chad":"TD", "Chile":"CL", "China":"CN", "Colombia":"CO", "Comoros":"KM", "Congo":"CG", "Costa Rica":"CR", "Croatia":"HR", "Cuba":"CU", "Cyprus":"CY", "Czechia":"CZ", "Denmark":"DK", "Djibouti":"DJ", "Dominican Republic":"DO", "Ecuador":"EC", "Egypt":"EG", "El Salvador":"SV", "Equatorial Guinea":"GQ", "Eritrea":"ER", "Estonia":"EE", "Eswatini":"SZ", "Ethiopia":"ET", "Fiji":"FJ", "Finland":"FI", "France":"FR", "Gabon":"GA", "Gambia":"GM", "Georgia":"GE", "Germany":"DE", "Ghana":"GH", "Greece":"GR", "Grenada":"GD", "Guatemala":"GT", "Guinea":"GN", "Guinea-Bissau":"GW", "Guyana":"GY", "Haiti":"HT", "Honduras":"HN", "Hungary":"HU", "Iceland":"IS", "India":"IN", "Indonesia":"ID", "Iran":"IR", "Iraq":"IQ", "Ireland":"IE", "Israel":"IL", "Italy":"IT", "Jamaica":"JM", "Japan":"JP", "Jordan":"JO", "Kazakhstan":"KZ", "Kenya":"KE", "Kuwait":"KW", "Kyrgyzstan":"KG", "Laos":"LA", "Latvia":"LV", "Lebanon":"LB", "Lesotho":"LS", "Liberia":"LR", "Libya":"LY", "Lithuania":"LT", "Luxembourg":"LU", "Madagascar":"MG", "Malawi":"MW", "Malaysia":"MY", "Maldives":"MV", "Mali":"ML", "Malta":"MT", "Mauritania":"MR", "Mauritius":"MU", "Mexico":"MX", "Moldova":"MD", "Monaco":"MC", "Mongolia":"MN", "Montenegro":"ME", "Morocco":"MA", "Mozambique":"MZ", "Myanmar":"MM", "Namibia":"NA", "Nepal":"NP", "Netherlands":"NL", "New Zealand":"NZ", "Nicaragua":"NI", "Niger":"NE", "Nigeria":"NG", "North Korea":"KP", "Norway":"NO", "Oman":"OM", "Pakistan":"PK", "Palau":"PW", "Palestine":"PS", "Panama":"PA", "Paraguay":"PY", "Peru":"PE", "Philippines":"PH", "Poland":"PL", "Portugal":"PT", "Qatar":"QA", "Romania":"RO", "Russia":"RU", "Rwanda":"RW", "Saudi Arabia":"SA", "Senegal":"SN", "Serbia":"RS", "Seychelles":"SC", "Sierra Leone":"SL", "Singapore":"SG", "Slovakia":"SK", "Slovenia":"SI", "Somalia":"SO", "South Africa":"ZA", "South Korea":"KR", "South Sudan":"SS", "Spain":"ES", "Sri Lanka":"LK", "Sudan":"SD", "Suriname":"SR", "Sweden":"SE", "Switzerland":"CH", "Syria":"SY", "Taiwan":"TW", "Tajikistan":"TJ", "Tanzania":"TZ", "Thailand":"TH", "Togo":"TG", "Tunisia":"TN", "Turkey":"TR", "Turkmenistan":"TM", "Uganda":"UG", "Ukraine":"UA", "United Arab Emirates":"AE", "United Kingdom":"GB", "United States":"US", "Uruguay":"UY", "Uzbekistan":"UZ", "Vanuatu":"VU", "Venezuela":"VE", "Vietnam":"VN", "Yemen":"YE", "Zambia":"ZM", "Zimbabwe":"ZW"
}

COUNTRY_DIAL_CODES = {
    "Afghanistan": "93", "Albania": "355", "Algeria": "213", "Andorra": "376", "Angola": "244", "Argentina": "54", "Armenia": "374", "Australia": "61", "Austria": "43", "Azerbaijan": "994", "Bahamas": "1", "Bahrain": "973", "Bangladesh": "880", "Barbados": "1", "Belarus": "375", "Belgium": "32", "Belize": "501", "Benin": "229", "Bhutan": "975", "Bolivia": "591", "Bosnia": "387", "Botswana": "267", "Brazil": "55", "Bulgaria": "359", "Burkina Faso": "226", "Burundi": "257", "Cambodia": "855", "Cameroon": "237", "Canada": "1", "Chad": "235", "Chile": "56", "China": "86", "Colombia": "57", "Comoros": "269", "Congo": "242", "Costa Rica": "506", "Croatia": "385", "Cuba": "53", "Cyprus": "357", "Czechia": "420", "Denmark": "45", "Djibouti": "253", "Ecuador": "593", "Egypt": "20", "El Salvador": "503", "Estonia": "372", "Ethiopia": "251", "Fiji": "679", "Finland": "358", "France": "33", "Gabon": "241", "Gambia": "220", "Georgia": "995", "Germany": "49", "Ghana": "233", "Greece": "30", "Guatemala": "502", "Guinea": "224", "Guyana": "592", "Haiti": "509", "Honduras": "504", "Hungary": "36", "Iceland": "354", "India": "91", "Indonesia": "62", "Iran": "98", "Iraq": "964", "Ireland": "353", "Israel": "972", "Italy": "39", "Ivory Coast": "225", "Jamaica": "1", "Japan": "81", "Jordan": "962", "Kazakhstan": "7", "Kenya": "254", "Kuwait": "965", "Kyrgyzstan": "996", "Laos": "856", "Latvia": "371", "Lebanon": "961", "Liberia": "231", "Libya": "218", "Lithuania": "370", "Luxembourg": "352", "Madagascar": "261", "Malawi": "265", "Malaysia": "60", "Maldives": "960", "Mali": "223", "Malta": "356", "Mauritania": "222", "Mauritius": "230", "Mexico": "52", "Moldova": "373", "Monaco": "377", "Mongolia": "976", "Montenegro": "382", "Morocco": "212", "Mozambique": "258", "Myanmar": "95", "Namibia": "264", "Nepal": "977", "Netherlands": "31", "New Zealand": "64", "Nicaragua": "505", "Niger": "227", "Nigeria": "234", "North Korea": "850", "North Macedonia": "389", "Norway": "47", "Oman": "968", "Pakistan": "92", "Palestine": "970", "Panama": "507", "Paraguay": "595", "Peru": "51", "Philippines": "63", "Poland": "48", "Portugal": "351", "Qatar": "974", "Romania": "40", "Russia": "7", "Rwanda": "250", "Saudi Arabia": "966", "Senegal": "221", "Serbia": "381", "Sierra Leone": "232", "Singapore": "65", "Slovakia": "421", "Slovenia": "386", "Somalia": "252", "South Africa": "27", "South Korea": "82", "Spain": "34", "Sri Lanka": "94", "Sudan": "249", "Sweden": "46", "Switzerland": "41", "Syria": "963", "Taiwan": "886", "Tajikistan": "992", "Tanzania": "255", "Thailand": "66", "Togo": "228", "Tunisia": "216", "Turkey": "90", "Turkmenistan": "993", "Uganda": "256", "Ukraine": "380", "United Arab Emirates": "971", "United Kingdom": "44", "United States": "1", "Uruguay": "598", "Uzbekistan": "998", "Venezuela": "58", "Vietnam": "84", "Yemen": "967", "Zambia": "260", "Zimbabwe": "263"
}

def get_flag(country_name):
    clean_name = str(country_name).replace(SETTINGS_CACHE['s1_suffix'], "").replace(SETTINGS_CACHE['s2_suffix'], "")
    clean_name = re.sub(r'(?i)\bpostpaid\b', '', clean_name).strip()
    if clean_name in COUNTRY_FLAGS: return COUNTRY_FLAGS[clean_name]
    clean_no_space = clean_name.replace(" ", "").lower()
    for name, flag in COUNTRY_FLAGS.items():
        if name.replace(" ", "").lower() in clean_no_space or clean_no_space in name.replace(" ", "").lower(): 
            return flag
    return "🚩"

def get_short_code(country_name):
    clean_name = str(country_name).replace(SETTINGS_CACHE['s1_suffix'], "").replace(SETTINGS_CACHE['s2_suffix'], "")
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
    return digits[:2] + ('X' * (len(digits) - 6)) + digits[-4:]

def format_cj_carrier(carrier_name):
    if not carrier_name: return ""
    country_str = carrier_name.split()[0].title()
    code = COUNTRY_DIAL_CODES.get(country_str, "")
    formatted_name = carrier_name.lower().replace(" - ", "-").replace(" ", "-")
    return f"{code}|{formatted_name}" if code else formatted_name

def extract_code(message):
    msg = str(message)
    wa_match = re.search(r'\b(\d{3})-(\d{3})\b', msg)
    if wa_match: return wa_match.group(1) + wa_match.group(2)
    kw = re.search(r'(?:otp|code|verification|verify|pin|passcode|password)[^0-9]{0,25}(\d{4,8})', msg, re.IGNORECASE)
    if kw: return kw.group(1)
    fb = re.search(r'\b(\d{4,8})\b', msg)
    return fb.group(1) if fb else "See Msg"

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
# 🗄️ DATABASE (VPS LEVEL CONFIG)
# ==============================================================================

DB_FILE = "bot_v83_enterprise.db"

class DatabasePool:
    def __init__(self, db_file, pool_size=30):
        self.db_file = db_file
        self.pool_size = pool_size
    @contextmanager
    def get_connection(self):
        conn = sqlite3.connect(self.db_file, timeout=60.0, check_same_thread=False)
        conn.execute('PRAGMA journal_mode=WAL;') 
        conn.execute('PRAGMA synchronous=OFF;')  
        conn.execute('PRAGMA temp_store=MEMORY;')
        conn.execute('PRAGMA cache_size=-10000;')
        conn.execute('PRAGMA mmap_size=3000000000;') 
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
        
        c.execute('''CREATE TABLE IF NOT EXISTS settings (
            id INTEGER PRIMARY KEY, otp_reward REAL DEFAULT 0.10, ref_reward REAL DEFAULT 0.05, min_withdraw REAL DEFAULT 50.0, 
            s1_suffix TEXT DEFAULT '', s2_suffix TEXT DEFAULT ' CJ'
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS channels (
            id INTEGER PRIMARY KEY AUTOINCREMENT, channel_username TEXT UNIQUE
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS withdrawals (
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, amount REAL,
            method TEXT, account TEXT, status TEXT DEFAULT 'pending', date TEXT DEFAULT CURRENT_TIMESTAMP
        )''')
        
        c.execute("SELECT otp_reward, ref_reward, min_withdraw, s1_suffix, s2_suffix FROM settings WHERE id=1")
        settings_row = c.fetchone()
        if not settings_row:
            c.execute("INSERT INTO settings (id, otp_reward, ref_reward, min_withdraw, s1_suffix, s2_suffix) VALUES (1, 0.10, 0.05, 50.0, '', ' CJ')")
        else:
            SETTINGS_CACHE["otp_reward"] = settings_row[0]
            SETTINGS_CACHE["ref_reward"] = settings_row[1]
            SETTINGS_CACHE["min_withdraw"] = float(settings_row[2]) if settings_row[2] else 50.0
            SETTINGS_CACHE["s1_suffix"] = settings_row[3] if settings_row[3] else ""
            SETTINGS_CACHE["s2_suffix"] = settings_row[4] if settings_row[4] else " CJ"
            
        c.execute("SELECT channel_username FROM channels")
        CHANNELS_CACHE.clear()
        rows = c.fetchall()
        if not rows:
            default_channels = ["@EarnXtract", "@RTx_Sms", "@ConsoleXRT", "@RTxOtpX"]
            for ch in default_channels:
                c.execute("INSERT OR IGNORE INTO channels (channel_username) VALUES (?)", (ch,))
                CHANNELS_CACHE.add(ch)
        else:
            for r in rows: CHANNELS_CACHE.add(r[0])
            
        conn.commit()
        
        c.execute("SELECT user_id, is_banned FROM users")
        USER_CACHE.clear(); BANNED_CACHE.clear()
        for row in c.fetchall():
            USER_CACHE.add(row[0])
            if row[1] == 1: BANNED_CACHE.add(row[0])

def sync_register_user_db(user_id, referrer_id=None):
    with db_pool.get_connection() as conn:
        c = conn.cursor()
        c.execute("SELECT user_id FROM users WHERE user_id=?", (user_id,))
        if not c.fetchone():
            c.execute("INSERT INTO users (user_id, join_date, referrer_id) VALUES (?, CURRENT_TIMESTAMP, ?)", (user_id, referrer_id))
            USER_INFO_CACHE.set(user_id, {"balance": 0.0, "referrer_id": referrer_id, "total_referrals": 0, "ref_earnings": 0.0})
            if referrer_id: 
                c.execute("UPDATE users SET total_referrals = total_referrals + 1 WHERE user_id=?", (referrer_id,))
                _ref_data = USER_INFO_CACHE.get(referrer_id)
                if _ref_data: 
                    _ref_data["total_referrals"] += 1
                    USER_INFO_CACHE.set(referrer_id, _ref_data)
        conn.commit()

async def ensure_user_fast(user_id, referrer_id=None):
    if user_id in USER_CACHE: return True
    USER_CACHE.add(user_id)
    if user_id not in USER_INFO_CACHE:
        USER_INFO_CACHE.set(user_id, {"balance": 0.0, "referrer_id": referrer_id, "total_referrals": 0, "ref_earnings": 0.0})
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
    cached = USER_INFO_CACHE.get(user_id)
    if cached is not None: return cached
    with db_pool.get_connection() as conn:
        c = conn.cursor()
        c.execute("SELECT balance, total_referrals, referrer_id, ref_earnings FROM users WHERE user_id=?", (user_id,))
        row = c.fetchone()
        if row:
            data = {"balance": row[0], "total_referrals": row[1], "referrer_id": row[2], "ref_earnings": row[3]}
            USER_INFO_CACHE.set(user_id, data)
            return data
        return {"balance": 0.0, "total_referrals": 0, "referrer_id": None, "ref_earnings": 0.0}

def sync_add_balance(user_id, amount):
    with db_pool.get_connection() as conn:
        c = conn.cursor()
        c.execute("UPDATE users SET balance = balance + ? WHERE user_id=?", (amount, user_id))
        c.execute("SELECT balance FROM users WHERE user_id=?", (user_id,))
        new_bal = c.fetchone()[0]
        _d = USER_INFO_CACHE.get(user_id)
        if _d: _d["balance"] = new_bal; USER_INFO_CACHE.set(user_id, _d)
        conn.commit()
        return new_bal

def sync_update_setting(key, value):
    with db_pool.get_connection() as conn:
        c = conn.cursor()
        settings_map = {"otp": "otp_reward", "ref": "ref_reward", "min_withdraw": "min_withdraw", "s1_suffix": "s1_suffix", "s2_suffix": "s2_suffix"}
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
        _d = USER_INFO_CACHE.get(user_id)
        if _d: _d["balance"] -= amount; USER_INFO_CACHE.set(user_id, _d)
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
            _d = USER_INFO_CACHE.get(user_id)
            if _d: _d["balance"] += amount; USER_INFO_CACHE.set(user_id, _d)
        elif status == 'approved':
            c.execute("SELECT referrer_id FROM users WHERE user_id=?", (user_id,))
            ref_row = c.fetchone()
            if ref_row and ref_row[0]:
                referrer_id = ref_row[0]
                ref_bonus = amount * 0.10
                c.execute("UPDATE users SET balance = balance + ?, ref_earnings = ref_earnings + ? WHERE user_id=?", (ref_bonus, ref_bonus, referrer_id))
                _rd = USER_INFO_CACHE.get(referrer_id)
                if _rd:
                    _rd["balance"] += ref_bonus; _rd["ref_earnings"] += ref_bonus
                    USER_INFO_CACHE.set(referrer_id, _rd)

        conn.commit()
        return True, user_id, amount, referrer_id, ref_bonus

def sync_checkpoint():
    with db_pool.get_connection() as conn:
        conn.execute("PRAGMA wal_checkpoint(TRUNCATE);")

# ==============================================================================
# 🔐 AUTHENTICATION & API CALLS
# ==============================================================================

async def get_session():
    global GLOBAL_SESSION
    if GLOBAL_SESSION is None or GLOBAL_SESSION.closed:
        connector = aiohttp.TCPConnector(limit=250, enable_cleanup_closed=True, ttl_dns_cache=600, use_dns_cache=True)
        timeout = aiohttp.ClientTimeout(total=15, connect=4)
        GLOBAL_SESSION = aiohttp.ClientSession(connector=connector, cookie_jar=aiohttp.CookieJar(unsafe=True), timeout=timeout)
    return GLOBAL_SESSION

async def auth_s1(force=False):
    global S1_TOKEN, LAST_AUTH_S1
    async with AUTH_LOCK_S1:
        if not force and time.time() - LAST_AUTH_S1 < 300 and S1_TOKEN: return True
        payload = {"email": S1_EMAIL, "password": S1_PASSWORD}
        headers = {
            "User-Agent": BASE_USER_AGENT, 
            "Accept": "application/json, text/plain, */*",
            "Content-Type": "application/json", 
            "Origin": "https://stexsms.com", 
            "Referer": "https://stexsms.com/",
            "Connection": "keep-alive"
        }
        try:
            session = await get_session()
            async with session.post(f"{S1_BASE_URL}/mauth/login", json=payload, headers=headers, timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    if data and str(data.get('meta', {}).get('code')) == '200':
                        S1_TOKEN = data['data']['token']
                        LAST_AUTH_S1 = time.time()
                        return True
        except Exception: pass
        return False

async def s1_api_request(method, url, json_payload=None, return_text=False):
    global S1_TOKEN
    for _ in range(2):
        try:
            if not S1_TOKEN and not await auth_s1(): continue
            session = await get_session()
            headers = {
                "User-Agent": BASE_USER_AGENT, 
                "mauthtoken": str(S1_TOKEN), 
                "Cookie": f"mauthtoken={S1_TOKEN}",
                "Accept": "application/json",
                "Connection": "keep-alive"
            }
            if method.upper() == 'GET': response = await session.get(url, headers=headers, timeout=8.0)
            else: response = await session.post(url, json=json_payload, headers=headers, timeout=8.0)
            
            if response.status in [401, 403]: S1_TOKEN = None; continue
            if response.status == 200:
                text = await response.text()
                if return_text: return 200, text
                try: return 200, json.loads(text)
                except: return 200, None
            return response.status, None
        except Exception as e: pass
    return 500, None

async def s2_api_request(method, endpoint, return_text=False):
    """ New Crackerjack API Wrapper Using Static Token """
    for _ in range(2):
        try:
            session = await get_session()
            headers = {
                "User-Agent": BASE_USER_AGENT,
                "auth-token": S2_STATIC_TOKEN,
                "X-Requested-With": "XMLHttpRequest",
                "Referer": "https://crackerjacksms.com/",
                "Accept": "application/json, text/javascript, */*; q=0.01"
            }
            cookies = {"authToken": S2_STATIC_TOKEN, "authRole": "Pro"}
            url = f"{S2_BASE_URL}{endpoint}"
            
            if method.upper() == 'GET':
                async with session.get(url, headers=headers, cookies=cookies, timeout=6.0) as resp:
                    if resp.status == 200:
                        text = await resp.text()
                        if return_text: return 200, text
                        try: return 200, json.loads(text)
                        except: return 200, None
        except Exception: pass
    return 500, None

# ==============================================================================
# 🔍 FACEBOOK ACCOUNT CHECKER
# ==============================================================================

async def check_facebook_account(number):
    try:
        session = await get_session()
        headers = {
            "User-Agent": BASE_USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "Sec-Fetch-Site": "same-origin",
            "Sec-Fetch-Mode": "navigate",
        }
        
        get_url = "https://limited.facebook.com/login/identify/?ctx=recover&c=%2Flogin%2F&search_attempts=1&ars=facebook_login&alternate_search=0&show_friend_search_filtered_list=0&birth_month_search=0&city_search=0"
        async with session.get(get_url, headers=headers, timeout=6.0) as resp:
            html_get = await resp.text()
            lsd_match = re.search(r'name="lsd" value="([^"]+)"', html_get)
            jazoest_match = re.search(r'name="jazoest" value="([^"]+)"', html_get)
            
            lsd = lsd_match.group(1) if lsd_match else ""
            jazoest = jazoest_match.group(1) if jazoest_match else ""

        if not lsd: return False

        post_url = get_url
        payload = {"lsd": lsd, "jazoest": jazoest, "email": str(number), "did_submit": "Search"}
        
        post_headers = headers.copy()
        post_headers["Origin"] = "https://limited.facebook.com"
        post_headers["Referer"] = get_url
        post_headers["Content-Type"] = "application/x-www-form-urlencoded"
        
        async with session.post(post_url, data=payload, headers=post_headers, timeout=8.0) as resp:
            html_post = await resp.text()
            
            if "Choose your account" in html_post or "profile/pic.php" in html_post or "Send code via SMS" in html_post or 'class="title mfsl fcb"' in html_post:
                return True
    except Exception as e:
        pass
    return False

async def auto_relogin_job(context: ContextTypes.DEFAULT_TYPE):
    await auth_s1(force=True)

async def memory_cleanup_job(context: ContextTypes.DEFAULT_TYPE):
    try:
        SUBSCRIPTION_CACHE.purge_expired()
        USER_INFO_CACHE.purge_expired()
        gc.collect()
    except Exception: pass

# ==============================================================================
# 🔒 MIDDLEWARES & UI
# ==============================================================================

async def check_subscription(user_id, bot, force=False):
    if not CHANNELS_CACHE: return True
    if not force:
        cached = SUBSCRIPTION_CACHE.get(user_id)
        if cached is not None: return cached 
    try:
        checks = await asyncio.gather(*[bot.get_chat_member(chat_id=ch, user_id=user_id) for ch in CHANNELS_CACHE], return_exceptions=True)
        for result in checks:
            if isinstance(result, Exception) or result.status in ["left", "kicked"]:
                SUBSCRIPTION_CACHE.set(user_id, False); return False
        SUBSCRIPTION_CACHE.set(user_id, True); return True
    except Exception:
        SUBSCRIPTION_CACHE.set(user_id, False); return False

async def send_join_prompt(update, context):
    keyboard = []
    row = []
    for i, c in enumerate(CHANNELS_CACHE):
        row.append({"text": f"🔗 Join {i+1}", "url": f"https://t.me/{c.replace('@', '')}", "style": "primary"})
        if len(row) == 2: keyboard.append(row); row = []
    if row: keyboard.append(row)
    keyboard.append([{"text": "✅ Join Done", "callback_data": "check_join", "style": "success"}])
    msg = "⛔ <b>You must join our channels to use this bot!</b>"
    if update.callback_query: await update.callback_query.edit_message_text(text=msg, reply_markup={"inline_keyboard": keyboard}, parse_mode=ParseMode.HTML)
    else: await update.message.reply_text(text=msg, reply_markup={"inline_keyboard": keyboard}, parse_mode=ParseMode.HTML)

async def check_ban_middleware(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if is_user_banned_fast(update.effective_user.id):
        if update.callback_query: await update.callback_query.answer("🚫 You are banned.", show_alert=True)
        else: await update.message.reply_text("🚫 <b>You have been banned.</b>", parse_mode=ParseMode.HTML)
        return True
    return False

# ==============================================================================
# 🚀 ULTRA-FAST OTP POLLER
# ==============================================================================

async def process_found_otp(context, hash_key, api_num, code_only, svc_name, raw_msg, is_multi=False, display_country_name="Unknown"):
    global WAITING_OTPS, NUM_TO_HASH
    user_data = WAITING_OTPS.get(hash_key)
    if not user_data: return
    
    user_id = user_data['user_id']
    chat_id = user_data['chat_id']
    full_num = user_data['full_num']
    c_name = user_data.get('country_name', display_country_name)
    
    custom_svc = user_data.get('service_name', svc_name).title()
    loop = asyncio.get_event_loop()
    
    user_info_before = await loop.run_in_executor(DB_EXECUTOR, sync_get_user_info, user_id)
    old_bal = user_info_before['balance']
    new_bal = await loop.run_in_executor(DB_EXECUTOR, sync_add_balance, user_id, SETTINGS_CACHE["otp_reward"])

    svc_display = "𝐹𝑏" if "facebook" in custom_svc.lower() else ("𝑊𝑠" if "whatsapp" in custom_svc.lower() else ("𝑇𝑔" if "telegram" in custom_svc.lower() else custom_svc[:2].title()))
    
    user_msg = (
        f"💬 <b>ɴᴇᴡ Oᴛᴘ Rᴇᴄɪᴠᴇᴅ</b>\n"
        f"╭─────────────────╮\n│  <code>+{full_num}</code>\n╰─────────────────╯\n"
        f"🟢 <b>Sᴇʀᴠɪᴄᴇ » {custom_svc}</b>\n"
        f"💰 <b>Bᴀʟᴀɴᴄᴇ - {old_bal:.2f} » {new_bal:.2f}</b>"
    )
    user_markup = {"inline_keyboard": [[{"text": str(code_only), "copy_text": {"text": str(code_only)}}]]}
    try: await context.bot.send_message(chat_id=chat_id, text=user_msg, reply_markup=user_markup, parse_mode=ParseMode.HTML)
    except: pass
    
    group_msg = f"╭─────────────────╮\n│  <b>{get_flag(c_name)} #{get_short_code(c_name)} » {svc_display} {mask_number_group(full_num)}</b>\n╰─────────────────╯"
    group_markup = {"inline_keyboard": [[{"text": str(code_only), "copy_text": {"text": str(code_only)}}], [{"text": "📢 Channel", "url": "https://t.me/EarnXtract"}]]}
    try: await context.bot.send_message(chat_id=OTP_GROUP_ID, text=group_msg, reply_markup=group_markup, parse_mode=ParseMode.HTML)
    except: pass

async def global_otp_checker_job(context: ContextTypes.DEFAULT_TYPE):
    global WAITING_OTPS, NUM_TO_HASH, LAST_INBOX_S1, LAST_INBOX_S2
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

    s1_task = asyncio.create_task(s1_api_request('GET', f"{S1_BASE_URL}/mdashboard/getnum/info?date={date_str}&page=1", return_text=True))
    
    s2_url = "/api/?page_no=1&filter%5B0%5D%5Bname%5D=status&filter%5B0%5D%5Bvalue%5D=All&filter%5B1%5D%5Bname%5D=length&filter%5B1%5D%5Bvalue%5D=30"
    s2_task = asyncio.create_task(s2_api_request('GET', s2_url, return_text=True))
    
    results = await asyncio.gather(s1_task, s2_task, return_exceptions=True)
    
    # Process S1 Inbox
    if not isinstance(results[0], Exception) and results[0][0] == 200 and results[0][1] != LAST_INBOX_S1:
        LAST_INBOX_S1 = results[0][1]
        try:
            for item in json.loads(LAST_INBOX_S1).get('data', {}).get('numbers', []):
                num_raw = str(item.get('number', '')).replace('+', '')
                raw_msg = item.get('sms_text', '')
                if not num_raw or not raw_msg: continue
                hash_key, waiter = _find_waiter(num_raw)
                if hash_key:
                    code_val = extract_code(raw_msg)
                    msg_sig = f"{code_val}_{str(raw_msg)[:15]}"
                    rcv_set = waiter.setdefault('received_codes', set())
                    if msg_sig not in rcv_set:
                        rcv_set.add(msg_sig)
                        await process_found_otp(context, hash_key, waiter['full_num'], code_val, item.get('app_name', ''), raw_msg, len(rcv_set) > 1, waiter.get('country_name'))
        except: pass

    # Process S2 (Crackerjack) Inbox
    if not isinstance(results[1], Exception) and results[1][0] == 200 and results[1][1] != LAST_INBOX_S2:
        LAST_INBOX_S2 = results[1][1]
        try:
            for item in json.loads(LAST_INBOX_S2).get('data', []):
                code = item.get('otp_code')
                status = item.get('status')
                if code and status == "Active":
                    num_raw = str(item.get('did', '')).replace('+', '')
                    raw_msg = item.get('last_message', '')
                    if not num_raw or not raw_msg: continue
                    
                    hash_key, waiter = _find_waiter(num_raw)
                    if hash_key:
                        msg_sig = f"{code}_{str(raw_msg)[:15]}"
                        rcv_set = waiter.setdefault('received_codes', set())
                        if msg_sig not in rcv_set:
                            rcv_set.add(msg_sig)
                            await process_found_otp(context, hash_key, waiter['full_num'], code, item.get('app', 'Service'), raw_msg, len(rcv_set) > 1, waiter.get('country_name'))
        except: pass

# ==============================================================================
# 🎯 HIGH-SPEED NUMBER GENERATION 
# ==============================================================================

async def _fetch_number_s1(payload): return await s1_api_request('POST', f"{S1_BASE_URL}/mdashboard/getnum/number", json_payload=payload)
async def _fetch_number_s2(url): return await s2_api_request('GET', url)

async def safe_delayed_fetch(delay, func, *args, **kwargs):
    if delay > 0: await asyncio.sleep(delay)
    return await func(*args, **kwargs)

async def process_number_generation(update: Update, context: ContextTypes.DEFAULT_TYPE, range_val, server_id, is_callback=True):
    global WAITING_OTPS, NUM_TO_HASH
    async with GENERATION_SEMAPHORE:
      wait_txt = "<b>⏳ 𝗖𝗼𝗻𝗻𝗲𝗰𝘁𝗶𝗻𝗴... 𝗚𝗲𝗻𝗲𝗿𝗮𝘁𝗶𝗻𝗴 𝗡𝘂𝗺𝗯𝗲𝗿𝘀... 🚀</b>"
      if is_callback:
          user_id = update.callback_query.from_user.id
          chat_id = update.callback_query.message.chat_id
          msg = await update.callback_query.edit_message_text(text=wait_txt, parse_mode=ParseMode.HTML)
      else:
          user_id = update.effective_user.id
          chat_id = update.effective_chat.id
          msg = await update.message.reply_text(text=wait_txt, parse_mode=ParseMode.HTML)
      
      country_name = context.user_data.get('real_country_name', 'Unknown')
      country_name = re.sub(r'(?i)\bpostpaid\b', '', country_name).strip()
      
      raw_svc = str(context.user_data.get('service_name', 'facebook')).lower()
      api_svc = 'facebook' if 'facebook' in raw_svc else 'whatsapp' if 'whatsapp' in raw_svc else 'telegram' if 'telegram' in raw_svc else 'facebook'

      fetched_numbers = []
      
      for attempt in range(2):
          if len(fetched_numbers) >= 2: break
          
          tasks = []
          if server_id == 1:
              r_val = str(range_val).strip()
              if not r_val.upper().endswith("XXX"): r_val += "XXX"
              payload = {"range": r_val, "app": api_svc, "service": api_svc, "is_national": False, "remove_plus": False}
              tasks = [_fetch_number_s1(payload), safe_delayed_fetch(0.2, _fetch_number_s1, payload)]
              
          elif server_id == 2:
              url = f"/api/sms/?carrier={range_val}"
              tasks = [_fetch_number_s2(url), safe_delayed_fetch(0.2, _fetch_number_s2, url)]

          if tasks:
              try:
                  results = await asyncio.wait_for(asyncio.gather(*tasks, return_exceptions=True), timeout=8.0)
                  for res in results:
                      if isinstance(res, tuple):
                          status, resp = res
                          if status in [200, 201] and isinstance(resp, dict):
                              num = ""
                              if server_id == 2 and str(resp.get('meta')) == '200':
                                  data_obj = resp.get('data', {})
                                  if isinstance(data_obj, dict): num = str(data_obj.get('did', ''))
                                      
                              elif server_id == 1 and 'data' in resp and isinstance(resp['data'], dict) and resp['data'].get('number'):
                                  num = str(resp['data']['number'])
                                  if country_name == "Unknown": country_name = resp['data'].get('country', country_name)
                                  country_name = re.sub(r'(?i)\bpostpaid\b', '', country_name).strip()
                              
                              if num and num != "None": 
                                  clean_n = num.replace('+', '')
                                  if clean_n not in fetched_numbers: 
                                      fetched_numbers.append(clean_n)
                                      if len(fetched_numbers) == 2: break
              except Exception: pass

      if fetched_numbers:
          s_suffix = ""
          if server_id == 1: s_suffix = SETTINGS_CACHE['s1_suffix']
          elif server_id == 2: s_suffix = SETTINGS_CACHE['s2_suffix']
          
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
              num_kb["inline_keyboard"].append([{"text": f"⎘ +{n}", "copy_text": {"text": str(n)}}])
              
          if 'facebook' in raw_svc:
              num_kb["inline_keyboard"].append([{"text": "🔍 Check FB Account", "callback_data": "chk_fb_acc"}])
              
          num_kb["inline_keyboard"].append([{"text": "🔄 Change Number", "callback_data": "change_num"}])
          num_kb["inline_keyboard"].append([{"text": "🌍 Change Country", "callback_data": "go_cat"}])
          num_kb["inline_keyboard"].append([{"text": "🗝️ Get OTP", "url": "https://t.me/RTxOtpX"}])
          
          try: await msg.edit_text(text=txt, reply_markup=num_kb, parse_mode=ParseMode.HTML)
          except Exception: pass
          
          context.user_data['fetched_numbers'] = fetched_numbers
          context.user_data['range'] = range_val 
          context.user_data['server'] = server_id
          
          for n in fetched_numbers:
              hash_key = get_hash_key(n)
              WAITING_OTPS[hash_key] = {
                  'full_num': n, 'user_id': user_id, 'chat_id': chat_id, 'msg_id': msg.message_id, 
                  'time': time.time(), 'received_codes': set(), 
                  'range': range_val, 'server_id': server_id, 'service_name': custom_svc, 'country_name': display_country_name
              }
              NUM_TO_HASH[clean_number(n)] = hash_key
      else:
          err_msg = "🔄 <b>No numbers found right now. Please try again.</b>"
          btn_back = {"inline_keyboard": [[{"text": "🔙 Back", "callback_data": "go_cat"}]]}
          try: await msg.edit_text(text=f"📡 <b>𝗦𝗲𝗿𝘃𝗲𝗿 𝗢𝗽𝘁𝗶𝗺𝗶𝘇𝗶𝗻𝗴:</b>\n{err_msg}", reply_markup=btn_back, parse_mode=ParseMode.HTML)
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
            c = log.get('country') or 'Unknown'
            if 'carrier_id' in log: 
                c_id = log.get('carrier_id', '')
                c = c_id.split()[0] if c_id else 'Unknown'
                
            c = re.sub(r'(?i)\bpostpaid\b', '', c).strip()
            app = log.get('app_name') or log.get('app') or 'Unknown'
            app = str(app).title()
            
            if 'Facebook' in app: app = 'Facebook'
            elif 'Whatsapp' in app: app = 'WhatsApp'
            elif 'Telegram' in app: app = 'Telegram'
            elif 'Alymscintl' in app: app = 'Alibaba'
            
            if app in ['Facebook', 'WhatsApp', 'Telegram', 'Alibaba'] and c != 'Unknown':
                counts[(app, c)] = counts.get((app, c), 0) + 1
                
    if not counts:
        return await update.message.reply_text("<b>⏳ No live traffic currently recorded.</b>", parse_mode=ParseMode.HTML)
        
    sorted_traffic = sorted(counts.items(), key=lambda x: x[1], reverse=True)[:20]
    
    txt = "📁 <b>LIVE-STOCK OTP COUNT</b>\n\n"
    for (app, c), count in sorted_traffic:
        flag = get_flag(c)
        short_c = get_short_code(c)
        app_display = "Fᴀᴄᴇʙᴏᴏᴋ" if app == 'Facebook' else ("Wʜᴀᴛsᴀᴘᴘ" if app == 'WhatsApp' else ("Tᴇʟᴇɢʀᴀᴍ" if app == 'Telegram' else "Aʟɪʙᴀʙᴀ"))
        
        if count >= 10: color = "🟢"
        elif count >= 3: color = "🟡"
        else: color = "🔴"
            
        txt += f"<b>{app_display} {flag} {short_c} » {count} OTPs {color}</b>\n"
        
    await update.message.reply_text(txt, parse_mode=ParseMode.HTML)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await check_ban_middleware(update, context): return
    user_id = update.effective_user.id
    referrer_id = None
    if context.args and context.args[0].startswith("ref_"):
        try: referrer_id = int(context.args[0].replace("ref_", ""))
        except: pass
        if referrer_id == user_id: referrer_id = None
    
    context.user_data.clear()
    is_sub, _ = await asyncio.gather(check_subscription(user_id, context.bot), ensure_user_fast(user_id, referrer_id))
    
    if not is_sub: await send_join_prompt(update, context)
    else: await show_main_menu(update, context)

_MAIN_MENU_KB = ReplyKeyboardMarkup(
    [["📱 GET NUMBER", "📊 LIVE TRAFFIC"], ["💳 BALANCE", "🎁 REFER"], ["🎧 LIVE SUPPORT"]],
    resize_keyboard=True
)

async def show_main_menu(update_obj, context):
    full_name = html.escape(update_obj.effective_user.full_name)
    msg = f"<b>Welcome {full_name}</b>"
    
    if hasattr(update_obj, 'message') and update_obj.message:
        await update_obj.message.reply_text(msg, reply_markup=_MAIN_MENU_KB, parse_mode=ParseMode.HTML)
    elif hasattr(update_obj, 'callback_query') and update_obj.callback_query:
        try: await update_obj.callback_query.message.delete()
        except: pass
        await context.bot.send_message(chat_id=update_obj.effective_chat.id, text=msg, reply_markup=_MAIN_MENU_KB, parse_mode=ParseMode.HTML)

async def cmd_2fa(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['state'] = 'WAITING_FOR_2FA'
    await update.message.reply_text("🔐 <b>2Fᴀ Cᴏᴅᴇ Gᴇɴᴀʀᴇᴛᴏʀ ⚙️</b>\n━━━━━━━━━━━━━━━━━━━━\n<b>Pᴀsᴛ Yᴏᴜʀ Sᴇᴄʀᴇᴛ Kᴇʏ :</b>", parse_mode=ParseMode.HTML)

async def start_category_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cat_kb = {
        "inline_keyboard": [
            [{"text": "⚙ Fᴀᴄᴇʙᴏᴏᴋ", "callback_data": "cat_facebook"}],
            [{"text": "Wʜᴀᴛsᴀᴘᴘ 𒊹︎︎", "callback_data": "cat_whatsapp"}],
            [{"text": "🚀 Tᴇʟᴇɢʀᴀᴍ", "callback_data": "cat_telegram"}],
            [{"text": "🔙 Mᴀɪɴ Mᴇɴᴜ ", "callback_data": "go_main"}]
        ]
    }
    txt = "<b>Sᴇʟᴇᴄᴛ Yᴏᴜ ᴄᴀᴛᴀɢᴏʀʏ </b>"
    
    if update and hasattr(update, 'callback_query') and update.callback_query: 
        await update.callback_query.edit_message_text(text=txt, reply_markup=cat_kb, parse_mode=ParseMode.HTML)
    else: 
        if update and hasattr(update, 'message') and update.message:
            await update.message.reply_text(text=txt, reply_markup=cat_kb, parse_mode=ParseMode.HTML)

async def handle_category_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global PRECOMPUTED_MENUS
    query = update.callback_query
    category = query.data.split('_')[1].lower()
    context.user_data['service_name'] = category.title()
    
    if PRECOMPUTED_MENUS.get(category):
        await query.edit_message_text(
            text=f"<b>Sᴇʟᴇᴄᴛ Cᴏᴜɴᴛʀʏ Fᴏʀ {category.title()}</b>", 
            reply_markup=PRECOMPUTED_MENUS[category], parse_mode=ParseMode.HTML
        )
        return

    btn_back = {"inline_keyboard": [[{"text": "🔙 Back", "callback_data": "go_cat"}]]}
    await query.edit_message_text(text=f"𝗡𝗼 𝗡𝘂𝗺𝗯𝗲𝗿 𝗙𝗶𝗻𝗱 𝗥𝗶𝗴𝗵𝘁 𝗡𝗼𝘄 𝗙𝗼𝗿 𝗧𝗵𝗶𝘀 𝗖𝗮𝘁𝗮𝗴𝗼𝗿𝘆 💣", reply_markup=btn_back, parse_mode=ParseMode.HTML)

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
    if user_id not in USER_CACHE: asyncio.ensure_future(ensure_user_fast(user_id))
    
    menu_actions = ["📱 GET NUMBER", "📊 LIVE TRAFFIC", "💳 BALANCE", "🎁 REFER", "🎧 LIVE SUPPORT"]
    admin_actions = ["Bot Status", "𝗕𝗼𝘁 𝗦𝘁𝗮𝘁𝘂𝘀", "Total Users", "𝗧𝗼𝘁𝗮𝗹 𝗨𝘀𝗲𝗿𝘀", "Broadcast", "𝗕𝗿𝗼𝗮𝗱𝗰𝗮𝘀𝘁", "Ban / Unban", "𝗕𝗮𝗻 / 𝗨𝗻𝗯𝗮𝗻", "Set Rewards", "𝗦𝗲𝘁 𝗥𝗲𝘄𝗮𝗿𝗱𝘀", "Set Min Withdraw", "𝗦𝗲𝘁 𝗠𝗶𝗻 𝗪𝗶𝘁𝗵𝗱𝗿𝗮𝘄", "Add Balance", "𝗔𝗱𝗱 𝗕𝗮𝗹𝗮𝗻𝗰𝗲", "Top Referrers", "𝗧𝗼 top 𝗥𝗲𝗳𝗲𝗿𝗿𝗲𝗿𝘀", "Set Suffix S1", "𝗦𝗲𝘁 𝗦𝘂𝗳𝗳𝗶𝘅 𝗦𝟭", "Set Suffix S2", "𝗦𝗲𝘁 𝗦𝘂𝗳𝗳𝗶𝘅 𝗦𝟮", "Main Menu", "𝗠𝗮𝗶𝗻 𝗠𝗲𝗻𝘂", "➕ 𝗔𝗱𝗱 𝗖𝗵𝗮𝗻𝗻𝗲𝗹", "🗑️ 𝗗𝗲𝗹 𝗖𝗵𝗮𝗻𝗻𝗲𝗹"]
    
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
                f"✅ <i>Servers Running Perfectly</i>"
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
            
        elif "𝗦𝗲𝘁 𝗦𝘂𝗳𝗳𝗶𝘅" in text or "Set Suffix" in text:
            if "S1" in text or "𝗦𝟭" in text: user_data['state'] = 'ADMIN_SET_S1_SUFFIX'
            elif "S2" in text or "𝗦𝟮" in text: user_data['state'] = 'ADMIN_SET_S2_SUFFIX'
            return await update.message.reply_text("✏️ <b>𝗦𝗲𝗻𝗱 𝘀𝘂𝗳𝗳𝗶𝘅.</b>\n(Send `-` to keep it blank)", parse_mode=ParseMode.HTML)

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
            for i, u_id in enumerate(users):
                try:
                    await context.bot.send_message(chat_id=u_id, text=f"📢 <b>𝗔𝗗𝗠𝗜𝗡 𝗕𝗥𝗢𝗔𝗗𝗖𝗔𝗦𝗧</b>\n━━━━━━━━━━━━━━━━━━━━\n{text}", parse_mode=ParseMode.HTML)
                    success += 1
                except: failed += 1
                if i % 25 == 0: await asyncio.sleep(1)   
                elif i % 500 == 0 and i > 0:
                    try: await msg.edit_text(f"⏳ <b>Broadcasting...</b>\n✅ {success} | ❌ {failed} | 📋 {i}/{len(users)}", parse_mode=ParseMode.HTML)
                    except: pass
            await msg.edit_text(f"✅ <b>𝗕𝗿𝗼𝗮𝗱𝗰𝗮𝘀𝘁 Complete𝗱!</b>\n🟢 Delivered: {success}\n🔴 Failed: {failed}", parse_mode=ParseMode.HTML)
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
            
        elif state in ['ADMIN_SET_S1_SUFFIX', 'ADMIN_SET_S2_SUFFIX']:
            val = text if text != "-" else ""
            key = "s1_suffix" if state == 'ADMIN_SET_S1_SUFFIX' else "s2_suffix"
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(DB_EXECUTOR, sync_update_setting, key, val)
            await update.message.reply_text(f"✅ <b>𝗦𝘂𝗳𝗳𝗶𝘅 𝘂𝗽𝗱𝗮𝘁𝗲𝗱 𝘁𝗼:</b> '{val}'", parse_mode=ParseMode.HTML)
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
                        out = f"✅ <b>2FA CODE GENERATED!</b>\n<b>⚠️ Auto-delete in 5 mins.</b>"
                        user_markup = {"inline_keyboard": [[{"text": str(code), "copy_text": {"text": str(code)}}]]}
                        await msg.edit_text(out, reply_markup=user_markup, parse_mode=ParseMode.HTML)
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
            f"<b>🟢 Your Referral Dashboard</b>\n\n"
            f"<b>🖲️ You Referred: {user_info['total_referrals']} users</b>\n"
            f"<b>💸 Total Commission: {user_info.get('ref_earnings', 0.0):.4f} ৳</b>\n\n"
            f"<b>You will get 10% commission when your referral withdraws money!</b>\n\n"
            f"<b>🔗 Referral Link:</b>\n<code>{ref_link}</code>"
        )
        
        markup = {"inline_keyboard": [[{"text": "🚀 Refer Now", "url": share_url}]]}
        await update.message.reply_text(msg, reply_markup=markup, parse_mode=ParseMode.HTML)

    elif text == "💳 BALANCE":
        loop = asyncio.get_event_loop()
        user_info = await loop.run_in_executor(DB_EXECUTOR, sync_get_user_info, user_id)
        
        msg = (
            f"<b>💳 Balance: {user_info['balance']:.2f} ৳</b>\n"
            f"<b>Minimum Withdraw: {SETTINGS_CACHE['min_withdraw']} ৳</b>"
        )
        markup = {"inline_keyboard": [[{"text": "💳 Withdraw Balance", "callback_data": "req_withdraw"}]]}
        await update.message.reply_text(msg, reply_markup=markup, parse_mode=ParseMode.HTML)
        
    elif text == "🎧 LIVE SUPPORT":
        user_data['state'] = 'WAITING_FOR_SUPPORT'
        await update.message.reply_text("<b>আপনার সমস্যাটি বলুন:</b>", parse_mode=ParseMode.HTML)
        
    elif state == 'WAITING_FOR_SUPPORT':
        for a_id in ADMIN_IDS:
            try: 
                markup = {"inline_keyboard": [[{"text": "💬 Reply", "callback_data": f"admrep_{user_id}"}]]}
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
# 🎮 BUTTON HANDLER & FACEBOOK CHECKER
# ==============================================================================

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await check_ban_middleware(update, context): return
    query = update.callback_query
    user_id = query.from_user.id
    data = query.data
    
    if user_id not in USER_CACHE:
        asyncio.ensure_future(ensure_user_fast(user_id))
    
    if data == "ignore": return await query.answer()
    elif data == "check_join":
        if await check_subscription(user_id, context.bot, force=True):
            await query.answer("✅ Verified!", show_alert=False)
            try: await query.message.delete()
            except: pass
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text=f"<b>Welcome {html.escape(query.from_user.full_name)}</b>",
                reply_markup=ReplyKeyboardMarkup([["📱 GET NUMBER", "📊 LIVE TRAFFIC"], ["💳 BALANCE", "🎁 REFER"], ["🎧 LIVE SUPPORT"]], resize_keyboard=True),
                parse_mode=ParseMode.HTML
            )
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
    
    # 🔥 FACEBOOK CHECK NUMBER FEATURE
    elif data == "chk_fb_acc":
        fetched_nums = context.user_data.get('fetched_numbers', [])
        if not fetched_nums:
            return await query.answer("⚠️ No numbers found to check!", show_alert=True)
        
        await query.answer("Checking Facebook accounts... please wait.")
        msg_text = "🔍 <b>Facebook Account Status:</b>\n\n"
        
        for num in fetched_nums:
            found = await check_facebook_account(num)
            if found: msg_text += f"✅ <b>Account Found:</b> <code>+{num}</code>\n"
            else: msg_text += f"❌ <b>No Account:</b> <code>+{num}</code>\n"
        
        msg_text += "\n<i>Requesting OTP...</i>"
        await query.message.reply_text(msg_text, parse_mode=ParseMode.HTML)

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
                [{"text": "Bᴋᴀsʜ ", "callback_data": "wdm_Bkash"}],
                [{"text": "Nᴀɢᴀᴅ ", "callback_data": "wdm_Nagad"}],
                [{"text": "Rᴇᴄʜᴀʀɢᴇ ", "callback_data": "wdm_Mobile_Recharge"}]
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
        ["Main Menu"]
    ]
    txt = "🔐 <b>𝗔𝗗𝗩𝗔𝗡𝗖𝗘𝗗 𝗔𝗗𝗠𝗜𝗡 𝗣𝗔𝗡𝗘𝗟</b> 🔐\n━━━━━━━━━━━━━━━━━━━━\n<i>Use the keyboard below to manage the bot:</i>"
    await update.message.reply_text(txt, reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True), parse_mode=ParseMode.HTML)

# ==============================================================================
# ☁️ INVISIBLE TELEGRAM CLOUD BACKUP & RESTORE SYSTEM
# ==============================================================================

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

# ==============================================================================
# 🌐 BACKGROUND CACHE UPDATER & MENU PRE-COMPUTER
# ==============================================================================

async def update_cache_job(context: ContextTypes.DEFAULT_TYPE):
    global CONSOLE_CACHE, PRECOMPUTED_MENUS
    try:
        gc.collect()
        s1_tasks = [s1_api_request('GET', f"{S1_BASE_URL}/mdashboard/console/info?page={i}") for i in range(1, 4)]
        s2_task = s2_api_request('GET', "/api/terminal")
        
        results = await asyncio.gather(*s1_tasks, s2_task, return_exceptions=True)
        
        # Parse S1 Feed
        s1_logs = []
        for res in results[:3]:
            if isinstance(res, tuple) and res[0] == 200 and isinstance(res[1], dict):
                s1_logs.extend(res[1].get('data', {}).get('logs', []))
        if s1_logs: CONSOLE_CACHE[1] = s1_logs[:150]
        
        # Parse S2 Crackerjack Feed
        s2_res = results[3]
        if not isinstance(s2_res, Exception) and s2_res[0] == 200 and isinstance(s2_res[1], dict):
            CONSOLE_CACHE[2] = s2_res[1].get('data', [])

        for cat in ["facebook", "whatsapp", "telegram"]:
            country_stats = {}
            
            # S1 Process
            for log in CONSOLE_CACHE[1]:
                if isinstance(log, dict):
                    c = log.get('country', 'Unknown')
                    r = log.get('range')
                    app_name = str(log.get('app_name', '')).lower()
                    c = re.sub(r'(?i)\bpostpaid\b', '', c).strip()
                    if cat in app_name and c and r and 'None' not in r:
                        key = (1, c)
                        if key not in country_stats: country_stats[key] = {'range': r, 'count': 0, 'c_name': c}
                        country_stats[key]['count'] += 1
                        
            # S2 Process (Live terminal from crackerjacksms)
            for log in CONSOLE_CACHE[2]:
                if isinstance(log, dict):
                    c_id = log.get('carrier_id', '')
                    app = str(log.get('app', '')).lower()
                    if c_id and cat in app:
                        c_name = c_id.split()[0]
                        c_name = re.sub(r'(?i)\bpostpaid\b', '', c_name).strip()
                        r = format_cj_carrier(c_id)
                        if r:
                            key = (2, c_name)
                            if key not in country_stats: country_stats[key] = {'range': r, 'count': 0, 'c_name': c_name}
                            country_stats[key]['count'] += 1

            if country_stats:
                sorted_keys = sorted(country_stats.keys(), key=lambda x: x[0])
                kb = []
                s1_suffix = SETTINGS_CACHE['s1_suffix']
                s2_suffix = SETTINGS_CACHE['s2_suffix']
                
                pattern = [2, 1]
                p_idx = 0
                row = []
                for key in sorted_keys:
                    srv_id, c_name = key
                    stats = country_stats[key]
                    display_name = c_name
                    if srv_id == 1: display_name += s1_suffix
                    elif srv_id == 2: display_name += s2_suffix
                    
                    btn_text = f"{get_flag(c_name)} {display_name}"
                    safe_c_name = str(c_name)[:15].replace(" ", "")
                    btn = {"text": btn_text, "callback_data": f"r_{srv_id}_{stats['range']}_{safe_c_name}"}
                    row.append(btn)
                    if len(row) == pattern[p_idx]:
                        kb.append(row)
                        row = []
                        p_idx = (p_idx + 1) % 2
                if row: kb.append(row)
                kb.append([{"text": "🔙 Back", "callback_data": "go_cat"}])
                PRECOMPUTED_MENUS[cat] = {"inline_keyboard": kb}

    except Exception: pass

async def post_init(app: Application):
    asyncio.create_task(auth_s1(force=True))

if __name__ == "__main__":
    init_db()
    app = (
        Application.builder()
        .token(TOKEN)
        .post_init(post_init)
        .concurrent_updates(True)        
        .connection_pool_size(128)       
        .connect_timeout(8)
        .read_timeout(15)
        .write_timeout(15)
        .pool_timeout(8)
        .build()
    )
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin_panel))
    app.add_handler(CommandHandler("backup", cmd_backup))
    app.add_handler(CommandHandler("restore", cmd_restore))
    app.add_handler(CommandHandler("2fa", cmd_2fa))
    
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # ⏱️ JOBS
    app.job_queue.run_repeating(global_otp_checker_job,  interval=1.5,  first=2)
    app.job_queue.run_repeating(update_cache_job,         interval=15,   first=2)
    app.job_queue.run_repeating(auto_relogin_job,         interval=300,  first=300)
    app.job_queue.run_repeating(memory_cleanup_job,       interval=300,  first=60)   
    
    logger.info("✨ VERSION 99 PRO EDITION — VPS READY ✨")
    app.run_polling(
        drop_pending_updates=True,
        allowed_updates=["message", "callback_query"],  
    )
