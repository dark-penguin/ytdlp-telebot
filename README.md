# ytdlp-telebot
A Telegram bot for [yt-dlp](https://github.com/yt-dlp/yt-dlp) made with Telebot
aka [pyTelegramBotAPI](https://github.com/eternnoir/pyTelegramBotAPI)

- You can message the bot privately, or invite it to a group chat
- The bot will monitor all posted messages, detect any HTTP[S] links in them,
and attempt to download them using yt-dlp
- Unsuccessful attempts are simply ignored (because not all links are videos).
On successfull attempts, the bot will upload the video into the chat,
annotating it with the original link.
- Multiple links per message are supported.
- Note that [Telegram limits the size of videos uploaded by bots to 50 MB](https://core.telegram.org/bots/faq#how-do-i-upload-a-large-file).
This bot will attempt to download videos below that size, ideally in 720p.
If no such format is detected, then the download attempt is considered a failure.


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
