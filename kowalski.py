# /// script
# dependencies = [
#   "slack_bolt",
# ]
# ///
#
import os
import re
import logging
import sqlite3
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler


INDICATOR = "$$"

logger = logging.getLogger(__name__)
# Initialize SQLite database
conn = sqlite3.connect("message_counts.db", check_same_thread=False)
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
        sender_user_id TEXT PRIMARY KEY,
        receiver_user_id TEXT,
        message TEXT
    )
''')
conn.commit()

# Initialize Slack app
app = App(token=os.environ.get("SLACK_BOT_TOKEN"))

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
    cursor.execute("INSERT INTO messages (sender_user_id, receiver_user_id, message) VALUES (?, ?)", (sender_id, receiver_id, message))
    conn.commit()


@app.event("message")
def handle_message_events(event, say):
    sender_id = event.get("user")
    text = event.get("text")

    message = None
    mentioned_users = []

    if not text:
        log.info(f"No text? WTF? {text}")
        return

    indicator_found = len(text.split(INDICATOR)) > 1
    try:
        mentioned_users = re.findall(r"<@(\w+)>", text)
        message = text.split(INDICATOR)[1]
    except IndexError:
        log.info("No user or text found for message: {text}")

    if not indicator_found:
        log.info("Indicator not found, ignoring")
        return

    if indicator_found:
        user_updates = {}
        for user_id in mentioned_users:
            counts_per_user[user_id] = update_message_count(user_id)
            if message:
                record_message(sender_id, user_id, message)
            say(f"{user_id} has {user_count} kk's!")

# Start the bot
if __name__ == "__main__":
    handler = SocketModeHandler(app, os.environ.get("SLACK_APP_TOKEN"))
    handler.start()
