#!/bin/bash
set -e

case "$1" in
    develop)
        echo "Running Development Server"
        exec python -B main.py
        ;;
    test)
        echo "Running Test"
        exec pytest
        ;;
    *)
        exec "$@"
esac