import logging

import llmfix_linux as m


def make_app() -> m.ToolbarApp:
    "A tray-less, caps-A-less app instance for exercising fix() in isolation."
    return m.ToolbarApp(use_tray=False, enable_caps_a=False)


def test_fix_pastes_model_output_then_restores_original_clipboard(clipboard, mock_completion):
    # Given a selection on the clipboard and a gateway that returns fixed text
    clipboard["value"] = "please //CC fix"
    calls = mock_completion(return_text="FIXED")

    # When we run the fix flow
    make_app().fix()

    # Then the model output was placed on the clipboard, then the original restored
    assert "FIXED" in clipboard["writes"]
    assert clipboard["writes"][-1] == "please //CC fix"
    assert clipboard["value"] == "please //CC fix"
    assert len(calls) == 1


def test_fix_does_nothing_when_selection_is_empty(clipboard, mock_completion):
    # Given an empty clipboard/selection
    clipboard["value"] = ""
    calls = mock_completion(return_text="FIXED")

    # When we run the fix flow
    make_app().fix()

    # Then no LLM call is made and the clipboard stays empty
    assert calls == []
    assert clipboard["value"] == ""


def test_fix_restores_clipboard_when_llm_fails(clipboard, mock_completion):
    # Given a selection and a gateway that raises
    clipboard["value"] = "text //CC"
    mock_completion(raises=RuntimeError("Connection error"))

    # When we run the fix flow
    make_app().fix()  # must not raise

    # Then the original selection is left intact on the clipboard
    assert clipboard["value"] == "text //CC"


def test_fix_notifies_and_logs_processing_then_pasted(clipboard, mock_completion, mock_notify, caplog):
    # Given a selection carrying a command and a gateway that returns fixed text
    clipboard["value"] = "please //CC fix"
    mock_completion(return_text="FIXED")

    # When we run the fix flow at INFO level
    with caplog.at_level(logging.INFO):
        make_app().fix()

    # Then a start and a done toast fired, and the input + result were logged at INFO
    titles = [c.args[0] for c in mock_notify.call_args_list]
    assert "Processing…" in titles
    assert "Pasted ✓" in titles
    assert any("Processing text" in r.message for r in caplog.records)
    assert any("Pasted result" in r.message for r in caplog.records)


def test_fix_notifies_on_error(clipboard, mock_completion, mock_notify):
    # Given a selection and a gateway that raises
    clipboard["value"] = "text //CC"
    mock_completion(raises=RuntimeError("boom"))

    # When we run the fix flow (must not raise)
    make_app().fix()

    # Then an error toast fired and the original clipboard is left intact
    titles = [c.args[0] for c in mock_notify.call_args_list]
    assert "LLMFix error" in titles
    assert clipboard["value"] == "text //CC"
