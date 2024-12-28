import os
import sys
import re
import signal
import logging
from dotenv import load_dotenv

import telebot
from yt_dlp import YoutubeDL, utils


logging.basicConfig(format="%(levelname)s:%(module)s: %(message)s")
logger = logging.getLogger(__name__)  # This logger's name does not matter!
DEBUG = "--debug" in sys.argv
logger.setLevel(logging.DEBUG if DEBUG else logging.WARNING)


load_dotenv()  # Load values from .env into envvars

token = os.environ.get('TOKEN', None)
if not token:
    logger.error("ERROR: Specify TOKEN in an .env file or an environment variable!")
    exit(1)
log_channel = os.environ.get('LOG_CHANNEL', None)
regex = os.environ.get('REGEX', r'\bhttps?://\S*\b')
tempdir = os.environ.get('TEMPDIR', '/tmp/ytdlp-telebot')

default_formats = (
                    ' ba + bv[width>=800][height<=800][filesize<50M]'
                    '/ba + bv[width<=800][height>=800][filesize<50M]'
                    '/   best[width>=800][height<=800][filesize<50M]'
                    '/   best[width<=800][height>=800][filesize<50M]'
                    
                    '/ba + bv[width<=800][height<=800][filesize<50M]'
                    '/   best[width<=800][height<=800][filesize<50M]'
                    
                    '/ba + bv[width>=800][height<=800]'
                    '/ba + bv[width<=800][height>=800]'
                    '/   best[width>=800][height<=800]'
                    '/   best[width<=800][height>=800]'
                    
                    '/ba + bv[width<=800][height<=800]'
                    '/   best[width<=800][height<=800]'
                    )

options = {'format_sort': ['codec:h265:h264:h263'],
           'max_filesize': 52428800,  # 50 MB - Telegram's limit for bots; abort if larger
           'subtitleslangs': ['en'],
           'writesubtitles': True,
           # 'progress_hooks': [progress],  # A function to call back!
           # 'verbose': True,  # They require it for bug reporting

           'paths': {'home': tempdir},  # Autocreated if don't exist!
           'concurrent_fragment_downloads': 10,
           'retries': 10,
           'fragment_retries': 10,

           'postprocessors': [{'key': 'FFmpegEmbedSubtitle',  # Subs: do not embed if subs already present?
                               'already_have_subtitle': False},
                              {'key': 'FFmpegMetadata',  # Metadata: only chapters
                               'add_chapters': True,
                               'add_infojson': False,
                               'add_metadata': False},]}

proxy = os.environ.get('PROXY', None)
if proxy:
    options.update({'proxy': proxy})

formats = os.environ.get('FORMATS', default_formats)
options.update({'format': formats})

logger.info(f"LOG_CHANNEL: {log_channel}")
logger.info(f"TEMPDIR: {tempdir}")
logger.info(f"REGEX: {regex}")
logger.info(f"PROXY: {proxy}")
logger.info(f"FORMATS: {formats}")

try:
    bot = telebot.TeleBot(token)
except Exception as err:
    logger.error(f"Failed to register the bot!\n{err}")
    exit(1)


def notify(error, url, extra=None):  # Post a message into the "notification channel"
    logger.info(f"-- Sending a notification for {url}: {error}")
    if log_channel:
        message = f'{error}'
        if DEBUG and isinstance(error, utils.DownloadError):  # Then it has .exc_info[1] !
            message += f'\n\n{type(error.exc_info[1])}'
        if extra:
            message += f'\n\n{extra}'
        message += f'\n\n{url}'
        bot.send_message(log_channel, message)  # It gets logged to stderr already, so no need to print it!


@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(message, "I extract links from any messages, "
                          "and if they contain any videos, I try to download and post them.")


@bot.message_handler(func=lambda message: True)  # Just check all messages - no need to filter here!
def check_message(message):
    matches = re.findall(regex, message.text)
    if not matches:
        return

    one_video_sent = False  # I've checked that this is safe for concurrent invocations!
    local_counter = 0
    for url in matches:
        logger.info(f"-- Downloading video {matches.index(url)+1} of {len(matches)}")

        local_counter += 1
        filename = f"{message.chat.id}-{message.id}-{local_counter}.%(ext)s"  # This filename will be unique

        try:
            # Quick check if this is a playlist - we don't want to accidentally download it
            # If we download a playlist non-flatly, it will throw errors about deleted videos!
            # We want the playlist to successfully abort, so it must not go into the "except:" territory!
            logger.info('-- First query: "flat" general information to check for playlist')
            with YoutubeDL(dict(options, outtmpl=filename, extract_flat=True)) as ydl:
                info = ydl.sanitize_info(ydl.extract_info(url, download=False))
            # It is possible that we get "Requested format not available" right here! (Not for a playlist!)
            # Then we fall into "except:", and 'info' is still unassigned!
            if info.get('entries') or (info.get('_type') == "playlist"):
                continue  # If this is a playlist, abort quietly

            logger.info('-- Second query: attempt to download the video')
            with YoutubeDL(dict(options, outtmpl=filename, extract_flat=False)) as ydl:
                info = ydl.sanitize_info(ydl.extract_info(url, download=True))

        except utils.DownloadError as error:  # Note that you can't handle errors "normally" in yt-dlp!
            # Check for UnsupportedError first, because it is also an ExtractorError!
            if isinstance(error.exc_info[1], utils.UnsupportedError):
                continue
            # Check this with "elif", or continue, because otherwise both will match!
            elif isinstance(error.exc_info[1], utils.ExtractorError):
                # !! NOTE that 'info' might still be unassigned!
                # We'd like to see what formats are available
                with YoutubeDL(dict(options, outtmpl=filename, extract_flat=False, listformats=True)) as ydl:
                    info = ydl.sanitize_info(ydl.extract_info(url, download=False))


                # TODO: The output is too large for Telegram - should process it first!
                # TODO: DEBUG - how the fuck do I process this JSON?..
                logger.info('-- Third query: extract formats')
                # with open("/tmpfs/test.log", 'w') as file:
                #     json.dump(info.get('formats'), file, indent=4)
                notify(error, url, "Formats available: <WIP>")
                continue
            notify(error, url)
            continue

        # DEBUG: dump 'info' into a file (you'll need to import json for this)
        # with open("/tmpfs/full.log", 'w') as file:
        #     json.dump(info, file, indent=4)
        # with open("/tmpfs/test.log", 'w') as file:
        #     json.dump(info.get('requested_downloads'), file, indent=4)


        # Get the actual filename that was created (with whatever extension it was assigned)
        filenames = info.get('requested_downloads')  # There's a list
        if len(filenames) != 1:
            notify(f"WARNING: Got {len(filenames)} downloaded files for some reason!", url)
        filename = filenames[0].get('filepath')

        # Check that we're going to delete a normal file
        if not os.path.isfile(filename):
            notify(f"WARNING: File not found: {filename}", url)

        with open(filename, 'rb') as file:
            try:
                # Repost the whole original text in the first message; in other messages, only post the URL
                text = message.text + f"\n\n@{message.from_user.username}"
                bot.send_video(message.chat.id, file, #reply_to_message_id=message.id,
                               caption=url if one_video_sent else text)
                one_video_sent = True
            except Exception as error:
                notify(error, url)

        os.remove(filename)

    if one_video_sent:
        bot.delete_message(message.chat.id, message.id)


def stop(sig, _):
    # Better 'print' this because it's not a "warning/error" level but we want to see it
    print(f"Caught {signal.Signals(sig).name}, exiting gracefully...")
    bot.stop_bot()
    exit(0)


# Register callables to execute on signals
# Those callables must accept two arguments: (signal, frame)
signal.signal(signal.SIGINT, stop)
signal.signal(signal.SIGTERM, stop)

bot.infinity_polling()
