import pytest

import llmfix_linux as m


def test_llm_returns_model_output_and_expands_command_in_text_mode(mock_completion):
    # Given a fake gateway that echoes a fixed answer
    calls = mock_completion(return_text="FIXED")

    # When we run a text-mode request containing a command token
    result = m.llm("please //CC this line")

    # Then the model output is returned and the token was expanded (not sent raw)
    assert result == "FIXED"
    sent = calls[0]["messages"][0]["content"]
    assert isinstance(sent, str)
    assert "edit to be clear and concise" in sent
    assert "//CC" not in sent


def test_llm_routes_to_given_model(mock_completion):
    # Given a fake gateway
    calls = mock_completion(return_text="ok")

    # When we call llm with an explicit model override
    m.llm("x", "claude-haiku")

    # Then the completion is routed to that model's gateway route
    assert calls[0]["model"] == "openai/claude-haiku"


def test_llm_disables_retries_and_targets_the_gateway(mock_completion):
    # Given a fake gateway
    calls = mock_completion(return_text="ok")

    # When we run any request
    m.llm("hello")

    # Then retries are disabled and the request targets the configured gateway
    kw = calls[0]
    assert kw["num_retries"] == 0
    assert kw["max_retries"] == 0
    assert kw["api_base"] == m.GATEWAY_BASE
    assert kw["model"].startswith("openai/")


def test_llm_attaches_screenshot_when_ss_token_present(monkeypatch, mock_completion, make_img):
    # Given screenshot capture is stubbed to a small image
    monkeypatch.setattr(m, "capture_screen", lambda: make_img(8, 8))
    calls = mock_completion(return_text="described")

    # When we run a request containing the //SS token
    m.llm("summarise //SS please")

    # Then the message content is multimodal with an inline image data URI
    content = calls[0]["messages"][0]["content"]
    assert isinstance(content, list)
    assert content[1]["type"] == "image_url"
    assert content[1]["image_url"]["url"].startswith("data:image/png;base64,")


def test_llm_reraises_when_gateway_call_fails(mock_completion, caplog):
    # Given a gateway that raises a connection error
    mock_completion(raises=RuntimeError("Connection error"))

    # When we run a request
    # Then the error propagates and the ai-gateway hint is logged
    with pytest.raises(RuntimeError):
        m.llm("anything")
    assert any("Is the ai-gateway up" in r.message for r in caplog.records)
