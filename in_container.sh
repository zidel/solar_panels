#!/bin/bash
set -eux

cmd="cd src/solar_panels && ${@}"

podman build -t solar_panels container
podman run \
    --interactive \
    --rm \
    --tty \
    --userns=keep-id \
    --volume /home/zidel/.keras:/home/zidel/.keras:Z \
    --volume /home/zidel/src/solar_panels:/home/zidel/src/solar_panels:Z \
    solar_panels \
    '/bin/bash' '-c' "${cmd}"
