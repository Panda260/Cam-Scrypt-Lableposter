# Cam-Scrypt-Lableposter

## Overview

Cam-Scrypt-Lableposter is a small Python service that overlays a "cam" badge (for example `cam.png`) onto poster images in a specified Jellyfin library. The service exposes a webhook endpoint (`/webhook`). Sending a POST to that endpoint triggers processing in the background and the endpoint returns HTTP 200 immediately.

## What you'll find in this repo

- `main.py` — main application: calls the Jellyfin API to fetch items and poster images, overlays the badge, and uploads the modified posters back to Jellyfin.
- `cam.png` — example badge file (not included in the image by default; mount it from the host or add it to the image).

## Environment variables

Configure the following environment variables in Docker or your runtime environment:

- `JELLYFIN_URL` — Jellyfin base URL (e.g. `http://10.0.4.50:8096`)
- `API_KEY` — Jellyfin API key (X-Emby-Token)
- `LIBRARY_ID` — target library ID in Jellyfin
- `WEBHOOK_PORT` — port the Flask webhook listens on (default: `5000`)

## Docker Compose example

Add this service entry to your `docker-compose.yml` (adapt values as needed):

```yaml
services:
  cam-poster:
    image: ghcr.io/panda260/cam-scrypt-lableposter:main
    restart: unless-stopped
    environment:
      - JELLYFIN_URL=http://0.0.0.0:8096
      - API_KEY=aaabbbccc
      - LIBRARY_ID=aaabbbccc
      - WEBHOOK_PORT=5000
    ports:
      - "5000:5000"
    volumes:
      - ./cam.png:/app/cam.png:ro
```

Note: Mounting `cam.png` from the host is recommended so you can replace the badge without rebuilding the container.

## Triggering the webhook

Send a POST request to the webhook endpoint to start processing. Example using `curl`:

```bash
curl -X POST http://localhost:9092/webhook
```

Replace `localhost:9092` with the host/IP and port where your container is accessible. The endpoint returns HTTP 200 immediately and processing runs in the background.

## Local testing (without Docker)

1. Create a Python virtual environment and install dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Windows (PowerShell):

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

2. Set environment variables and run `main.py`:

Linux/macOS example:

```bash
export JELLYFIN_URL="http://10.0.4.50:8096"
export API_KEY="your_api_key"
export LIBRARY_ID="your_library_id"
export WEBHOOK_PORT=9092
python main.py
```

PowerShell example:

```powershell
$env:JELLYFIN_URL = 'http://10.0.4.50:8096'
$env:API_KEY = 'your_api_key'
$env:LIBRARY_ID = 'your_library_id'
$env:WEBHOOK_PORT = '9092'
python main.py
```

## Logs & troubleshooting

- Check container logs: `docker-compose logs -f cam-poster` or `docker logs -f <container>`.
- Common issues:
  - `cam.png` missing in the container — mount it or add it to the image.
  - Incorrect `LIBRARY_ID` or `API_KEY` — Jellyfin API errors will appear in logs.
  - Network/firewall issues preventing the container from reaching Jellyfin.
- If the webhook returns 200 but posters are not updated, inspect the logs for `download_item_image`, `add_badge`, and `upload_image_to_jellyfin` messages.

## Production notes

- The app currently uses Flask's development server. For production deployments, use a WSGI server like `gunicorn` and a reverse proxy (e.g. nginx).
- Consider protecting the webhook with a shared secret header such as `X-Auth-Token` and an environment variable `WEBHOOK_TOKEN`.

## License & support

This repository contains helper scripts — adapt them to your environment. For support or questions open an issue in the repository.
