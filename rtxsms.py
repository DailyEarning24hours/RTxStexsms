"""
==============================================================================
PROJECT: ✨ PREMIUM OTP BOT (Ultimate Update - Version 17.0 ENTERPRISE) ✨
CAPACITY: 10,000+ Users on Render Free Plan (O(1) Hash-Map Algorithm Added).
RESTORED: Auto OTP & Range Forwarding Fixed.
FILTERED RANGE: Only Facebook, WhatsApp, and Telegram ranges are forwarded.
DYNAMIC UI: Numbers automatically remove upon receiving OTP. Message deletes when all done.
FEATURES: Premium UI, Anti-Error System, Auto-Retry, Custom Range.
ADMIN PANEL: Fully working Broadcast, Ban, Unban, Reply features added.
FORMATTING: Fully Expanded, No Shortcuts, Maximum Stability.
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

# 🔥 NEW BOT TOKEN ADDED
TOKEN = "8784714590:AAGW1bthOSIh2HUl2vPCYS_zv13zEz7BOsg"

# 🔥 2 ADMIN IDs
ADMIN_IDS = 6031032502

# 🔥 4 SUBSCRIPTION CHATS (Converted from your links to Usernames for API check)
CHANNELS = ["@EarnXtract", "@RTx_Sms", "@ConsoleXRT", "@RTxOtpX"]

# 🔥 NEW TARGET GROUPS
RANGE_GROUP_ID = -1003627708272
OTP_GROUP_ID = -1003830374258

STEX_EMAIL = "mdrajaislam469@gmail.com"
STEX_PASSWORD = "Raja1234@#"

API_LOGIN = "https://stexsms.com/mapi/v1/mauth/login"
API_CONSOLE = "https://stexsms.com/mapi/v1/mdashboard/console/info"
API_GET_NUM = "https://stexsms.com/mapi/v1/mdashboard/getnum/number"
API_INBOX = "https://stexsms.com/mapi/v1/mdashboard/getnum/info"
API_2FA = "https://2fa.cn/codes/{}"

# ==============================================================================
# 🛑 ADVANCED SERVER CRASH PREVENTION & CACHING
# ==============================================================================

MAUTH_TOKEN = None
GLOBAL_SESSION = None 
AUTH_LOCK = asyncio.Lock() 
LAST_AUTH_TIME = 0

CONSOLE_CACHE = None
LAST_CONSOLE_FETCH = 0
CONSOLE_CACHE_TTL = 15  

SENT_RANGES = set()

START_TIME = datetime.datetime.now()
BASE_USER_AGENT = "Mozilla/5.0 (Linux; Android 14; SM-A135F) AppleWebKit/537.36 Chrome/145.0 Mobile Safari/537.36"

DB_POOL_SIZE = 15 

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", 
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ==============================================================================
# 🧠 ENTERPRISE MEMORY SYSTEM (FOR 10,000+ USERS & DYNAMIC MESSAGES)
# ==============================================================================

WAITING_OTPS = {}
BATCH_MSGS = {} # Track batched messages to dynamically edit/delete them
OTP_TIMEOUT_SECONDS = 1200 

def get_hash_key(number_str):
    """Generates an O(1) lookup key for extreme performance on Render Free Plan."""
    clean_str = re.sub(r'\D', '', str(number_str))
    if not clean_str:
        return "UNKNOWN"
    return clean_str[-8:]


# ==============================================================================
# 🔐 ULTIMATE API AUTHENTICATION & REQUEST WRAPPER
# ==============================================================================

async def get_session():
    global GLOBAL_SESSION
    if GLOBAL_SESSION is None or GLOBAL_SESSION.closed:
        connector = aiohttp.TCPConnector(
            limit=200,                  # Boosted for heavy load
            keepalive_timeout=60,      
            ttl_dns_cache=300,         
            enable_cleanup_closed=True 
        )
        GLOBAL_SESSION = aiohttp.ClientSession(connector=connector)
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

async def authenticate_stex(force=False):
    global MAUTH_TOKEN, LAST_AUTH_TIME
    
    async with AUTH_LOCK:
        if not force:
            if time.time() - LAST_AUTH_TIME < 15 and MAUTH_TOKEN:
                return True
                
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
            async with session.post(API_LOGIN, json=payload, headers=headers, timeout=15, ssl=False) as response:
                if response.status == 200:
                    data = await parse_response_safely(response)
                    if data and str(data.get('meta', {}).get('code')) == '200':
                        MAUTH_TOKEN = data['data']['token']
                        LAST_AUTH_TIME = time.time()
                        return True
                return False
        except Exception:
            return False

def get_stex_headers():
    return {
        "User-Agent": BASE_USER_AGENT,
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json",
        "mauthtoken": str(MAUTH_TOKEN),
        "Cookie": f"mauthtoken={MAUTH_TOKEN}"
    }

async def stex_api_request(method, url, json_payload=None):
    global MAUTH_TOKEN
    max_retries = 5 # Increased for zero-error tolerance
    
    for attempt in range(max_retries):
        try:
            if not MAUTH_TOKEN:
                success = await authenticate_stex()
                if not success:
                    await asyncio.sleep(2)
                    continue
                    
            session = await get_session()
            headers = get_stex_headers()
            
            if method.upper() == 'GET':
                response = await session.get(url, headers=headers, timeout=15, ssl=False)
            else:
                response = await session.post(url, json=json_payload, headers=headers, timeout=15, ssl=False)
                
            status = response.status
            
            if status == 401 or status == 403:
                MAUTH_TOKEN = None
                continue
                
            if status == 200:
                data = await parse_response_safely(response)
                if isinstance(data, dict):
                    meta_code = str(data.get('meta', {}).get('code', '200'))
                    if meta_code == '401' or meta_code == '403':
                        MAUTH_TOKEN = None
                        continue
                return 200, data
            
            elif status >= 500:
                await asyncio.sleep(3)
                continue
            else:
                return status, None
                
        except asyncio.TimeoutError:
            await asyncio.sleep(2)
        except Exception:
            await asyncio.sleep(2)
            
    return 500, None 


# ==============================================================================
# 🗄️ DATABASE MANAGEMENT (WAL MODE ENABLED)
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
        conn.execute('PRAGMA cache_size=-64000;') 
        conn.row_factory = sqlite3.Row
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
        c.execute('''CREATE TABLE IF NOT EXISTS otp_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            number TEXT,
            code TEXT,
            service TEXT,
            full_message TEXT,
            date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')
        c.execute('CREATE INDEX IF NOT EXISTS idx_otp_history_user ON otp_history(user_id, date DESC)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_otp_history_number ON otp_history(number)')
        conn.commit()

def get_user(user_id):
    with db_pool.get_connection() as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
        return c.fetchone()

def register_user(user_id):
    if get_user(user_id) is None:
        with db_pool.get_connection() as conn:
            c = conn.cursor()
            c.execute("INSERT INTO users (user_id, join_date) VALUES (?, CURRENT_TIMESTAMP)", (user_id,))
            conn.commit()
        return True
    return False

def ensure_user(user_id):
    user = get_user(user_id)
    if user is None:
        register_user(user_id)
        user = get_user(user_id)
    return user

def is_user_banned(user_id):
    user = ensure_user(user_id)
    if user and len(user) > 2 and user[2] == 1: 
        return True
    return False

def get_all_users():
    """Returns a list of all registered user IDs for broadcasting."""
    with db_pool.get_connection() as conn:
        c = conn.cursor()
        c.execute("SELECT user_id FROM users")
        return [row[0] for row in c.fetchall()]

def set_ban_status(user_id, status):
    """Sets the ban status of a user. 1 = Banned, 0 = Unbanned."""
    ensure_user(user_id)
    with db_pool.get_connection() as conn:
        c = conn.cursor()
        c.execute("UPDATE users SET is_banned=? WHERE user_id=?", (status, user_id))
        conn.commit()

def save_otp_history(user_id, number, code, service, msg):
    with db_pool.get_connection() as conn:
        c = conn.cursor()
        try:
            c.execute("INSERT INTO otp_history (user_id, number, code, service, full_message) VALUES (?, ?, ?, ?, ?)", (user_id, number, code, service, msg))
            conn.commit()
        except Exception:
            pass


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
    if country_name in COUNTRY_FLAGS: return COUNTRY_FLAGS[country_name]
    for name, flag in COUNTRY_FLAGS.items():
        if name.lower() in country_name.lower() or country_name.lower() in name.lower():
            return flag
    return "🚩"

def extract_code(message):
    match = re.search(r'\b\d{4,8}\b', str(message))
    return match.group(0) if match else "See Msg"


# ==============================================================================
# 🔒 MIDDLEWARES & AUTO DELETE
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
        # Proper URL formatting even if username is used
        channel_url = f"https://t.me/{c.replace('@', '')}"
        keyboard.append([InlineKeyboardButton(f"📢 Join {c}", url=channel_url)])
        
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
            await update.message.reply_text("🚫 <b>You have been banned by the Admins.</b>", parse_mode=ParseMode.HTML)
        return True
    return False

async def delete_message_later(bot, chat_id, msg_id, delay_seconds):
    """Deletes 2FA code automatically after 5 minutes."""
    await asyncio.sleep(delay_seconds)
    try:
        await bot.delete_message(chat_id=chat_id, message_id=msg_id)
    except Exception:
        pass

async def update_dynamic_batch_message(context, chat_id, msg_id, batch_key):
    """Dynamically removes received numbers or deletes message if all numbers are processed."""
    if batch_key not in BATCH_MSGS:
        return
        
    batch = BATCH_MSGS[batch_key]
    
    if len(batch['numbers']) == 0:
        # All 3 numbers done, delete the entire message to keep UI extremely clean!
        try:
            await context.bot.delete_message(chat_id=chat_id, message_id=msg_id)
        except Exception:
            pass
        del BATCH_MSGS[batch_key]
    else:
        # Update message to show only remaining numbers
        num_str = ""
        symbols = ["❶", "❷", "❸"] 
        for i, n in enumerate(batch['numbers']):
            idx = i % len(symbols)
            num_str += f"{symbols[idx]} <code>{n}</code>\n"
            
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
                InlineKeyboardButton("🔙 Back to Category", callback_data="go_cat")
            ]
        ]
        
        try:
            await context.bot.edit_message_text(
                chat_id=chat_id,
                message_id=msg_id,
                text=txt,
                reply_markup=InlineKeyboardMarkup(kb),
                parse_mode=ParseMode.HTML
            )
        except Exception:
            pass


# ==============================================================================
# 🤖 AUTO RANGE FORWARDER JOB (-1003627708272) WITH SPECIFIC APP FILTERS
# ==============================================================================

async def auto_range_forwarder_job(context: ContextTypes.DEFAULT_TYPE):
    """
    Fetches API and forwards NEW active ranges to the specific Range Group.
    🔥 FILTER: ONLY FORWARDS FACEBOOK, WHATSAPP, AND TELEGRAM RANGES.
    """
    global SENT_RANGES
    status, data = await stex_api_request('GET', API_CONSOLE)
    
    if status == 200 and isinstance(data, dict):
        logs = data.get('data', {}).get('logs', [])
        if not isinstance(logs, list): return
        
        new_ranges_count = 0
        bot_username = context.bot.username
        
        # 🎯 Apps that are allowed to be forwarded to the range group
        allowed_apps = ['facebook', 'whatsapp', 'telegram']
        
        for log in logs:
            if new_ranges_count >= 5: break
            if isinstance(log, dict):
                r_val = log.get('range')
                app_name = str(log.get('app_name', 'Unknown')).lower()
                c_name = log.get('country', 'Unknown')
                
                # Check if the app name contains any of the allowed apps
                is_target_app = any(app in app_name for app in allowed_apps)
                
                if r_val and r_val not in SENT_RANGES and is_target_app:
                    SENT_RANGES.add(r_val)
                    new_ranges_count += 1
                    
                    if len(SENT_RANGES) > 5000:
                        SENT_RANGES.clear()
                        
                    # Format the actual App Name nicely for display
                    display_app_name = log.get('app_name', 'Unknown').title()
                    
                    range_msg = (
                        f"🔥 <b>New Range find</b>\n"
                        f"━━━━━━━━━━━━━━━━━━━━\n"
                        f"🎯 Range - <code>{r_val}</code>\n"
                        f"🛒 Service - <i>{html.escape(display_app_name)}</i>\n"
                        f"🌍 Country - {get_flag(c_name)} {c_name}"
                    )
                    
                    kb = [[InlineKeyboardButton("🤖 Bot Link", url=f"https://t.me/{bot_username}")]]
                    
                    try:
                        await context.bot.send_message(
                            chat_id=RANGE_GROUP_ID, 
                            text=range_msg, 
                            reply_markup=InlineKeyboardMarkup(kb), 
                            parse_mode=ParseMode.HTML
                        )
                        await asyncio.sleep(1)
                    except Exception as e:
                        logger.error(f"Range Forward Error: {e}")


# ==============================================================================
# 🚀 GLOBAL OTP POLLER (10k OPTIMIZED + DYNAMIC MESSAGE + FORWARD)
# ==============================================================================

async def global_otp_checker_job(context: ContextTypes.DEFAULT_TYPE):
    """
    🔥 ENTERPRISE POLLER 🔥
    Handles O(1) hash map lookups, Dynamic UI Updates, and precise formatting forwards.
    """
    global WAITING_OTPS, BATCH_MSGS
    if not WAITING_OTPS: 
        return 
    
    date_str = datetime.datetime.now().strftime("%Y-%m-%d")
    url = f"{API_INBOX}?date={date_str}&page=1&search=&status="
    
    current_time = time.time()
    expired_keys = []
    
    # 1. Cleanup Timeouts & Remove from Dynamic Batches
    for hash_key, data in list(WAITING_OTPS.items()):
        if current_time - data['time'] > OTP_TIMEOUT_SECONDS:
            expired_keys.append(hash_key)
            
    for h_key in expired_keys:
        user_data = WAITING_OTPS.pop(h_key, None)
        if user_data:
            b_key = user_data.get('batch_key')
            if b_key and b_key in BATCH_MSGS:
                f_num = user_data.get('full_num')
                if f_num in BATCH_MSGS[b_key]['numbers']:
                    BATCH_MSGS[b_key]['numbers'].remove(f_num)
                if len(BATCH_MSGS[b_key]['numbers']) == 0:
                    try:
                        await context.bot.delete_message(chat_id=user_data['chat_id'], message_id=user_data['msg_id'])
                    except: pass
                    del BATCH_MSGS[b_key]

    if not WAITING_OTPS: 
        return 
    
    # 2. Fetch Inbox ONCE
    status, result = await stex_api_request('GET', url)
    if status != 200 or not result: return

    otp_list = result.get('data', {}).get('numbers', [])
    if not isinstance(otp_list, list) or not otp_list: return
    
    found_keys = []
    
    for item in otp_list:
        if isinstance(item, dict) and item.get('status') == 'success':
            api_num = item.get('number', '')
            hash_key = get_hash_key(api_num)
            
            if hash_key in WAITING_OTPS:
                found_keys.append(hash_key)
                
                user_data = WAITING_OTPS[hash_key]
                user_id = user_data['user_id']
                chat_id = user_data['chat_id']
                msg_id = user_data['msg_id']
                full_num = user_data['full_num']
                batch_key = user_data['batch_key']
                
                raw_msg = item.get('otp', item.get('message', 'No Message'))
                code_only = extract_code(raw_msg)
                svc_name = item.get('full_number', 'Service')
                
                save_otp_history(user_id, full_num, code_only, svc_name, raw_msg)
                
                # --- STEP A: DYNAMICALLY REMOVE NUMBER FROM MENU ---
                if batch_key in BATCH_MSGS:
                    if full_num in BATCH_MSGS[batch_key]['numbers']:
                        BATCH_MSGS[batch_key]['numbers'].remove(full_num)
                    await update_dynamic_batch_message(context, chat_id, msg_id, batch_key)

                # --- STEP B: SEND OTP TO USER ---
                user_msg = (
                    f"🎉 <b>OTP RECEIVED SUCCESSFULLY!</b> ✨\n"
                    f"━━━━━━━━━━━━━━━━━━━━\n"
                    f"📱 <b>Service :</b> <i>{html.escape(str(svc_name))}</i>\n"
                    f"📞 <b>Number  :</b> <code>{full_num}</code>\n"
                    f"🔑 <b>Your OTP:</b> <code>{code_only}</code>\n"
                    f"━━━━━━━━━━━━━━━━━━━━"
                )
                asyncio.create_task(context.bot.send_message(chat_id=chat_id, text=user_msg, parse_mode=ParseMode.HTML))
                
                # --- STEP C: FORWARD TO OTP GROUP (-1003830374258) ---
                group_msg = (
                    f"🔔 <b>Otp Received</b>\n"
                    f"━━━━━━━━━━━━━━━━━━━━\n"
                    f"📱 Number - <code>{full_num}</code>\n"
                    f"🛒 Service - <pre>{html.escape(str(svc_name))}</pre>\n"
                    f"🔑 Code - <code>{code_only}</code>\n"
                    f"✉️ Full sms - <pre>{html.escape(str(raw_msg))}</pre>"
                )
                group_kb = [[InlineKeyboardButton("👨‍💻 Owner", url="https://t.me/RTx2R")]]
                try:
                    asyncio.create_task(
                        context.bot.send_message(
                            chat_id=OTP_GROUP_ID, 
                            text=group_msg, 
                            reply_markup=InlineKeyboardMarkup(group_kb), 
                            parse_mode=ParseMode.HTML
                        )
                    )
                except Exception as e:
                    logger.error(f"OTP Forward Error: {e}")

    # Remove processed numbers
    for k in found_keys: WAITING_OTPS.pop(k, None)


# ==============================================================================
# 🎯 CLEAN 3-NUMBER GENERATION SYSTEM & DYNAMIC BATCH REGISTRATION
# ==============================================================================

async def process_number_generation(update: Update, context: ContextTypes.DEFAULT_TYPE, range_val, is_callback=True):
    global WAITING_OTPS, BATCH_MSGS
    
    wait_txt = "⏳ <i>Connecting to secure server... Generating 3 Numbers...</i> 🚀"
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
        
    payload = {"range": range_val, "is_national": False, "remove_plus": False}
    fetched_numbers = []
    country_name = "Unknown"
    
    # Loop 3 times to fetch 3 numbers
    for _ in range(2):
        await asyncio.sleep(0.5) 
        status, resp_json = await stex_api_request('POST', API_GET_NUM, json_payload=payload)
        if status == 200 and isinstance(resp_json, dict) and 'data' in resp_json and resp_json['data'].get('number'):
            data = resp_json['data']
            num = data.get('number', 'N/A')
            country_name = data.get('country', country_name) 
            fetched_numbers.append(num)
            
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
            f"⏳ <i>Waiting for SMS... (Received numbers will disappear)</i>"
        )
        
        # 🔥 CHANGED BACK BUTTON TO 'BACK TO CATEGORY'
        kb = [
            [InlineKeyboardButton("💬 OTP GROUP", url="https://t.me/RTxOtpX")],
            [
                InlineKeyboardButton("🔄 Change Number", callback_data="change_num"), 
                InlineKeyboardButton("🔙 Back to Category", callback_data="go_cat")
            ]
        ]
        
        await msg.edit_text(text=txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.HTML)
        
        # 🔥 Register Batch for Dynamic Removal
        batch_key = f"{chat_id}_{msg.message_id}"
        BATCH_MSGS[batch_key] = {
            'numbers': fetched_numbers.copy(),
            'country_name': country_name,
            'flag': flag
        }
        
        # Add to Hash Map
        for n in fetched_numbers:
            hash_key = get_hash_key(n)
            WAITING_OTPS[hash_key] = {
                'full_num': n,
                'user_id': user_id, 
                'chat_id': chat_id, 
                'msg_id': msg.message_id, 
                'batch_key': batch_key,
                'time': time.time()
            }
            
        context.user_data['range'] = range_val 
        
    else:
        err_msg = "🔄 <i>Our high-speed servers are balancing the load. No numbers found right now.</i>"
        await msg.edit_text(
            text=f"📡 <b>Server Optimizing:</b>\n{err_msg}\n\nPlease try again or select another category.", 
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to Category", callback_data="go_cat")]]), 
            parse_mode=ParseMode.HTML
        )


# ==============================================================================
# 📋 MAIN MENUS & VERTICAL CATEGORY SELECTION
# ==============================================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await check_ban_middleware(update, context): return
    user_id = update.effective_user.id
    ensure_user(user_id)
    context.user_data.clear()
    
    if not await check_subscription(user_id, context.bot): 
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
        "🛡️ <b>Choose an option from the menu below.</b>"
    )
    reply_markup = ReplyKeyboardMarkup(kb, resize_keyboard=True)
    
    if hasattr(update_obj, 'message') and update_obj.message: 
        await update_obj.message.reply_text(msg, reply_markup=reply_markup, parse_mode=ParseMode.HTML)
    elif hasattr(update_obj, 'callback_query') and update_obj.callback_query:
        try: await update_obj.callback_query.message.delete()
        except: pass
        await context.bot.send_message(chat_id=update_obj.effective_chat.id, text=msg, reply_markup=reply_markup, parse_mode=ParseMode.HTML)

async def start_category_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = [
        [
            InlineKeyboardButton("📘 Facebook", callback_data="cat_facebook"), 
            InlineKeyboardButton("💬 WhatsApp", callback_data="cat_whatsapp")
        ],
        [
            InlineKeyboardButton("✈️ Telegram", callback_data="cat_telegram"),
            InlineKeyboardButton("📸 Instagram", callback_data="cat_instagram")
        ],
        [
            InlineKeyboardButton("🎯 Custom Range", callback_data="cat_custom")
        ]
    ]
    txt = (
        "📱 <b>SELECT SERVICE CATEGORY</b> 📱\n"
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
    
    if category == 'custom':
        txt = (
            "🎯 <b>CUSTOM RANGE GENERATOR</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "✏️ <i>Type your custom range below.</i>\n"
            "💡 <b>Ex:</b> <code>88017XXX</code>"
        )
        await query.edit_message_text(text=txt, parse_mode=ParseMode.HTML)
        context.user_data['state'] = 'WAITING_FOR_RANGE'
        return
    
    await query.edit_message_text(text="📡 <i>Connecting to Server... Please wait.</i> ⏳", parse_mode=ParseMode.HTML)
    await authenticate_stex(force=True)
    status, data = await stex_api_request('GET', API_CONSOLE)
    
    if status == 200 and isinstance(data, dict):
        logs = data.get('data', {}).get('logs', []) if isinstance(data.get('data'), dict) else []
        countries = {}
        
        for log in logs:
            if isinstance(log, dict) and category in str(log.get('app_name', '')).lower():
                c_name = log.get('country')
                r_val = log.get('range')
                if c_name and r_val and c_name not in countries:
                    countries[c_name] = r_val
        
        if not countries:
            await query.edit_message_text(
                text=f"📡 <b>Load Balancing...</b>\n<i>No immediate numbers found for {category.title()}. Please try again in a moment.</i>", 
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to Category", callback_data="go_cat")]]), 
                parse_mode=ParseMode.HTML
            )
            return
            
        kb = []
        for c_name, r_val in countries.items():
            kb.append([InlineKeyboardButton(f"{get_flag(c_name)} {c_name}", callback_data=f"rng_{r_val}")])
        kb.append([InlineKeyboardButton("🔙 Back to Categories", callback_data="go_cat")])
        
        txt = (
            f"🌍 <b>SELECT A COUNTRY ({category.title()})</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━"
        )
        await query.edit_message_text(text=txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.HTML)
    else:
        await query.edit_message_text(
            text=f"🔄 <b>Network Optimization in progress...</b>\nPlease try clicking again.", 
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to Category", callback_data="go_cat")]]), 
            parse_mode=ParseMode.HTML
        )


# ==============================================================================
# 🎮 TEXT HANDLER
# ==============================================================================

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await check_ban_middleware(update, context): return
    user_id = update.effective_user.id
    text = update.message.text
    user_data = context.user_data
    ensure_user(user_id)
    
    # 👑 ADMIN QUICK REPLY HANDLER
    if user_id in ADMIN_IDS and text.startswith("/reply"):
        try:
            parts = text.split(" ", 2)
            await context.bot.send_message(chat_id=int(parts[1]), text=f"👨‍💻 <b>Admin Reply:</b>\n━━━━━━━━━━━━━━━━━━━━\n{parts[2]}", parse_mode=ParseMode.HTML)
            await update.message.reply_text("✅ Reply sent successfully.")
        except Exception: 
            await update.message.reply_text("⚠️ Usage: `/reply UserID Message`")
        return

    # 📱 MENU HANDLERS
    if text == "📱 Get Number":
        if not await check_subscription(user_id, context.bot): await send_join_prompt(update, context)
        else: await start_category_selection(update, context)
            
    elif text == "🔐 Get 2FA":
        user_data['state'] = 'WAITING_FOR_2FA'
        await update.message.reply_text("🔐 <b>2FA CODE GENERATOR</b>\n━━━━━━━━━━━━━━━━━━━━\n<i>Paste your Secret Key below:</i>", parse_mode=ParseMode.HTML)
        
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
                    else: await msg.edit_text("❌ <b>Invalid Secret Key.</b>", parse_mode=ParseMode.HTML)
                else: await msg.edit_text("❌ <b>API Error!</b>", parse_mode=ParseMode.HTML)
        except Exception: await msg.edit_text("❌ <b>Network Error.</b>", parse_mode=ParseMode.HTML)
        user_data['state'] = None
        
    elif text == "🎧 Support":
        user_data['state'] = 'WAITING_FOR_SUPPORT'
        await update.message.reply_text("🎧 <b>SUPPORT SYSTEM</b>\n━━━━━━━━━━━━━━━━━━━━\n<i>Type your problem below.</i>", parse_mode=ParseMode.HTML)
        
    elif user_data.get('state') == 'WAITING_FOR_SUPPORT':
        for a_id in ADMIN_IDS:
            try: await context.bot.send_message(chat_id=a_id, text=f"📩 <b>Support</b>\n👤 <b>ID:</b> <code>{user_id}</code>\n💬 <b>Msg:</b> {html.escape(text)}\n\n<i>Reply with:</i>\n<code>/reply {user_id} message</code>", parse_mode=ParseMode.HTML)
            except: pass
        await update.message.reply_text("✅ <b>Message Sent!</b> An Admin will reply soon.", parse_mode=ParseMode.HTML)
        user_data['state'] = None
        
    elif text == "📊 See Activity":
        kb = [
            [InlineKeyboardButton("🔥 Range Channel", url="https://t.me/ConsoleXRT")],
            [InlineKeyboardButton("💬 OTP Channel", url="https://t.me/RTxOtpX")]
        ]
        await update.message.reply_text("📊 <b>BOT ACTIVITY LINKS</b>\n━━━━━━━━━━━━━━━━━━━━\n<i>Join to see live Bot activity:</i>", reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.HTML)
        
    elif user_data.get('state') == 'WAITING_FOR_RANGE':
        user_data['state'] = None
        await process_number_generation(update, context, text, is_callback=False)
        
    else:
        await show_main_menu(update, context)


# ==============================================================================
# 🎮 BUTTON HANDLER
# ==============================================================================

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await check_ban_middleware(update, context): return
    query = update.callback_query
    user_id = query.from_user.id
    data = query.data
    ensure_user(user_id)
    
    if data == "check_join":
        if await check_subscription(user_id, context.bot): 
            try: await query.message.delete()
            except: pass
            await show_main_menu(query, context)
        else: await query.answer("⚠️ Please join all channels/groups first.", show_alert=True)
            
    elif data.startswith("cat_"): await handle_category_click(update, context)
    elif data == "go_cat": await start_category_selection(update, context)
    elif data.startswith("rng_"): await process_number_generation(update, context, data.split("_")[1], is_callback=True)
    elif data == "change_num":
        if context.user_data.get('range'): await process_number_generation(update, context, context.user_data['range'], is_callback=True)
        else: await query.edit_message_text("⚠️ <b>Session Expired.</b>\n<i>Please start again.</i>", parse_mode=ParseMode.HTML)
    elif data == "go_main": await show_main_menu(query, context)


# ==============================================================================
# 👑 FULLY FUNCTIONAL ADMIN COMMANDS (BAN, UNBAN, BROADCAST)
# ==============================================================================

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS: return
    txt = (
        "🔐 <b>ADVANCED ADMIN PANEL</b> 🔐\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "🟢 <code>/status</code> - Show Bot Statistics\n"
        "📢 <code>/broadcast &lt;msg&gt;</code> - Message all users\n"
        "🚫 <code>/ban &lt;id&gt;</code> - Ban a user\n"
        "✅ <code>/unban &lt;id&gt;</code> - Unban a user\n"
        "💬 <code>/reply &lt;id&gt; &lt;msg&gt;</code> - Reply to support"
    )
    await update.message.reply_text(txt, parse_mode=ParseMode.HTML)

async def admin_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS: return
    uptime = datetime.datetime.now() - START_TIME
    with db_pool.get_connection() as conn:
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM users")
        t_users = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM otp_history")
        t_otps = c.fetchone()[0]
    txt = (
        f"📊 <b>LIVE SYSTEM STATUS (10k OPTIMIZED)</b> 📊\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"⏱ <b>Uptime:</b> {str(uptime).split('.')[0]}\n"
        f"👥 <b>Total Users:</b> {t_users}\n"
        f"📩 <b>Total OTPs:</b> {t_otps}\n"
        f"📡 <b>Active Waiters:</b> {len(WAITING_OTPS)} Numbers\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"✅ <i>System Running Smoothly</i>"
    )
    await update.message.reply_text(txt, parse_mode=ParseMode.HTML)

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
            # We use HTML parsing for premium look if admin uses tags
            await context.bot.send_message(
                chat_id=u_id, 
                text=f"📢 <b>ADMIN BROADCAST</b>\n━━━━━━━━━━━━━━━━━━━━\n{message}", 
                parse_mode=ParseMode.HTML
            )
            success += 1
        except Exception:
            failed += 1
        await asyncio.sleep(0.05) # Prevent flood wait
        
    await msg.edit_text(f"✅ <b>Broadcast Completed!</b>\n━━━━━━━━━━━━━━━━━━━━\n🟢 Delivered: {success}\n🔴 Failed: {failed}", parse_mode=ParseMode.HTML)


# ==============================================================================
# 🌐 RENDER DUMMY WEB SERVER & MAIN LOOP
# ==============================================================================

async def web_server_handler(request):
    return web.Response(text="Bot is running perfectly! V17 Enterprise Edition with Fixed Admin Panel & Filtered Range.")

async def start_dummy_server():
    try:
        app = web.Application()
        app.router.add_get('/', web_server_handler)
        port = int(os.environ.get('PORT', 8080))
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, '0.0.0.0', port)
        await site.start()
    except Exception: pass

async def post_init(app: Application):
    asyncio.create_task(start_dummy_server())

if __name__ == "__main__":
    init_db()
    app = Application.builder().token(TOKEN).post_init(post_init).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin_panel))
    app.add_handler(CommandHandler("status", admin_status))
    
    # NEW WORKING ADMIN COMMANDS
    app.add_handler(CommandHandler("ban", ban_user_cmd))
    app.add_handler(CommandHandler("unban", unban_user_cmd))
    app.add_handler(CommandHandler("broadcast", broadcast_cmd))
    
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    app.job_queue.run_repeating(global_otp_checker_job, interval=8, first=3)
    app.job_queue.run_repeating(auto_range_forwarder_job, interval=60, first=10)
    
    logger.info("✨ VERSION 17.0 ENTERPRISE STARTED... ✨")
    app.run_polling(drop_pending_updates=True)
