# Handoff — add processing notifications + verbose logging to llmfix-linux

> Task doc for a fresh Claude Code session. Read this top-to-bottom, then follow
> the plan. Reference implementation to copy the style from: **tigris-whisper**.

---

## LAUNCH PROMPT (paste this into the new session, run from `~/Work/tools/llmfix-linux`)

```
You are working in ~/Work/tools/llmfix-linux (a hotkey-driven LLM text fixer).

Goal: when I fire the hotkey and text is sent for processing, give me visible
feedback that something is happening, and make the logging verbose enough that
the log shows "processing text X with command Y" and the pasted return value.

First read, in order:
  1. ./260713__notify_verbose_handoff.md   (the full plan — follow it)
  2. ./CLAUDE.md                            (repo rules: TDD, uv, surgical changes)
  3. ~/Work/tools/tigris-whisper/src/whisper_hotkey_linux.py  (notify() reference, lines 32-40, 54, 65, 80, 96)

Then implement it with red/green TDD (the repo already has a pytest suite —
`uv run pytest -q`, currently 45 tests). Mock the notify-send subprocess
boundary in tests so no real desktop popups fire. When green, verify manually
by running the app, then commit on a branch `feat/notify-verbose`, push to
origin (my danieljelinko fork), open a PR and merge it — same flow as the last
two changes on this repo.
```

---

## What the user asked for

1. **Validation feedback**: while text is being sent to the LLM, show the user
   that *something is happening* (a desktop notification, like tigris-whisper).
2. **Verbose log**: log "I am processing text *X* with command *Y*, pasting
   return value *Z*". Today most of `fix()`/`llm()` logs at DEBUG, so at the
   default INFO level the user sees almost nothing between "Fix called" and
   "Fix done".
3. Make it more verbose generally.

## Reference implementation — tigris-whisper

`~/Work/tools/tigris-whisper/src/whisper_hotkey_linux.py`:

- **`notify(title, body="", silent=False)`** (lines 32-40): shells out to
  `notify-send "<AppName>" "<title>\n<body>"`; adds
  `--hint=boolean:suppress-sound:true` when `silent`; wraps in
  `try/except FileNotFoundError` so a missing binary is a no-op.
- Called at each stage: `notify("Listening…")` on start (54),
  `notify("Transcribing…", silent=True)` mid (65), `notify("Done", text[:197]+"…", silent=True)`
  at the end (96), `notify("Transcription error", str(e))` on failure (80).
- Logs the payload and result at **INFO** (`log.info("Transcript copied: %s", text)`).

`notify-send` is installed here: `/usr/bin/notify-send` (v0.8.3).

## Current llmfix state (what you're changing)

- Single script `llmfix_linux.py`. Commands live in `commands.toml`
  (loaded over `DEFAULT_CODES`). Entry hotkey → `ToolbarApp.fix()`.
- `fix()` (around line 338): saves clipboard → `copy_selection()` (Ctrl+C) →
  reads selection → `llm(inp)` → copies result → `paste_clipboard()` (Ctrl+V) →
  restores clipboard. **Almost every log line here is `log.debug`.**
- `llm(inp)` builds the prompt via `replace_all(inp, CODES)`, routes through the
  local ai-gateway; `//SS` triggers screenshot mode.
- Logging is set in `setup_logging()`: format
  `%(asctime)s - %(levelname)s - %(message)s`, default level **INFO**.
- `subprocess` is **not yet imported**; add it.
- Test suite exists: `tests/` (10 files, 45 tests), run `uv run pytest -q`.
  `tests/conftest.py` has an autouse `safe_hardware` fixture that mocks
  `kb`/`mouse` and no-ops `time.sleep`, plus `mock_completion` and `clipboard`
  factory fixtures.

## Plan (red/green TDD — one cycle at a time)

**1. `matched_commands(inp, codes)` — pure helper (which commands are in the text)**
- Red: `test_matched_commands_returns_present_keys_longest_first`,
  `test_matched_commands_empty_when_none_present`.
- Green:
  ```python
  def matched_commands(inp: str, codes: dict[str, str]) -> list[str]:
      "The // command keys present in `inp`, longest first (matches replace_all precedence)."
      return sorted((c for c in codes if c in inp), key=len, reverse=True)
  ```

**2. `notify(title, body, silent)` — desktop notification (copy tigris)**
- Red: `test_notify_invokes_notify_send_with_title`,
  `test_notify_silent_adds_suppress_sound_hint`,
  `test_notify_swallows_missing_binary` (patch `m.subprocess.run` to raise
  `FileNotFoundError` → no exception). Assert on the mocked `subprocess.run`.
- Green: mirror tigris's helper; title app-name `"LLMFix"`; `import subprocess`.

**3. Wire verbose logging + notifications into `fix()`**
- After reading a non-empty `inp`:
  - `cmds = matched_commands(inp, CODES)`
  - `notify("Processing…", f"{', '.join(cmds) or 'no command'}: {inp[:80]}")`
  - `log.info("Processing text %r with command(s) %s", inp[:200], cmds or ["(none)"])`
- After the paste:
  - `log.info("Pasted result %r", res[:200])`
  - `notify("Pasted ✓", res[:180] + ("…" if len(res) > 180 else ""), silent=True)`
- Error path: add `notify("LLMFix error", str(e))` (keep existing `log.error`).
- Red first: extend `tests/test_fix.py` with
  `test_fix_notifies_and_logs_processing_then_pasted` (patch `m.notify` with a
  MagicMock via a fixture; assert it's called for start + done; assert caplog
  has "Processing text" and "Pasted result") and
  `test_fix_notifies_on_error`.
- **conftest**: add `monkeypatch.setattr(m.subprocess, "run", MagicMock())` to
  the autouse fixture so no real popups fire during the whole suite; add a
  `mock_notify` fixture that patches `m.notify` for the fix() assertions.

**4. Verify**
- `uv run pytest -q` → all green (45 + new).
- Manual: `uv run llmfix_linux.py`, select `some text //CC`, press Ctrl+Alt+J.
  Expect a "Processing…" toast then "Pasted ✓", and stdout showing
  `INFO ... Processing text '...' with command(s) ['//CC']` and
  `INFO ... Pasted result '...'`. (ai-gateway must be up: `cd ../../ai-gateway && just up`.)
- notify-send absent → still works (debug log only), no crash.

## Success criteria

- [ ] `matched_commands` + `notify` implemented and unit-tested.
- [ ] `fix()` emits a start + end notification and INFO logs of the input text,
      matched command(s), and pasted result.
- [ ] Full suite green, order-independent (`pytest-randomly` is installed).
- [ ] No real desktop notifications during tests (subprocess boundary mocked).
- [ ] Manually verified with the live gateway.

## Gotchas / non-obvious

- Tests **require an X display** — importing the module builds pynput
  `Controller()` at module load. Fine on this desktop; would fail headless.
- Put the verbose lines at **INFO** (not DEBUG) — the default level; that's the
  whole point (the user sees them without `--log-level DEBUG`).
- **Truncate** text/result (~80–200 chars) in both logs and notifications;
  clipboards can be huge.
- Keep it surgical (CLAUDE.md rule): one `notify()` helper + one
  `matched_commands()` + edits inside `fix()`. Don't refactor `llm()`.
- Reserve `try/except` for the subprocess boundary only (matches CLAUDE style).
- Branch `feat/notify-verbose`; commit subject imperative ≤72 chars; end body
  with `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`. Push to
  `origin` (danieljelinko fork), `gh pr create --repo danieljelinko/llmfix-linux
  --base main`, then `gh pr merge --squash --delete-branch`.
- Delete this handoff file (or `git mv` to `archive/`) once the work is merged.
