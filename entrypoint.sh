#!/bin/bash
set -e

case "$1" in
    develop)
        echo "Running Development Server"
        # exec python main.py
        exec adev runserver --livereload --port $PORT main.py
        ;;
    test)
        echo "Running Test"
        exec pytest
        ;;
    *)
        exec "$@"
esac