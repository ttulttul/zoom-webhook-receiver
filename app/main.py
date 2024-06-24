from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import hmac
import hashlib
import os
import logging
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# Get the Zoom Webhook Secret Token from environment variable
ZOOM_WEBHOOK_SECRET_TOKEN = os.getenv("ZOOM_WEBHOOK_SECRET_TOKEN")

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
                
                # Log the download URL with the token (using Authorization header method)
                logger.info(f"Transcript download URL: {download_url}")
                logger.info(f"Use the following curl command to download the transcript:")
                logger.info(f"curl --request GET --url {download_url} --header 'authorization: Bearer {download_token}' --header 'content-type: application/json'")
                
                # You can add your logic here to actually download and process the transcript
                
                return JSONResponse(status_code=200, content={"status": "Transcript URL logged"})
        
        # If no transcript file was found
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
