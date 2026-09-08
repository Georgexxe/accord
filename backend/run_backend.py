"""
StoryParity Backend Server Launcher
"""

import uvicorn
import os
import sys

if __name__ == "__main__":
    # Ensure current directory is in PYTHONPATH
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    port = int(os.environ.get("PORT", 8000))
    host = os.environ.get("HOST", "127.0.0.1")
    print(f"[StoryParity] Starting API server on http://{host}:{port}", flush=True)
    uvicorn.run("app.main:app", host=host, port=port, reload=False, log_level="info")

