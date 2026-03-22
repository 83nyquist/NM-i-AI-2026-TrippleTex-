#!/bin/bash
while true; do
    echo "Starting localhost.run tunnel..."
    ssh -o StrictHostKeyChecking=no -R 80:localhost:8000 nokey@localhost.run > lhr.log 2>&1
    echo "Tunnel died. Restarting in 2 seconds..."
    sleep 2
done
