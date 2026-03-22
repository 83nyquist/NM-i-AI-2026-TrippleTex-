#!/bin/bash
while true; do
    echo "Starting serveo tunnel..."
    ssh -o StrictHostKeyChecking=no -R 80:localhost:8000 serveo.net > serveo.log 2>&1
    echo "Tunnel died. Restarting in 2 seconds..."
    sleep 2
done
