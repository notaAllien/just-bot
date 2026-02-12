import requests
import time
import json
import os
from datetime import datetime

# ===== CONFIGURATION - CHANGE THESE =====
# For Railway: Set TELEGRAM_BOT_TOKEN as environment variable
# For local testing: Replace the default value with your token
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
API_URL = "https://app.yoso.fun/api/markets/0xd1bc6d6736488bcad0c9ce78764f9c52a12a28f9"
BTC_API_URL = "https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT"
CHECK_INTERVAL = 60  # Check every 60 seconds (1 minute)

# Price thresholds
YES_THRESHOLD = 0.50
BTC_THRESHOLD = 95000  # Set your desired BTC threshold in USD

# File to store user chat IDs
USERS_FILE = "users.json"

# Track if we already notified
already_notified_yes = False
already_notified_btc = False


def load_users():
    """Load user chat IDs from file"""
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'r') as f:
            return json.load(f)
    return []


def save_users(users):
    """Save user chat IDs to file"""
    with open(USERS_FILE, 'w') as f:
        json.dump(users, f)


def add_user(chat_id):
    """Add a new user to the list"""
    users = load_users()
    if chat_id not in users:
        users.append(chat_id)
        save_users(users)
        print(f"✅ New user added: {chat_id}")
        return True
    return False


def send_telegram_message(chat_id, message):
    """Send a message to a specific chat"""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML"
    }
    try:
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            return True
        else:
            print(f"❌ Failed to send to {chat_id}: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Error sending message to {chat_id}: {e}")
        return False


def broadcast_message(message):
    """Send message to all users"""
    users = load_users()
    success_count = 0
    
    for chat_id in users:
        if send_telegram_message(chat_id, message):
            success_count += 1
        time.sleep(0.1)  # Small delay to avoid rate limits
    
    print(f"📤 Broadcast sent to {success_count}/{len(users)} users")
    return success_count


def check_for_new_users():
    """Check for new messages and add users who started the bot"""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates"
    
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            
            if data.get('ok') and data.get('result'):
                for update in data['result']:
                    if 'message' in update:
                        chat_id = update['message']['chat']['id']
                        text = update['message'].get('text', '')
                        
                        # Handle /check command
                        if text.strip().lower() == '/check':
                            yes_price = fetch_yes_price()
                            btc_price = fetch_btc_price()
                            
                            if yes_price is not None and btc_price is not None:
                                send_telegram_message(
                                    chat_id,
                                    f"✅ <b>Bot is Active!</b>\n\n"
                                    f"📊 Current Prices:\n"
                                    f"• YES: <b>{yes_price:.4f}</b> (Alert at ≤ {YES_THRESHOLD})\n"
                                    f"• BTC: <b>${btc_price:,.2f}</b> (Alert at ≤ ${BTC_THRESHOLD:,})\n\n"
                                    f"🟢 Monitoring active"
                                )
                            else:
                                send_telegram_message(
                                    chat_id,
                                    f"✅ <b>Bot is Active!</b>\n\n"
                                    f"⚠️ Unable to fetch current prices\n"
                                    f"🟢 Monitoring active"
                                )
                        # If user sent /start or any other message, add them
                        elif add_user(chat_id):
                            send_telegram_message(
                                chat_id,
                                f"👋 <b>Welcome to Price Monitor Bot!</b>\n\n"
                                f"📊 Monitoring:\n"
                                f"• YES price: ≤ {YES_THRESHOLD}\n"
                                f"• BTC price: ≤ ${BTC_THRESHOLD:,}\n\n"
                                f"💡 Commands:\n"
                                f"• /check - Check if bot is active\n\n"
                                f"👥 Current subscribers: {len(load_users())}"
                            )
                
                # Mark updates as read by getting offset
                if data['result']:
                    last_update_id = data['result'][-1]['update_id']
                    requests.get(f"{url}?offset={last_update_id + 1}")
    
    except Exception as e:
        print(f"❌ Error checking for new users: {e}")


def fetch_yes_price():
    """Fetch YES price from the API"""
    try:
        response = requests.get(API_URL, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            yes_price = float(data.get('yesPrice', 0))
            return yes_price
        else:
            print(f"❌ YES API Error: Status {response.status_code}")
            return None
            
    except Exception as e:
        print(f"❌ Error fetching YES price: {e}")
        return None


def fetch_btc_price():
    """Fetch BTC price from Binance API"""
    try:
        response = requests.get(BTC_API_URL, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            btc_price = float(data['price'])
            return btc_price
        else:
            print(f"❌ BTC API Error: Status {response.status_code}")
            return None
            
    except Exception as e:
        print(f"❌ Error fetching BTC price: {e}")
        return None


def main():
    """Main bot loop"""
    global already_notified_yes, already_notified_btc
    
    print("🤖 Price Monitor Bot Started!")
    print(f"📊 YES Threshold: ≤ {YES_THRESHOLD}")
    print(f"💰 BTC Threshold: ≤ ${BTC_THRESHOLD:,}")
    print(f"⏱️  Checking every {CHECK_INTERVAL} seconds")
    print(f"💡 Use /check command to verify bot status")
    print(f"👥 Current subscribers: {len(load_users())}\n")
    
    # Counter for checking new users (check every 10 seconds)
    user_check_counter = 0
    
    while True:
        try:
            # Check for new users every 10 seconds
            if user_check_counter % 10 == 0:
                check_for_new_users()
            
            # Fetch prices every minute
            if user_check_counter % CHECK_INTERVAL == 0:
                yes_price = fetch_yes_price()
                btc_price = fetch_btc_price()
                
                if yes_price is not None and btc_price is not None:
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] YES: {yes_price:.4f} | BTC: ${btc_price:,.2f} | Users: {len(load_users())}")
                    
                    # Check YES price threshold
                    if yes_price <= YES_THRESHOLD and not already_notified_yes:
                        broadcast_message(
                            f"🚨 <b>YES PRICE ALERT!</b>\n\n"
                            f"💰 Current Price: <b>{yes_price:.4f}</b>\n"
                            f"🎯 Hit threshold: ≤ {YES_THRESHOLD}\n"
                            f"⏰ Time: {datetime.now().strftime('%I:%M:%S %p')}"
                        )
                        already_notified_yes = True
                        print(f"🚨 ALERT! YES price is {yes_price:.4f}")
                    
                    # Reset YES notification if price goes back above threshold
                    elif yes_price > YES_THRESHOLD and already_notified_yes:
                        already_notified_yes = False
                        print(f"✅ Reset - YES price back above {YES_THRESHOLD}")
                    
                    # Check BTC price threshold
                    if btc_price <= BTC_THRESHOLD and not already_notified_btc:
                        broadcast_message(
                            f"🚨 <b>BTC PRICE ALERT!</b>\n\n"
                            f"💰 Current Price: <b>${btc_price:,.2f}</b>\n"
                            f"🎯 Hit threshold: ≤ ${BTC_THRESHOLD:,}\n"
                            f"⏰ Time: {datetime.now().strftime('%I:%M:%S %p')}"
                        )
                        already_notified_btc = True
                        print(f"🚨 ALERT! BTC price is ${btc_price:,.2f}")
                    
                    # Reset BTC notification if price goes back above threshold
                    elif btc_price > BTC_THRESHOLD and already_notified_btc:
                        already_notified_btc = False
                        print(f"✅ Reset - BTC price back above ${BTC_THRESHOLD:,}")
            
            # Wait 1 second and increment counter
            time.sleep(1)
            user_check_counter += 1
            
        except KeyboardInterrupt:
            print("\n\n🛑 Bot stopped by user")
            broadcast_message("🛑 <b>Bot Stopped</b>\n\nThe price monitoring service has been stopped.")
            break
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            time.sleep(10)


if __name__ == "__main__":
    main()
