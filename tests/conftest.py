import types
from typing import Any, Callable
from unittest.mock import MagicMock

import pytest
from PIL import Image

import llmfix_linux as m


@pytest.fixture(autouse=True)
def safe_hardware(monkeypatch):
    "Replace real keyboard/mouse with mocks and no-op every sleep, so no test emits a real keystroke or stalls."
    monkeypatch.setattr(m, "kb", MagicMock(name="kb"))
    monkeypatch.setattr(m, "mouse", MagicMock(name="mouse"))
    monkeypatch.setattr(m.time, "sleep", lambda *a, **k: None)


@pytest.fixture
def make_img() -> Callable[..., Image.Image]:
    "Factory: build a solid RGB test image of a given size."
    def _build(w: int = 10, h: int = 10, color: tuple[int, int, int] = (120, 30, 200)) -> Image.Image:
        return Image.new("RGB", (w, h), color)
    return _build


@pytest.fixture
def mock_completion(monkeypatch) -> Callable[..., list[dict[str, Any]]]:
    "Factory: install a fake litellm.completion; returns the list that records each call's kwargs."
    calls: list[dict[str, Any]] = []
    def _install(return_text: str = "OUTPUT", raises: Exception | None = None) -> list[dict[str, Any]]:
        def fake(*args, **kwargs):
            calls.append(kwargs)
            if raises is not None: raise raises
            msg = types.SimpleNamespace(content=return_text)
            return types.SimpleNamespace(choices=[types.SimpleNamespace(message=msg)])
        monkeypatch.setattr(m, "completion", fake)
        return calls
    return _install


@pytest.fixture
def clipboard(monkeypatch) -> dict[str, Any]:
    "In-memory clipboard replacing pyperclip; `value` is current content, `writes` records every copy()."
    state: dict[str, Any] = {"value": "", "writes": []}
    monkeypatch.setattr(m.pyperclip, "paste", lambda: state["value"])
    def _copy(v):
        state["value"] = v
        state["writes"].append(v)
    monkeypatch.setattr(m.pyperclip, "copy", _copy)
    return state
