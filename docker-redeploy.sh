#!/bin/bash

./docker-build.sh || exit 1

sudo systemctl restart ytdlp || exit 1

sudo journalctl -u ytdlp -f  # Just Ctrl+C out of it
