#!/bin/bash

CONTAINER="ytdlp"

error() { echo -e "\nERROR: $1\n${USAGE:+\nUSAGE: $USAGE\n}" >&2; exit "${2:-1}"; }  # It's already quoted!

container_present() {
	if [ "$(docker ps -a | awk '{print $NF;}' | tail -n +2 | grep "^$CONTAINER\$")" == "$CONTAINER" ]
	then return 0  # The container is present
	else return 1  # The container is not present
	fi
}

#git pull || error "Failed to 'git pull'!"

./docker-build.sh "$CONTAINER" || error "Failed to build!"

if container_present; then
	echo "Stopping container '$CONTAINER' ..."
    docker stop "$CONTAINER" || error "Failed to stop container '$CONTAINER'!"
else echo "Container '$CONTAINER' not running - not stopping"
fi

while container_present; do sleep 1; done  # Apparently it does not disappear immediately!

echo -e "\nLaunching...\n"

docker run -it --rm --name "$CONTAINER" "$CONTAINER"
