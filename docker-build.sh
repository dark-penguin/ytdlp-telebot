#!/bin/bash

APPNAME="ytdlp"
DEPS="ffmpeg python3-setuptools"  # get-pip.py on pre-Bookworm requires setuptools
FROM="debian:bullseye"
CMD="cd '$APPNAME' && python3 'main.py'"  # Launched with Bash

error() { echo "ERROR: $1"; exit "${2:-1}"; }
usage() { echo -e "\nERROR: $1\n\nUSAGE: $0 <tag>" >&2; exit 1; }

# Check arguments
[ -z "$1" ] && usage "Not enough arguments!"
[ -n "$2" ] && usage "Too many arguments!"
[ "$(whoami)" == "root" ] && error "NEVER run production stuff as root!!"


# Autodetect parameters
USER_NAME="$(whoami)"
USER_ID="$(id -u)"
GROUP_ID="$(id -g)"

TAG="$1"
BUILDDIR="/tmp/docker-build-$APPNAME-$(date '+%H%M%S')"  # Two builds within the same second are not allowed


# Do not pollute the current directory with build artifacts
[ -d "$BUILDDIR" ] && { echo -e "ERROR: $BUILDDIR already exists!\nClean up with:\n\trm -Rf $BUILDDIR" >&2; exit 1; }
cp -a "$(dirname "$0")" "$BUILDDIR"
cd "$BUILDDIR" || error "Could not cd into '$BUILDDIR' !"


# = = = = = = Build the Dockerfile
cat << EOF > Dockerfile || error "Failed to create the Dockerfile!" 2

FROM $FROM

RUN apt-get update && apt-get install -y eatmydata && ln -s /usr/bin/eatmydata /usr/local/bin/apt-get

RUN apt-get install -y python3 wget $DEPS  # Without quotes!

RUN addgroup --gid "$GROUP_ID" "$USER_NAME"
RUN adduser --gecos "" --add_extra_groups --disabled-password \
    --uid "$USER_ID" --gid "$GROUP_ID" "$USER_NAME"

USER "$USER_NAME"
WORKDIR "/home/$USER_NAME"

RUN echo '[ -d "\$HOME/.local/bin" ] && PATH="\$HOME/.local/bin:\$PATH"' >> ~/.bashrc

# pip from the repos won't allow us to install packages from pip!
# Allow installing the latest pip for this user only
RUN mkdir -p ~/.config/pip
RUN echo "[global]\nbreak-system-packages = true" > ~/.config/pip/pip.conf
# Install pip (installation will default to --user)
RUN wget -T5 -t5 -w2 -O- https://bootstrap.pypa.io/get-pip.py | python3 -
# Add pip-completion
RUN grep -q 'pip_completion' 2>/dev/null ~/.bash_aliases || python3 -m pip completion --bash >> ~/.bash_aliases

COPY --chown="$USER_ID:$GROUP_ID" . "$APPNAME"

RUN cd "$APPNAME" && python3 -m pip install --user -r requirements.txt

#CMD ["/bin/bash", "-c", "$CMD"]

WORKDIR "/home/$USER_NAME/$APPNAME"
CMD ["python3", "main.py"]

EOF
# = = = = = =


# Set DEBUG to non-empty for "debug mode" (see the Dockerfile before building)
[ -n "$DEBUG" ] && { less "$BUILDDIR/Dockerfile"; echo -e "\nDEBUG MODE - exiting before build"; exit 0; }


echo -e "\n=== Building...\n"
docker build --progress=plain -t "$TAG" . # || error "Build failed!" 2  # No use - https://github.com/moby/moby/issues/1150
echo -e "\n=== Cleaning up the directory...\n"
#docker image prune -f
echo -e "\n=== Done\n"

[ -z "$DEBUG" ] && rm -Rf "$BUILDDIR"
