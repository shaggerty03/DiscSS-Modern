#!/bin/bash

set -x

MAX_RESTARTS=100
restart_count=0

while true; do
    # Check if we've exceeded max restarts
    if [ $restart_count -ge $MAX_RESTARTS ]; then
        echo "Exceeded maximum number of restarts ($MAX_RESTARTS). Exiting."
        exit 1
    fi

    # Try to build
    if ! npm run build; then
        echo "Build failed, retrying in 5 seconds..."
        sleep 5
        continue
    fi

    # Run the application
    if ! npm run start; then
        exit_code=$?
        restart_count=$((restart_count + 1))
        echo "Process crashed with exit code $exit_code at $(date)" >> restart.log
        echo "Restart attempt $restart_count of $MAX_RESTARTS"
        
        # Optional: different wait times based on exit code
        if [ $exit_code -eq 255 ]; then
            echo "FFmpeg error detected, restarting in 10 seconds..."
            sleep 10
        else
            echo "Unknown error, restarting in 5 seconds..."
            sleep 5
        fi
    fi
done