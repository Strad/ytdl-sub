from __future__ import annotations

from typing import Dict, List

from ytdl_sub.validators.strict_dict_validator import StrictDictValidator
from ytdl_sub.validators.validators import (
    BoolValidator,
    DictValidator,
    IntValidator,
    ListValidator,
    StringValidator,
)


class HookValidator(StrictDictValidator):
    """Validates a single hook definition."""

    _required_keys = {"type"}
    _optional_keys = {"timeout_sec", "ignore_errors"}
    _allow_extra_keys = True

    def __init__(self, name: str, value):
        super().__init__(name=name, value=value)
        self.type = self._validate_key("type", StringValidator).value
        self.timeout_sec = self._validate_key("timeout_sec", IntValidator, default=30).value
        self.ignore_errors = self._validate_key("ignore_errors", BoolValidator, default=True).value

    @property
    def dict(self) -> Dict:
        return {
            **self._dict,
            "type": self.type,
            "timeout_sec": self.timeout_sec,
            "ignore_errors": self.ignore_errors,
        }


class HookListValidator(ListValidator[HookValidator]):
    _inner_list_type = HookValidator

    @property
    def list_dict(self) -> List[Dict]:
        return [hook.dict for hook in self.list]


class HooksValidator(DictValidator):
    """Validates the hooks section mapping events to lists of hooks."""

    def __init__(self, name: str, value):
        super().__init__(name=name, value=value)
        self._hooks: Dict[str, HookListValidator] = {
            key: HookListValidator(name=f"{name}.{key}", value=val)
            for key, val in self._dict.items()
        }

    @property
    def dict(self) -> Dict[str, List[Dict]]:
        return {key: hook.list_dict for key, hook in self._hooks.items()}
