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
CHECK_INTERVAL = 60  # Check every 60 seconds (1 minute)

# Price threshold
THRESHOLD = 0.40

# File to store user chat IDs
USERS_FILE = "users.json"

# Track if we already notified
already_notified = False


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
                        
                        # If user sent /start or any message
                        if add_user(chat_id):
                            send_telegram_message(
                                chat_id,
                                f"👋 <b>Welcome!</b>\n\n"
                                f"You will receive alerts when YES price hits ≤ {THRESHOLD}\n\n"
                                f"Current subscribers: {len(load_users())}"
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
            print(f"❌ API Error: Status {response.status_code}")
            return None
            
    except Exception as e:
        print(f"❌ Error fetching data: {e}")
        return None


def main():
    """Main bot loop"""
    global already_notified
    
    print("🤖 YES Price Monitor Bot Started!")
    print(f"📊 Watching for YES price <= {THRESHOLD}")
    print(f"⏱️  Checking every {CHECK_INTERVAL} seconds")
    print(f"👥 Current subscribers: {len(load_users())}\n")
    
    # Counter for checking new users (check every 10 seconds)
    user_check_counter = 0
    
    while True:
        try:
            # Check for new users every 10 seconds
            if user_check_counter % 10 == 0:
                check_for_new_users()
            
            # Fetch current YES price every minute
            if user_check_counter % CHECK_INTERVAL == 0:
                yes_price = fetch_yes_price()
                
                if yes_price is not None:
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] YES Price: {yes_price:.4f} | Users: {len(load_users())}")
                    
                    # Check if price is at or below threshold
                    if yes_price <= THRESHOLD and not already_notified:
                        # Broadcast to all users
                        broadcast_message(
                            f"🚨 <b>YES PRICE ALERT!</b>\n\n"
                            f"💰 Current Price: <b>{yes_price:.4f}</b>\n"
                            f"🎯 Hit threshold: ≤ {THRESHOLD}\n"
                            f"⏰ Time: {datetime.now().strftime('%I:%M:%S %p')}"
                        )
                        already_notified = True
                        print(f"🚨 ALERT BROADCAST! YES price is {yes_price:.4f}")
                    
                    # Reset notification if price goes back above threshold
                    elif yes_price > THRESHOLD and already_notified:
                        already_notified = False
                        print(f"✅ Reset - price back above {THRESHOLD}")
            
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
