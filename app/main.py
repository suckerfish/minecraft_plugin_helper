"""Minecraft Plugin Manager - Web UI for managing plugins and server."""

import os
from pathlib import Path
from fastapi import FastAPI, UploadFile, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from dotenv import load_dotenv

from .unraid import UnraidClient

# Load environment variables
load_dotenv()

UNRAID_URL = os.getenv("UNRAID_URL", "http://192.168.1.200")
UNRAID_API_KEY = os.getenv("UNRAID_API_KEY", "")
MINECRAFT_CONTAINER = os.getenv("MINECRAFT_CONTAINER", "itzg-minecraft-server")
PLUGINS_PATH = Path(os.getenv("PLUGINS_PATH", "./test_plugins")).resolve()

# Ensure plugins directory exists
PLUGINS_PATH.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="Minecraft Plugin Manager")

# Initialize Unraid client
unraid = UnraidClient(UNRAID_URL, UNRAID_API_KEY)


# --- API Endpoints ---


@app.get("/health")
async def health_check():
    """Health check endpoint for container orchestration."""
    return {"status": "healthy"}


@app.get("/api/status")
async def get_status():
    """Get Minecraft server container status."""
    try:
        status = await unraid.get_container_status(MINECRAFT_CONTAINER)
        if status:
            return {"container": status.name, "state": status.state}
        return {"container": MINECRAFT_CONTAINER, "state": "NOT_FOUND"}
    except Exception as e:
        return {"container": MINECRAFT_CONTAINER, "state": "ERROR", "error": str(e)}


@app.post("/api/restart")
async def restart_server():
    """Restart the Minecraft server container."""
    try:
        success = await unraid.restart_container(MINECRAFT_CONTAINER)
        if success:
            return {"success": True, "message": "Server restarted successfully"}
        return {"success": False, "message": "Failed to restart server"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/start")
async def start_server():
    """Start the Minecraft server container."""
    try:
        success = await unraid.start_container(MINECRAFT_CONTAINER)
        if success:
            return {"success": True, "message": "Server started successfully"}
        return {"success": False, "message": "Failed to start server"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/stop")
async def stop_server():
    """Stop the Minecraft server container."""
    try:
        success = await unraid.stop_container(MINECRAFT_CONTAINER)
        if success:
            return {"success": True, "message": "Server stopped successfully"}
        return {"success": False, "message": "Failed to stop server"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def safe_path(subpath: str) -> Path:
    """Validate and return safe path within PLUGINS_PATH."""
    # Normalize and resolve the path
    if not subpath:
        return PLUGINS_PATH

    # Remove leading slashes and normalize
    clean_path = subpath.lstrip("/")
    target = (PLUGINS_PATH / clean_path).resolve()

    # Ensure it's within PLUGINS_PATH (prevent path traversal)
    try:
        target.relative_to(PLUGINS_PATH.resolve())
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid path")

    return target


@app.get("/api/files")
async def list_files(path: str = ""):
    """List all files and folders in a directory."""
    try:
        target = safe_path(path)

        if not target.exists():
            raise HTTPException(status_code=404, detail="Directory not found")

        if not target.is_dir():
            raise HTTPException(status_code=400, detail="Not a directory")

        items = []
        for item in target.iterdir():
            stat = item.stat()
            items.append({
                "name": item.name,
                "type": "folder" if item.is_dir() else "file",
                "size": stat.st_size if item.is_file() else None,
                "modified": stat.st_mtime,
            })

        # Sort: folders first, then by name
        items.sort(key=lambda x: (0 if x["type"] == "folder" else 1, x["name"].lower()))

        # Build breadcrumb path
        rel_path = target.relative_to(PLUGINS_PATH.resolve())
        breadcrumbs = []
        if str(rel_path) != ".":
            parts = rel_path.parts
            for i, part in enumerate(parts):
                breadcrumbs.append({
                    "name": part,
                    "path": "/".join(parts[:i+1])
                })

        return {
            "path": str(rel_path) if str(rel_path) != "." else "",
            "breadcrumbs": breadcrumbs,
            "items": items
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/files/upload")
async def upload_file(file: UploadFile, path: str = ""):
    """Upload a file to a specific directory."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    target_dir = safe_path(path)

    if not target_dir.exists():
        raise HTTPException(status_code=404, detail="Directory not found")

    if not target_dir.is_dir():
        raise HTTPException(status_code=400, detail="Not a directory")

    # Sanitize filename
    safe_name = Path(file.filename).name
    if not safe_name or safe_name.startswith("."):
        raise HTTPException(status_code=400, detail="Invalid filename")

    file_path = target_dir / safe_name

    try:
        content = await file.read()
        file_path.write_bytes(content)
        return {"success": True, "filename": safe_name, "size": len(content)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/files/mkdir")
async def create_folder(name: str, path: str = ""):
    """Create a new folder."""
    target_dir = safe_path(path)

    if not target_dir.exists():
        raise HTTPException(status_code=404, detail="Parent directory not found")

    # Sanitize folder name
    safe_name = Path(name).name
    if not safe_name or safe_name.startswith("."):
        raise HTTPException(status_code=400, detail="Invalid folder name")

    new_folder = target_dir / safe_name

    if new_folder.exists():
        raise HTTPException(status_code=400, detail="Folder already exists")

    try:
        new_folder.mkdir()
        return {"success": True, "folder": safe_name}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/files")
async def delete_item(path: str):
    """Delete a file or empty folder."""
    if not path:
        raise HTTPException(status_code=400, detail="Path required")

    target = safe_path(path)

    if not target.exists():
        raise HTTPException(status_code=404, detail="Item not found")

    # Don't allow deleting the root
    if target.resolve() == PLUGINS_PATH.resolve():
        raise HTTPException(status_code=400, detail="Cannot delete root directory")

    try:
        if target.is_file():
            target.unlink()
        elif target.is_dir():
            # Only delete empty directories for safety
            if any(target.iterdir()):
                raise HTTPException(status_code=400, detail="Folder is not empty")
            target.rmdir()
        return {"success": True, "deleted": path}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- Static Files ---


# Mount static files
static_path = Path(__file__).parent / "static"
if static_path.exists():
    app.mount("/static", StaticFiles(directory=str(static_path)), name="static")


@app.get("/")
async def index():
    """Serve the main UI."""
    index_path = static_path / "index.html"
    if index_path.exists():
        return FileResponse(index_path)
    return JSONResponse({"error": "UI not found"}, status_code=404)
