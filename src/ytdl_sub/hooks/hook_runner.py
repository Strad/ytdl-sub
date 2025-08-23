"""Minimal hook runner implementation for tests."""
from typing import Any, Dict


class HookRunner:
    """Placeholder hook runner.

    The real implementation is responsible for executing user-defined hooks. In the
    test environment, this stub provides the expected interface so callers can
    invoke :func:`run` without failing.
    """

    @staticmethod
    def run(hook_name: str, context: Dict[str, Any]):  # pragma: no cover - placeholder
        """Execute a hook.

        Parameters
        ----------
        hook_name:
            Name of the hook to execute.
        context:
            Context passed to the hook.
        """
        _ = hook_name, context
