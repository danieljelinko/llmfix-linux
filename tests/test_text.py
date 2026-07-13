import llmfix_linux as m


def test_gateway_model_adds_openai_prefix_when_missing():
    # Given a bare gateway model id
    model_id = "claude-sonnet"

    # When we build its litellm route
    route = m.gateway_model(model_id)

    # Then it is prefixed with the OpenAI-compatible provider
    assert route == "openai/claude-sonnet"


def test_gateway_model_keeps_id_when_already_prefixed():
    # Given a model id that already carries the openai/ prefix
    model_id = "openai/gpt-4o"

    # When we build its litellm route
    route = m.gateway_model(model_id)

    # Then it is returned unchanged
    assert route == "openai/gpt-4o"


def test_replace_all_substitutes_every_token_when_present():
    # Given text containing two known command tokens
    text = "start //C middle //CC end"

    # When we expand them
    result = m.replace_all(text, {"//C": "FIX-C", "//CC": "FIX-CC"})

    # Then both tokens are replaced by their instructions
    assert result == "start FIX-C middle FIX-CC end"


def test_replace_all_prefers_longer_token_when_prefix_collides():
    # Given a shorter token that is a prefix of a longer one (//C vs //CC)
    text = "expand //CC here"
    reps = {"//C": "SHORT", "//CC": "LONG"}

    # When we expand (dict order lists the shorter key first)
    result = m.replace_all(text, reps)

    # Then the longer token wins and the shorter one does not shadow it
    assert result == "expand LONG here"


def test_replace_all_leaves_text_untouched_when_no_token_matches():
    # Given text with no command tokens
    text = "plain text, nothing to expand"

    # When we run replacement with a command map
    result = m.replace_all(text, {"//C": "FIX-C"})

    # Then the text is unchanged
    assert result == "plain text, nothing to expand"
