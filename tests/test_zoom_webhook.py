import json
import os

from aioresponses import aioresponses
from app.main import app
from dotenv import load_dotenv
from fastapi.testclient import TestClient
import pytest
import responses

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_env_vars():
    load_dotenv()

async def fetch_transcript(download_url, download_token):
    async with aiohttp.ClientSession() as session:
        async with session.get(download_url, headers={"Authorization": f"Bearer {download_token}"}) as response:
            response.raise_for_status()
            transcript_content = await response.text()
            return transcript_content

@responses.activate
def test_zoom_webhook_transcript_ready():
    # Mock the Zapier webhook
    responses.add(
        responses.POST, 
        'https://hooks.zapier.com/hooks/catch/6470/2bivqdk/',
        json={'status': 'ok'}, 
        status=200
    )

    payload = {
        "event": "recording.transcript_completed",
        "download_token": os.getenv('TEST_TRANSCRIPT_BEARER'),
        "payload": {
            "object": {
                "recording_files": [
                    {
                        "file_type": "TRANSCRIPT",
                        "download_url": os.getenv('TEST_TRANSCRIPT_URL')
                    }
                ],
                "topic": "Test Meeting",
                "start_time": "2023-07-08T10:00:00Z",
                "host_email": "host@example.com"
            }
        }
    }
    response = client.post("/zoom/transcript-ready", json=payload)
    assert response.status_code == 200
    assert response.json() == {"status": "Transcript details processed"}

    # Check that the forward request was made correctly
    assert len(responses.calls) == 1
    assert responses.calls[0].request.url == os.getenv('TRANSCRIPT_FORWARD_URL')
    forward_payload = json.loads(responses.calls[0].request.body)
    assert forward_payload['download_url'] == os.getenv('TEST_TRANSCRIPT_URL')
    assert forward_payload['download_token'] == os.getenv('TEST_TRANSCRIPT_BEARER')
    assert forward_payload['meeting_topic'] == "Test Meeting"
    assert forward_payload['meeting_start_time'] == "2023-07-08T10:00:00Z"
    assert forward_payload['host_email'] == "host@example.com"

def test_zoom_webhook_unexpected_event():
    payload = {
        "event": "unexpected.event",
        "payload": {}
    }
    response = client.post("/zoom/transcript-ready", json=payload)
    assert response.status_code == 400
    assert response.json() == {"error": "Unexpected event type"}

def test_zoom_webhook_missing_transcript():
    payload = {
        "event": "recording.transcript_completed",
        "download_token": "test_download_token",
        "payload": {
            "object": {
                "recording_files": [
                    {
                        "file_type": "MP4",
                        "download_url": "https://example.com/video.mp4"
                    }
                ],
                "topic": "Test Meeting",
                "start_time": "2023-07-08T10:00:00Z",
                "host_email": "host@example.com"
            }
        }
    }
    response = client.post("/zoom/transcript-ready", json=payload)
    assert response.status_code == 404
    assert response.json() == {"error": "No transcript file found in the webhook data"}
