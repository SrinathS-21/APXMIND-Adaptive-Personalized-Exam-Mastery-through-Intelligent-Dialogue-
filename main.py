"""
APXMIND — Main Entry Point
===========================

Launches the FastAPI server with Uvicorn.

Usage:
    python main.py                    # Start with default settings
    python main.py --port 8001        # Custom port
    python main.py --reload           # Development with auto-reload

Or directly via Uvicorn:
    uvicorn src.apxmind.server.app:app --reload --port 8000
"""

import argparse
import os
import sys

# Ensure the project root is on the path
sys.path.insert(0, os.path.dirname(__file__))


def main():
    parser = argparse.ArgumentParser(description="APXMIND API Server")
    parser.add_argument("--host", default="127.0.0.1", help="Bind host (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8000, help="Bind port (default: 8000)")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload for development")
    parser.add_argument("--workers", type=int, default=1, help="Number of worker processes")
    args = parser.parse_args()

    import uvicorn

    print(f"""
    ╔═══════════════════════════════════════════════╗
    ║         APXMIND API Server v2.0.0              ║
    ║   AI-powered NEET Exam Preparation Tutor      ║
    ╠═══════════════════════════════════════════════╣
    ║   http://{args.host}:{args.port}                      ║
    ║   Docs:  http://{args.host}:{args.port}/docs          ║
    ╚═══════════════════════════════════════════════╝
    """)

    uvicorn.run(
        "src.apxmind.server.app:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        workers=args.workers,
        log_level="info",
    )


if __name__ == "__main__":
    main()
