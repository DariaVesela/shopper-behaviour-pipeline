# Python Coding Standards

> Distilled from *Writing Professional Python: A Code Quality Guide for Energy Trading Developers* by Jordan Dimov (© 2026). This file is a condensed checklist of the guide's rules. Read the original for the full reasoning and worked examples.

**Guiding principle:** wrong-but-plausible output is worse than a crash. A crash stops the pipeline; a silently wrong number flows downstream before anyone notices. Every rule below serves that principle.

---

## 1. Tooling

| Tool | Purpose | Commands |
| --- | --- | --- |
| `ruff` | Linting, import sorting and formatting (replaces flake8, black, isort, pylint, pyupgrade) | `ruff check --fix .` · `ruff format .` |
| `uv` | Python versions, virtualenvs, dependencies (replaces pip, pip-tools, Poetry) | `uv init` · `uv add <pkg>` · `uv run <cmd>` |
| `pytest` | Test runner | `pytest` · `pytest -v` · `pytest tests/test_x.py` |

- Configure `ruff` in `pyproject.toml`.
- On Windows, develop in WSL. If you need `zoneinfo`, install `tzdata` from PyPI, not from Anaconda.

## 2. Project Structure

- **File and directory names use underscores, never spaces** (`price_simulator.py`). Legacy scripts and schedulers break on whitespace in paths.
- **File names must match their contents.** Rename a module when its scope grows beyond its name.
- **Every module has three sections only:** imports → definitions → `if __name__ == "__main__":` guard. No top-level executable code outside the guard; importing a module must never run anything.
- **Imports go at the top**, grouped as standard library / third-party / local. No wildcard imports. No imports scattered through the file.
- **No unused imports.**
- **No commented-out code.** Delete it; git has the history.
- **`.gitignore`** covers at least `.idea/`, `.vscode/`, `*.iml`, `__pycache__/`, `*.pyc` and `.env`. Put IDE files in a global gitignore (`~/.gitignore_global`) too.
- **Every repo has a README** with a one-line description, install/run instructions, example output and key design decisions.

## 3. Functions

- **One function, one responsibility.** If a function generates data, transforms it *and* writes it to disk, split it.
- **Prefer a dispatch dictionary over long `if/elif` chains** when choosing between interchangeable implementations.
- **DRY:** if you copy a block and change one value, that value should be a parameter.
- **Use every parameter you accept.** A parameter that's accepted but ignored (e.g. a bound that's hardcoded internally) is a broken contract.
- **Remove unused parameters.** They are part of the public interface.
- **Return values; don't print them.** `print()` belongs in `main()`. Use `logging` for diagnostic output.
- **Side effects are additional, never alternative.** A function that writes a file must still return its result:

  ```python
  if save_to_csv:
      df.to_csv(path)
  return df  # always
  ```

- **No global state.** Pass data in as arguments and return results. Use a class or dataclass when state genuinely needs sharing.
- **No mutable default arguments.** Use the `None` sentinel (ruff rule `B006`):

  ```python
  def record(item: dict, ledger: list | None = None) -> list:
      if ledger is None:
          ledger = []
      ledger.append(item)
      return ledger
  ```

- **Docstrings say what the function does and how to use it.** Let type hints document the parameters; skip Java-style parameter inventories.

## 4. Pythonic Idioms

| Instead of | Use |
| --- | --- |
| `for i in range(len(xs)): xs[i]` | `for x in xs:` |
| Manual index counter | `enumerate(xs)` |
| Parallel indexing of two lists | `zip(a, b)` |
| Simple append loop | List comprehension (keep a loop for multi-step logic or side effects) |
| `open()` … `close()` | `with open(...) as f:` |
| Looping over `.keys()` to find one key | `d.get(key)` / `key in d` |
| String concatenation with `str()` | f-strings |
| Nested `if/else` | Flat `if/elif/else` |
| `get_x()` / `set_x()` methods | Plain attributes; `@property` for computed or validated values |
| `line.split(",")` on CSVs | The `csv` module |

- **Don't shadow builtins** (`id`, `type`, `list`, `dict`, `input`, `iter`, `next`, `open`, `filter`, `map`). Use `_` for throwaway loop variables.

## 5. Data Modelling

- **Model domain entities as types, not plain dicts.** Dicts give no typo protection, are mutable by default and have no declared shape.
- **Default to `@dataclass(frozen=True, slots=True)`** for records that shouldn't change after creation. To change one, create a modified copy with `dataclasses.replace()`; never mutate in place.
- **Use `StrEnum` (3.11+) for constrained string values** rather than repeating `if x not in [...]` validation. Members compare equal to plain strings.
- **Use domain vocabulary in interfaces** (`granularity="half-hourly"`, not `granularity="30"`).
- **Don't merge genuinely different domain concepts into one abstraction.** Remove *structural* duplication, but keep *domain* distinctions separate.

## 6. Testing

- **Put tests in `tests/`, in files named `test_*.py`**, so a bare `pytest` finds them.
- **Test core logic, not CLI or printed output.** The CLI is a thin adapter over the logic.
- **Tests must be independent of execution order.** Use fixtures with setup and teardown; needing an ordering plugin means tests share state.
- **Make outputs idempotent.** Prefer *generate once → persist → serve* over regenerating on each request.
- **Skipping tests is a deliberate, stated trade-off**, never an omission. Prototypes tend to become production.

## 7. Performance & Numerics

- **Know overhead vs throughput.** Vectorized libraries (NumPy) carry fixed setup costs; for small inputs, plain Python can be faster. Measure before choosing.
- **Measure simply:** `time.perf_counter()` for ad-hoc timing, `timeit` when you need repetition and warm-up. Don't build benchmarking infrastructure before you need it.
- **Model noise and volatility multiplicatively when they scale with level** (percentage moves, not fixed absolute offsets).

## 8. Judgement: Avoid Accidental Complexity

Distinguish *essential* complexity, which is inherent to the problem, from *accidental* complexity, which comes from your implementation choices (Moseley & Marks, *Out of the Tar Pit*, 2006). Keep the accidental kind to a minimum.

- **Build the simplest working version first**, then add edge cases incrementally.
- **No premature abstraction.** Follow the rule of three: inline it once, write a function the second time, consider an abstraction at three.
  - A small number of strategies → a dictionary, not dynamic loading.
  - A handful of constants → `constants.py`, not a YAML config.
- **No reflexive defensive code.** Before adding a check or `try/except`, ask: *what specific failure is this preventing?*
  - **Be defensive at system boundaries:** user input, external APIs and services, file I/O, untrusted data.
  - **Don't be defensive** between functions you control, after a guarantee already holds, "just in case", or where the runtime or type system already catches the problem.
- **Never swallow broad exceptions silently.** A caught-and-ignored bug produces exactly the wrong-but-plausible output this document exists to prevent.

---

## Review Checklist

- [ ] `ruff check` and `ruff format` are clean
- [ ] No top-level code outside the `__main__` guard
- [ ] Imports at the top, grouped, none unused
- [ ] No commented-out code
- [ ] Each function does one thing, returns its result and uses every parameter
- [ ] No mutable defaults, no globals, no shadowed builtins
- [ ] Domain records are typed (frozen dataclasses / StrEnums), not loose dicts
- [ ] Tests live in `tests/`, cover logic, and are order-independent
- [ ] Every `try/except` names the specific failure it handles
- [ ] No abstraction with fewer than three users