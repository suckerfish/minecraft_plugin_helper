# Minecraft Plugin Manager

A web UI for managing Minecraft server plugins and controlling the server container on Unraid.

## Features

- **File Browser**: Navigate, upload, and delete files in your plugins directory
- **Folder Management**: Create new folders, navigate subdirectories
- **Server Control**: Start, stop, and restart your Minecraft container via Unraid's GraphQL API
- **Status Monitoring**: Real-time container status display

## Screenshots

The UI provides:
- Server status bar with Start/Stop/Restart buttons
- Breadcrumb navigation for folder hierarchy
- Drag & drop file upload
- File/folder listing with delete functionality

## Setup

### Prerequisites

- Python 3.14+
- [uv](https://github.com/astral-sh/uv) for package management
- Unraid server with API access enabled
- itzg/minecraft-server container (or similar)

### Docker Deployment

1. Copy `.env.example` to `.env` and configure:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` with your settings:
   ```
   UNRAID_URL=http://192.168.1.200
   UNRAID_API_KEY=your_api_key_here
   MINECRAFT_CONTAINER=itzg-minecraft-server
   PLUGINS_PATH=/mnt/user/appdata/minecraft/plugins
   PORT=8340
   ```

3. Run (pulls image from ghcr.io):
   ```bash
   docker compose up -d
   ```

4. Open http://localhost:8340

### Local Development

1. Clone the repository

2. Create virtual environment and install dependencies:
   ```bash
   uv sync
   ```

3. Copy `.env.example` to `.env` and configure:
   ```bash
   cp .env.example .env
   ```

4. Edit `.env` with your settings:
   ```
   UNRAID_URL=http://192.168.1.200
   UNRAID_API_KEY=your_api_key_here
   MINECRAFT_CONTAINER=itzg-minecraft-server
   PLUGINS_PATH=./test_plugins
   PORT=8340
   ```

5. Run the development server:
   ```bash
   uv run uvicorn app.main:app --host 0.0.0.0 --port 8340 --reload
   ```

6. Open http://localhost:8340

### Unraid API Key

1. In Unraid WebGUI, go to **Settings → Management Access → API**
2. Create a new API key with **Docker container read/modify** permissions
3. Copy the key to your `.env` file

## Project Structure

```
minecraft_helper/
├── .github/
│   └── workflows/
│       └── docker.yml   # CI/CD: builds and pushes to ghcr.io
├── app/
│   ├── main.py          # FastAPI application
│   ├── unraid.py        # Unraid GraphQL API client
│   └── static/
│       └── index.html   # Web UI
├── Dockerfile           # Container image definition
├── compose.yaml         # Docker Compose configuration
├── .dockerignore        # Files excluded from build
├── .env.example         # Environment template
├── .env                 # Your configuration (gitignored)
├── pyproject.toml       # Python dependencies
└── README.md
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check for container orchestration |
| `/api/status` | GET | Get Minecraft container status |
| `/api/start` | POST | Start the container |
| `/api/stop` | POST | Stop the container |
| `/api/restart` | POST | Restart the container |
| `/api/files` | GET | List files/folders (query: `path`) |
| `/api/files/upload` | POST | Upload file (query: `path`) |
| `/api/files/mkdir` | POST | Create folder (query: `name`, `path`) |
| `/api/files` | DELETE | Delete file/folder (query: `path`) |

## TODO

- [x] Docker packaging (Dockerfile + compose.yaml)
- [x] CI/CD pipeline (GitHub Actions → ghcr.io)
- [ ] Unraid Community Applications template
- [ ] File download functionality
- [ ] Bulk delete / multi-select
- [ ] File rename functionality
- [ ] Container logs viewer

## Tech Stack

- **Backend**: Python, FastAPI, httpx
- **Frontend**: Vanilla HTML/CSS/JavaScript
- **API**: Unraid GraphQL API

## License

MIT
