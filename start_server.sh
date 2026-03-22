#!/bin/bash
echo "Starting FastAPI server..."
uvicorn main:app --port 8000 &
SERVER_PID=$!

echo "FastAPI server started with PID $SERVER_PID"
echo "--------------------------------------------------------"
echo "Please open a NEW terminal window and run the following command:"
echo "ngrok http 8000"
echo "--------------------------------------------------------"
echo "Then, copy the ngrok Forwarding URL (e.g. https://<id>.ngrok.app)"
echo "append '/solve' to it, and submit that to the competition platform!"
echo ""
echo "Press Ctrl+C to stop the FastAPI server."

# Wait for the server process
wait $SERVER_PID
