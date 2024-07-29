import hashlib
import hmac
import os
import logging
import requests
import textwrap

import aiohttp
import anthropic
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from dotenv import load_dotenv

# The setup function is invoked by some glue code to wire up
# FastAPI endpoints to this plugin.
def setup(app: FastAPI):
    @app.post("/zoom/transcript-ready")
    async def zoom_transcript_ready(request: Request):
        "Called by Zoom when a transcript is ready for download"
        body = await request.json()
        
        match body.get("event"):
            case "endpoint.url_validation":
                return handle_validation(body)
            case "recording.transcript_completed":
                return await handle_transcript_ready(body)
            case _:
                raise HTTPException(status_code=400, detail=f"Unexpected event type: {body.get('event')}")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Provide a test transcript for testing purposes
TEST_TRANSCRIPT="""
Ken: Hey good morning everyone. This is a great day isn't it?

Scott: Yes, I'm so keen to get going on that new project.

Ken: Yes I am happy about that.

Des: I think we should paint the office walls brown."""

def load_config():
    # Load environment variables from .env file
    load_dotenv()
    
    # Load the Claude model and default to claude-3-5-sonnet-20240620
    claude_model = os.getenv("CLAUDE_MODEL") or "claude-3-5-sonnet-20240620"
    anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
    anthropic_api_url = os.getenv("ANTHROPIC_API_URL")
    
    # Get the Zoom Webhook Secret Token from environment variable
    zoom_webhook_secret_token = os.getenv("ZOOM_WEBHOOK_SECRET_TOKEN")
    
    # Get the endpoint URL for forwarding transcript details
    transcript_forward_url = os.getenv("TRANSCRIPT_FORWARD_URL")
    
    logger.info(f"Loaded configuration: CLAUDE_MODEL={claude_model}, "
                f"ZOOM_WEBHOOK_SECRET_TOKEN={'set' if zoom_webhook_secret_token else 'not set'}, "
                f"TRANSCRIPT_FORWARD_URL={transcript_forward_url}")
    
    return anthropic_api_key, anthropic_api_url, claude_model, zoom_webhook_secret_token, transcript_forward_url

ANTHROPIC_API_KEY, ANTHROPIC_API_URL, CLAUDE_MODEL, ZOOM_WEBHOOK_SECRET_TOKEN, TRANSCRIPT_FORWARD_URL = load_config()

app = FastAPI()

MEETING_SUMMARY_PROMPT = textwrap.dedent("""\
    You are tasked with summarizing the management team's daily huddle at
    MailChannels. This summary is crucial as it will be primarily read by the CEO,
    who relies on it to stay informed about the company's daily operations and key
    issues. Write the summary in the first person singular as if you observed the meeting.
    Refer to individuals using their first name and use colloquial language. While
    the content of the meeting is important, you have a friendly and collegial
    relationship with the team and are on a first-name basis with everyone including
    the CEO.

    First, carefully read through the following meeting transcript:

    <meeting_transcript>
    {transcript}
    </meeting_transcript>

    Your goal is to create a concise summary of this meeting,
    paying special attention to matters that seem to be of extreme importance to
    the CEO. Follow these steps:

    1. Identify key points discussed in the meeting, including:
       - Major decisions made
       - Important updates on ongoing projects
       - Challenges or obstacles mentioned
       - Achievements or milestones reached
       - Action items assigned to team members

    2. Pay particular attention to topics that are likely to be of high interest to the CEO, such as:
       - Financial matters
       - Strategic initiatives
       - Major client issues or opportunities
       - Significant operational changes
       - Competitive landscape updates
       - Issues relating to team morale

    3. Summarize the meeting in a clear, concise manner. The summary should:
       - Be no longer than 2 paragraphs
       - Highlight the most critical information first
       - Avoid unnecessary details or tangential discussions

    4. Throughout the summary, prioritize information that aligns with known
       CEO interests or concerns. If certain topics were emphasized or revisited
       multiple times during the meeting, ensure they are prominently featured in the
       summary.

    6. Use a professional, clear, and direct tone in your writing. Avoid jargon
       unless it's commonly used within the company. Be crisp; the CEO is short on time.
    """)

async def summarize(transcript: str) -> str:
    headers = {
        "Content-Type": "application/json",
        "X-API-Key": ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01"
    }

    payload: Dict[str, Any] = {
        "model": CLAUDE_MODEL,
        "max_tokens": 4096,
        "temperature": 0,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": MEETING_SUMMARY_PROMPT.format(transcript=transcript)
                    }
                ]
            }
        ]
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(ANTHROPIC_API_URL, json=payload, headers=headers) as response:
            if response.status == 200:
                data = await response.json()
                return data['content'][0]['text']
            else:
                raise Exception(f"API request failed with status {response.status}: {await response.text()}")

# Get the Zoom Webhook Secret Token from environment variable
ZOOM_WEBHOOK_SECRET_TOKEN = os.getenv("ZOOM_WEBHOOK_SECRET_TOKEN")
# Get the endpoint URL for forwarding transcript details
TRANSCRIPT_FORWARD_URL = os.getenv("TRANSCRIPT_FORWARD_URL")

def handle_validation(body):
    plain_token = body["payload"]["plainToken"]
    
    if not ZOOM_WEBHOOK_SECRET_TOKEN:
        return JSONResponse(status_code=500, content={"error": "Zoom Webhook Secret Token not set"})
    
    hashed_token = hmac.new(
        ZOOM_WEBHOOK_SECRET_TOKEN.encode('utf-8'),
        plain_token.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()

    return JSONResponse(status_code=200, content={
        "plainToken": plain_token,
        "encryptedToken": hashed_token
    })

async def handle_transcript_ready(body):
    try:
        # Extract relevant information
        download_token = body.get("download_token")
        recording_files = body["payload"]["object"]["recording_files"]

        for file in recording_files:
            transcript_content = ""
            
            if file["id"] == "TESTING123":
                logger.info("sending test transcript")
                transcript_content = TEST_TRANSCRIPT
                
            elif file["file_type"] == "TRANSCRIPT":
                download_url = file["download_url"]

                # Download the transcript file
                async with aiohttp.ClientSession() as session:
                    async with session.get(download_url, headers={"Authorization": f"Bearer {download_token}"}) as response:
                        response.raise_for_status()
                        transcript_content = await response.text()
            else:
                logger.error("can't handle this type of file object: {file}")
                continue

            # Summarize the transcript:
            transcript_summary = await summarize(transcript_content)

            # Prepare the JSON payload for the forward request
            forward_payload = {
                "transcript_summary": transcript_summary,
                "meeting_topic": body["payload"]["object"]["topic"],
                "meeting_start_time": body["payload"]["object"]["start_time"],
                "host_email": body["payload"]["object"]["host_email"]
            }

            # Send the HTTPS POST request asynchronously
            if TRANSCRIPT_FORWARD_URL:
                try:
                    async with aiohttp.ClientSession() as session:
                        async with session.post(TRANSCRIPT_FORWARD_URL, json=forward_payload) as response:
                            response.raise_for_status()
                            logger.info(f"Successfully forwarded transcript content to {TRANSCRIPT_FORWARD_URL}")
                except aiohttp.ClientError as e:
                    logger.error(f"Failed to forward transcript content: {str(e)}")
                    raise HTTPException(status_code=500, detail="Failed to forward transcript content")
            else:
                logger.warning("TRANSCRIPT_FORWARD_URL is not set. Skipping forwarding.")

            return JSONResponse(status_code=200, content={"status": "Transcript content processed"})

        # If no transcript file was found
        logger.warning(f"No transcript file was found in the webhook data: {body}")
        raise HTTPException(status_code=404, detail="No transcript file found in the webhook data")

    except KeyError as e:
        # Handle missing keys in the webhook data
        logger.error(f"Error processing webhook data: Missing key {str(e)}")
        raise HTTPException(status_code=400, detail=f"Missing data in webhook: {str(e)}")

    except aiohttp.ClientError as e:
        # Handle errors related to downloading the transcript
        logger.error(f"Error downloading transcript: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to download transcript")

    except Exception as e:
        # Handle any other unexpected errors
        logger.error(f"Unexpected error processing webhook data: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

if __name__ == "__main__":
    import sys
    sample_transcript = sys.stdin.read().strip()

    if not sample_transcript:
        print("Provide a transcript on standard input")
    else:
        summary = summarize(sample_transcript)
        print(summary)
