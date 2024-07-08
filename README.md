# Zoom Transcript Webhook Handler

This project implements a webhook handler for Zoom's transcript-ready
notifications. It receives webhook events from Zoom when a meeting transcript
is ready, processes the information, and logs the download URL for the
transcript.

## Features

- Handles Zoom webhook validation challenges
- Processes 'recording.transcript_completed' events from Zoom
- Extracts and logs transcript download URLs
- Dockerized for easy deployment
- Includes a test script to simulate Zoom webhook events

## Prerequisites

- Docker
- Make (optional, for using Makefile commands)
- Zoom account with webhook functionality enabled
- Python 3.10 or higher (for local development and testing)

## Setup

1. Clone this repository:
   ```
   git clone https://github.com/ttulttul/zoom-webhook-handler.git
   cd zoom-webhook-handler
   ```

2. Create a `.env` file in the project root and add your Zoom Webhook Secret Token and other secrets:
   ```
   ZOOM_WEBHOOK_SECRET_TOKEN=your_zoom_webhook_secret_token_here
   TRANSCRIPT_FORWARD_URL=your_zapier_webhook_url_here
   TEST_TRANSCRIPT_URL=url_of_a_zoom_transcript_for_testing
   TEST_TRANSCRIPT_BEARER=zoom_bearer_token_for_testing
   CLAUDE_MODEL=anthropic_claude_model_name
   ANTHROPIC_API_KEY=your_anthropic_key
   ```

3. Build the Docker image:
   ```
   make build
   ```

## Usage

1. Start the application:
   ```
   make run
   ```

2. The webhook handler will be available at `http://localhost:8000/zoom/transcript-ready`

3. Configure your Zoom app to send webhook events to this URL, using something like `ngrok` to route to a public URL if desired

4. To view logs:
   ```
   make logs
   ```

5. To stop the application:
   ```
   make down
   ```

## Testing

You can send a test webhook event using the provided script:

```
make test-webhook
```

This will send a simulated Zoom transcript-ready event to your local webhook handler.

## Makefile Commands

- `make build`: Build the Docker image
- `make run`: Run the Docker container
- `make stop`: Stop the Docker container
- `make down`: Stop and remove the Docker container
- `make rebuild`: Rebuild and restart the Docker container
- `make logs`: View container logs
- `make test-webhook`: Send a test webhook event
- `make test-local`: Run tests in a local venv
- `make test-local-verbose`: Same as `test-local` but with debug logging
- `make clean`: Remove all Docker artifacts related to this project

## Project Structure

```
zoom-transcript-webhook-handler/
├── app/
│   └── main.py
├── .env
├── .gitignore
├── Dockerfile
├── Makefile
├── README.md
├── requirements.txt
└── test_webhook.sh
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
