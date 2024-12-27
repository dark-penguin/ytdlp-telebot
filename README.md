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
### Level 1: Windows
Not tested. It would probably be enough to adjust paths in your .env file.

### Level 2: Linux
You might have some trouble installing Python packages from pip
unless you already have it set up and/or know how to use virtualenv.
Explaining how to set up Python is out of scope, so consider using Docker instead. 

- Clone the project
- Create a new bot and get a token from [BotFather](https://t.me/BotFather)
- Copy `env_example` into `.env`, adjust its values (TOKEN is mandatory,
the rest are optional, in case you want to override the defaults)
- Install dependencies and run the bot
```bash
pip install -r requirements.txt
python3 main.py
```

### Level 3: Docker
Naturally, you must have Docker installed and working, but this is as simple as
installing a package and adding yourself to the `docker` group.

- Clone the project
- Create a new bot and get a token from [BotFather](https://t.me/BotFather)
- Copy `env_example` into `.env`, adjust its values (TOKEN is mandatory,
the rest are optional, in case you want to override the defaults)
- Simply launch `docker-redeploy.sh`. It will [re]build the container,
stop the old one if it's already running, and launch the new one.
- If you want it installed as a service, install the service file:
```bash
sudo cp ytdlp.service /etc/systemd/system/
sudo systemctl enable ytdlp  # To be started at system boot
sudo systemctl start ytdlp  # To start it now
```
