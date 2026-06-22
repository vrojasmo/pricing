#!/usr/bin/env python3
"""
Arranca el servidor web de Bover Price Monitor.

Uso:
    python server.py              # http://localhost:8000
    python server.py --port 3000  # puerto personalizado
    python server.py --reload     # modo desarrollo (auto-reload)
"""

import argparse
import sys

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--reload", action="store_true")
    args = parser.parse_args()

    import uvicorn
    print(f"\n  🚀  Bover Price Monitor")
    print(f"  ──────────────────────────────────────")
    print(f"  URL: http://localhost:{args.port}")
    print(f"  Pulsa Ctrl+C para detener\n")

    uvicorn.run(
        "webapp.app:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level="warning",
    )
