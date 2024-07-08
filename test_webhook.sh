#!/bin/bash

# Read settings from .env
source .env

# URL of your webhook endpoint
WEBHOOK_URL="http://localhost:8000/zoom/transcript-ready"

# Current timestamp
TIMESTAMP=$(date +%s%N | cut -b1-13)

# JSON payload
JSON_PAYLOAD=$(cat <<EOF
{
  "event": "recording.transcript_completed",
  "event_ts": $TIMESTAMP,
  "payload": {
    "account_id": "AAAAAABBBB",
    "object": {
      "id": 1234567890,
      "uuid": "4444AAAiAAAAAiAiAiiAii==",
      "host_id": "x1yCzABCDEfg23HiJKl4mN",
      "account_id": "x1yCzABCDEfg23HiJKl4mN",
      "host_email": "jchill@example.com",
      "topic": "My Personal Recording",
      "type": 4,
      "start_time": "2021-07-13T21:44:51Z",
      "timezone": "America/Los_Angeles",
      "password": "123456",
      "duration": 60,
      "share_url": "https://example.com",
      "total_size": 529758,
      "recording_count": 1,
      "recording_files": [
        {
          "id": "ed6c2f27-2ae7-42f4-b3d0-835b493e4fa8",
          "meeting_id": "098765ABCD",
          "recording_start": "2021-03-23T22:14:57Z",
          "recording_end": "2021-03-23T23:15:41Z",
          "file_type": "TRANSCRIPT",
          "file_size": 142,
          "play_url": "https://example.com/recording/play/Qg75t7xZBtEbAkjdlgbfdngBBBB",
          "download_url": "$TEST_TRANSCRIPT_URL",
          "status": "completed",
          "recording_type": "audio_transcript"
        }
      ]
    }
  },
  "download_token": "$TEST_TRANSCRIPT_BEARER"
}
EOF
)

# Send the webhook
curl -X POST $WEBHOOK_URL \
  -H "Content-Type: application/json" \
  -d "$JSON_PAYLOAD"

echo # Print a newline for better readability of output
