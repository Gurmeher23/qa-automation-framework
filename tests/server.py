"""Run the app under test in a background thread on a free port."""

from __future__ import annotations

import socket
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path

import uvicorn

from app.config import Settings
from app.main import create_app


@dataclass
class LiveServer:
    """A uvicorn server in a thread. Binds the socket up front, so there is no port race."""

    db_path: Path
    admin_username: str = "admin"
    admin_password: str = "admin-test-password"
    url: str = ""
    _server: uvicorn.Server | None = field(default=None, repr=False)
    _thread: threading.Thread | None = field(default=None, repr=False)

    def start(self) -> LiveServer:
        sock = socket.socket()
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
        settings = Settings(
            database_url=f"sqlite:///{self.db_path}",
            secret_key="test-secret",
            admin_username=self.admin_username,
            admin_password=self.admin_password,
        )
        config = uvicorn.Config(create_app(settings), log_level="warning")
        self._server = uvicorn.Server(config)
        self._thread = threading.Thread(target=self._server.run, kwargs={"sockets": [sock]}, daemon=True)
        self._thread.start()
        deadline = time.monotonic() + 15
        while not self._server.started:
            if time.monotonic() > deadline:
                raise RuntimeError("Test server did not start within 15s")
            time.sleep(0.05)
        self.url = f"http://127.0.0.1:{port}"
        return self

    def stop(self) -> None:
        if self._server:
            self._server.should_exit = True
        if self._thread:
            self._thread.join(timeout=10)
