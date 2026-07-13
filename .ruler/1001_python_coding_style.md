# Python coding style

## Naming

- Name functions/methods with a verb+object (e.g. `load_segments`, `save_preds`); avoid vague adjectives like `safe` or `enhanced`.

## Function arguments

- Don't hardcode project-specific values (label strings, tag names, sender/role identifiers like `"SENDER"`, `"ann"`, `"sdr guest"`) inside generic functions. Pass them in as arguments — keep the function a generic mechanism, let the caller supply its vocabulary.
- Expose such project-dependent values as **required parameters** (no defaults), so every call site states them explicitly. A default that only makes sense for one project is hidden coupling: it makes the function look generic while silently serving one corpus.
  ```python
  def find_text_ids_with_label(project, db, *, tag="SENDER", role="ann", label="sdr guest"): ...  # bad: looks generic, isn't
  def find_text_ids_with_label(project, tag, role, label, db): ...                                # good: caller passes its own
  ```

## Layout

- Write one-liners with `:` or ternary expressions: `if x: y()` or `z = a if cond else b`.
- Define short functions in one line: `def f(): return x`.
- Align similar logic to emphasize structure:
  ```python
  if cond: x = f(a, b)  # why this branch
  else:    x = f(b, a)
  ```
- Use tuple unpacking for member assignment: `self.x, self.y = x, y`.
- Import multiple modules per line: `import os, sys`.
- Use spacing to mirror math or domain conventions: `x = a*b + c`.
- No trailing whitespace.

## Code style

- No unnecessary comments; fit everything in one line when possible.
- Place short `#` comments at end of statement or immediately after a parameter.
- Use backticks for parameter names in docstrings.
- Use type hints for all functions. Prefer PEP 585 built-in generics: `dict[str, Any]` not `Dict[str, Any]` (import `Any` from `typing`; lowercase `any` is a builtin function, not a type).
- Reserve `try/except` for unstable external interactions (network, subprocess, filesystem). Let internal errors propagate.

## Other principles

- Use `fastcore.parallel.parallel()` for concurrent operations.
- On inconsistency or bug: find the root cause and communicate it. Patching symptoms is not acceptable.
