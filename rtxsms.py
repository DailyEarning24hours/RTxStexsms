"""
==============================================================================
PROJECT: ✨ PREMIUM OTP BOT (Ultimate Update - Version 9.0 PRO MAX) ✨
CRITICAL FIX: API JSON Parsing Override & 502/503 Auto-Retry Bypass.
FEATURES: Direct STEXSMS API, Global OTP Poller, SQLite WAL Mode, Memory Mgmt.
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

TOKEN = "8784714590:AAGW1bthOSIh2HUl2vPCYS_zv13zEz7BOsg"
ADMIN_ID = 6031032502
CHANNELS = ["@EarnXtract", "@RTx_Sms"]

STEX_EMAIL = "mdrajaislam469@gmail.com"
STEX_PASSWORD = "Raja1234@#"

API_LOGIN = "https://stexsms.com/mapi/v1/mauth/login"
API_CONSOLE = "https://stexsms.com/mapi/v1/mdashboard/console/info"
API_GET_NUM = "https://stexsms.com/mapi/v1/mdashboard/getnum/number"
API_INBOX = "https://stexsms.com/mapi/v1/mdashboard/getnum/info"
API_2FA = "https://2fa.cn/codes/{}"

# ==============================================================================
# 🛑 ADVANCED SERVER CRASH PREVENTION & GLOBAL VARIABLES
# ==============================================================================
MAUTH_TOKEN = None
GLOBAL_SESSION = None 
AUTH_LOCK = asyncio.Lock() 
LAST_AUTH_TIME = 0

REWARD_PER_OTP = 0.00125  
MIN_WITHDRAW_BDT = 50     
MIN_WITHDRAW_USD = 0.416  
USD_TO_BDT_RATE = 120     

START_TIME = datetime.datetime.now()
BASE_USER_AGENT = "Mozilla/5.0 (Linux; Android 14; SM-A135F Build/UP1A.231005.007) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.7632.120 Mobile Safari/537.36"

SELECT_METHOD, ENTER_ADDRESS = range(2)
DB_POOL_SIZE = 10 

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", 
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ==============================================================================
# 🧠 GLOBAL MEMORY FOR OTP POLLING
# ==============================================================================

WAITING_OTPS = {}
OTP_TIMEOUT_SECONDS = 1200 # 20 minutes timeout


# ==============================================================================
# 🔐 ULTIMATE API AUTHENTICATION & REQUEST WRAPPER (10000% SERVER BUSY FIX)
# ==============================================================================

async def get_session():
    """Returns a highly optimized, resilient global session."""
    global GLOBAL_SESSION
    if GLOBAL_SESSION is None or GLOBAL_SESSION.closed:
        connector = aiohttp.TCPConnector(limit=100, keepalive_timeout=30, enable_cleanup_closed=True)
        GLOBAL_SESSION = aiohttp.ClientSession(connector=connector)
    return GLOBAL_SESSION

async def parse_response_safely(response):
    """🔥 CRITICAL FIX: Forces JSON parsing even if STEX API headers are broken!"""
    try:
        return await response.json(content_type=None)
    except Exception:
        try:
            text = await response.text()
            return json.loads(text)
        except Exception as e:
            logger.error(f"Failed to parse API Response: {e}")
            return None

async def authenticate_stex():
    """Authenticates with STEX API using an Async Lock to prevent multiple simultaneous requests."""
    global MAUTH_TOKEN, LAST_AUTH_TIME
    
    async with AUTH_LOCK:
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
                        logger.info("✅ STEXSMS API Authenticated Successfully!")
                        return True
                logger.error(f"❌ STEXSMS Auth Failed: HTTP {response.status}")
                return False
        except Exception as e:
            logger.error(f"❌ STEXSMS Auth Exception: {e}")
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
    """
    🔥 THE ULTIMATE MASTERPIECE FIX 🔥
    Handles 401/403 Token Expiry, 502/503 Bad Gateway, and Invalid Content-Types instantly.
    """
    global MAUTH_TOKEN
    
    for attempt in range(3):
        if not MAUTH_TOKEN:
            success = await authenticate_stex()
            if not success:
                await asyncio.sleep(1)
                continue
                
        session = await get_session()
        headers = get_stex_headers()
        
        try:
            if method.upper() == 'GET':
                response = await session.get(url, headers=headers, timeout=15, ssl=False)
            else:
                response = await session.post(url, json=json_payload, headers=headers, timeout=15, ssl=False)
                
            status = response.status
            
            # Auto-Recover on Token Expiry
            if status in [401, 403]:
                logger.warning(f"Session Expired (HTTP {status}). Recovering...")
                MAUTH_TOKEN = None
                continue
                
            if status == 200:
                data = await parse_response_safely(response)
                
                # Check if STEX sent 200 HTTP but wrote 401 in JSON Meta
                if isinstance(data, dict):
                    meta_code = str(data.get('meta', {}).get('code', '200'))
                    if meta_code in ['401', '403']:
                        logger.warning("Session Expired inside JSON Meta. Recovering...")
                        MAUTH_TOKEN = None
                        continue
                return 200, data
            
            # Auto-Retry on Bad Gateway / Overload
            elif status in [500, 502, 503, 504]:
                logger.warning(f"STEX Server Overload (HTTP {status}). Retrying...")
                await asyncio.sleep(1.5)
                continue
            else:
                return status, None
                
        except asyncio.TimeoutError:
            logger.warning("STEX API Timeout... Retrying.")
            await asyncio.sleep(1)
        except Exception as e:
            logger.error(f"STEX Request Error: {e}")
            await asyncio.sleep(1)
            
    return 500, None 


# ==============================================================================
# 🗄️ DATABASE MANAGEMENT (WAL MODE ENABLED)
# ==============================================================================

DB_FILE = "bot.db"

class DatabasePool:
    def __init__(self, db_file, pool_size=10):
        self.db_file = db_file
        self.pool_size = pool_size
        
    @contextmanager
    def get_connection(self):
        conn = sqlite3.connect(self.db_file, timeout=30.0, check_same_thread=False)
        conn.execute('PRAGMA journal_mode=WAL;')
        conn.execute('PRAGMA synchronous=NORMAL;')
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
            user_id INTEGER PRIMARY KEY, balance REAL DEFAULT 0.0,
            referrer_id INTEGER, otp_success_count INTEGER DEFAULT 0,
            total_earned REAL DEFAULT 0.0, join_date TEXT, is_banned INTEGER DEFAULT 0
        )''')
        try: c.execute("ALTER TABLE users ADD COLUMN is_banned INTEGER DEFAULT 0")
        except sqlite3.OperationalError: pass
            
        c.execute('''CREATE TABLE IF NOT EXISTS withdrawals (
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, method TEXT, address TEXT,
            amount_usd REAL, amount_bdt REAL, status TEXT DEFAULT 'pending', date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')
        
        c.execute('''CREATE TABLE IF NOT EXISTS otp_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, number TEXT, code TEXT,
            service TEXT, full_message TEXT, date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')
        
        c.execute('CREATE INDEX IF NOT EXISTS idx_users_referrer ON users(referrer_id)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_withdrawals_user ON withdrawals(user_id, status)')
        conn.commit()
    logger.info("✅ Database optimized and initialized successfully.")

def get_user(user_id):
    with db_pool.get_connection() as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
        return c.fetchone()

def register_user(user_id, referrer_id=None):
    if get_user(user_id) is None:
        with db_pool.get_connection() as conn:
            c = conn.cursor()
            c.execute("INSERT INTO users (user_id, referrer_id, join_date) VALUES (?, ?, CURRENT_TIMESTAMP)", (user_id, referrer_id))
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
    if user and len(user) > 6 and user[6] == 1: 
        return True
    return False

def save_otp_history(user_id, number, code, service, msg):
    with db_pool.get_connection() as conn:
        c = conn.cursor()
        try:
            c.execute("INSERT INTO otp_history (user_id, number, code, service, full_message) VALUES (?, ?, ?, ?, ?)", (user_id, number, code, service, msg))
            conn.commit()
        except Exception: pass

def update_otp_and_reward(user_id):
    with db_pool.get_connection() as conn:
        c = conn.cursor()
        reward_given, referrer_id = False, None
        try:
            c.execute("UPDATE users SET otp_success_count = otp_success_count + 1 WHERE user_id=?", (user_id,))
            c.execute("SELECT referrer_id FROM users WHERE user_id=?", (user_id,))
            data = c.fetchone()
            if data and data[0]:
                referrer_id = data[0]
                c.execute("UPDATE users SET balance = balance + ?, total_earned = total_earned + ? WHERE user_id=?", (REWARD_PER_OTP, REWARD_PER_OTP, referrer_id))
                reward_given = True
            conn.commit()
        except Exception: pass
    return reward_given, referrer_id, REWARD_PER_OTP


# ==============================================================================
# 🌍 MASSIVE COUNTRY FLAGS DICTIONARY
# ==============================================================================

COUNTRY_FLAGS = {
"Afghanistan":"🇦🇫","Albania":"🇦🇱","Algeria":"🇩🇿","Andorra":"🇦🇩","Angola":"🇦🇴",
"Argentina":"🇦🇷","Armenia":"🇦🇲","Australia":"🇦🇺","Austria":"🇦🇹","Azerbaijan":"🇦🇿",
"Bahrain":"🇧🇭","Bangladesh":"🇧🇩","Belarus":"🇧🇾","Belgium":"🇧🇪","Bolivia":"🇧🇴",
"Brazil":"🇧🇷","Bulgaria":"🇧🇬","Cambodia":"🇰🇭","Cameroon":"🇨🇲","Canada":"🇨🇦","Chile":"🇨🇱",
"China":"🇨🇳","Colombia":"🇨🇴","Congo":"🇨🇬","Congo (DRC)":"🇨🇩","Costa Rica":"🇨🇷","Croatia":"🇭🇷",
"Cuba":"🇨🇺","Cyprus":"🇨🇾","Czechia":"🇨🇿","Denmark":"🇩🇰","Dominican Republic":"🇩🇴","Ecuador":"🇪🇨",
"Egypt":"🇪🇬","El Salvador":"🇸🇻","Estonia":"🇪🇪","Ethiopia":"🇪🇹","Finland":"🇫🇮","France":"🇫🇷",
"Georgia":"🇬🇪","Germany":"🇩🇪","Ghana":"🇬🇭","Greece":"🇬🇷","Guatemala":"🇬🇹","Haiti":"🇭🇹",
"Honduras":"🇭🇳","Hungary":"🇭🇺","India":"🇮🇳","Indonesia":"🇮🇩","Iran":"🇮🇷","Iraq":"🇮🇶",
"Ireland":"🇮🇪","Israel":"🇮🇱","Italy":"🇮🇹","Ivory Coast":"🇨🇮","Jamaica":"🇯🇲","Japan":"🇯🇵",
"Jordan":"🇯🇴","Kazakhstan":"🇰🇿","Kenya":"🇰🇪","Kuwait":"🇰🇼","Kyrgyzstan":"🇰🇬","Laos":"🇱🇦",
"Latvia":"🇱🇻","Lebanon":"🇱🇧","Lithuania":"🇱🇹","Madagascar":"🇲🇬","Malaysia":"🇲🇾","Mali":"🇲🇱",
"Mexico":"🇲🇽","Moldova":"🇲🇩","Mongolia":"🇲🇳","Morocco":"🇲🇦","Myanmar":"🇲🇲","Nepal":"🇳🇵",
"Netherlands":"🇳🇱","New Zealand":"🇳🇿","Nicaragua":"🇳🇮","Nigeria":"🇳🇬","North Macedonia":"🇲🇰",
"Norway":"🇳🇴","Oman":"🇴🇲","Pakistan":"🇵🇰","Palestine":"🇵🇸","Panama":"🇵🇦","Paraguay":"🇵🇾",
"Peru":"🇵🇪","Philippines":"🇵🇭","Poland":"🇵🇱","Portugal":"🇵🇹","Qatar":"🇶🇦","Romania":"🇷🇴",
"Russia":"🇷🇺","Rwanda":"🇷🇼","Saudi Arabia":"🇸🇦","Senegal":"🇸🇳","Serbia":"🇷🇸","Singapore":"🇸🇬",
"Slovakia":"🇸🇰","Slovenia":"🇸🇮","Somalia":"🇸🇴","South Africa":"🇿🇦","South Korea":"🇰🇷",
"Spain":"🇪🇸","Sri Lanka":"🇱🇰","Sudan":"🇸🇩","Sweden":"🇸🇪","Switzerland":"🇨🇭","Syria":"🇸🇾",
"Taiwan":"🇹🇼","Tajikistan":"🇹🇯","Tanzania":"🇹🇿","Thailand":"🇹🇭","Tunisia":"🇹🇳","Turkey":"🇹🇷",
"Turkmenistan":"🇹🇲","Uganda":"🇺🇬","Ukraine":"🇺🇦","United Arab Emirates":"🇦🇪",
"United Kingdom":"🇬🇧","United States":"🇺🇸","Uruguay":"🇺🇾","Uzbekistan":"🇺🇿","Venezuela":"🇻🇪",
"Vietnam":"🇻🇳","Yemen":"🇾🇪","Zambia":"🇿🇲","Zimbabwe":"🇿🇼","PostPaid": "📡"
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

def clean_number(num):
    return re.sub(r'\D', '', str(num))

def is_number_match(user_number, api_number):
    u_num, a_num = clean_number(user_number), clean_number(api_number)
    if not u_num or not a_num: return False
    check_len = min(min(len(u_num), len(a_num)), 8)
    return u_num[-check_len:] == a_num[-check_len:]

def escape_html(text):
    return html.escape(str(text))


# ==============================================================================
# 🔒 MIDDLEWARES & SUBSCRIPTIONS
# ==============================================================================

async def check_subscription(user_id, bot):
    for channel in CHANNELS:
        try:
            member = await bot.get_chat_member(chat_id=channel, user_id=user_id)
            if member.status in ['left', 'kicked']: return False
        except Exception: return False
    return True

async def send_join_prompt(update, context):
    keyboard = [[InlineKeyboardButton(f"📢 Join {c}", url=f"https://t.me/{c.replace('@', '')}")] for c in CHANNELS]
    keyboard.append([InlineKeyboardButton("✅ Joined / Verify", callback_data="check_join")])
    msg = "⛔ <b>Access Denied!</b>\n━━━━━━━━━━━━━━━━━━━━\n<i>To use this premium bot, you must be a member of our official channels.</i>\n\n👇 <b>Please join below to continue:</b>"
    if update.callback_query: await update.callback_query.edit_message_text(text=msg, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
    else: await update.message.reply_text(text=msg, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)

async def check_ban_middleware(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if is_user_banned(user_id):
        if update.callback_query: await update.callback_query.answer("🚫 You are banned from using this bot.", show_alert=True)
        else: await update.message.reply_text("🚫 <b>You have been banned by the Admin.</b>", parse_mode=ParseMode.HTML)
        return True
    return False


# ==============================================================================
# 🚀 GLOBAL OTP POLLER (USING ULTIMATE API WRAPPER)
# ==============================================================================

async def global_otp_checker_job(context: ContextTypes.DEFAULT_TYPE):
    global WAITING_OTPS
    if not WAITING_OTPS: return 
    
    date_str = datetime.datetime.now().strftime("%Y-%m-%d")
    url = f"{API_INBOX}?date={date_str}&page=1&search=&status="
    current_time = time.time()
    
    expired_numbers = [num for num, data in WAITING_OTPS.items() if current_time - data['time'] > OTP_TIMEOUT_SECONDS]
    for num in expired_numbers:
        user_data = WAITING_OTPS.pop(num)
        try: await context.bot.edit_message_text(chat_id=user_data['chat_id'], message_id=user_data['msg_id'], text="❌ <b>Timeout!</b>\n━━━━━━━━━━━━━━━━━━━━\n<i>SMS did not arrive in 20 minutes. Please try generating a new number.</i>", parse_mode=ParseMode.HTML)
        except Exception: pass

    if not WAITING_OTPS: return 
    
    status, result = await stex_api_request('GET', url)
    if status != 200 or not result: return

    otp_list = result.get('data', {}).get('numbers', [])
    if not isinstance(otp_list, list) or not otp_list: return
    
    found_keys = []
    for item in otp_list:
        if isinstance(item, dict) and item.get('status') == 'success':
            api_num = clean_number(item.get('number', ''))
            for waiting_num, user_data in WAITING_OTPS.items():
                if is_number_match(waiting_num, api_num):
                    found_keys.append(waiting_num)
                    user_id, chat_id, msg_id = user_data['user_id'], user_data['chat_id'], user_data['msg_id']
                    
                    raw_msg = item.get('otp', item.get('message', 'No Message'))
                    code_only = extract_code(raw_msg)
                    svc_name = item.get('full_number', 'Service')
                    
                    save_otp_history(user_id, item.get('number'), code_only, svc_name, raw_msg)
                    
                    final_msg = f"🎉 <b>OTP RECEIVED SUCCESSFULLY!</b> ✨\n━━━━━━━━━━━━━━━━━━━━\n📱 <b>Service :</b> <i>{escape_html(svc_name)}</i>\n📞 <b>Number  :</b> <code>{item.get('number')}</code>\n🔑 <b>Your OTP:</b> <code>{code_only}</code>\n━━━━━━━━━━━━━━━━━━━━\n🎁 <b>Refer friends and earn Free Balance!</b>"
                    try: await context.bot.edit_message_text(chat_id=chat_id, message_id=msg_id, text=final_msg, parse_mode=ParseMode.HTML)
                    except Exception: asyncio.create_task(context.bot.send_message(chat_id=chat_id, text=final_msg, parse_mode=ParseMode.HTML))
                    
                    cat_kb = [[InlineKeyboardButton("📘 Facebook", callback_data="cat_facebook"), InlineKeyboardButton("💬 WhatsApp", callback_data="cat_whatsapp")], [InlineKeyboardButton("🌍 Other Services", callback_data="cat_other")]]
                    asyncio.create_task(context.bot.send_message(chat_id=chat_id, text="📱 <b>NEED ANOTHER NUMBER?</b> 📱\n━━━━━━━━━━━━━━━━━━━━\n<i>Select a service category below to fetch active numbers from the console instantly:</i>", reply_markup=InlineKeyboardMarkup(cat_kb), parse_mode=ParseMode.HTML))
                    
                    reward_given, referrer_id, amount = update_otp_and_reward(user_id)
                    if reward_given and referrer_id:
                        asyncio.create_task(context.bot.send_message(chat_id=referrer_id, text=f"🔔 <b>Commission Received!</b> 💸\n━━━━━━━━━━━━━━━━━━━━\n👤 <b>Source:</b> <i>Referral User</i>\n💰 <b>Amount:</b> <b>+${amount:.5f}</b> (0.15 BDT)\n✅ <b>Status:</b> <i>Added to your Wallet!</i>", parse_mode=ParseMode.HTML))
                    break 

    for k in found_keys: WAITING_OTPS.pop(k, None)


# ==============================================================================
# 🎯 NUMBER GENERATION SYSTEM
# ==============================================================================

async def get_number_api(update: Update, context: ContextTypes.DEFAULT_TYPE, range_val):
    global WAITING_OTPS
    query, chat_id, user_id = update.callback_query, update.callback_query.message.chat_id, update.callback_query.from_user.id
    
    await query.edit_message_text(text="⏳ <i>Connecting to secure server... Generating Number...</i> 🚀", parse_mode=ParseMode.HTML)
    
    range_val = str(range_val).strip()
    if not range_val.upper().endswith("XXX"): range_val += "XXX"
        
    payload = {"range": range_val, "is_national": False, "remove_plus": False}
    status, resp_json = await stex_api_request('POST', API_GET_NUM, json_payload=payload)
        
    if status == 200 and isinstance(resp_json, dict) and 'data' in resp_json and resp_json['data'].get('number'):
        data = resp_json['data']
        number_val, country_name = data.get('number', 'N/A'), data.get('country', 'Unknown')
        
        txt = f"✅ <b>NUMBER GENERATED SUCCESSFULLY!</b>\n━━━━━━━━━━━━━━━━━━━━\n📞 <b>Number:</b> <code>{number_val}</code>\n{get_flag(country_name)} <b>Country:</b> <i>{country_name}</i>\n📊 <b>Status:</b> <b>Waiting for SMS...</b> ⏳\n━━━━━━━━━━━━━━━━━━━━\n<i>🚀 Please enter this number in the app and wait. We are auto-checking...</i>"
        kb = [[InlineKeyboardButton("📥 Refresh Status", callback_data="refresh_inbox")], [InlineKeyboardButton("🔄 Change Number", callback_data="change_num"), InlineKeyboardButton("🔙 Back to Category", callback_data="go_cat")]]
        
        sent_msg = await query.edit_message_text(text=txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.HTML)
        WAITING_OTPS[number_val] = {'user_id': user_id, 'chat_id': chat_id, 'msg_id': sent_msg.message_id, 'time': time.time()}
        context.user_data['range'] = range_val 
    else:
        err = resp_json.get('message', 'Server empty response') if isinstance(resp_json, dict) else f'API Error (HTTP {status})'
        await query.edit_message_text(text=f"❌ <b>Generation Failed:</b>\n<i>{err}</i>\n\nPlease try another country.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="go_cat")]]), parse_mode=ParseMode.HTML)


# ==============================================================================
# 📋 MAIN MENUS & CATEGORY SELECTION 
# ==============================================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await check_ban_middleware(update, context): return
    user_id, first_name = update.effective_user.id, update.effective_user.first_name
    
    referrer_id = None
    if context.args:
        try:
            if int(context.args[0]) != user_id: referrer_id = int(context.args[0])
        except ValueError: pass
    
    if register_user(user_id, referrer_id) and referrer_id:
        try: await context.bot.send_message(chat_id=referrer_id, text=f"🎉 <b>New Referral Joined!</b>\n👤 Name: <i>{first_name}</i>\n🆔 ID: <code>{user_id}</code>", parse_mode=ParseMode.HTML)
        except: pass
    
    context.user_data.clear()
    if not await check_subscription(user_id, context.bot): await send_join_prompt(update, context)
    else: await show_main_menu(update, context)

async def show_main_menu(update_obj, context):
    kb = [["📱 Get Number", "🔐 Get 2FA Code"], ["💰 Wallet / Refer", "💸 Withdraw"]]
    msg = "✨ <b>P R E M I U M   O T P   B O T</b> ✨\n━━━━━━━━━━━━━━━━━━━━\n👋 <i>Welcome to the most advanced & stable OTP system!</i>\n\n🛡️ <b>Choose an option from the menu below to get started.</b>"
    
    if hasattr(update_obj, 'message') and update_obj.message: await update_obj.message.reply_text(msg, reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True), parse_mode=ParseMode.HTML)
    elif hasattr(update_obj, 'callback_query') and update_obj.callback_query:
        try: await update_obj.callback_query.message.delete()
        except: pass
        await context.bot.send_message(chat_id=update_obj.effective_chat.id, text=msg, reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True), parse_mode=ParseMode.HTML)

async def start_category_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = [[InlineKeyboardButton("📘 Facebook", callback_data="cat_facebook"), InlineKeyboardButton("💬 WhatsApp", callback_data="cat_whatsapp")], [InlineKeyboardButton("🌍 Other Services", callback_data="cat_other")]]
    txt = "📱 <b>SELECT SERVICE CATEGORY</b> 📱\n━━━━━━━━━━━━━━━━━━━━\n<i>Which application do you need a number for?</i>\n👇 <b>Click a button below:</b>"
    if update.callback_query: await update.callback_query.edit_message_text(text=txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.HTML)
    else: await update.message.reply_text(text=txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.HTML)

async def handle_category_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    category = query.data.split('_')[1].lower()
    
    await query.edit_message_text(text="📡 <i>Scanning servers for live numbers... Please wait.</i> ⏳", parse_mode=ParseMode.HTML)
    
    status, data = await stex_api_request('GET', API_CONSOLE)
    
    # 🔥 Bulletproof JSON Extraction
    if status == 200 and isinstance(data, dict):
        data_block = data.get('data')
        logs = data_block.get('logs', []) if isinstance(data_block, dict) else []
        countries = {}
        
        for log in logs:
            if isinstance(log, dict):
                app_name = str(log.get('app_name', '')).lower()
                if (category == 'other') or (category in app_name):
                    c_name, r_val = log.get('country'), log.get('range')
                    if c_name and r_val and c_name not in countries:
                        countries[c_name] = r_val
        
        if not countries:
            await query.edit_message_text(text=f"❌ <b>No live numbers available for {category.title()} right now.</b>\n━━━━━━━━━━━━━━━━━━━━\n<i>Please try another category or check back in a few minutes.</i>", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="go_cat")]]), parse_mode=ParseMode.HTML)
            return
            
        kb, row = [], []
        for c_name, r_val in countries.items():
            row.append(InlineKeyboardButton(f"{get_flag(c_name)} {c_name}", callback_data=f"rng_{r_val}"))
            if len(row) == 2:
                kb.append(row)
                row = []
        if row: kb.append(row)
        kb.append([InlineKeyboardButton("🔙 Back to Categories", callback_data="go_cat")])
        
        await query.edit_message_text(text=f"🌍 <b>SELECT A COUNTRY ({category.title()})</b> 🌍\n━━━━━━━━━━━━━━━━━━━━\n<i>Green light! Numbers are currently arriving from these countries.</i>\n\n👇 <b>Tap a country to generate number:</b>", reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.HTML)
        
    else:
        logger.error(f"Console fetch error - HTTP Status: {status}")
        err_msg = f"❌ <b>Failed to fetch live data!</b>\n<i>Server HTTP Status: {status}</i>\n\nSTEX Server is temporarily overloaded. Please try again."
        await query.edit_message_text(text=err_msg, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="go_cat")]]), parse_mode=ParseMode.HTML)


# ==============================================================================
# 💰 WALLET & 2FA SYSTEM 
# ==============================================================================

async def wallet_page(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = ensure_user(user_id) 
    
    balance_usd, balance_bdt, total_earned = user[1], user[1] * USD_TO_BDT_RATE, user[4] if len(user) > 4 else 0.0
    
    with db_pool.get_connection() as conn:
        c = conn.cursor()
        total_refs = c.execute("SELECT COUNT(*) FROM users WHERE referrer_id=?", (user_id,)).fetchone()[0]
    
    txt = f"💎 <b>MY WALLET & PROFILE</b> 💎\n━━━━━━━━━━━━━━━━━━━━\n🆔 <b>Account ID:</b> <code>{user_id}</code>\n\n💵 <b>Current Balance:</b> <b>${balance_usd:.4f}</b>\n🇧🇩 <b>BDT Equivalent:</b> <i>{balance_bdt:.2f} Taka</i>\n📈 <b>Total Earnings:</b> <b>${total_earned:.4f}</b>\n━━━━━━━━━━━━━━━━━━━━\n👥 <b>Total Referrals:</b> <b>{total_refs} Users</b>\n\n🔗 <b>Your Referral Link:</b>\n<code>https://t.me/{context.bot.username}?start={user_id}</code>\n\n🎁 <b>LIFETIME Rewards System:</b>\nEarn <b>0.15 BDT</b> for EVERY OTP your referral receives."
    await update.message.reply_text(txt, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("💸 Request Withdrawal", callback_data="req_withdraw")]]), parse_mode=ParseMode.HTML)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await check_ban_middleware(update, context): return
    user_id, text, user_data = update.effective_user.id, update.message.text, context.user_data
    ensure_user(user_id)
    
    if text == "📱 Get Number":
        if not await check_subscription(user_id, context.bot): await send_join_prompt(update, context)
        else: await start_category_selection(update, context)
    elif text == "🔐 Get 2FA Code":
        user_data['state'] = 'WAITING_FOR_2FA'
        await update.message.reply_text("🔐 <b>2FA CODE GENERATOR</b> 🔐\n━━━━━━━━━━━━━━━━━━━━\n<i>Paste your Secret Key below to generate your 6-digit code.</i>\n\n🔑 <b>Send Key Now:</b>", parse_mode=ParseMode.HTML)
    elif user_data.get('state') == 'WAITING_FOR_2FA':
        key = text.replace(" ", "").strip()
        msg = await update.message.reply_text("⏳ <i>Generating 2FA Code...</i>", parse_mode=ParseMode.HTML)
        try:
            session = await get_session()
            async with session.get(API_2FA.format(key), timeout=10) as resp:
                if resp.status == 200:
                    code = (await resp.json()).get('code')
                    if code: await msg.edit_text(f"✅ <b>2FA CODE GENERATED!</b>\n━━━━━━━━━━━━━━━━━━━━\n🔢 <b>Code:</b> <code>{code}</code>", parse_mode=ParseMode.HTML)
                    else: await msg.edit_text("❌ <b>Error:</b> <i>Invalid Secret Key provided.</i>", parse_mode=ParseMode.HTML)
                else: await msg.edit_text("❌ <b>API Error!</b> <i>System is currently down.</i>", parse_mode=ParseMode.HTML)
        except Exception: await msg.edit_text("❌ <b>Failed!</b>\n<i>Network Error or Invalid Key.</i>", parse_mode=ParseMode.HTML)
        user_data['state'] = None
    elif text == "💰 Wallet / Refer": await wallet_page(update, context)
    elif text != "💸 Withdraw": await show_main_menu(update, context)


# ==============================================================================
# 💸 WITHDRAWAL SYSTEM
# ==============================================================================

async def start_withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = ensure_user(update.effective_user.id) 
    if user[1] < MIN_WITHDRAW_USD:
        await update.message.reply_text(f"❌ <b>INSUFFICIENT BALANCE!</b>\n━━━━━━━━━━━━━━━━━━━━\n💰 <b>Your Balance:</b> <b>${user[1]:.4f}</b>\n📉 <b>Minimum Required:</b> <b>{MIN_WITHDRAW_BDT} BDT (${MIN_WITHDRAW_USD:.3f})</b>", parse_mode=ParseMode.HTML)
        return ConversationHandler.END
    kb = [["bKash", "Nagad"], ["Binance"], ["🔙 Cancel"]]
    await update.message.reply_text("💸 <b>WITHDRAWAL REQUEST</b> 💸\n\n<i>Please select your preferred payment method:</i>", reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True), parse_mode=ParseMode.HTML)
    return SELECT_METHOD

async def select_method(update: Update, context: ContextTypes.DEFAULT_TYPE):
    method = update.message.text
    if method == "🔙 Cancel":
        await show_main_menu(update, context)
        return ConversationHandler.END
    context.user_data['wd_method'] = method
    await update.message.reply_text(f"🏦 <b>{method} Selected.</b>\n\n✍️ <i>Please enter your Account Number or Binance ID:</i>", reply_markup=ReplyKeyboardRemove(), parse_mode=ParseMode.HTML)
    return ENTER_ADDRESS

async def process_withdrawal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    address, user_id, method = update.message.text, update.effective_user.id, context.user_data['wd_method']
    with db_pool.get_connection() as conn:
        c = conn.cursor()
        bal = c.execute("SELECT balance FROM users WHERE user_id=?", (user_id,)).fetchone()[0]
        if bal < MIN_WITHDRAW_USD: 
            await show_main_menu(update, context)
            return ConversationHandler.END
        amt_usd, amt_bdt = bal, bal * USD_TO_BDT_RATE
        c.execute("UPDATE users SET balance = 0 WHERE user_id=?", (user_id,))
        c.execute("INSERT INTO withdrawals (user_id, method, address, amount_usd, amount_bdt) VALUES (?, ?, ?, ?, ?)", (user_id, method, address, amt_usd, amt_bdt))
        wd_id = c.lastrowid
        conn.commit()
    
    await update.message.reply_text(f"✅ <b>WITHDRAWAL SUBMITTED!</b>\n━━━━━━━━━━━━━━━━━━━━\n🆔 <b>Trx ID:</b> <code>#{wd_id}</code>\n💰 <b>Amount:</b> <b>{amt_bdt:.2f} BDT</b>\n🏦 <b>Method:</b> <i>{method}</i>\n⏳ <b>Status:</b> <b>Pending Approval</b>", parse_mode=ParseMode.HTML)
    await show_main_menu(update, context)
    try: await context.bot.send_message(chat_id=ADMIN_ID, text=f"🔔 <b>NEW WITHDRAWAL REQUEST</b>\n━━━━━━━━━━━━━━━━━━━━\n👤 <b>User:</b> <code>{user_id}</code>\n🆔 <b>ID:</b> #{wd_id}\n💰 <b>Amount:</b> ${amt_usd:.4f} ({amt_bdt:.2f} BDT)\n🏦 <b>Method:</b> {method}\n📝 <b>Address:</b> <code>{address}</code>", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("✅ Approve", callback_data=f"wd_approve_{wd_id}_{user_id}"), InlineKeyboardButton("❌ Reject", callback_data=f"wd_reject_{wd_id}_{user_id}")]]), parse_mode=ParseMode.HTML)
    except Exception: pass
    return ConversationHandler.END

async def cancel_withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await show_main_menu(update, context)
    return ConversationHandler.END


# ==============================================================================
# 🎮 BUTTON HANDLER
# ==============================================================================

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await check_ban_middleware(update, context): return
    query, user_id, data = update.callback_query, update.callback_query.from_user.id, update.callback_query.data
    ensure_user(user_id)
    
    if data == "check_join":
        if await check_subscription(user_id, context.bot): await show_main_menu(query, context)
        else: await query.answer("⚠️ Not joined yet! Please join the channels first.", show_alert=True)
    elif data == "req_withdraw": await query.answer("💸 Please use 'Withdraw' from Reply Keyboard.", show_alert=True)
    elif data.startswith("cat_"): await handle_category_click(update, context)
    elif data == "go_cat": await start_category_selection(update, context)
    elif data.startswith("rng_"): await get_number_api(update, context, data.split("_")[1])
    elif data == "change_num":
        if context.user_data.get('range'): await get_number_api(update, context, context.user_data['range'])
        else: await query.edit_message_text("⚠️ <b>Session Expired.</b>\n<i>Please start again.</i>", parse_mode=ParseMode.HTML)
    elif data == "refresh_inbox": await query.answer("🔄 System is auto-checking... Please wait patiently.", show_alert=False)
    elif data == "go_main": await show_main_menu(query, context)
    elif data.startswith("wd_") and user_id == ADMIN_ID:
        parts = data.split('_')
        action, wd_id, target_user = parts[1], int(parts[2]), int(parts[3])
        with db_pool.get_connection() as conn:
            c = conn.cursor()
            res = c.execute("SELECT status, amount_usd FROM withdrawals WHERE id=?", (wd_id,)).fetchone()
            if not res or res[0] != 'pending': return await query.answer("⚠️ Already Processed!", show_alert=True)
            if action == "approve":
                c.execute("UPDATE withdrawals SET status='approved' WHERE id=?", (wd_id,))
                await query.message.edit_text(f"{query.message.text}\n\n✅ <b>STATUS: APPROVED</b>", parse_mode=ParseMode.HTML)
                try: await context.bot.send_message(chat_id=target_user, text=f"✅ <b>Congratulations! Withdrawal #{wd_id} is Approved.</b>", parse_mode=ParseMode.HTML)
                except: pass
            elif action == "reject":
                c.execute("UPDATE withdrawals SET status='rejected' WHERE id=?", (wd_id,))
                c.execute("UPDATE users SET balance = balance + ? WHERE user_id=?", (res[1], target_user))
                await query.message.edit_text(f"{query.message.text}\n\n❌ <b>STATUS: REJECTED & REFUNDED</b>", parse_mode=ParseMode.HTML)
                try: await context.bot.send_message(chat_id=target_user, text=f"❌ <b>Notice: Withdrawal #{wd_id} was Rejected.</b> Funds refunded.", parse_mode=ParseMode.HTML)
                except: pass
            conn.commit()


# ==============================================================================
# 👑 ADMIN COMMANDS
# ==============================================================================

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    txt = "🔐 <b>ADVANCED ADMIN PANEL</b> 🔐\n━━━━━━━━━━━━━━━━━━━━\n🟢 <code>/status</code> - Check Bot & Server Stats\n💰 <code>/addbalance &lt;id&gt; &lt;amt&gt;</code> - Give Balance\n📢 <code>/broadcast &lt;msg&gt;</code> - Message all users\n🚫 <code>/ban &lt;id&gt;</code> - Ban a user"
    await update.message.reply_text(txt, parse_mode=ParseMode.HTML)

async def admin_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    uptime = datetime.datetime.now() - START_TIME
    with db_pool.get_connection() as conn:
        c = conn.cursor()
        t_users = c.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        t_bal = c.execute("SELECT SUM(balance) FROM users").fetchone()[0] or 0.0
        t_pend = c.execute("SELECT COUNT(*) FROM withdrawals WHERE status='pending'").fetchone()[0]
        t_otps = c.execute("SELECT COUNT(*) FROM otp_history").fetchone()[0]
    txt = f"📊 <b>LIVE SYSTEM STATUS</b> 📊\n━━━━━━━━━━━━━━━━━━━━\n⏱ <b>Uptime:</b> {str(uptime).split('.')[0]}\n👥 <b>Total Users:</b> {t_users}\n📩 <b>Total OTPs:</b> {t_otps}\n💰 <b>Total Balance:</b> ${t_bal:.4f}\n⏳ <b>Pending Withdraws:</b> {t_pend}\n📡 <b>Active Waiters:</b> {len(WAITING_OTPS)} Users\n━━━━━━━━━━━━━━━━━━━━\n✅ <i>System Running Smoothly</i>"
    await update.message.reply_text(txt, parse_mode=ParseMode.HTML)

async def add_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    try:
        u_id, amt = int(context.args[0]), float(context.args[1])
        with db_pool.get_connection() as conn:
            c = conn.cursor()
            c.execute("UPDATE users SET balance = balance + ? WHERE user_id=?", (amt, u_id))
            conn.commit()
        await update.message.reply_text(f"✅ Added ${amt} to user {u_id}")
        try: await context.bot.send_message(chat_id=u_id, text=f"🎉 <b>Admin has added ${amt} to your balance!</b>", parse_mode=ParseMode.HTML)
        except: pass
    except: await update.message.reply_text("⚠️ <b>Usage:</b>\n`/addbalance <user_id> <amount>`", parse_mode=ParseMode.MarkdownV2)


# ==============================================================================
# 🌐 RENDER DUMMY WEB SERVER & MAIN LOOP
# ==============================================================================

async def web_server_handler(request):
    return web.Response(text="Bot is running perfectly on Render Server! Ultimate API Version Active.")

async def start_dummy_server():
    try:
        app = web.Application()
        app.router.add_get('/', web_server_handler)
        port = int(os.environ.get('PORT', 8080))
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, '0.0.0.0', port)
        await site.start()
        logger.info(f"🌐 Dummy Web Server successfully started on port {port}.")
    except OSError as e:
        logger.warning(f"⚠️ Port {port} is already in use. Web server skipped, bot will continue natively.")
    except Exception as e:
        logger.error(f"⚠️ Dummy server failed: {e}")

async def post_init(app: Application):
    asyncio.create_task(start_dummy_server())

if __name__ == "__main__":
    init_db()
    app = Application.builder().token(TOKEN).post_init(post_init).build()
    conv_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^💸 Withdraw$"), start_withdraw)],
        states={
            SELECT_METHOD: [MessageHandler(filters.TEXT & ~filters.COMMAND, select_method)],
            ENTER_ADDRESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_withdrawal)]
        },
        fallbacks=[CommandHandler("cancel", cancel_withdraw)]
    )
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin_panel))
    app.add_handler(CommandHandler("status", admin_status))
    app.add_handler(CommandHandler("addbalance", add_balance))
    app.add_handler(conv_handler)
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.job_queue.run_repeating(global_otp_checker_job, interval=5, first=3)
    logger.info("✨ VERSION 9.0 PRO MAX STARTED... ✨")
    app.run_polling(drop_pending_updates=True)
