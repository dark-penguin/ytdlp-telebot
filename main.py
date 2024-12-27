import os
import re
import signal
from datetime import datetime
from dotenv import load_dotenv

import telebot
from yt_dlp import YoutubeDL, utils

# import json  # For debug dumpung a part of the json info


load_dotenv()  # Load envvars from .env

token = os.environ.get('TOKEN', None)
if not token:
    print("ERROR: Specify TOKEN in an .env file or an environment variable!")
    exit(1)
log_channel = os.environ.get('LOG_CHANNEL', None)
regex = os.environ.get('REGEX', r'\bhttps?://\S*\b')
tempdir = os.environ.get('TEMPDIR', '/tmp/ytdlp-bot-downloading')  # Amend for Windows?..
resultdir = os.environ.get('RESULTDIR', '/tmp/ytdlp-bot-done')

options = {'format': 'ba + bv[height<=800] '
                     '/ ba + bv[width<=800] '  # For vertical videos, it's width, not height!
                     '/ best[height<=800] '
                     '/ best[width<=800]',
           'format_sort': ['codec:h265:h264:h263'],
           'max_filesize': 52428800,  # 50 MB - Telegram's limit for bots; abort if larger
           'subtitleslangs': ['en'],
           'writesubtitles': True,
           # 'progress_hooks': [progress],  # A function to call back!..

           'paths': {'temp': tempdir, 'home': resultdir},  # Autocreated!
           'concurrent_fragment_downloads': 10,

           'postprocessors': [{'key': 'FFmpegEmbedSubtitle',  # Subs: do not embed if subs already present?
                               'already_have_subtitle': False,
                               },
                              {'key': 'FFmpegMetadata',  # Metadata: only chapters
                               'add_chapters': True,
                               'add_infojson': False,
                               'add_metadata': False,
                               },
                              # {'key': 'FFmpegConcat',  # Looks like something I did not ask for!
                              #  'only_multi_video': True,
                              #  'when': 'playlist'
                              #  }
                              ],

           # Options set by default for the commandline (but not for the API!)
           # 'extract_flat': True,  # Get only top-level info (do not go into resolving playlists/URLs)
           # This has to stay off, because otherwise it just reports "oh, it's an URL redirect somewhere"!
           # 'ignoreerrors': 'only_download',  # False  # Does not seem to do anything!
           'retries': 10,
           'fragment_retries': 10,
           }

proxy = os.environ.get('PROXY', None)
if proxy:
    options.update({'proxy': proxy})

try:
    bot = telebot.TeleBot(token)
except Exception as fuck:
    print(f"Failed to register the bot!\n{fuck}")
    exit(1)


def log(message):
    # It gets logged to stderr already, so no need to print it!
    if log_channel:
        bot.send_message(log_channel, message)


@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(message, "I extract links from any messages, "
                          "and if they contain any videos, I try to download and post them.")


# @bot.message_handler(func=lambda message: True)
# def echo_all(message):
#     bot.reply_to(message, message.text)
#     bot.delete_message(message.chat.id, message.id)


# @bot.message_handler(func=lambda message: re.match(r'https?://', message))
@bot.message_handler(func=lambda message: True)  # Just check all messages!
def check_message(message):
    matches = re.findall(regex, message.text)
    if not matches:
        return

    for url in matches:
        timestamp = f"{datetime.now():%Y-%m-%d_%H:%M:%S}"  # 2024-12-27 14:30:15
        filename = f'{timestamp}.%(ext)s'

        # Quick check if this is a playlist to give the error sooner
        with YoutubeDL(dict(options, outtmpl=filename, extract_flat=True)) as ydl:
            try:
                info = ydl.sanitize_info(ydl.extract_info(url, download=False))
            except utils.DownloadError as shit:
                # No need to warn about non-video links
                # No need to print either, because it's logged already!
                # print(f"{shit}\n{url}")
                continue
            except Exception as shit:
                log(f"{shit}\n{url}")
                continue

            if info.get('entries') or (info.get('_type') == "playlist"):
                # log(f"Playlist\n{url}")
                bot.reply_to(message, f"😾 Suck me off, that's a playlist!\n{url}")
                continue

        # Try to download it (I wonder if it could still be a playlist behind an URL redirect...)
        with YoutubeDL(dict(options, outtmpl=filename)) as ydl:
            try:
                info = ydl.sanitize_info(ydl.extract_info(url, download=True))
            except utils.DownloadError as shit:
                # No need to warn about non-video links
                # No need to print either, because it's logged already!
                # print(f"{shit}\n{url}")
                continue
            except Exception as shit:
                log(f"{shit}\n{url}")
                continue

        # DEBUG: (you'll need to import json for this)
        # with open("/tmpfs/full.log", 'w') as file:
        #     json.dump(info, file, indent=4)
        # with open("/tmpfs/test.log", 'w') as file:
        #     json.dump(info.get('requested_downloads'), file, indent=4)

        # Get the actual filename that was created (with whatever extension it was assigned)
        filenames = info.get('requested_downloads')  # There's a list
        if len(filenames) != 1:
            log(f"WHAT THE FUCK! Got {len(filenames)} downloaded files!\n{url}")
        filename = filenames[0].get('filepath')

        # Check that we're going to delete a normal file
        if not os.path.isfile(filename):
            log(f"WHAT THE FUCK! File does not exist (or is not a file): {filename}\n{url}")

        with open(filename, 'rb') as file:
            try:
                bot.send_video(message.chat.id, file, caption=url)
                os.remove(filename)
            except Exception as shit:
                log(f"{shit}\n{url}")


def stop(sig, frame):
    print(f"Caught {signal.Signals(sig).name}, exiting gracefully...")
    bot.stop_bot()
    exit(0)


# Register callables to execute on signals
# Those callables must accept two arguments: (signal, frame)
signal.signal(signal.SIGINT, stop)
signal.signal(signal.SIGTERM, stop)

bot.infinity_polling()
