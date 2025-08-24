import json
import threading
import http.server
import shutil
from pathlib import Path
import importlib.util
import sys

import pytest

hooks_file = Path(__file__).resolve().parents[2] / "src" / "ytdl_sub" / "hooks.py"
spec = importlib.util.spec_from_file_location("ytdl_sub.hooks", hooks_file)
module = importlib.util.module_from_spec(spec)
sys.modules["ytdl_sub.hooks"] = module
spec.loader.exec_module(module)


class _Handler(http.server.BaseHTTPRequestHandler):
    received = {}

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)
        _Handler.received = json.loads(body)
        self.send_response(200)
        self.end_headers()

    def log_message(self, *_):  # pragma: no cover - suppress server logs
        return


def test_after_move_webhook_receives_final_path(tmp_path):
    work = tmp_path / "work"
    out_dir = tmp_path / "out"
    work.mkdir()
    out_dir.mkdir()
    src = work / "sample.txt"
    src.write_text("data", encoding="utf-8")
    dest = out_dir / "sample.txt"
    shutil.move(src, dest)

    server = http.server.HTTPServer(("localhost", 0), _Handler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever)
    thread.daemon = True
    thread.start()

    hook = module.WebhookHook(
        url=f"http://localhost:{port}",
        body_json={"path": "{final_filepath}"},
    )
    runner = module.HookRunner({"after_move": [hook]})
    runner.run("after_move", {"final_filepath": str(dest)})

    server.shutdown()
    thread.join()

    assert _Handler.received["path"] == str(dest)
