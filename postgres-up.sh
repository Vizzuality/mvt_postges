#!/bin/bash

case "$1" in
    local)
        type docker-compose >/dev/null 2>&1 || { echo >&2 "docker-compose is required but it's not installed.  Aborting."; exit 1; }
        docker-compose -f docker-compose-local.yml build && docker-compose -f docker-compose-local.yml up
        ;;
    *)
        echo "Usage: postgres-up.sh {local}" >&2
        exit 1
        ;;
esac

exit 0