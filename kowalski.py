# /// script
# dependencies = [
#   "slack_bolt",
# ]
# ///
#
import os
import sqlite3
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

# Initialize SQLite database
conn = sqlite3.connect("message_counts.db")
cursor = conn.cursor()

# Create table if it doesn't exist
cursor.execute('''
    CREATE TABLE IF NOT EXISTS message_counts (
        user_id TEXT PRIMARY KEY,
        message_count INTEGER
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

@app.event("message")
def handle_message_events(event, say):
    user = event.get("user")
    text = event.get("text")

    first_token = text.split(" ")[0]
    second_token = text.split(" ")[1]
    if "@" in first_token and second_token == INDICATOR:
        user_count = update_message_count(user, text)
        say(f"{user} has {user_count} kk's!")

# Start the bot
if __name__ == "__main__":
    handler = SocketModeHandler(app, os.environ.get("SLACK_APP_TOKEN"))
    handler.start()
