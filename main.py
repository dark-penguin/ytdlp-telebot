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


def extract_formats(info):
    result = []
    for i in info:  # There are multiple format entries!
        # Extract data
        # format_id = i.get('format_id')
        filesize = i.get('filesize')
        width = i.get('width')
        height = i.get('height')
        fps = i.get('fps')
        video = i.get('vcodec', 'none') or 'none'
        audio = i.get('acodec', 'none') or 'none'
        samplerate = i.get('asr')
        bitrate = i.get('abr') or i.get('tbr')
        vbr = i.get('vbr')

        # Normalize data
        filesize = filesize // 1048576 if filesize else None
        # video = video if video != 'none' else None
        # audio = audio if audio != 'none' else None
        video = video.split('.')[0] if video != 'none' else None
        audio = audio.split('.')[0] if audio != 'none' else None

        if not video and not audio:
            continue  # Skip the "stupid" formats

        result.append({
            'filesize': filesize,
            'width': width,
            'height': height,
            'fps': fps,
            'video': video,
            'audio': audio,
            'samplerate': samplerate,
            'bitrate': bitrate,
            'vbr': vbr,
            })

    def sorter(key):
        if key['video']:
            return max(key['width'], key['height']), key['fps'], key['vbr'] or 0
        elif key['audio']:
            return key['bitrate'], 0, key['bitrate'] or 0

    result.sort(key=sorter)
    return result


def render_formats(result):
    display = f"{'Resolution':^14} {'Bitrate':^9} {'Size':^8} {'Codecs'}\n"
    # One line is up to 50 symbols long (usually); that's what fits well
    # Max message length is 4096 chars, and we have the caption on top of that
    # So, we can afford up to 80 lines (even a little over that)
    max_lines = 80
    if result[-max_lines:] != result:
        display += f"  <...over {max_lines} lines - truncated...>\n"
    for r in result[-max_lines:]:
        size = f"({r['filesize']} MB)" if r['filesize'] else f"(      )"
        resolution = f"{r['width'] or '-'}x{r['height'] or '-'}p{r['fps'] or ''}" if r['video'] \
            else f"{r['samplerate'] or '---'}"
        bitrate = f"{int(r['vbr']) if r['vbr'] else '---'}:{int(r['bitrate']) if r['bitrate'] else '---'}"
        codecs = f"{r['video'] or '---'}:{r['audio'] or '---'}"

        display += f"{resolution:14} {bitrate:9} {size:>8} {codecs}\n"
    print("Formats available:\n", display)  # This line is added after markup
    return display


def escape_markdown(text):
    special_chars = r'[_*`\[\]()~#>+-.]'
    escaped_text = re.sub(special_chars, r'\\\g<0>', text)
    return escaped_text


def notify(error, url=None, extra=None):  # Post a message into the "notification channel"
    logger.info(f"-- Sending a notification for {url}: {error}")
    if log_channel:
        message = f'{error}'
        if DEBUG and isinstance(error, utils.DownloadError):  # Then it has .exc_info[1] !
            message += f'\n\n{type(error.exc_info[1])}'
        if extra:
            message += f'\n\n{extra}'
        if url:
            message += f'\n\n{url}'
        # It gets logged to stderr already, so no need to print it!
        bot.send_message(log_channel, message)


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
                logger.info('-- Third query: extract formats')
                try:
                    with YoutubeDL(dict(options, outtmpl=filename, extract_flat=False, listformats=True)) as ydl:
                        info = ydl.sanitize_info(ydl.extract_info(url, download=False))
                except utils.DownloadError as new_error:
                    notify(error, url, "Formats available: FAILED to extract! (see the error below)")
                    notify(new_error, url, "This happened while trying to extract available formats")
                    continue

                # Parse 'info' and present it (now it's definitely assigned!)
                # notify(error, url, f"{render_formats(extract_formats(info.get('formats')))}")
                notify(error, url)
                # Escape existing message, then apply markup on top of it
                rendered_formats = escape_markdown(render_formats(extract_formats(info.get('formats'))))
                rendered_formats = f"Formats available:\n```\n{rendered_formats}\n```"
                bot.send_message(log_channel, rendered_formats, parse_mode='MarkdownV2')
                continue
            notify(error, url)
            continue

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
                bot.send_video(message.chat.id, file, caption=url if one_video_sent else text)
                one_video_sent = True
            except Exception as error:
                notify(error, url)

        os.remove(filename)

    if one_video_sent:
        try:
            bot.delete_message(message.chat.id, message.id)
        except Exception as error:
            notify(error)


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
