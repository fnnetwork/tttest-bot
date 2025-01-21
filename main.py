import os
import json
from flask import Flask, request
import requests
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, MessageHandler, CallbackContext
from telegram.ext.filters import TEXT
from telegram.ext import Application

# Bot Token
BOT_TOKEN = "7447128452:AAG8JiAD58SdFPglxbxT7_Z0EV3otNumIl8"
WEBHOOK_URL = f"https://electra-downloaders.herokuapp.com/{BOT_TOKEN}"


# Initialize the bot
application = Application.builder().token(BOT_TOKEN).build()

# Flask App
app = Flask(__name__)

# Create session directory
SESSION_FOLDER = "session/"
os.makedirs(SESSION_FOLDER, exist_ok=True)

# Helper functions
def send_typing_action(chat_id):
    """Send typing action to the user."""
    requests.post(f"{API_URL}sendChatAction", json={"chat_id": chat_id, "action": "typing"})

def send_message(chat_id, text, reply_markup=None):
    """Send a text message to the user."""
    data = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
    }
    if reply_markup:
        data["reply_markup"] = json.dumps(reply_markup)
    requests.post(f"{API_URL}sendMessage", json=data)

def send_audio(chat_id, audio_url, caption):
    """Send audio to the user."""
    send_typing_action(chat_id)
    data = {
        "chat_id": chat_id,
        "audio": audio_url,
        "caption": caption,
        "parse_mode": "Markdown",
    }
    requests.post(f"{API_URL}sendAudio", json=data)

def fetch_song_data(query):
    """Fetch song data from the Spotify API."""
    url = f"https://teleserviceapi.vercel.app/spotify?q={query}"
    response = requests.get(url)
    return response.json()

def download_song(spotify_url):
    """Fetch the download link for a song."""
    url = f"https://teleservicesapi.vercel.app/spotify?spotify_url={spotify_url}"
    response = requests.get(url)
    return response.json().get("download_link")

def save_session(chat_id, session_data):
    """Save session data to a JSON file."""
    with open(os.path.join(SESSION_FOLDER, f"session_{chat_id}.json"), "w") as f:
        json.dump(session_data, f)

def load_session(chat_id):
    """Load session data from a JSON file."""
    session_file = os.path.join(SESSION_FOLDER, f"session_{chat_id}.json")
    if os.path.exists(session_file):
        with open(session_file, "r") as f:
            return json.load(f)
    return None

# Telegram Bot Handlers
def start(update: Update, context: CallbackContext):
    """Handle the /start command."""
    chat_id = update.message.chat_id
    send_typing_action(chat_id)

    welcome_message = (
        "👑 <b>Welcome, Your Highness!</b> 👑\n\n"
        "🎶 I'm your assistant for all things music! 🎧\n\n"
        "🔥 <b>Search Songs:</b> Just type the name of a song, and I'll find it for you.\n"
        "🎵 <b>High-Quality Downloads:</b> Get your favorite tracks in the best audio quality.\n\n"
        "📢 <b>Stay Updated:</b> Join our <a href='https://t.me/fn_network_back'>Updates Channel</a>.\n"
        "💡 <b>Pro Tip:</b> Add me to your groups for shared music fun!\n\n"
        "🎉 <i>Let's get started!</i> 🎤"
    )

    keyboard = [[InlineKeyboardButton("📢 Updates Channel", url="https://t.me/fn_network_back")]]
    reply_markup = {"inline_keyboard": keyboard}

    send_message(chat_id, welcome_message, reply_markup)

def handle_message(update: Update, context: CallbackContext):
    """Handle user text messages."""
    chat_id = update.message.chat_id
    text = update.message.text

    send_typing_action(chat_id)
    song_data = fetch_song_data(text)

    if song_data and "tracks" in song_data and song_data["tracks"]:
        send_initial_song_details(chat_id, song_data, 0)
    else:
        send_message(chat_id, "Sorry, I couldn't find any song with that name.")

def send_initial_song_details(chat_id, song_data, track_index):
    """Send the first track's details."""
    total_tracks = len(song_data["tracks"])
    track = song_data["tracks"][track_index]

    track_name = track["trackName"]
    artist = track["artist"]
    album = track["album"]
    spotify_url = track["spotifyUrl"]
    image_url = track["image"]

    # Create navigation buttons
    keyboard = []
    if track_index > 0:
        keyboard.append([InlineKeyboardButton("⬅️ Back", callback_data="prev")])
    if track_index < total_tracks - 1:
        keyboard.append([InlineKeyboardButton("Next ➡️", callback_data="next")])
    keyboard.append([InlineKeyboardButton("Download", callback_data=f"/dwn {spotify_url}")])

    message = (
        f"🎼 Name: {track_name}\n"
        f"👨‍🎨 Artist: {artist}\n"
        f"✨ Album: {album} <a href='{image_url}'>ㅤ</a>"
    )

    reply_markup = {"inline_keyboard": keyboard}
    send_message(chat_id, message, reply_markup)
    save_session(chat_id, {"query": song_data, "track_index": track_index})

def callback_handler(update: Update, context: CallbackContext):
    """Handle button clicks."""
    query = update.callback_query
    chat_id = query.message.chat_id
    message_id = query.message.message_id
    callback_data = query.data

    session_data = load_session(chat_id)
    if not session_data:
        send_message(chat_id, "Please search for a song first.")
        return

    track_index = session_data["track_index"]
    song_data = session_data["query"]

    if callback_data == "next" and track_index < len(song_data["tracks"]) - 1:
        send_initial_song_details(chat_id, song_data, track_index + 1)
    elif callback_data == "prev" and track_index > 0:
        send_initial_song_details(chat_id, song_data, track_index - 1)
    elif callback_data.startswith("/dwn"):
        spotify_url = callback_data.replace("/dwn ", "")
        download_link = download_song(spotify_url)
        if download_link:
            caption = "*🎶 Music downloaded by your bot 🎵*\n\n_Enjoy your Beats 🎧_"
            send_audio(chat_id, download_link, caption)
        else:
            send_message(chat_id, "Sorry, I couldn't fetch the download link.")

# Start the bot
@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def webhook():
    """Webhook to receive updates."""
    update = Update.de_json(request.get_json(), Bot(BOT_TOKEN))
    dispatcher.process_update(update)
    return "OK"

if __name__ == "__main__":
    application.run_polling()
    application = Application.builder().token(BOT_TOKEN).build()
    dispatcher = application

    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(MessageHandler(TEXT, handle_message))
    dispatcher.add_handler(CallbackQueryHandler(callback_handler))

    # Bind to Heroku's PORT
    port = int(os.environ.get("PORT", 5000))
    # Set webhook
    application.run_webhook(
        listen="0.0.0.0",
        port=port,
        url_path=BOT_TOKEN,
        webhook_url=WEBHOOK_URL
