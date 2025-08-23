"""Hook execution utilities."""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Mapping, MutableMapping
import json
import os
import subprocess
import time
import urllib.request
import urllib.error


@dataclass
class ExecHook:
    """Definition for an executable hook."""

    cmd: str
    args: List[str] | None = None
    env: MutableMapping[str, str] | None = None
    timeout_sec: float | None = None
    retries: int = 0
    pass_json_stdin: bool = False
    ignore_errors: bool = False


@dataclass
class WebhookHook:
    """Definition for a webhook hook."""

    url: str
    headers: MutableMapping[str, str] | None = None
    body_json: Any | None = None
    timeout_sec: float | None = None
    retries: int = 0
    ignore_errors: bool = False


Hook = ExecHook | WebhookHook


class _SafeFormatDict(dict):
    """Dictionary returning placeholder for missing keys when formatting."""

    def __missing__(self, key: str) -> str:  # pragma: no cover - simple
        return "{" + key + "}"


def _expand_placeholders(value: Any, ctx: Mapping[str, Any]) -> Any:
    """Recursively expand ``{key}`` placeholders in ``value`` using ``ctx``."""

    if isinstance(value, str):
        return value.format_map(_SafeFormatDict(ctx))
    if isinstance(value, list):
        return [_expand_placeholders(v, ctx) for v in value]
    if isinstance(value, tuple):  # pragma: no cover - not expected but for completeness
        return tuple(_expand_placeholders(v, ctx) for v in value)
    if isinstance(value, dict):
        return {k: _expand_placeholders(v, ctx) for k, v in value.items()}
    return value


def _expanded_hook(hook: Hook, ctx: Mapping[str, Any]) -> Hook:
    data = asdict(hook)
    data = _expand_placeholders(data, ctx)
    return type(hook)(**data)


class HookRunner:
    """Runs hooks registered for events."""

    def __init__(self, hooks: Mapping[str, List[Hook]] | None = None) -> None:
        self._hooks: Dict[str, List[Hook]] = {k: list(v) for k, v in (hooks or {}).items()}

    def run(self, event: str, ctx: Mapping[str, Any]) -> None:
        """Run hooks for ``event`` with context ``ctx``."""

        for hook in self._hooks.get(event, []):
            expanded = _expanded_hook(hook, ctx)
            if isinstance(expanded, ExecHook):
                self._run_exec(expanded, ctx)
            else:
                self._run_webhook(expanded, ctx)

    def _run_exec(self, hook: ExecHook, ctx: Mapping[str, Any]) -> None:
        args = [hook.cmd]
        if hook.args:
            args.extend(hook.args)

        env = os.environ.copy()
        if hook.env:
            env.update(hook.env)

        input_data = None
        text = False
        if hook.pass_json_stdin:
            input_data = json.dumps(ctx)
            text = True

        attempt = 0
        while True:
            try:
                subprocess.run(
                    args,
                    input=input_data,
                    text=text,
                    env=env,
                    timeout=hook.timeout_sec,
                    check=True,
                )
                return
            except (subprocess.SubprocessError, OSError, TimeoutError) as exc:  # pragma: no cover - general
                if attempt < hook.retries:
                    attempt += 1
                    time.sleep(min(2 ** attempt, 60))
                    continue
                if not hook.ignore_errors:
                    raise exc
                return

    def _run_webhook(self, hook: WebhookHook, ctx: Mapping[str, Any]) -> None:
        data_bytes = None
        headers = dict(hook.headers or {})
        if hook.body_json is not None:
            data_bytes = json.dumps(hook.body_json).encode()
            headers.setdefault("Content-Type", "application/json")

        attempt = 0
        while True:
            try:
                req = urllib.request.Request(hook.url, data=data_bytes, headers=headers)
                with urllib.request.urlopen(req, timeout=hook.timeout_sec):
                    pass
                return
            except urllib.error.URLError as exc:  # pragma: no cover - network failures
                if attempt < hook.retries:
                    attempt += 1
                    time.sleep(min(2 ** attempt, 60))
                    continue
                if not hook.ignore_errors:
                    raise exc
                return
