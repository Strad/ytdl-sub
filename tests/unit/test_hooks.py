import sys
import os
import json
import threading
import time
import http.server
import urllib.error
import subprocess
import importlib.util
from pathlib import Path

import pytest

hooks_file = Path(__file__).resolve().parents[2] / "src" / "ytdl_sub" / "hooks.py"
spec = importlib.util.spec_from_file_location("ytdl_sub.hooks", hooks_file)
module = importlib.util.module_from_spec(spec)
sys.modules["ytdl_sub.hooks"] = module
spec.loader.exec_module(module)

ExecHook = module.ExecHook
WebhookHook = module.WebhookHook
HookRunner = module.HookRunner
_expanded_hook = module._expanded_hook


class TestHooks:
    def test_placeholder_expansion(self):
        ctx = {
            "cmd": "echo",
            "arg": "hello",
            "envval": "VAL",
            "domain": "example.com",
            "path": "hook",
            "body": "world",
        }
        exec_hook = ExecHook(cmd="{cmd}", args=["{arg}"], env={"K": "{envval}"})
        webhook_hook = WebhookHook(
            url="http://{domain}/{path}", body_json={"msg": "{body}"}
        )

        expanded_exec = _expanded_hook(exec_hook, ctx)
        expanded_web = _expanded_hook(webhook_hook, ctx)

        assert expanded_exec.cmd == "echo"
        assert expanded_exec.args == ["hello"]
        assert expanded_exec.env["K"] == "VAL"
        assert expanded_web.url == "http://example.com/hook"
        assert expanded_web.body_json == {"msg": "world"}

    def test_json_context_stdin(self, tmp_path):
        output_file = tmp_path / "out.txt"
        script = (
            "import sys, json, os; "
            "data=json.load(sys.stdin); "
            "open(os.environ['OUT'],'w').write(data['foo'])"
        )
        hook = ExecHook(
            cmd=sys.executable,
            args=["-c", script],
            env={"OUT": str(output_file)},
            pass_json_stdin=True,
        )
        runner = HookRunner({"event": [hook]})
        runner.run("event", {"foo": "bar"})
        assert output_file.read_text() == "bar"

    def test_exec_timeout(self):
        hook = ExecHook(
            cmd=sys.executable,
            args=["-c", "import time; time.sleep(1)"],
            timeout_sec=0.01,
        )
        runner = HookRunner({"event": [hook]})
        with pytest.raises(subprocess.TimeoutExpired):
            runner.run("event", {})

    def test_webhook_timeout(self):
        class SlowHandler(http.server.BaseHTTPRequestHandler):
            def do_POST(self):
                time.sleep(1)
                self.send_response(200)
                self.end_headers()

            def log_message(self, *_):  # pragma: no cover - suppress server logs
                return

        server = http.server.HTTPServer(("localhost", 0), SlowHandler)
        port = server.server_address[1]
        thread = threading.Thread(target=server.serve_forever)
        thread.daemon = True
        thread.start()

        hook = WebhookHook(url=f"http://localhost:{port}", timeout_sec=0.01)
        runner = HookRunner({"event": [hook]})
        with pytest.raises(urllib.error.URLError):
            runner.run("event", {})

        server.shutdown()
        thread.join()

    def test_ignore_errors_exec(self):
        failing = ExecHook(
            cmd=sys.executable,
            args=["-c", "import sys; sys.exit(1)"],
            ignore_errors=False,
        )
        runner = HookRunner({"event": [failing]})
        with pytest.raises(subprocess.CalledProcessError):
            runner.run("event", {})

        ignoring = ExecHook(
            cmd=sys.executable,
            args=["-c", "import sys; sys.exit(1)"],
            ignore_errors=True,
        )
        runner = HookRunner({"event": [ignoring]})
        runner.run("event", {})

    def test_ignore_errors_webhook(self):
        url = "http://localhost:9"  # typically unused port; connection should fail quickly
        failing = WebhookHook(url=url, ignore_errors=False)
        runner = HookRunner({"event": [failing]})
        with pytest.raises(urllib.error.URLError):
            runner.run("event", {})

        ignoring = WebhookHook(url=url, ignore_errors=True)
        runner = HookRunner({"event": [ignoring]})
        runner.run("event", {})
