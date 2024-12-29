# ytdlp-telebot
A Telegram bot for [yt-dlp](https://github.com/yt-dlp/yt-dlp) made with Telebot
aka [pyTelegramBotAPI](https://github.com/eternnoir/pyTelegramBotAPI)

- You can message the bot privately, or invite it to a group chat.
- The bot will monitor all posted messages, detect any HTTP[S] links in them,
and attempt to download them using yt-dlp.
- If it succeeds, it will upload the video, post it with the contents of your
original post, and remove your original post to avoid clutter.
- Multiple links per message are supported. If there are multiple links in your post,
then the bot will download all of them and post multiple videos, each video annotated
with its own URL. The contents of your original post are then only copied to the first video.
- Unsuccessful attempts are simply ignored (because not all links are videos).
- Note that [Telegram limits the size of videos uploaded by bots to 50 MB](https://core.telegram.org/bots/faq#how-do-i-upload-a-large-file).
This bot will attempt to download videos below that size, ideally in 720p.
If no such format is detected, then the download attempt is considered a failure.
- You can optionally enable sending notifications about some errors into
a specified channel. For example, you will receive notifications about videos
which are available but failed to download, so you can investigate the reason.


## Self hosting

### Windows / Linux
It is assumed that you already have Python installed and configured, and can install
requirements from pip.

- Clone the project
- Create a new bot and get a token from [BotFather](https://t.me/BotFather)
- Copy `env_example` into `.env`, adjust its values
  - `TOKEN` is mandatory, the rest are optional
  - On Windows, you might want to adjust `TEMPDIR`, because by default it will
    download to the root of your current drive. For example, if you want videos
    to be downloaded into the current directory, specify "."
  - `PROXY`, if you need it


- Install [ffmpeg](https://ffmpeg.org/)
- Install dependencies: `pip install -r requirements.txt`
- Run the bot: `python3 main.py` (on Windows: `python main.py`)

### Docker
It is assumed that you already have Docker installed and configured.

- Clone the project
- Create a new bot and get a token from [BotFather](https://t.me/BotFather)
- Copy `env_example` into `.env`, adjust its values


- Install the systemd service file:
```bash
sudo cp ytdlp.service /etc/systemd/system/
sudo systemctl enable ytdlp  # If you want it to be started at system boot
```
- Launch `docker-redeploy.sh`: it will build/rebuild the container, restart the service,
and then attach to the logs to let you confirm a successful redeployment.
(Just use Ctrl+C to detach from the logs.)


## Known issues
- The bot ignores messages that have any kind of attachments ('photo', 'document',
'audio', 'video', 'voice', 'sticker', 'contact', 'location', 'poll'). This is actually good:
if you have any kind of attachment, then it's not just a meme you want to pre-download
for convenience, and any links are probably not the main focus of the message.
You can always repost the links in separate messages if you want. Trying to repost
and delete the priginal message is likely not a very good idea in this case.
- When reposting the contents of the original message, it is not possible
(at least according to my research) to preserve its formatting. So, the formatting
will be lost, and the message still deleted, because there is no way to even know
if there was any formatting. This is not much of a problem though.
