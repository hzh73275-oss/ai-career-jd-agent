from __future__ import annotations

import functools
import os
import sys
import threading
import time
import webbrowser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FRONTEND_DIR = ROOT / "frontend"
VENV_PYTHON = ROOT.parent / ".venv" / "Scripts" / "python.exe"


def ensure_project_python() -> None:
  if os.environ.get("RESUME_JD_APP_BOOTSTRAPPED") == "1":
    return
  if not VENV_PYTHON.exists():
    return
  current_python = Path(sys.executable).resolve()
  target_python = VENV_PYTHON.resolve()
  if current_python == target_python:
    return
  env = os.environ.copy()
  env["RESUME_JD_APP_BOOTSTRAPPED"] = "1"
  os.execve(str(target_python), [str(target_python), *sys.argv], env)


ensure_project_python()

if str(ROOT) not in sys.path:
  sys.path.insert(0, str(ROOT))

import uvicorn


class NoCacheStaticHandler(SimpleHTTPRequestHandler):
  def end_headers(self) -> None:
    self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
    self.send_header("Pragma", "no-cache")
    self.send_header("Expires", "0")
    super().end_headers()


def start_api_server(host: str, port: int) -> uvicorn.Server:
  config = uvicorn.Config(
    "src.api.server:app",
    host=host,
    port=port,
    log_level="warning",
  )
  server = uvicorn.Server(config)
  thread = threading.Thread(target=server.run, daemon=True)
  thread.start()
  print(f"API: http://{host}:{port}")
  return server


def start_static_server(name: str, host: str, port: int, handler) -> ThreadingHTTPServer:
  server = ThreadingHTTPServer((host, port), handler)
  thread = threading.Thread(target=server.serve_forever, daemon=True)
  thread.start()
  print(f"{name}: http://{host}:{port}")
  return server


def main() -> None:
  if not FRONTEND_DIR.exists():
    raise RuntimeError(f"Frontend folder not found: {FRONTEND_DIR}")

  api_server = start_api_server("127.0.0.1", 8765)

  frontend_handler = functools.partial(
    NoCacheStaticHandler,
    directory=str(FRONTEND_DIR),
  )
  ui_server = start_static_server("UI", "127.0.0.1", 5175, frontend_handler)

  url = "http://127.0.0.1:5175"
  print("")
  print("Started. Keep this terminal open.")
  print(f"Open: {url}")
  webbrowser.open(url)

  try:
    while True:
      time.sleep(1)
  except KeyboardInterrupt:
    print("\nStopping...")
    api_server.should_exit = True
    ui_server.shutdown()


if __name__ == "__main__":
  main()
