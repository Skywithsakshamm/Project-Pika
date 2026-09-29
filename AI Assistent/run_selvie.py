"""
Selvie Launcher Entry Point.
Runs the complete desktop assistant experience or backend service.
"""
import sys
import argparse
import subprocess
from pathlib import Path

# Add project root to sys.path
ROOT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT_DIR))

from config.settings import settings

def main():
    parser = argparse.ArgumentParser(description="Selvie Personal AI Desktop Assistant")
    parser.add_argument("--backend-only", action="store_true", help="Run only the FastAPI backend server")
    parser.add_argument("--headless", action="store_true", help="Run background daemon without GUI")
    parser.add_argument("--port", type=int, default=settings.PORT, help="Port to run backend on")
    args = parser.parse_args()

    if args.port:
        settings.PORT = args.port

    if args.backend_only or args.headless:
        import uvicorn
        from backend.database.db import init_db
        init_db()
        print(f"[Selvie] Starting backend server on http://{settings.HOST}:{settings.PORT}")
        uvicorn.run("backend.main:app", host=settings.HOST, port=settings.PORT, log_level="info")
    else:
        # Launch PySide6 Desktop GUI (which automatically runs backend in background thread)
        from backend.desktop_app import main as run_desktop_app
        run_desktop_app()

if __name__ == "__main__":
    main()
