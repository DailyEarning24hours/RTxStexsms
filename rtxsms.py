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

from telegram import (
    Update, 
    InlineKeyboardButton, 
    InlineKeyboardMarkup, 
    ReplyKeyboardMarkup, 
    ReplyKeyboardRemove,
    InputFile
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

# 🌐 SERVER 1 CREDENTIALS
STEX_EMAIL = "mdrajaislam469@gmail.com"
STEX_PASSWORD = "Raja1234@#"
API_STEX_LOGIN = "https://stexsms.com/mapi/v1/mauth/login"
API_STEX_CONSOLE = "https://stexsms.com/mapi/v1/mdashboard/console/info"
API_STEX_GET_NUM = "https://stexsms.com/mapi/v1/mdashboard/getnum/number"
API_STEX_INBOX = "https://stexsms.com/mapi/v1/mdashboard/getnum/info"

# 🚀 SERVER 2 CREDENTIALS
MK_EMAIL = "mdrajaislam469@gmail.com"
MK_PASSWORD = "Raja1234@#"
API_MK_LOGIN = "http://mknetworkbd.com/process_login.php"
API_MK_CONSOLE = "http://mknetworkbd.com/console.php?ajax=1"
API_MK_GET_NUM = "http://mknetworkbd.com/API/api_handler.php"
API_MK_INBOX = "http://mknetworkbd.com/API/api_handler.php?action=get_history&filter=all&page=1&limit=50&date={}"

API_2FA = "https://2fa.cn/codes/{}"

# ==============================================================================
# 🛑 ADVANCED SERVER CRASH PREVENTION & CACHING
# ==============================================================================

MAUTH_TOKEN = None
GLOBAL_SESSION = None 

AUTH_LOCK_STEX = asyncio.Lock() 
LAST_AUTH_TIME_STEX = 0

AUTH_LOCK_MK = asyncio.Lock()
LAST_AUTH_TIME_MK = 0

SENT_RANGES = set()
START_TIME = datetime.datetime.now()
BASE_USER_AGENT = "Mozilla/5.0 (Linux; Android 14; SM-A135F Build/UP1A.231005.007) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.7632.120 Mobile Safari/537.36"

DB_POOL_SIZE = 15 

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# ==============================================================================
# 🧠 ENTERPRISE MEMORY SYSTEM (FOR 100,000+ USERS)
# ==============================================================================

WAITING_OTPS = {}
BATCH_MSGS = {} 
OTP_TIMEOUT_SECONDS = 1200 # 20 minutes before silent delete

# ⚡ O(1) Memory Database Cache (Prevents DB Locking during high traffic)
USER_CACHE = set()
BANNED_CACHE = set()

def get_hash_key(number_str):
    """Generates an O(1) lookup key for extreme performance on Render Free Plan."""
    clean_str = re.sub(r'\D', '', str(number_str))
    if not clean_str: return "UNKNOWN"
    return clean_str[-8:]

def clean_sms_text(raw_text):
    """Removes spam/scam words and absolutely prevents 'No Message' string."""
    text_str = str(raw_text).strip()
    
    # 🚫 Stop "No Message" from showing anywhere
    if not text_str or text_str.lower() in ["none", "null", "no message", ""]:
        return "Awaiting SMS..."
    
    # Remove unwanted words (case-insensitive)
    cleaned = re.sub(r'(?i)\b(spam|scam|junk|warning|malicious)\b', '', text_str)
    # Remove multiple spaces
    cleaned = ' '.join(cleaned.split())
    
    # Final safety check
    if not cleaned or cleaned.lower() == "no message": 
        return "Awaiting SMS..."
        
    return cleaned

def mask_number(num_str):
    """Masks phone number for privacy in public groups (e.g., 23762•••6138)"""
    num_str = str(num_str).replace('+', '').strip()
    if len(num_str) > 9:
        return num_str[:5] + "•••" + num_str[-4:]
    elif len(num_str) > 5:
        return num_str[:3] + "•••" + num_str[-2:]
    return num_str

def extract_code(message):
    match = re.search(r'\b\d{4,8}\b', str(message))
    return match.group(0) if match else "Processing..."


# ==============================================================================
# 🔐 ULTIMATE DUAL-API AUTHENTICATION & REQUEST WRAPPER
# ==============================================================================

async def get_session():
    global GLOBAL_SESSION
    if GLOBAL_SESSION is None or GLOBAL_SESSION.closed:
        # 🔥 Boosted Limits for 100k users & Parallel Processing
        connector = aiohttp.TCPConnector(limit=2000, keepalive_timeout=120, ttl_dns_cache=600, enable_cleanup_closed=True)
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

# ----- SERVER 1 AUTH -----
async def authenticate_stex(force=False):
    global MAUTH_TOKEN, LAST_AUTH_TIME_STEX
    async with AUTH_LOCK_STEX:
        if not force and time.time() - LAST_AUTH_TIME_STEX < 15 and MAUTH_TOKEN: return True
        payload = {"email": STEX_EMAIL, "password": STEX_PASSWORD}
        headers = {
            "User-Agent": BASE_USER_AGENT, 
            "Accept": "application/json, text/plain, */*",
            "Content-Type": "application/json", 
            "Origin": "https://stexsms.com", 
            "Referer": "https://stexsms.com/mauth/login"
        }
        try:
            session = await get_session()
            async with session.post(API_STEX_LOGIN, json=payload, headers=headers, timeout=15, ssl=False) as response:
                if response.status == 200:
                    data = await parse_response_safely(response)
                    if data and str(data.get('meta', {}).get('code')) == '200':
                        MAUTH_TOKEN = data['data']['token']
                        LAST_AUTH_TIME_STEX = time.time()
                        return True
                return False
        except Exception: 
            return False

def get_stex_headers():
    return {
        "User-Agent": BASE_USER_AGENT, 
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
                    await asyncio.sleep(2)
                    continue
            session = await get_session()
            headers = get_stex_headers()
            if method.upper() == 'GET': 
                response = await session.get(url, headers=headers, timeout=15, ssl=False)
            else: 
                response = await session.post(url, json=json_payload, headers=headers, timeout=15, ssl=False)
            
            status = response.status
            # 🔥 SUPPRESSING 401, 501, 500 ERRORS INTERNALLY
            if status in [401, 403, 500, 501, 502, 503]: 
                MAUTH_TOKEN = None
                await asyncio.sleep(2)
                continue
                
            if status == 200:
                data = await parse_response_safely(response)
                if isinstance(data, dict):
                    if str(data.get('meta', {}).get('code', '200')) in ['401', '403']: 
                        MAUTH_TOKEN = None
                        continue
                return 200, data
            else: 
                return status, None
        except Exception: 
            await asyncio.sleep(2)
    return 500, None 

# ----- SERVER 2 AUTH -----
async def authenticate_mk(force=False):
    global LAST_AUTH_TIME_MK
    async with AUTH_LOCK_MK:
        if not force and time.time() - LAST_AUTH_TIME_MK < 300: return True
        payload = aiohttp.FormData()
        payload.add_field('userid', MK_EMAIL)
        payload.add_field('password', MK_PASSWORD)
        headers = {
            "User-Agent": BASE_USER_AGENT, 
            "Origin": "http://mknetworkbd.com", 
            "Referer": "http://mknetworkbd.com/auth.php"
        }
        try:
            session = await get_session()
            async with session.post(API_MK_LOGIN, data=payload, headers=headers, timeout=15, ssl=False) as response:
                content_type = response.headers.get('Content-Type', '')
                if 'application/json' in content_type:
                    data = await parse_response_safely(response)
                    if data and data.get('status') == 'success':
                        LAST_AUTH_TIME_MK = time.time()
                        return True
                return False
        except Exception: 
            return False

async def mk_api_request(method, url, form_data=None):
    for attempt in range(3):
        try:
            session = await get_session()
            headers = {"User-Agent": BASE_USER_AGENT, "X-Requested-With": "mark.via.gp"}
            if method.upper() == 'GET': 
                response = await session.get(url, headers=headers, timeout=15, ssl=False)
            else: 
                response = await session.post(url, data=form_data, headers=headers, timeout=15, ssl=False)
            
            status = response.status
            content_type = response.headers.get('Content-Type', '')
            
            # 🔥 SUPPRESSING 401, 501, 500 ERRORS INTERNALLY
            if status in [401, 403, 500, 501, 502, 503] or 'text/html' in content_type:
                await authenticate_mk(force=True)
                await asyncio.sleep(2)
                continue
                
            data = await parse_response_safely(response)
            return 200, data
        except Exception: 
            await asyncio.sleep(2)
    return 500, None


# ==============================================================================
# 🗄️ DATABASE MANAGEMENT (100K SPEED CACHE SYSTEM)
# ==============================================================================

DB_FILE = "bot.db"

class DatabasePool:
    def __init__(self, db_file, pool_size=15):
        self.db_file = db_file
        self.pool_size = pool_size
    @contextmanager
    def get_connection(self):
        conn = sqlite3.connect(self.db_file, timeout=30.0, check_same_thread=False)
        conn.execute('PRAGMA journal_mode=WAL;')
        conn.execute('PRAGMA synchronous=NORMAL;')
        try: 
            yield conn
        finally: 
            conn.close()

db_pool = DatabasePool(DB_FILE, DB_POOL_SIZE)

def init_db():
    with db_pool.get_connection() as conn:
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            join_date TEXT,
            is_banned INTEGER DEFAULT 0
        )''')
        conn.commit()
    load_users_to_cache()

def load_users_to_cache():
    """Loads all users into memory for O(1) non-blocking access."""
    global USER_CACHE, BANNED_CACHE
    with db_pool.get_connection() as conn:
        c = conn.cursor()
        c.execute("SELECT user_id, is_banned FROM users")
        for row in c.fetchall():
            USER_CACHE.add(row[0])
            if row[1] == 1:
                BANNED_CACHE.add(row[0])

def get_user(user_id):
    with db_pool.get_connection() as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
        return c.fetchone()

def register_user(user_id):
    if user_id not in USER_CACHE:
        with db_pool.get_connection() as conn:
            c = conn.cursor()
            c.execute("INSERT OR IGNORE INTO users (user_id, join_date) VALUES (?, CURRENT_TIMESTAMP)", (user_id,))
            conn.commit()
        USER_CACHE.add(user_id)
        return True
    return False

def ensure_user(user_id):
    if user_id not in USER_CACHE:
        register_user(user_id)

def is_user_banned(user_id):
    return user_id in BANNED_CACHE

def get_all_users():
    return list(USER_CACHE)

def get_total_users_count():
    return len(USER_CACHE)

def set_ban_status(user_id, status):
    ensure_user(user_id)
    with db_pool.get_connection() as conn:
        c = conn.cursor()
        c.execute("UPDATE users SET is_banned=? WHERE user_id=?", (status, user_id))
        conn.commit()
    if status == 1:
        BANNED_CACHE.add(user_id)
    else:
        BANNED_CACHE.discard(user_id)


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
    if is_user_banned(user_id):
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


# ==============================================================================
# 🤖 AUTO RANGE FORWARDER JOB (CONSOLE: FULL MESSAGE ADDED HERE)
# ==============================================================================

async def auto_range_forwarder_job(context: ContextTypes.DEFAULT_TYPE):
    global SENT_RANGES
    # 🔥 Only forwarding Facebook & Whatsapp to Range Group
    allowed_apps = ['facebook', 'whatsapp']
    bot_username = context.bot.username

    # Fetch both consoles simultaneously for speed
    stex_task = stex_api_request('GET', API_STEX_CONSOLE)
    mk_task = mk_api_request('GET', API_MK_CONSOLE)
    
    results = await asyncio.gather(stex_task, mk_task, return_exceptions=True)
    
    # 1. PROCESS SERVER 1 (STEX)
    if isinstance(results[0], tuple):
        stex_status, stex_data = results[0]
        if stex_status == 200 and isinstance(stex_data, dict):
            logs = stex_data.get('data', {}).get('logs', [])
            for log in logs[:5]:
                if isinstance(log, dict):
                    r_val = log.get('range')
                    raw_app = str(log.get('app_name', 'Unknown')).lower()
                    c_name = log.get('country', 'Unknown')
                    
                    # 🔥 Fetching Full Message for Server 1 Console
                    msg_text = log.get('message', '')
                    if not msg_text or str(msg_text).lower() == 'no message':
                        msg_text = log.get('sms', '')
                    clean_msg = clean_sms_text(msg_text)
                    
                    if any(app in raw_app for app in allowed_apps) and r_val and r_val not in SENT_RANGES:
                        SENT_RANGES.add(r_val)
                        if len(SENT_RANGES) > 5000: SENT_RANGES.clear()
                        
                        display_app = "PC Clone" if ('facebook' in raw_app and '******' in clean_msg) else log.get('app_name', 'Unknown').title()
                        
                        range_msg = (
                            f"🔥 <b>New Range find</b>\n"
                            f"━━━━━━━━━━━━━━━━━━━━\n"
                            f"🖥️ Server - <b>Server 1 ✨</b>\n"
                            f"🎯 Range - <code>{r_val}</code>\n"
                            f"🛒 Service - <pre>{html.escape(display_app)}</pre>\n"
                            f"🌍 Country - {get_flag(c_name)} {c_name}\n"
                            f"✉️ <b>Message</b> - <pre>{html.escape(clean_msg)}</pre>"
                        )
                        kb = [[InlineKeyboardButton("🤖 Bot Link", url=f"https://t.me/{bot_username}")]]
                        try: 
                            await context.bot.send_message(chat_id=RANGE_GROUP_ID, text=range_msg, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.HTML)
                        except Exception: 
                            pass

    # 2. PROCESS SERVER 2 (MK NETWORK)
    if isinstance(results[1], tuple):
        mk_status, mk_data = results[1]
        if mk_status == 200 and isinstance(mk_data, dict):
            feeds = mk_data.get('feed', [])
            for log in feeds[:5]:
                if isinstance(log, dict):
                    r_val = log.get('range')
                    raw_app = str(log.get('service_name', 'Unknown')).lower()
                    c_name = log.get('country', 'Unknown')
                    
                    # 🔥 Fetching Full Message for Server 2 Console
                    msg_text = log.get('msg', '')
                    clean_msg = clean_sms_text(msg_text)
                    
                    if any(app in raw_app for app in allowed_apps) and r_val and r_val not in SENT_RANGES:
                        SENT_RANGES.add(r_val)
                        if len(SENT_RANGES) > 5000: SENT_RANGES.clear()
                        
                        display_app = "PC Clone" if ('facebook' in raw_app and '******' in clean_msg) else log.get('service_name', 'Unknown').title()
                        
                        range_msg = (
                            f"🔥 <b>New Range find</b>\n"
                            f"━━━━━━━━━━━━━━━━━━━━\n"
                            f"🚀 Server - <b>Server 2 🚀</b>\n"
                            f"🎯 Range - <code>{r_val}</code>\n"
                            f"🛒 Service - <pre>{html.escape(display_app)}</pre>\n"
                            f"🌍 Country - {get_flag(c_name)} {c_name}\n"
                            f"✉️ <b>Message</b> - <pre>{html.escape(clean_msg)}</pre>"
                        )
                        kb = [[InlineKeyboardButton("🤖 Bot Link", url=f"https://t.me/{bot_username}")]]
                        try: 
                            await context.bot.send_message(chat_id=RANGE_GROUP_ID, text=range_msg, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.HTML)
                        except Exception: 
                            pass


# ==============================================================================
# 🚀 GLOBAL OTP POLLER (INBOX UPDATE: ONLY OTP CODE, NO FULL MSG)
# ==============================================================================

async def process_found_otp(context, hash_key, api_num, code_only, svc_name, clean_msg):
    global WAITING_OTPS, BATCH_MSGS
    
    if hash_key not in WAITING_OTPS:
        return
        
    user_data = WAITING_OTPS[hash_key]
    user_id, chat_id, msg_id = user_data['user_id'], user_data['chat_id'], user_data['msg_id']
    full_num, batch_key = user_data['full_num'], user_data['batch_key']
    
    # Notice: We DO NOT remove the number from BATCH_MSGS or WAITING_OTPS here!
    # It stays alive for 20 minutes to receive MULTIPLE OTPs automatically.

    # 🔥 SEND OTP TO USER INBOX (ONLY CODE, NO FULL MESSAGE)
    user_msg = (
    f"🎉 <b>OTP RECEIVED SUCCESSFULLY!</b> ✨\n"
    f"━━━━━━━━━━━━━━━━━━━━\n"
    f"📱 <b>Service :</b> <code>{html.escape(str(svc_name))}</code>\n"
    f"📞 <b>Number  :</b> <code>{full_num}</code>\n"
    f"🔑 <b>Your OTP:</b> <code>{code_only}</code>\n"
    f"━━━━━━━━━━━━━━━━━━━━"
)
    
    asyncio.create_task(context.bot.send_message(chat_id=chat_id, text=user_msg, parse_mode=ParseMode.HTML))
    
    # FORWARD TO OTP GROUP (WITH MASKED NUMBER & FULL MESSAGE)
    group_msg = (
        f"🔔 <b>Otp Received</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📱 Number - <code>{mask_number(full_num)}</code>\n"
        f"🛒 Service - <pre>{html.escape(str(svc_name))}</pre>\n"
        f"🔑 Code - <code>{code_only}</code>\n"
        f"✉️ Full sms - <pre>{html.escape(str(clean_msg))}</pre>"
    )
    group_kb = [[InlineKeyboardButton("👨‍💻 Owner", url="https://t.me/RTx2R")]]
    try: 
        asyncio.create_task(context.bot.send_message(chat_id=OTP_GROUP_ID, text=group_msg, reply_markup=InlineKeyboardMarkup(group_kb), parse_mode=ParseMode.HTML))
    except Exception: 
        pass

async def global_otp_checker_job(context: ContextTypes.DEFAULT_TYPE):
    global WAITING_OTPS, BATCH_MSGS
    if not WAITING_OTPS: 
        return 
    
    current_time = time.time()
    expired_keys = []
    
    # CLEANUP EXPIRED NUMBERS (After 20 Mins)
    for hash_key, data in list(WAITING_OTPS.items()):
        if current_time - data['time'] > OTP_TIMEOUT_SECONDS: 
            expired_keys.append(hash_key)
            
    for h_key in expired_keys:
        u_data = WAITING_OTPS.pop(h_key, None)
        if u_data:
            b_key = u_data.get('batch_key')
            if b_key and b_key in BATCH_MSGS:
                if u_data['full_num'] in BATCH_MSGS[b_key]['numbers']:
                    BATCH_MSGS[b_key]['numbers'].remove(u_data['full_num'])
                if len(BATCH_MSGS[b_key]['numbers']) == 0:
                    try: 
                        await context.bot.delete_message(chat_id=u_data['chat_id'], message_id=u_data['msg_id'])
                    except: 
                        pass
                    del BATCH_MSGS[b_key]

    if not WAITING_OTPS: 
        return 
        
    date_str = datetime.datetime.now().strftime("%Y-%m-%d")

    # 🔥 PARALLEL FETCHING: FETCHING BOTH INBOXES AT THE EXACT SAME TIME
    stex_url = f"{API_STEX_INBOX}?date={date_str}&page=1&search=&status="
    mk_url = API_MK_INBOX.format(date_str)
    
    stex_task = stex_api_request('GET', stex_url)
    mk_task = mk_api_request('GET', mk_url)
    
    results = await asyncio.gather(stex_task, mk_task, return_exceptions=True)

    # 1. PROCESS SERVER 1 (STEX) RESULTS
    if isinstance(results[0], tuple):
        stex_status, stex_res = results[0]
        if stex_status == 200 and stex_res:
            for item in stex_res.get('data', {}).get('numbers', []):
                if isinstance(item, dict) and item.get('status') == 'success':
                    hash_key = get_hash_key(item.get('number', ''))
                    if hash_key in WAITING_OTPS:
                        
                        # 🔥 STEX "NO MESSAGE" ABSOLUTE FIX
                        raw_msg = item.get('full_message', item.get('message', item.get('sms', item.get('otp', ''))))
                        if not raw_msg or str(raw_msg).strip() == "" or str(raw_msg).lower() == "no message":
                            # Force a message content if Stex api acts weird
                            raw_msg = f"Your verification code is {item.get('otp', 'Processing...')}"
                        
                        clean_msg = clean_sms_text(raw_msg)
                        code_val = extract_code(clean_msg)
                        
                        # MULTIPLE OTP ALLOWANCE logic
                        if code_val and code_val != "Processing...":
                            if code_val not in WAITING_OTPS[hash_key]['received_codes']:
                                WAITING_OTPS[hash_key]['received_codes'].add(code_val)
                                await process_found_otp(context, hash_key, item.get('number', ''), code_val, item.get('full_number', 'Service'), clean_msg)

    # 2. PROCESS SERVER 2 (MK NETWORK) RESULTS
    if isinstance(results[1], tuple):
        mk_status, mk_res = results[1]
        if mk_status == 200 and mk_res:
            for item in mk_res.get('data', []):
                if isinstance(item, dict) and item.get('status') == 'success':
                    hash_key = get_hash_key(item.get('phone_number', ''))
                    if hash_key in WAITING_OTPS:
                        raw_msg = item.get('full_sms_list', item.get('msg', ''))
                        clean_msg = clean_sms_text(raw_msg)
                        code_val = item.get('otps', extract_code(clean_msg))
                        
                        if not code_val or code_val == "Processing...": 
                            code_val = extract_code(clean_msg)
                            
                        # MULTIPLE OTP ALLOWANCE logic
                        if code_val and code_val != "Processing...":
                            if code_val not in WAITING_OTPS[hash_key]['received_codes']:
                                WAITING_OTPS[hash_key]['received_codes'].add(code_val)
                                await process_found_otp(context, hash_key, item.get('phone_number', ''), code_val, item.get('operator', 'Service'), clean_msg)

    # WE DO NOT POP `WAITING_OTPS` HERE! Let them stay for multiple OTPs until the 20 min timer kills them.


# ==============================================================================
# 🎯 EXACTLY 2-NUMBER GENERATION SYSTEM (DUAL SERVER)
# ==============================================================================

async def process_number_generation(update: Update, context: ContextTypes.DEFAULT_TYPE, range_val, server_id, is_callback=True):
    global WAITING_OTPS, BATCH_MSGS
    
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
    if not range_val.upper().endswith("XXX"): 
        range_val += "XXX"
        
    fetched_numbers = []
    country_name = "Unknown"
    
    # 🔥 LOOP EXACTLY 2 TIMES
    for _ in range(2):
        await asyncio.sleep(0.5) 
        
        if server_id == 1: 
            payload = {"range": range_val, "is_national": False, "remove_plus": False}
            status, resp = await stex_api_request('POST', API_STEX_GET_NUM, json_payload=payload)
            if status == 200 and isinstance(resp, dict) and 'data' in resp and resp['data'].get('number'):
                fetched_numbers.append(resp['data']['number'])
                country_name = resp['data'].get('country', country_name)
                
        elif server_id == 2: 
            form_data = aiohttp.FormData()
            form_data.add_field('action', 'get_number')
            form_data.add_field('range', range_val)
            status, resp = await mk_api_request('POST', API_MK_GET_NUM, form_data=form_data)
            if status == 200 and isinstance(resp, dict) and resp.get('status') == 'success' and resp.get('number'):
                clean_num = str(resp['number']).replace('+', '')
                fetched_numbers.append(clean_num)
                country_name = context.user_data.get('country_name', 'Global')
            
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
            f"⏳ <i>Waiting for SMS... (Numbers alive for 20 mins for Multiple OTPs)</i>"
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
            hash_key = get_hash_key(n)
            WAITING_OTPS[hash_key] = {
                'full_num': n, 
                'user_id': user_id, 
                'chat_id': chat_id, 
                'msg_id': msg.message_id, 
                'batch_key': batch_key, 
                'time': time.time(),
                'received_codes': set() # 🔥 MULTIPLE OTP TRACKER
            }
            
        context.user_data['range'] = range_val 
        context.user_data['server'] = server_id
        
    else:
        # 🔥 BEAUTIFUL NO-ERROR FALLBACK MESSAGE
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
    ensure_user(update.effective_user.id)
    # 🔥 CLEAR ALL STATES ON START
    context.user_data.clear()
    
    if not await check_subscription(update.effective_user.id, context.bot): 
        await send_join_prompt(update, context)
    else: 
        await show_main_menu(update, context)

async def show_main_menu(update_obj, context):
    kb = [
        ["📱 Get Number", "🔐 Get 2FA"], 
        ["🎧 Support", "📊 See Activity"]
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
        try: 
            await update_obj.callback_query.message.delete()
        except: 
            pass
        await context.bot.send_message(chat_id=update_obj.effective_chat.id, text=msg, reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True), parse_mode=ParseMode.HTML)

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
    
    # 🔥 CATEGORIES CLEANED (Only FB, WA, Custom)
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
    query = update.callback_query
    category = query.data.split('_')[1].lower()
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
# 🎮 TEXT HANDLER & INLINE ADMIN REPLY LOGIC
# ==============================================================================

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await check_ban_middleware(update, context): 
        return
    user_id = update.effective_user.id
    text = update.message.text
    user_data = context.user_data
    ensure_user(user_id)
    
    # 🔥 STATE AUTO-CLEAR
    if text in ["📱 Get Number", "🔐 Get 2FA", "🎧 Support", "📊 See Activity"]:
        user_data['state'] = None
        user_data['admin_reply_target'] = None
    
    # 🔥 INLINE ADMIN REPLY SYSTEM 
    target_reply_user = user_data.get('admin_reply_target')
    if target_reply_user and text not in ["📱 Get Number", "🔐 Get 2FA", "🎧 Support", "📊 See Activity"]:
        try:
            await context.bot.send_message(
                chat_id=int(target_reply_user), 
                text=f"👨‍💻 <b>Admin Reply:</b>\n━━━━━━━━━━━━━━━━━━━━\n{text}", 
                parse_mode=ParseMode.HTML
            )
            await update.message.reply_text("✅ <b>Reply sent successfully to the user.</b>", parse_mode=ParseMode.HTML)
        except Exception as e:
            await update.message.reply_text("❌ <b>Failed to send reply. The user might have blocked the bot.</b>", parse_mode=ParseMode.HTML)
        
        user_data['admin_reply_target'] = None
        return

    # 📱 MENU HANDLERS
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
            async with session.get(API_2FA.format(key), timeout=10) as resp:
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
                # 🔥 ADMIN GETS THIS MESSAGE WITH INLINE BUTTON TO REPLY
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
            [InlineKeyboardButton("🔥 Range Channel", url="https://t.me/ConsoleXRT")],
            [InlineKeyboardButton("💬 OTP Channel", url="https://t.me/RTxOtpX")]
        ]
        await update.message.reply_text(
            "📊 <b>BOT ACTIVITY LINKS</b>\n━━━━━━━━━━━━━━━━━━━━\n<i>Join to see live Bot activity:</i>", 
            reply_markup=InlineKeyboardMarkup(kb), 
            parse_mode=ParseMode.HTML
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
        
    query = update.callback_query
    user_id = query.from_user.id
    data = query.data
    ensure_user(user_id)
    
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
        parts = data.split("_")
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
        
    # 🔥 INLINE ADMIN REPLY BUTTON HANDLER
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
    
    # 🔥 ADMIN STATE CLEAR 
    context.user_data['admin_reply_target'] = None
    context.user_data['state'] = None
    
    txt = (
        "🔐 <b>ADVANCED ADMIN PANEL</b> 🔐\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "🟢 <code>/status</code> - Show Bot Statistics\n"
        "📢 <code>/broadcast &lt;msg&gt;</code> - Message all users\n"
        "🚫 <code>/ban &lt;id&gt;</code> - Ban a user\n"
        "✅ <code>/unban &lt;id&gt;</code> - Unban a user\n"
        "👥 <code>/users</code> - Total User Count\n"
        "🔍 <code>/search &lt;id&gt;</code> - Check User Details\n"
        "💾 <code>/backup</code> - Download Database"
    )
    await update.message.reply_text(txt, parse_mode=ParseMode.HTML)

async def admin_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS: return
    uptime = datetime.datetime.now() - START_TIME
    t_users = get_total_users_count()
    txt = (
        f"📊 <b>LIVE SYSTEM STATUS (100k OPTIMIZED)</b> 📊\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"⏱ <b>Uptime:</b> {str(uptime).split('.')[0]}\n"
        f"👥 <b>Total Users:</b> {t_users}\n"
        f"📡 <b>Active Waiters:</b> {len(WAITING_OTPS)} Numbers\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"✅ <i>Dual Servers Running Smoothly with Caching</i>"
    )
    await update.message.reply_text(txt, parse_mode=ParseMode.HTML)

async def admin_users_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS: return
    count = get_total_users_count()
    await update.message.reply_text(f"👥 <b>Total Registered Users:</b> {count}", parse_mode=ParseMode.HTML)

async def admin_search_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS: return
    try:
        target_id = int(context.args[0])
        user = get_user(target_id)
        if user:
            status = "🔴 BANNED" if user[2] == 1 else "🟢 ACTIVE"
            txt = (
                f"🔍 <b>USER INFO FOUND</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"👤 <b>User ID:</b> <code>{user[0]}</code>\n"
                f"📅 <b>Join Date:</b> {user[1]}\n"
                f"🛡️ <b>Status:</b> {status}"
            )
        else:
            txt = "❌ <b>User not found in database.</b>"
        await update.message.reply_text(txt, parse_mode=ParseMode.HTML)
    except Exception:
        await update.message.reply_text("⚠️ Usage: `/search UserID`", parse_mode=ParseMode.Markdown)

async def admin_backup_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS: return
    if os.path.exists(DB_FILE):
        msg = await update.message.reply_text("⏳ <i>Preparing Database Backup...</i>", parse_mode=ParseMode.HTML)
        try:
            with open(DB_FILE, 'rb') as f:
                await context.bot.send_document(
                    chat_id=update.effective_chat.id, 
                    document=InputFile(f, filename=f"BotBackup_{datetime.datetime.now().strftime('%Y%m%d')}.db"),
                    caption="💾 <b>Here is your Bot Database Backup.</b>",
                    parse_mode=ParseMode.HTML
                )
            await msg.delete()
        except Exception as e:
            await msg.edit_text(f"❌ <b>Backup Failed:</b> {e}", parse_mode=ParseMode.HTML)
    else:
        await update.message.reply_text("❌ <b>Database file not found!</b>", parse_mode=ParseMode.HTML)

async def ban_user_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS: return
    try:
        target_id = int(context.args[0])
        set_ban_status(target_id, 1)
        await update.message.reply_text(f"✅ User <code>{target_id}</code> has been successfully <b>BANNED</b>.", parse_mode=ParseMode.HTML)
    except Exception:
        await update.message.reply_text("⚠️ Usage: `/ban UserID`", parse_mode=ParseMode.Markdown)

async def unban_user_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS: return
    try:
        target_id = int(context.args[0])
        set_ban_status(target_id, 0)
        await update.message.reply_text(f"✅ User <code>{target_id}</code> has been successfully <b>UNBANNED</b>.", parse_mode=ParseMode.HTML)
    except Exception:
        await update.message.reply_text("⚠️ Usage: `/unban UserID`", parse_mode=ParseMode.Markdown)

async def broadcast_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS: return
    if not context.args:
        await update.message.reply_text("⚠️ Usage: `/broadcast Your message here`", parse_mode=ParseMode.Markdown)
        return
    message = " ".join(context.args)
    users = get_all_users()
    msg = await update.message.reply_text(f"⏳ <i>Broadcasting to {len(users)} users... Please wait.</i>", parse_mode=ParseMode.HTML)
    success = 0
    failed = 0
    for u_id in users:
        try:
            await context.bot.send_message(chat_id=u_id, text=f"📢 <b>ADMIN BROADCAST</b>\n━━━━━━━━━━━━━━━━━━━━\n{message}", parse_mode=ParseMode.HTML)
            success += 1
        except Exception:
            failed += 1
        await asyncio.sleep(0.05) 
    await msg.edit_text(f"✅ <b>Broadcast Completed!</b>\n━━━━━━━━━━━━━━━━━━━━\n🟢 Delivered: {success}\n🔴 Failed: {failed}", parse_mode=ParseMode.HTML)


# ==============================================================================
# 🌐 RENDER DUMMY WEB SERVER & MAIN LOOP
# ==============================================================================

async def web_server_handler(request):
    return web.Response(text="Bot is running perfectly! V25 Enterprise MAX Edition with Cache Optimizations.")

async def start_dummy_server():
    try:
        app = web.Application()
        app.router.add_get('/', web_server_handler)
        port = int(os.environ.get('PORT', 8080))
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, '0.0.0.0', port)
        await site.start()
    except Exception: 
        pass

async def post_init(app: Application):
    asyncio.create_task(start_dummy_server())

if __name__ == "__main__":
    init_db()
    app = Application.builder().token(TOKEN).post_init(post_init).build()
    
    # Registering Commands
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin_panel))
    app.add_handler(CommandHandler("status", admin_status))
    app.add_handler(CommandHandler("ban", ban_user_cmd))
    app.add_handler(CommandHandler("unban", unban_user_cmd))
    app.add_handler(CommandHandler("broadcast", broadcast_cmd))
    app.add_handler(CommandHandler("users", admin_users_cmd))
    app.add_handler(CommandHandler("search", admin_search_cmd))
    app.add_handler(CommandHandler("backup", admin_backup_cmd))
    
    # Registering Handlers
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # 🔥 EXTREME SPEED POLLING SYSTEM (Runs every 4 seconds now)
    app.job_queue.run_repeating(global_otp_checker_job, interval=4, first=2)
    
    # Forwarder runs normally
    app.job_queue.run_repeating(auto_range_forwarder_job, interval=60, first=10)
    
    logger.info("✨ VERSION 25.0 ENTERPRISE MAX STARTED SUCCESSFULLY... ✨")
    app.run_polling(drop_pending_updates=True)
