# Cam-Scrypt-Lableposter

A small Flask service that stamps a "cam" badge (`cam.png`) onto every poster in a Jellyfin library. A `POST` to `/webhook` starts a background job that downloads each poster, overlays the badge and uploads the result back to Jellyfin.

## How it works

1. `POST /webhook` returns HTTP 200 immediately and starts the job in a background thread.
2. The job checks that `cam.png` exists, then **waits 900 seconds (15 minutes)** — giving Jellyfin time to finish scanning and fetching metadata/artwork for newly added media.
3. It verifies that `LIBRARY_ID` exists via `/Library/VirtualFolders`.
4. It fetches all items in the library recursively and keeps those with posters: `Movie`, `Series` and `BoxSet`.
5. For each item it downloads the `Primary` image, scales the badge to the full poster width, pastes it at the top edge, saves it as JPEG (quality 95, converting RGBA/LA/P posters to RGB) and uploads it back.
6. Progress is logged every 10 items, followed by a final summary.

> **Note:** Uploaded posters replace the originals. Every run processes the whole library again, so posters that already have a badge get another one on top. Because the badge sits at the same position, this usually looks the same, but keep it in mind if you use a semi-transparent badge.

## Configuration

| Variable | Required | Default | Description |
|---|---|---|---|
| `JELLYFIN_URL` | yes | – | Jellyfin base URL, e.g. `http://jellyfin.local:8096` |
| `API_KEY` | yes | – | Jellyfin API key (Dashboard → API Keys) |
| `LIBRARY_ID` | yes | – | ID of the library to process |
| `WEBHOOK_PORT` | no | `5000` | Port the webhook server listens on |

Authentication uses the `Authorization: MediaBrowser Token="<API_KEY>"` header, which Jellyfin 10.11+ requires (the old `X-Emby-Token` / `api_key` methods are disabled there by default).

To find the library ID, start a run with any value: the job lists all libraries with their IDs in the log before aborting because the target library was not found.

## Docker

Images are built by GitHub Actions and published to GHCR on every push:

- `ghcr.io/panda260/cam-scrypt-lableposter:latest` — `main` branch
- `ghcr.io/panda260/cam-scrypt-lableposter:<branch>` — any branch
- `ghcr.io/panda260/cam-scrypt-lableposter:sha-<commit>` — a specific build

`cam.png` is included in the image. Mount your own file over `/app/cam.png` to change the badge without rebuilding.

### Docker Compose

```yaml
services:
  cam-poster:
    image: ghcr.io/panda260/cam-scrypt-lableposter:latest
    restart: unless-stopped
    environment:
      - JELLYFIN_URL=http://jellyfin.local:8096
      - API_KEY=your_api_key
      - LIBRARY_ID=your_library_id
      - WEBHOOK_PORT=5000
    ports:
      - "5000:5000"
    volumes:
      - ./cam.png:/app/cam.png:ro   # optional: custom badge
```

### Build locally

```bash
docker build -t cam-poster .
docker run --rm -p 5000:5000 \
  -e JELLYFIN_URL=http://jellyfin.local:8096 \
  -e API_KEY=your_api_key \
  -e LIBRARY_ID=your_library_id \
  cam-poster
```

## Triggering

```bash
curl -X POST http://localhost:5000/webhook
```

Response:

```json
{"status": "success", "message": "Webhook received, timer started (300 seconds)", "timestamp": 1760000000.0}
```

The message text is outdated; the actual delay is 900 seconds. Each request starts its own job, so several triggers in quick succession run in parallel.

The endpoint fits well with the Jellyfin Webhook plugin (e.g. on "Item Added"), but any HTTP client works — the request body is ignored.

## Running without Docker

Requires Python 3 (the Docker image uses 3.11).

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

export JELLYFIN_URL="http://jellyfin.local:8096"
export API_KEY="your_api_key"
export LIBRARY_ID="your_library_id"
export WEBHOOK_PORT=5000
python main.py
```

Run it from the repository directory: `cam.png` is looked up relative to the current working directory.

## Troubleshooting

- Logs: `docker compose logs -f cam-poster` or `docker logs -f <container>`.
- Nothing happens after the trigger: the job is still in its 15-minute countdown (`Countdown N` lines in the log).
- `Badge file missing: cam.png`: the file is not in the working directory (`/app` in the container).
- `Target library ... not found`: wrong `LIBRARY_ID`, or the API key lacks access. Compare with the library list printed just before.
- HTTP 401 errors: invalid `API_KEY`.
- `Error downloading image`: the item has no poster yet.
- The startup log mentions a `/status` endpoint; it is not implemented.

## Production notes

- The service uses Flask's development server and has no authentication on `/webhook`. Only expose it on a trusted network, or put it behind a reverse proxy that restricts access.
