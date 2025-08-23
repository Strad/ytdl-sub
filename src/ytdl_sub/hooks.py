from __future__ import annotations

import json
import subprocess
import urllib.request
from typing import Dict, List, Optional

from ytdl_sub.utils.logger import Logger

logger = Logger.get("hooks")


class HookRunner:
    """Simple runner to execute configured hooks."""

    def __init__(self, hooks: Optional[Dict[str, List[Dict]]] = None):
        self._hooks = hooks or {}

    def _run_exec(self, hook: Dict) -> None:
        command = hook.get("cmd") or hook.get("command") or hook.get("args")
        timeout = hook.get("timeout_sec", 30)
        ignore_errors = hook.get("ignore_errors", True)
        if command is None:
            return
        try:
            subprocess.run(command, timeout=timeout, check=not ignore_errors)  # type: ignore[arg-type]
        except Exception as exc:  # pylint: disable=broad-except
            logger.warning("exec hook failed: %s", exc)
            if not ignore_errors:
                raise

    def _run_webhook(self, hook: Dict, payload: Dict) -> None:
        url = hook.get("url")
        timeout = hook.get("timeout_sec", 30)
        ignore_errors = hook.get("ignore_errors", True)
        if url is None:
            return
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=timeout):  # noqa: S310 - local network
                pass
        except Exception as exc:  # pylint: disable=broad-except
            logger.warning("webhook hook failed: %s", exc)
            if not ignore_errors:
                raise

    def _run_hooks(self, name: str, payload: Optional[Dict] = None) -> None:
        hooks = self._hooks.get(name, [])
        for hook in hooks:
            hook_type = hook.get("type")
            if hook_type == "exec":
                self._run_exec(hook)
            elif hook_type == "webhook":
                self._run_webhook(hook, payload or {})
            else:
                logger.warning("Unknown hook type '%s'", hook_type)

    def after_move(self, payload: Optional[Dict] = None) -> None:
        """Run hooks after a file has been moved."""
        self._run_hooks("after_move", payload)
