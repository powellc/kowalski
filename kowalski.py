# /// script
# dependencies = [
#   "slack_bolt",
# ]
# ///
#
import os
import re
import logging
import random
import sqlite3
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

CONGRATS = [
    "Congratulations! 🎉",
    "Well done! 👏",
    "Awesome job! 💪",
    "Kudos to you! 🌟",
    "Hats off! 🎩",
    "Way to go! 🚀",
    "You did it! 🎯",
    "Great work! 🔥",
    "Keep it up! ✨",
    "Fantastic! 🎊",
    "Brilliant! 🌈",
    "Amazing! 🌟",
    "Impressive! 💥",
    "Outstanding! 🏆",
    "You nailed it! 🔨",
    "Cheers to your success! 🥂",
    "Excellent! 🌟",
    "What a win! 🏅",
    "Legendary! 🌠",
    "Superb! 🌻"
]

INDICATOR = "$$"
DB_NAME = os.environ.get("DB_NAME", "kowalski.db")
BACKDOOR_USERS = os.environ.get("BACKDOOR_USERS", "").split(",")

logger = logging.getLogger(__name__)
# Initialize SQLite database
conn = sqlite3.connect(DB_NAME, check_same_thread=False)
cursor = conn.cursor()

# Create table if it doesn't exist
cursor.execute('''
    CREATE TABLE IF NOT EXISTS message_counts (
        user_id TEXT PRIMARY KEY,
        message_count INTEGER
    )
''') 
cursor.execute('''
    CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sender_user_id TEXT,
        sender_user TEXT,
        receiver_user_id TEXT,
        receiver_user TEXT,
        message TEXT
    )
''')
conn.commit()

# Initialize Slack app
app = App(token=os.environ.get("SLACK_BOT_TOKEN"))
client = WebClient(token=os.environ["SLACK_BOT_TOKEN"])

def get_username(user_id):
    try:
        response = client.users_info(user=user_id)
        if response.get("ok"):
            username = response.get("user", {}).get("name")
            display_name = response.get("user", {}).get("profile", {}).get("display_name")
            if not display_name:
                display_name = response.get("user", {}).get("profile", {}).get("real_name")
            return username, display_name
    except SlackApiError as e:
        print(f"Error fetching user info: {e.response.get('error')}")
    return None, None

def update_message_count(user_id):
    """Increment the message count for the user in SQLite."""
    cursor.execute("SELECT message_count FROM message_counts WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()

    if result:
        # User exists, update their message count
        new_count = result[0] + 1
        cursor.execute("UPDATE message_counts SET message_count = ? WHERE user_id = ?", (new_count, user_id))
    else:
        # User doesn't exist, insert a new entry with a count of 1
        new_count = 1
        cursor.execute("INSERT INTO message_counts (user_id, message_count) VALUES (?, ?)", (user_id, new_count))

    conn.commit()
    return new_count

def record_message(sender_id, receiver_id, message):
    sender, display_name = get_username(sender_id)
    receiver, display_name = get_username(receiver_id)
    cursor.execute("INSERT INTO messages (sender_user_id, sender_user, receiver_user_id, receiver_user, message) VALUES (?, ?, ?, ?, ?)", (sender_id, sender, receiver_id, receiver, message))
    conn.commit()


@app.event("message")
def handle_message_events(event, say):
    sender_id = event.get("user")
    text = event.get("text")

    message = None
    mentioned_users = []

    if not text:
        print("No message .. probs a delete")
        return

    indicator_found = len(text.split(INDICATOR)) > 1
    try:
        mentioned_users = re.findall(r"<@(\w+)>", text)
        message = text.split(INDICATOR)[1]
    except IndexError:
        print(f"No user or text found for message: {text}")

    if not indicator_found:
        print("Indicator not found, ignoring")
        return

    if indicator_found:
        for user_id in mentioned_users:
            username, display_name = get_username(user_id)
            sender_is_receiver = sender_id == user_id and not username in BACKDOOR_USERS
            if sender_is_receiver:
                say(f"Nice try {display_name} ... ")
                break

            username = get_username(user_id)
            user_count = update_message_count(user_id)

            if message and not sender_is_receiver:
                record_message(sender_id, user_id, message)
            random_congrats = random.choice(CONGRATS)
            say(f"{display_name} has ${user_count}, {random_congrats}")

# Start the bot
if __name__ == "__main__":
    handler = SocketModeHandler(app, os.environ.get("SLACK_APP_TOKEN"))
    handler.start()
