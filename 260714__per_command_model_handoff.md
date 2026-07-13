# Handoff — per-command model selection for llmfix-linux

> Task doc for a fresh Claude Code session. Read this top-to-bottom, then follow
> the plan. Style/flow reference: the sibling `archive/260713__notify_verbose_handoff.md`
> (same repo, same TDD discipline).

---

## LAUNCH PROMPT (paste this into the new session, run from `~/Work/tools/llmfix-linux`)

```
You are working in ~/Work/tools/llmfix-linux (a hotkey-driven LLM text fixer).

Goal: let each `//` command pick its own gateway model, so cheap edits don't
burn a premium model — e.g. spellcheck (//C, //DOH) on claude-haiku, heavier
rewrites stay on claude-sonnet.

First read, in order:
  1. ./260714__per_command_model_handoff.md   (the full plan — follow it)
  2. ./CLAUDE.md                               (repo rules: TDD, uv, surgical changes)
  3. ./llmfix_linux.py                          (load_commands, CODES, matched_commands, llm, fix)
  4. ./commands.toml                            (the [commands] table you'll extend)

Then implement it with red/green TDD (the repo has a pytest suite —
`uv run pytest -q`, currently 52 tests). Mock the litellm.completion and
notify/subprocess boundaries as the existing fixtures already do. When green,
verify manually against the live ai-gateway, then commit on a branch
`feat/per-command-model`, push to origin (danieljelinko fork), open a PR and
squash-merge — same flow as the last two changes on this repo.
```

---

## What the user asked for

Each `//` command should be able to invoke a **specific gateway model**. Spellcheck
and typo-fix commands don't need `claude-sonnet` — `claude-haiku` is cheaper and
plenty. Rewrites/transformations stay on the default. Commands with no pinned
model fall back to `LLMFIX_MODEL` (today's global default, `claude-sonnet`).

**Three design decisions already made (do not re-litigate):**
1. **Schema — inline table per command.** A `[commands]` value may be a plain
   string (instruction only, as today) **or** a table `{ instruction = "...",
   model = "..." }`. Fully backward-compatible.
2. **Ship a sensible starter map** (below) — the user tweaks from there.
3. **Longest match wins** — when several commands match one text, the model is
   the pinned model of the **single longest** matched command, else the default.

## The model layer — how the gateway resolves aliases

llmfix sends `openai/<alias>` to LiteLLM (`http://127.0.0.1:4001/v1`), which maps
the alias to a real upstream id and forwards to CLIProxyAPI (`:8317`). The alias
map is `~/Work/ai-gateway/litellm-config.yaml`. Aliases currently exposed:

| alias | resolves to | note |
|---|---|---|
| `claude-sonnet` | `claude-sonnet-5` | llmfix default |
| `claude-opus` | `claude-opus-4-8` | |
| `claude-fable` | `claude-fable-5` | top-tier |
| `claude-haiku` | `claude-haiku-4-5-20251001` | fast/cheap |
| `gpt-codex` | `gpt-5-codex` | |
| `gemini` | `gemini-3-pro-preview` | |

Check live: `curl -s http://127.0.0.1:4001/v1/models`. The `/chat/completions`
response echoes the **alias**, not the resolved id — read the config to see the
real model.

## Current llmfix state (what you're changing)

- `commands.toml` holds `[commands]` as `"//X" = "instruction string"` — loaded
  over `DEFAULT_CODES` by `load_commands(path, defaults)`, which returns
  `{**defaults, **data["commands"]}`. Result is assigned to module-level `CODES`.
- `CODES: dict[str, str]` (command → instruction) is consumed by `replace_all`,
  `matched_commands`, and `print_codes`. **Keep this shape** so those and their
  tests stay green — normalize table specs down to their instruction string.
- `matched_commands(inp, CODES)` returns the matched command keys **longest
  first** (already used by `fix()` for the notify/log line).
- `llm(inp)` builds the prompt and calls `completion(model=gateway_model(MODEL), …)`
  — hardcodes the global `MODEL`. `//SS` in the text triggers screenshot/vision mode.
- `fix()` (in `ToolbarApp`) reads the selection, computes `cmds`, notifies, logs,
  calls `llm(inp)`, pastes.
- `MODEL = os.environ.get("LLMFIX_MODEL", "claude-sonnet")`.

## Proposed starter map (Cycle 6 — user tweaks after)

Only **pin** the cheap ones and the vision one; everything unpinned falls back to
the sonnet default, so the diff to `commands.toml` stays small:

| command | model | why |
|---|---|---|
| `//C` (spelling/grammar/punctuation) | `claude-haiku` | mechanical correction |
| `//DOH` (typos) | `claude-haiku` | mechanical correction |
| `//HH` (Hungarian typos) | `claude-haiku` | mechanical — **verify haiku's Hungarian quality** |
| `//SS` (screenshot) | `claude-sonnet` | must be **vision-capable** |
| all others (`//CC`, `//FR`, `//FO`, `//BLUF`, `//MD`, `//FS`, `//PC`) | *(unpinned → default)* | rewrites where quality matters |

Example `commands.toml` after:
```toml
[commands]
"//C"   = { instruction = "// Correct the spelling and grammar and punctuation, ...", model = "claude-haiku" }
"//CC"  = "// edit to be clear and concise, prefer to use bulletpoints ..."   # unchanged string → default
"//DOH" = { instruction = "// edit to fix typo's and spelling mistakes", model = "claude-haiku" }
"//SS"  = { instruction = "", model = "claude-sonnet" }
```

## Plan (red/green TDD — one cycle at a time)

**1. Spec accessors — read instruction/model from a str-or-table value**
```python
def command_instruction(value: str | dict[str, Any]) -> str:
    "Instruction text of a command spec: the string itself, or its `instruction` field."
    return value if isinstance(value, str) else value.get("instruction", "")

def command_model(value: str | dict[str, Any]) -> str | None:
    "Model alias a command spec pins, or None for a bare string / table without `model`."
    return None if isinstance(value, str) else value.get("model")
```
Red: `test_command_instruction_returns_string_as_is`,
`test_command_instruction_reads_field_when_table`,
`test_command_model_none_when_string`, `test_command_model_reads_field_when_table`.

**2. Loaders — raw specs, back-compat instruction map, model map**
```python
def load_command_specs(path, defaults) -> dict[str, str | dict[str, Any]]:
    "Today's load_commands body: merge [commands] over defaults; values may be string or table."
    # (unchanged parse + malformed-fallback logic)

def load_commands(path, defaults) -> dict[str, str]:
    "Command → instruction (table specs reduced to their instruction). Back-compat shape."
    return {c: command_instruction(v) for c, v in load_command_specs(path, defaults).items()}

def load_models(path, defaults) -> dict[str, str]:
    "Command → pinned model alias, only for commands that pin one."
    return {c: mdl for c, v in load_command_specs(path, defaults).items() if (mdl := command_model(v))}
```
Module level (parse once): `SPECS = load_command_specs(commands_path(), DEFAULT_CODES)`;
`CODES = {c: command_instruction(v) for c, v in SPECS.items()}`;
`MODELS = {c: m2 for c, v in SPECS.items() if (m2 := command_model(v))}`.
Red: a table-valued toml yields the instruction in `load_commands` **and** the
model in `load_models`; the existing `test_load_commands_*` stay green (string in
→ string out). Confirm `test_shipped_commands_toml_loads_and_keeps_screenshot_sentinel`
still passes once `//SS` becomes a table (normalizes back to `""`).

**3. `model_for` — longest match wins**
```python
def model_for(inp: str, codes: dict[str, str], models: dict[str, str], default: str) -> str:
    "Model for `inp`: the pinned model of the longest matched command, else `default`."
    matched = matched_commands(inp, codes)
    return models.get(matched[0], default) if matched else default
```
Red: `test_model_for_uses_longest_matched_commands_pin`,
`test_model_for_falls_back_to_default_when_longest_unpinned` (**the //CC-vs-//C
case**: `//C` pinned to haiku must NOT leak into a `//CC` request — the longer
`//CC` wins and, if unpinned, yields the default), `test_model_for_default_when_no_command`.

**4. `llm(inp, model=…)` — route to a given model**
Add a `model: str = MODEL` param; replace the three `MODEL` refs (the two
`Using {MODEL}` logs and `gateway_model(MODEL)`) with `model`.
Red: `test_llm_routes_to_given_model` — `mock_completion` records kwargs; assert
`calls[0]["model"] == "openai/claude-haiku"` when `llm("x", "claude-haiku")`.
Keep `test_llm_*` green (default arg preserves today's behaviour).

**5. Wire into `fix()`**
```python
cmds  = matched_commands(inp, CODES)
model = model_for(inp, CODES, MODELS, MODEL)
notify("Processing…", f"{', '.join(cmds) or 'no command'} [{model}]: {inp[:80]}")
log.info("Processing text %r with command(s) %s using model %s", inp[:200], cmds or ["(none)"], model)
try:
    res = llm(inp, model)
```
Red: `test_fix_routes_command_to_its_pinned_model` (seed a pinned command via a
`monkeypatch`/fixture over `m.MODELS`+`m.CODES`; assert the recorded completion
`model` is the pinned alias) and `test_fix_uses_default_model_when_command_unpinned`.
Use the existing `clipboard`, `mock_completion`, `mock_notify` fixtures.

**6. Apply the starter map to `commands.toml` + verify**
Edit `commands.toml` per the table above. `uv run pytest -q` green;
`uv run llmfix_linux.py --list` still renders (screenshot help for `//SS`).

**7. Manual verify (ai-gateway up: `cd ../../ai-gateway && just up`)**
Drive the real `fix()` against the live gateway with an in-memory clipboard and
stubbed keyboard (see `archive/260713__notify_verbose_handoff.md` step 4 / the
scratchpad `manual_verify.py` pattern). Select `some typo //DOH`, expect the log
`… using model claude-haiku` and the `[claude-haiku]` tag in the toast; select
`make this concise //CC`, expect `… using model claude-sonnet`.

## Success criteria

- [ ] `command_instruction` / `command_model` / `load_command_specs` / `load_models`
      / `model_for` implemented and unit-tested.
- [ ] A table-valued command routes to its pinned model; unpinned falls back to
      `LLMFIX_MODEL`; longest-match wins (no `//C`→`//CC` leak).
- [ ] `commands.toml` carries the starter map; `CODES`-based consumers unchanged.
- [ ] Full suite green, order-independent (`pytest-randomly` installed).
- [ ] Manually verified against the live gateway (right model per command).

## Gotchas / non-obvious

- **`//C` is a substring of `//CC`** — `matched_commands` returns both for a
  `//CC` text. `model_for` must key off the **single longest** matched command,
  not the first pinned one, or a `//C` haiku pin poisons every `//CC` request.
  (The instruction expansion in `replace_all` is already safe via longest-first.)
- **Keep `CODES: dict[str,str]`.** `replace_all`, `matched_commands`, `print_codes`
  and their tests assume string values — normalize table specs in the loader.
- **`//SS` must resolve to a vision-capable model** (sonnet/opus/gemini, not
  haiku) — the screenshot branch of `llm()` sends an image. The starter map pins
  it to `claude-sonnet`; document that constraint next to the command.
- **`test_shipped_commands_toml_loads_and_keeps_screenshot_sentinel`** asserts
  `result["//SS"] == ""`; once `//SS` is a table, the loader's instruction
  normalization keeps that true. It also uses `.startswith(...)` for `//CC` (the
  wording is user-editable — don't re-tighten it to an exact match).
- **Aliases drift.** Real ids track the upstream CLI catalogs; the valid alias
  list is whatever `curl :4001/v1/models` returns. Don't invent aliases.
- Tests **require an X display** (pynput `Controller()` at import) and the manual
  verify needs the ai-gateway up on `:4001`.
- Branch `feat/per-command-model`; imperative commit subject ≤72 chars; end body
  with `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`.
  Push to `origin` (danieljelinko fork); `gh pr create --repo
  danieljelinko/llmfix-linux --base main`; then `gh pr merge --squash --delete-branch`.
- Archive this handoff (`git mv` to `archive/`) once the work is merged.
