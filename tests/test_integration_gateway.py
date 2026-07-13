import time

import pytest

import llmfix_linux as m

DEAD_GATEWAY = "http://127.0.0.1:54321/v1"  # a closed local port => connection refused


def test_llm_raises_fast_against_a_dead_gateway(monkeypatch):
    # Given the real litellm path pointed at a closed local port
    monkeypatch.setattr(m, "GATEWAY_BASE", DEAD_GATEWAY)

    # When we make a real request that cannot connect
    start = time.monotonic()
    with pytest.raises(Exception):
        m.llm("hello")
    elapsed = time.monotonic() - start

    # Then it fails quickly because retries are disabled (a retrying client took ~2s+ before the fix)
    assert elapsed < 1.5
