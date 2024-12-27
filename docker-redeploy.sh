#!/bin/bash

CONTAINER="ytdlp"

error() { echo -e "\nERROR: $1\n${USAGE:+\nUSAGE: $USAGE\n}" >&2; exit "${2:-1}"; }  # It's already quoted!

#git pull || error "Failed to 'git pull'!"

./docker-build.sh "$CONTAINER" || error "Failed to build!"

if container_present; then
	echo "Stopping container '$CONTAINER' ..."
    docker stop "$CONTAINER" || error "Failed to stop container '$CONTAINER'!"
else echo "Container '$CONTAINER' not running - not stopping"
fi

# The container does not disappear immediately after stopping!
while true; do [ -z "$(docker ps -a | awk "{print \$NF;}" | tail -n +2 | grep "^ytdlp$")" ] && break; sleep 1; done

echo -e "\nLaunching...\n"

docker run -d --rm --name "$CONTAINER" "$CONTAINER"
