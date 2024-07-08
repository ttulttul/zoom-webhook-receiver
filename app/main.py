from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import hmac
import hashlib
import os
import logging
import requests
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# Get the Zoom Webhook Secret Token from environment variable
ZOOM_WEBHOOK_SECRET_TOKEN = os.getenv("ZOOM_WEBHOOK_SECRET_TOKEN")
# Get the endpoint URL for forwarding transcript details
TRANSCRIPT_FORWARD_URL = os.getenv("TRANSCRIPT_FORWARD_URL")

@app.get("/")
async def root():
    return {"message": "Hello World"}

@app.post("/zoom/transcript-ready")
async def zoom_transcript_ready(request: Request):
    body = await request.json()
    
    if body.get("event") == "endpoint.url_validation":
        return handle_validation(body)
    
    if body.get("event") == "recording.transcript_completed":
        return handle_transcript_ready(body)
    
    # Handle unexpected events
    return JSONResponse(status_code=400, content={"error": "Unexpected event type"})

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

def handle_transcript_ready(body):
    try:
        # Extract relevant information
        download_token = body.get("download_token")
        recording_files = body["payload"]["object"]["recording_files"]
        
        for file in recording_files:
            if file["file_type"] == "TRANSCRIPT":
                download_url = file["download_url"]
                
                # Prepare the JSON payload for the forward request
                forward_payload = {
                    "download_url": download_url,
                    "download_token": download_token,
                    "meeting_topic": body["payload"]["object"]["topic"],
                    "meeting_start_time": body["payload"]["object"]["start_time"],
                    "host_email": body["payload"]["object"]["host_email"]
                }
                
                # Send the HTTPS POST request
                if TRANSCRIPT_FORWARD_URL:
                    try:
                        response = requests.post(TRANSCRIPT_FORWARD_URL, json=forward_payload)
                        response.raise_for_status()
                        logger.info(f"Successfully forwarded transcript details to {TRANSCRIPT_FORWARD_URL}")
                    except requests.exceptions.RequestException as e:
                        logger.error(f"Failed to forward transcript details: {str(e)}")
                        return JSONResponse(status_code=500, content={"error": "Failed to forward transcript details"})
                else:
                    logger.warning("TRANSCRIPT_FORWARD_URL is not set. Skipping forwarding.")
                
                return JSONResponse(status_code=200, content={"status": "Transcript details processed"})
        
        # If no transcript file was found
        logger.warning("No transcript file was found in the webhook data: {body}")
        return JSONResponse(status_code=404, content={"error": "No transcript file found in the webhook data"})
    
    except KeyError as e:
        # Handle missing keys in the webhook data
        logger.error(f"Error processing webhook data: Missing key {str(e)}")
        return JSONResponse(status_code=400, content={"error": f"Missing data in webhook: {str(e)}"})
    
    except Exception as e:
        # Handle any other unexpected errors
        logger.error(f"Unexpected error processing webhook data: {str(e)}")
        return JSONResponse(status_code=500, content={"error": "Internal server error"})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
