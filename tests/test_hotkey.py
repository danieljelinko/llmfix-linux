import pytest

import llmfix_linux as m


class ImmediateThread:
    "Stand-in for threading.Thread that runs the target synchronously on start()."
    def __init__(self, target=None, daemon=None, **kw): self._target = target
    def start(self):
        if self._target: self._target()


@pytest.fixture(autouse=True)
def run_threads_synchronously(monkeypatch):
    "Make callback/cleanup threads run inline so triggers are observable within the test."
    monkeypatch.setattr(m.threading, "Thread", ImmediateThread)


class CharKey:
    "A hashable stand-in for a pynput character key (SimpleNamespace defines __eq__, so it isn't hashable)."
    def __init__(self, c: str): self.char = c

def char_key(c: str) -> CharKey:
    return CharKey(c)


def test_hotkey_fires_callback_on_ctrl_alt_j():
    # Given a listener wired to a counting callback
    hits = []
    hk = m.HotkeyListener(lambda: hits.append(1))

    # When Ctrl, Alt, then 'j' are pressed
    hk.on_press(m.Key.ctrl)
    hk.on_press(m.Key.alt)
    hk.on_press(char_key("j"))

    # Then the callback fires once
    assert hits == [1]


def test_hotkey_fires_callback_on_caps_then_a():
    # Given a listener with the Caps+A trigger enabled
    hits = []
    hk = m.HotkeyListener(lambda: hits.append(1), enable_caps_a=True)

    # When CapsLock is pressed and then 'a' within the window
    hk.on_press(m.Key.caps_lock)
    hk.on_press(char_key("a"))

    # Then the callback fires
    assert hits == [1]


def test_hotkey_ignores_plain_a_without_caps():
    # Given a listener with Caps+A enabled but no Caps pressed
    hits = []
    hk = m.HotkeyListener(lambda: hits.append(1), enable_caps_a=True)

    # When only 'a' is pressed
    hk.on_press(char_key("a"))

    # Then the callback does not fire
    assert hits == []


def test_hotkey_does_not_fire_caps_a_when_disabled():
    # Given a listener with the Caps+A trigger disabled
    hits = []
    hk = m.HotkeyListener(lambda: hits.append(1), enable_caps_a=False)

    # When CapsLock then 'a' are pressed
    hk.on_press(m.Key.caps_lock)
    hk.on_press(char_key("a"))

    # Then the callback does not fire
    assert hits == []


def test_hotkey_release_discards_tracked_key():
    # Given a listener tracking a held key
    hk = m.HotkeyListener(lambda: None)
    hk.on_press(m.Key.ctrl)
    assert m.Key.ctrl in hk.keys

    # When the key is released
    hk.on_release(m.Key.ctrl)

    # Then it is no longer tracked
    assert m.Key.ctrl not in hk.keys
