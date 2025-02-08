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
    "Superb! 🌻",
]

REACTIONS_TO_TRACK = ["yellow_heart"]
INDICATOR = "^^"
DB_NAME = os.environ.get("DB_NAME", "kowalski.db")
BACKDOOR_USERS = os.environ.get("BACKDOOR_USERS", "").split(",")
DB_DUMP_URL = os.environ.get("DB_DUMP_URL", "")

logger = logging.getLogger(__name__)
# Initialize SQLite database
conn = sqlite3.connect(DB_NAME, check_same_thread=False)
cursor = conn.cursor()

# Create table if it doesn't exist
cursor.execute(
    """
    CREATE TABLE IF NOT EXISTS message_counts (
        user_id TEXT PRIMARY KEY,
        message_count INTEGER
    )
"""
)
cursor.execute(
    """
    CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sender_user_id TEXT,
        sender_user TEXT,
        receiver_user_id TEXT,
        receiver_user TEXT,
        message TEXT
    )
"""
)
conn.commit()

# Initialize Slack app
app = App(token=os.environ.get("SLACK_BOT_TOKEN"))
client = WebClient(token=os.environ["SLACK_BOT_TOKEN"])


def get_username(user_id):
    try:
        response = client.users_info(user=user_id)
        if response.get("ok"):
            username = response.get("user", {}).get("name")
            display_name = (
                response.get("user", {}).get("profile", {}).get("display_name")
            )
            if not display_name:
                display_name = (
                    response.get("user", {}).get("profile", {}).get("real_name")
                )
            return username, display_name
    except SlackApiError as e:
        print(f"Error fetching user info: {e.response.get('error')}")
    return None, None


def update_message_count(user_id):
    """Increment the message count for the user in SQLite."""
    cursor.execute(
        "SELECT message_count FROM message_counts WHERE user_id = ?", (user_id,)
    )
    result = cursor.fetchone()

    if result:
        # User exists, update their message count
        new_count = result[0] + 1
        cursor.execute(
            "UPDATE message_counts SET message_count = ? WHERE user_id = ?",
            (new_count, user_id),
        )
    else:
        # User doesn't exist, insert a new entry with a count of 1
        new_count = 1
        cursor.execute(
            "INSERT INTO message_counts (user_id, message_count) VALUES (?, ?)",
            (user_id, new_count),
        )

    conn.commit()
    return new_count


def record_message(sender_id, receiver_id, message):
    sender, display_name = get_username(sender_id)
    receiver, display_name = get_username(receiver_id)
    cursor.execute(
        "INSERT INTO messages (sender_user_id, sender_user, receiver_user_id, receiver_user, message) VALUES (?, ?, ?, ?, ?)",
        (sender_id, sender, receiver_id, receiver, message),
    )
    conn.commit()


def get_all_counts():
    """Fetch all user message counts from SQLite and format them as a string."""
    cursor.execute(
        "SELECT user_id, message_count FROM message_counts order by message_count desc"
    )
    rows = cursor.fetchall()

    if not rows:
        return "No message counts recorded yet."

    response = "*The Loved:*\n"
    for user_id, count in rows:
        user, display = get_username(user_id)
        response += f"- {display} has ${count}\n"

    return response


def get_response(display_name, user_count) -> str:
    random_congrats = random.choice(CONGRATS)
    return f"{display_name} has 💞{user_count}💕 -- {random_congrats}"


@app.event("message")
def handle_message_events(event, say):
    sender_id = event.get("user")
    text = event.get("text")

    message = None
    mentioned_users = []

    if not text:
        print("No message .. probs a delete or an image")
        return

    if text.lower() == "how loved are we?":
        response = get_all_counts()
        say(response)
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
            # if sender_is_receiver:
            #    say(f"Nice try {display_name} ... ")
            #    break

            username = get_username(user_id)
            user_count = update_message_count(user_id)

            if message and not sender_is_receiver:
                record_message(sender_id, user_id, message)
            random_congrats = random.choice(CONGRATS)
            say(get_response(display_name, user_count))


@app.event("app_mention")
def handle_message_events(event, say):
    sender_id = event.get("user")
    text = event.get("text")

    username, display = get_username(sender_id)
    if "dump database" in text and DB_DUMP_URL:
        say(f"Sure thing {display}! You can download my DB from {DB_DUMP_URL}")
        return

    say("Sorry, I didn't understand that!")


@app.event("reaction_added")
def handle_reaction_added(event, say):
    """Handle the reaction_added event to update message counts based on specific reactions."""
    receiver_id = event.get("item_user")
    sender_id = event.get("user")
    reaction_name = event.get("reaction")

    if receiver_id and sender_id:
        # Ensure the bot doesn't count its own reactions
        if receiver_id != sender_id:
            # Only update counts for certain reactions
            username, display_name = get_username(receiver_id)
            print(reaction_name, " - ", display_name)
            if reaction_name in REACTIONS_TO_TRACK:
                user_count = update_message_count(receiver_id)
                say(get_response(display_name, user_count))


# Start the bot
if __name__ == "__main__":
    handler = SocketModeHandler(app, os.environ.get("SLACK_APP_TOKEN"))
    handler.start()
