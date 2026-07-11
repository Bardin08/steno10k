# M1·L — Ported Utility Library Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `steno10k/lib/` — a pure capability library (media, transcription, LLM, retry, docx, prompts) ported from `lecturemate10k` onto the F1 contracts, that the stage/CLI units will call.

**Architecture:** `lib` is a black-box capability layer with a one-way dependency: `lib → contracts` only (never `api`/`stages`). Some modules port near-intact (ffmpeg, retry, markdown→docx render), some are partial ports with rewritten surfaces (llm implements the F1 `LLMClient` protocol; bundle orchestration is decoupled), and the prompt content is written from scratch (English, domain-neutral). The LLM layer is provider-neutral (any OpenAI-compatible endpoint; standard `Retry-After` backoff, no vendor-specific code). Retry/timeout and Whisper decode knobs are hardcoded M1 constants, deferred to M2 config via an ADR.

**Tech Stack:** Python 3.12, `faster-whisper` (ctranslate2), `openai`, `httpx`, `python-docx`, `ffmpeg` (system binary), pytest, mypy (strict), ruff.

**Reference (parts bin):** `/Users/vladyslavbardin/Docs/Personal/lecturemate10k/src/audio_pipeline/`.

**Spec:** `docs/specs/2026-07-11-steno10k-m1-l-utility-library-design.md`.

---

## File Structure

Created under `backend/`:

- `src/steno10k/lib/__init__.py` — package marker.
- `src/steno10k/lib/retry.py` — pure backoff/`Retry-After` helpers (provider-neutral).
- `src/steno10k/lib/names.py` — `normalize_recording_name` (reuses `contracts.slug`).
- `src/steno10k/lib/ffmpeg.py` — chunk planning + ffmpeg/ffprobe subprocess I/O.
- `src/steno10k/lib/docx.py` — markdown→docx renderer + decoupled `build_bundle`.
- `src/steno10k/lib/prompts.py` — prompt registry: English domain-neutral defaults + override loader (F2 convention).
- `src/steno10k/lib/llm.py` — `OpenAICompatibleClient` implementing `contracts.llm.LLMClient`.
- `src/steno10k/lib/transcriber.py` — faster-whisper worker + `transcribe_chunks`.
- `tests/lib/test_*.py` — ported + new unit tests.
- `docs/adr/0001-defer-llm-and-whisper-config-knobs.md` — deferred-config decision record.
- `backend/pyproject.toml` — new runtime deps + mypy overrides (modified).

---

## Task 0: Branch, dependencies, package skeleton

**Files:**
- Modify: `backend/pyproject.toml`
- Create: `backend/src/steno10k/lib/__init__.py`
- Create: `backend/tests/lib/__init__.py`

- [ ] **Step 1: Create the feature branch**

This plan runs in the isolated worktree already on `docs/m1-pipeline-spec`. Start the implementation branch from the current `origin/main`:

```bash
cd /Users/vladyslavbardin/Docs/Personal/steno10k-m1
git fetch origin --quiet
git checkout -b feat/l-utility-library origin/main
```

- [ ] **Step 2: Add runtime dependencies + mypy overrides**

Edit `backend/pyproject.toml`. Replace the `dependencies` list and add mypy overrides. New `dependencies`:

```toml
dependencies = [
    "fastapi>=0.115",
    "uvicorn[standard]>=0.32",
    "pydantic>=2.9",
    "pyyaml>=6.0",
    "python-multipart>=0.0.9",
    "faster-whisper>=1.0",
    "openai>=1.50",
    "httpx>=0.27",
    "python-docx>=1.1",
]
```

Remove `httpx` from the `dev` group (now runtime). The `dev` group becomes:

```toml
dev = ["ruff>=0.7", "mypy>=1.13", "pytest>=8.3", "types-pyyaml"]
```

Append after the `[tool.mypy]` block (these third-party libs ship no/partial stubs; strict mypy needs the override):

```toml
[[tool.mypy.overrides]]
module = ["faster_whisper.*", "docx.*"]
ignore_missing_imports = true
```

- [ ] **Step 3: Create the package markers**

```bash
mkdir -p backend/src/steno10k/lib backend/tests/lib
printf '' > backend/src/steno10k/lib/__init__.py
printf '' > backend/tests/lib/__init__.py
```

- [ ] **Step 4: Sync the environment**

Run: `cd backend && uv sync`
Expected: resolves and installs `faster-whisper`, `openai`, `python-docx` (may take a minute — pulls `ctranslate2`).

- [ ] **Step 5: Commit**

```bash
git add backend/pyproject.toml backend/uv.lock backend/src/steno10k/lib/__init__.py backend/tests/lib/__init__.py
git commit -m "chore(lib): add media/LLM/docx runtime deps and lib package skeleton"
```

---

## Task 1: Import-boundary guard

Enforces the §1 rule: `lib` imports only from `contracts`/stdlib/third-party — never `api` or `stages`.

**Files:**
- Test: `backend/tests/lib/test_import_boundary.py`

- [ ] **Step 1: Write the failing test**

```python
from __future__ import annotations

import ast
from pathlib import Path

_LIB_DIR = Path(__file__).resolve().parents[2] / "src" / "steno10k" / "lib"
_FORBIDDEN = ("steno10k.api", "steno10k.stages")


def _imports(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.extend(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.append(node.module)
    return names


def test_lib_never_imports_api_or_stages():
    offenders: list[str] = []
    for py in _LIB_DIR.glob("*.py"):
        for mod in _imports(py):
            if any(mod == f or mod.startswith(f + ".") for f in _FORBIDDEN):
                offenders.append(f"{py.name} -> {mod}")
    assert offenders == [], f"lib must not import api/stages: {offenders}"
```

- [ ] **Step 2: Run test to verify it passes**

Run: `cd backend && uv run pytest tests/lib/test_import_boundary.py -v`
Expected: PASS (only `__init__.py` exists, no forbidden imports). This guard now protects every later task.

- [ ] **Step 3: Commit**

```bash
git add backend/tests/lib/test_import_boundary.py
git commit -m "test(lib): guard lib->api/stages import boundary"
```

---

## Task 2: `lib/retry.py` — provider-neutral backoff

Port near-intact, **minus** the reference's provider-specific `retry_delay` regex branch. `extract_retry_after_seconds` keeps only the standard HTTP `Retry-After` header path.

**Files:**
- Create: `backend/src/steno10k/lib/retry.py`
- Test: `backend/tests/lib/test_retry.py`

- [ ] **Step 1: Write the failing test**

```python
from __future__ import annotations

from steno10k.lib.retry import compute_backoff_wait, extract_retry_after_seconds


def _wait(attempt, is_rate_limit=False, server_hint=None):
    return compute_backoff_wait(
        attempt, initial=2.0, base=2.0, max_wait=60.0,
        rate_limit_floor=30.0, is_rate_limit=is_rate_limit, server_hint=server_hint,
    )


def test_backoff_grows_exponentially():
    assert _wait(1) == 2.0
    assert _wait(2) == 4.0
    assert _wait(3) == 8.0


def test_backoff_capped_at_max_wait():
    assert _wait(10) == 60.0


def test_rate_limit_uses_floor_when_backoff_is_smaller():
    assert _wait(1, is_rate_limit=True) == 30.0


def test_rate_limit_server_hint_wins_when_largest():
    assert _wait(1, is_rate_limit=True, server_hint=45.0) == 45.0


def test_non_rate_limit_ignores_floor_and_hint():
    assert _wait(1, is_rate_limit=False, server_hint=999.0) == 2.0


class _Resp:
    def __init__(self, headers):
        self.headers = headers


class _Err(Exception):
    def __init__(self, msg, headers=None):
        super().__init__(msg)
        self.response = _Resp(headers) if headers is not None else None


def test_extract_retry_after_from_header():
    assert extract_retry_after_seconds(_Err("boom", headers={"Retry-After": "12"})) == 12.0


def test_provider_specific_body_is_ignored():
    # Provider-neutral: a vendor-style "retry_delay { seconds: 42 }" body is NOT parsed.
    assert extract_retry_after_seconds(_Err("429 ... retry_delay { seconds: 42 } ...")) is None


def test_extract_retry_after_none_when_absent():
    assert extract_retry_after_seconds(_Err("plain error")) is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/lib/test_retry.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'steno10k.lib.retry'`.

- [ ] **Step 3: Write the implementation**

Create `backend/src/steno10k/lib/retry.py`:

```python
from __future__ import annotations


def extract_retry_after_seconds(err: Exception) -> float | None:
    """Best-effort read of a server-suggested retry delay from a rate-limit error.

    Provider-neutral: only the standard HTTP `Retry-After` response header is
    honored. Any OpenAI-compatible gateway returns it; no vendor-specific
    error-body parsing is done.
    """
    resp = getattr(err, "response", None)
    if resp is not None:
        headers = getattr(resp, "headers", None)
        if headers:
            ra = headers.get("retry-after") or headers.get("Retry-After")
            if ra:
                try:
                    return float(ra)
                except (TypeError, ValueError):
                    return None
    return None


def compute_backoff_wait(
    attempt: int,
    *,
    initial: float,
    base: float,
    max_wait: float,
    rate_limit_floor: float,
    is_rate_limit: bool,
    server_hint: float | None,
) -> float:
    """Backoff for a failed attempt (1-based).

    Non-rate-limit: exponential backoff capped at `max_wait`.
    Rate-limit: the larger of the backoff, the floor, and any server hint.
    """
    base_wait = min(max_wait, initial * (base ** (attempt - 1)))
    if not is_rate_limit:
        return base_wait
    return max(base_wait, rate_limit_floor, server_hint or 0.0)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && uv run pytest tests/lib/test_retry.py -v`
Expected: PASS (9 tests).

- [ ] **Step 5: Commit**

```bash
git add backend/src/steno10k/lib/retry.py backend/tests/lib/test_retry.py
git commit -m "feat(lib): provider-neutral retry/backoff helpers"
```

---

## Task 3: `lib/names.py` — recording filename normalization (reuse `contracts.slug`)

Do **not** port `filenames.py`. Add one thin helper that reuses the existing, already-tested `contracts.slug.slugify`, preserving the file extension.

**Files:**
- Create: `backend/src/steno10k/lib/names.py`
- Test: `backend/tests/lib/test_names.py`

- [ ] **Step 1: Write the failing test**

```python
from __future__ import annotations

from steno10k.lib.names import normalize_recording_name


def test_spaces_and_case_become_hyphenated_lowercase():
    assert normalize_recording_name("My Recording 1.MP3") == "my-recording-1.mp3"


def test_extension_is_preserved_and_lowercased():
    assert normalize_recording_name("clip.M4A") == "clip.m4a"


def test_cyrillic_is_transliterated_via_slug():
    assert normalize_recording_name("Лекція 1.m4a") == "lektsiia-1.m4a"


def test_no_extension_returns_slug_only():
    assert normalize_recording_name("just a name") == "just-a-name"


def test_empty_stem_falls_back_to_untitled():
    assert normalize_recording_name(".m4a") == "untitled.m4a"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/lib/test_names.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'steno10k.lib.names'`.

- [ ] **Step 3: Write the implementation**

Create `backend/src/steno10k/lib/names.py`:

```python
from __future__ import annotations

from pathlib import Path

from steno10k.contracts.slug import slugify


def normalize_recording_name(name: str) -> str:
    """Safe, unicode-safe recording filename: slugified stem + lowercased extension.

    Reuses `contracts.slug.slugify` (no second normalizer). A name with no stem
    (e.g. ".m4a") slugifies to "untitled" per `slugify`.
    """
    p = Path(name)
    return f"{slugify(p.stem)}{p.suffix.lower()}"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && uv run pytest tests/lib/test_names.py -v`
Expected: PASS (5 tests). (`slugify("")` returns `"untitled"`, and `Path(".m4a").stem == ""`, `Path(".m4a").suffix == ".m4a"`.)

- [ ] **Step 5: Commit**

```bash
git add backend/src/steno10k/lib/names.py backend/tests/lib/test_names.py
git commit -m "feat(lib): recording-name normalization reusing contracts.slug"
```

---

## Task 4: `lib/ffmpeg.py` — chunk planning + ffmpeg I/O

Port near-intact. `plan_chunks` is pure (ported test). `extract_chunk`/`get_duration_seconds` shell out to ffmpeg/ffprobe (binary-gated integration test).

**Files:**
- Create: `backend/src/steno10k/lib/ffmpeg.py`
- Test: `backend/tests/lib/test_ffmpeg.py`

- [ ] **Step 1: Write the failing test (ported `plan_chunks` + a binary-gated integration test)**

```python
from __future__ import annotations

import shutil
import subprocess

import pytest

from steno10k.lib.ffmpeg import get_duration_seconds, plan_chunks

_HAS_FFMPEG = shutil.which("ffmpeg") is not None and shutil.which("ffprobe") is not None


def test_empty_audio_returns_no_chunks():
    assert plan_chunks(duration=0, chunk_seconds=600, overlap_seconds=15, min_chunk_seconds=20) == []


def test_short_audio_returns_single_chunk():
    assert plan_chunks(duration=300, chunk_seconds=600, overlap_seconds=15, min_chunk_seconds=20) == [(0.0, 300.0)]


def test_exact_chunk_length_returns_one_chunk():
    assert plan_chunks(duration=600, chunk_seconds=600, overlap_seconds=15, min_chunk_seconds=20) == [(0.0, 600.0)]


def test_two_chunks_have_overlap_on_second():
    assert plan_chunks(duration=900, chunk_seconds=600, overlap_seconds=15, min_chunk_seconds=20) == [(0.0, 600.0), (585.0, 900.0)]


def test_first_chunk_never_has_negative_start():
    chunks = plan_chunks(duration=1200, chunk_seconds=600, overlap_seconds=15, min_chunk_seconds=20)
    assert chunks[0][0] == 0.0


def test_skips_trailing_chunk_below_min_seconds():
    assert plan_chunks(duration=601, chunk_seconds=600, overlap_seconds=15, min_chunk_seconds=20) == [(0.0, 600.0)]


def test_keeps_trailing_chunk_at_or_above_min_seconds():
    assert plan_chunks(duration=625, chunk_seconds=600, overlap_seconds=15, min_chunk_seconds=20) == [(0.0, 600.0), (585.0, 625.0)]


def test_first_chunk_can_be_short():
    assert plan_chunks(duration=10, chunk_seconds=600, overlap_seconds=15, min_chunk_seconds=20) == [(0.0, 10.0)]


def test_min_chunk_seconds_zero_keeps_short_trailing_chunk():
    assert plan_chunks(duration=601, chunk_seconds=600, overlap_seconds=15, min_chunk_seconds=0) == [(0.0, 600.0), (585.0, 601.0)]


def test_chunks_cover_entire_audio():
    chunks = plan_chunks(duration=1800.0, chunk_seconds=600, overlap_seconds=15, min_chunk_seconds=20)
    assert chunks[0][0] == 0.0
    assert chunks[-1][1] == 1800.0


@pytest.mark.skipif(not _HAS_FFMPEG, reason="ffmpeg/ffprobe not installed")
def test_get_duration_of_generated_tone(tmp_path):
    wav = tmp_path / "tone.wav"
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi",
         "-i", "sine=frequency=440:duration=2", str(wav)],
        check=True, capture_output=True,
    )
    assert 1.8 <= get_duration_seconds(wav) <= 2.2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/lib/test_ffmpeg.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'steno10k.lib.ffmpeg'`.

- [ ] **Step 3: Write the implementation**

Create `backend/src/steno10k/lib/ffmpeg.py`:

```python
from __future__ import annotations

import json
import logging
import shutil
import subprocess
from pathlib import Path

log = logging.getLogger("steno10k.ffmpeg")

SUPPORTED_EXTENSIONS = {".m4a", ".mp3", ".wav", ".flac", ".aac", ".ogg"}


class FFmpegError(RuntimeError):
    pass


def ensure_ffmpeg_available() -> None:
    if shutil.which("ffmpeg") is None:
        raise FFmpegError("ffmpeg not found in PATH. Install it (e.g. `brew install ffmpeg`).")
    if shutil.which("ffprobe") is None:
        raise FFmpegError("ffprobe not found in PATH. Install ffmpeg (e.g. `brew install ffmpeg`).")


def get_duration_seconds(audio_path: Path) -> float:
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "json", str(audio_path),
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    except subprocess.CalledProcessError as e:
        raise FFmpegError(f"ffprobe failed for {audio_path}: {e.stderr}") from e
    data = json.loads(result.stdout)
    return float(data["format"]["duration"])


def extract_chunk(
    src: Path,
    dst: Path,
    start_seconds: float,
    end_seconds: float,
    output_format: str = "m4a",
) -> None:
    """Extract chunk [start, end) into dst, re-encoding for accurate cuts."""
    dst.parent.mkdir(parents=True, exist_ok=True)
    duration = max(0.0, end_seconds - start_seconds)
    if duration <= 0:
        raise FFmpegError(f"Invalid chunk duration for {src}: {start_seconds}-{end_seconds}")

    cmd = [
        "ffmpeg", "-y", "-loglevel", "error",
        "-ss", f"{start_seconds:.3f}", "-i", str(src),
        "-t", f"{duration:.3f}", "-vn",
    ]
    if output_format == "m4a":
        cmd += ["-c:a", "aac", "-b:a", "96k"]
    elif output_format == "mp3":
        cmd += ["-c:a", "libmp3lame", "-b:a", "96k"]
    elif output_format == "wav":
        cmd += ["-c:a", "pcm_s16le", "-ar", "16000", "-ac", "1"]
    else:
        cmd += ["-c:a", "copy"]
    cmd.append(str(dst))

    try:
        subprocess.run(cmd, capture_output=True, text=True, check=True)
    except subprocess.CalledProcessError as e:
        raise FFmpegError(f"ffmpeg chunk failed for {src}: {e.stderr}") from e


def plan_chunks(
    duration: float,
    chunk_seconds: int,
    overlap_seconds: int,
    min_chunk_seconds: int,
) -> list[tuple[float, float]]:
    """Return (start, end) tuples covering the audio.

    For chunk index i: start = max(0, i*chunk - overlap), end = min(duration, (i+1)*chunk).
    Trailing chunks shorter than min_chunk_seconds are dropped (unless it is the
    first chunk, or min_chunk_seconds <= 0 which disables the drop).
    """
    chunks: list[tuple[float, float]] = []
    if duration <= 0:
        return chunks
    i = 0
    while True:
        nominal_start = i * chunk_seconds
        if nominal_start >= duration:
            break
        start = max(0.0, nominal_start - overlap_seconds)
        end = min(duration, (i + 1) * chunk_seconds)
        if end <= start:
            break
        if i > 0 and min_chunk_seconds > 0 and (end - start) < min_chunk_seconds:
            break
        chunks.append((start, end))
        i += 1
    return chunks
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && uv run pytest tests/lib/test_ffmpeg.py -v`
Expected: PASS. The 10 `plan_chunks` tests pass; `test_get_duration_of_generated_tone` PASSES if ffmpeg is installed, else SKIPPED.

- [ ] **Step 5: Commit**

```bash
git add backend/src/steno10k/lib/ffmpeg.py backend/tests/lib/test_ffmpeg.py
git commit -m "feat(lib): ffmpeg chunk planning and extraction"
```

---

## Task 5: `lib/docx.py` — markdown→docx render (port near-intact)

**Files:**
- Create: `backend/src/steno10k/lib/docx.py`
- Test: `backend/tests/lib/test_docx_render.py`

- [ ] **Step 1: Write the failing test (ported render tests)**

```python
from __future__ import annotations

from docx import Document

from steno10k.lib.docx import _split_inline, render_markdown_to_docx


def test_plain_text_is_single_plain_run():
    assert _split_inline("hello world") == [("hello world", "plain")]


def test_bold_span():
    assert _split_inline("a **b** c") == [("a ", "plain"), ("b", "bold"), (" c", "plain")]


def test_italic_span_with_asterisk():
    assert _split_inline("a *b* c") == [("a ", "plain"), ("b", "italic"), (" c", "plain")]


def test_italic_span_with_underscore():
    assert _split_inline("a _b_ c") == [("a ", "plain"), ("b", "italic"), (" c", "plain")]


def test_code_span():
    assert _split_inline("see `x = 1` now") == [("see ", "plain"), ("x = 1", "code"), (" now", "plain")]


def test_bold_takes_precedence_over_italic():
    assert _split_inline("**bold**") == [("bold", "bold")]


def test_stray_marker_is_literal():
    assert _split_inline("a * b") == [("a * b", "plain")]


def test_unclosed_bold_is_literal():
    assert _split_inline("a **b c") == [("a **b c", "plain")]


def test_empty_string():
    assert _split_inline("") == []


def test_code_content_is_not_reparsed():
    assert _split_inline("`**not bold**`") == [("**not bold**", "code")]


def _paras(doc):
    return [(p.style.name, p.text) for p in doc.paragraphs]


def test_headings_levels():
    doc = Document()
    render_markdown_to_docx("# H1\n## H2\n### H3\n#### H4", doc)
    styles = [p.style.name for p in doc.paragraphs if p.text]
    assert styles == ["Heading 1", "Heading 2", "Heading 3", "Heading 4"]


def test_plain_paragraph():
    doc = Document()
    render_markdown_to_docx("Just a sentence.", doc)
    assert ("Normal", "Just a sentence.") in _paras(doc)


def test_bullet_list():
    doc = Document()
    render_markdown_to_docx("- one\n- two", doc)
    assert [p.text for p in doc.paragraphs if p.style.name == "List Bullet"] == ["one", "two"]


def test_nested_bullet():
    doc = Document()
    render_markdown_to_docx("- top\n  - child", doc)
    assert any(p.style.name == "List Bullet 2" and p.text == "child" for p in doc.paragraphs)


def test_numbered_list():
    doc = Document()
    render_markdown_to_docx("1. first\n2. second", doc)
    assert [p.text for p in doc.paragraphs if p.style.name == "List Number"] == ["first", "second"]


def test_horizontal_rule_is_skipped():
    doc = Document()
    render_markdown_to_docx("a\n\n---\n\nb", doc)
    texts = [p.text for p in doc.paragraphs if p.text]
    assert "---" not in texts and "a" in texts and "b" in texts


def test_bold_run_in_paragraph():
    doc = Document()
    render_markdown_to_docx("a **b** c", doc)
    para = next(p for p in doc.paragraphs if p.text == "a b c")
    assert [r.text for r in para.runs if r.bold] == ["b"]


def test_blank_lines_do_not_create_empty_paragraphs():
    doc = Document()
    render_markdown_to_docx("a\n\n\nb", doc)
    assert [p.text for p in doc.paragraphs if p.text] == ["a", "b"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/lib/test_docx_render.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'steno10k.lib.docx'`.

- [ ] **Step 3: Write the implementation (render half)**

Create `backend/src/steno10k/lib/docx.py`:

```python
from __future__ import annotations

import logging
import re
from pathlib import Path

from docx import Document
from docx.text.paragraph import Paragraph

from steno10k.contracts.errors import ErrorLog

log = logging.getLogger("steno10k.docx")

_INLINE_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("code", re.compile(r"`([^`]+)`")),
    ("bold", re.compile(r"\*\*([^*]+)\*\*")),
    ("italic", re.compile(r"\*([^*]+)\*")),
    ("italic", re.compile(r"_([^_]+)_")),
]


def _split_inline(text: str) -> list[tuple[str, str]]:
    """Tokenize one line into (text, style) runs: plain|bold|italic|code."""
    if not text:
        return []
    best: tuple[int, int, str, str] | None = None
    for style, pat in _INLINE_PATTERNS:
        m = pat.search(text)
        if m is None:
            continue
        if best is None or m.start() < best[0]:
            best = (m.start(), m.end(), style, m.group(1))
    if best is None:
        return [(text, "plain")]
    start, end, style, inner = best
    runs: list[tuple[str, str]] = []
    if start > 0:
        runs.extend(_split_inline(text[:start]))
    runs.append((inner, style))
    if end < len(text):
        runs.extend(_split_inline(text[end:]))
    return runs


_HEADING_RE = re.compile(r"^(#{1,4})\s+(.*)$")
_BULLET_RE = re.compile(r"^(\s*)[-*]\s+(.*)$")
_NUMBERED_RE = re.compile(r"^\s*\d+\.\s+(.*)$")
_HR_RE = re.compile(r"^\s*---+\s*$")


def _apply_inline(paragraph: Paragraph, text: str) -> None:
    for run_text, style in _split_inline(text):
        run = paragraph.add_run(run_text)
        if style == "bold":
            run.bold = True
        elif style == "italic":
            run.italic = True
        elif style == "code":
            run.font.name = "Courier New"


def render_markdown_to_docx(markdown: str, doc: Document) -> None:
    """Append a supported Markdown subset to `doc`.

    Supports ATX headings (#-####), `-`/`*` bullets (nested by indent), numbered
    lists, `**bold**`/`*italic*`/`_italic_`/`` `code` `` spans, plain paragraphs.
    `---` rules and blank lines produce nothing; malformed markup degrades to text.
    """
    for raw_line in markdown.splitlines():
        line = raw_line.rstrip()
        if not line.strip() or _HR_RE.match(line):
            continue
        m = _HEADING_RE.match(line)
        if m:
            doc.add_heading(m.group(2).strip(), level=len(m.group(1)))
            continue
        m = _BULLET_RE.match(line)
        if m:
            style = "List Bullet 2" if len(m.group(1)) >= 2 else "List Bullet"
            _apply_inline(doc.add_paragraph(style=style), m.group(2).strip())
            continue
        m = _NUMBERED_RE.match(line)
        if m:
            _apply_inline(doc.add_paragraph(style="List Number"), m.group(1).strip())
            continue
        _apply_inline(doc.add_paragraph(), line.strip())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && uv run pytest tests/lib/test_docx_render.py -v`
Expected: PASS (all render/inline tests).

- [ ] **Step 5: Commit**

```bash
git add backend/src/steno10k/lib/docx.py backend/tests/lib/test_docx_render.py
git commit -m "feat(lib): markdown-to-docx renderer"
```

---

## Task 6: `lib/docx.py` — decoupled `build_bundle` (rewrite orchestration)

Rewrite the reference `build_bundle`: it now takes explicit `(markdown_path → docx_path)` pairs and a `contracts.errors.ErrorLog`. No `filenames` import, no old error logger, no hardcoded `conspect.md`/`_raw`/`_conspect` names.

**Files:**
- Modify: `backend/src/steno10k/lib/docx.py`
- Test: `backend/tests/lib/test_docx_bundle.py`

- [ ] **Step 1: Write the failing test**

```python
from __future__ import annotations

from pathlib import Path

from docx import Document

from steno10k.contracts.errors import ErrorLog
from steno10k.lib.docx import build_bundle


def _make_md(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_builds_docx_for_each_existing_source(tmp_path):
    src = tmp_path / "clean.md"
    _make_md(src, "# Title\n\nBody.")
    dst = tmp_path / "out" / "clean.docx"
    err = ErrorLog(tmp_path / "errors.log")
    build_bundle([(src, dst)], force=False, err_log=err)
    assert dst.exists()
    assert err.count == 0
    # Round-trips as a real docx.
    assert any(p.text == "Title" for p in Document(str(dst)).paragraphs)


def test_missing_source_is_skipped_not_errored(tmp_path):
    dst = tmp_path / "out" / "missing.docx"
    err = ErrorLog(tmp_path / "errors.log")
    build_bundle([(tmp_path / "nope.md", dst)], force=False, err_log=err)
    assert not dst.exists()
    assert err.count == 0


def test_existing_dst_not_overwritten_unless_force(tmp_path):
    src = tmp_path / "clean.md"
    _make_md(src, "hello")
    dst = tmp_path / "out" / "clean.docx"
    dst.parent.mkdir(parents=True)
    dst.write_text("SENTINEL", encoding="utf-8")
    err = ErrorLog(tmp_path / "errors.log")
    build_bundle([(src, dst)], force=False, err_log=err)
    assert dst.read_text(encoding="utf-8") == "SENTINEL"  # untouched
    build_bundle([(src, dst)], force=True, err_log=err)
    assert dst.read_text(encoding="utf-8", errors="ignore") != "SENTINEL"  # rebuilt


def test_one_bad_source_does_not_abort_sibling(tmp_path, monkeypatch):
    import steno10k.lib.docx as docxmod

    good = tmp_path / "good.md"
    bad = tmp_path / "bad.md"
    _make_md(good, "good")
    _make_md(bad, "bad")
    good_dst = tmp_path / "out" / "good.docx"
    bad_dst = tmp_path / "out" / "bad.docx"
    err = ErrorLog(tmp_path / "errors.log")

    real_build_one = docxmod._build_one

    def flaky(source: Path, dst: Path, force: bool) -> None:
        if source == bad:
            raise RuntimeError("render exploded")
        real_build_one(source, dst, force)

    monkeypatch.setattr(docxmod, "_build_one", flaky)
    build_bundle([(bad, bad_dst), (good, good_dst)], force=False, err_log=err)
    assert good_dst.exists()      # sibling still built
    assert not bad_dst.exists()
    assert err.count == 1         # the bad one was logged
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/lib/test_docx_bundle.py -v`
Expected: FAIL — `ImportError: cannot import name 'build_bundle'`.

- [ ] **Step 3: Add the implementation to `lib/docx.py`**

Append to `backend/src/steno10k/lib/docx.py`:

```python
def _build_one(source: Path, dst: Path, force: bool) -> None:
    """Render one markdown source into one .docx at dst. Assumes source exists."""
    if dst.exists() and not force:
        return
    doc = Document()
    render_markdown_to_docx(source.read_text(encoding="utf-8"), doc)
    dst.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(dst))


def build_bundle(
    pairs: list[tuple[Path, Path]],
    force: bool,
    err_log: ErrorLog,
) -> None:
    """Render each (markdown_path -> docx_path) pair independently.

    A missing source is skipped silently (not an error). A render failure on one
    pair is logged to `err_log` and does not abort the others (per-file isolation).
    """
    for source, dst in pairs:
        if not source.exists():
            log.info("bundle: skipping %s (source %s not found)", dst.name, source.name)
            continue
        try:
            _build_one(source, dst, force)
        except Exception as e:  # per-file isolation boundary (lxml/zip errors, etc.)
            err_log.log("bundle", dst.name, e)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && uv run pytest tests/lib/test_docx_bundle.py -v`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add backend/src/steno10k/lib/docx.py backend/tests/lib/test_docx_bundle.py
git commit -m "feat(lib): decoupled build_bundle over explicit source/target pairs"
```

---

## Task 7: `lib/prompts.py` — prompt registry (loader reworked + content from scratch)

English, domain-neutral defaults for `clean` and `summarize` (no `conspect`/`verify`/Ukrainian). Override convention matches F2: a file `<override_dir>/<name>.md` wins over the built-in default; rollback = delete the override.

**Files:**
- Create: `backend/src/steno10k/lib/prompts.py`
- Test: `backend/tests/lib/test_prompts.py`

- [ ] **Step 1: Write the failing test**

```python
from __future__ import annotations

import pytest

from steno10k.lib.prompts import (
    PROMPT_NAMES,
    default_prompt,
    load_prompts,
    resolve_prompt,
)


def test_prompt_names_are_the_m1_llm_stages():
    assert set(PROMPT_NAMES) == {"clean", "summarize"}


def test_defaults_are_english_and_domain_neutral():
    text = default_prompt("clean") + default_prompt("summarize")
    lowered = text.lower()
    for banned in ("lecture", "conspect", "ukrainian", "лекц"):
        assert banned not in lowered


def test_summarize_default_has_target_language_placeholder():
    assert "{target_output_language}" in default_prompt("summarize")


def test_unknown_prompt_name_raises():
    with pytest.raises(KeyError):
        default_prompt("nope")


def test_resolve_returns_default_when_no_override(tmp_path):
    content, source = resolve_prompt("clean", tmp_path)
    assert source == "default"
    assert content == default_prompt("clean")


def test_override_file_wins(tmp_path):
    (tmp_path / "clean.md").write_text("CUSTOM CLEAN", encoding="utf-8")
    content, source = resolve_prompt("clean", tmp_path)
    assert source == "override"
    assert content == "CUSTOM CLEAN"


def test_rollback_by_removing_override(tmp_path):
    override = tmp_path / "clean.md"
    override.write_text("CUSTOM", encoding="utf-8")
    assert resolve_prompt("clean", tmp_path)[1] == "override"
    override.unlink()
    assert resolve_prompt("clean", tmp_path)[1] == "default"


def test_load_prompts_bundle(tmp_path):
    (tmp_path / "summarize.md").write_text("CUSTOM SUM", encoding="utf-8")
    prompts = load_prompts(tmp_path)
    assert prompts.clean == default_prompt("clean")
    assert prompts.summarize == "CUSTOM SUM"


def test_load_prompts_with_no_override_dir_uses_defaults():
    prompts = load_prompts(None)
    assert prompts.clean == default_prompt("clean")
    assert prompts.summarize == default_prompt("summarize")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/lib/test_prompts.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'steno10k.lib.prompts'`.

- [ ] **Step 3: Write the implementation**

Create `backend/src/steno10k/lib/prompts.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

PROMPT_NAMES: tuple[str, ...] = ("clean", "summarize")

# English, domain-neutral built-in defaults. The `summarize` template carries a
# `{target_output_language}` placeholder that the summarize stage formats; the
# loader itself never formats (it only stores/loads text).
_DEFAULTS: dict[str, str] = {
    "clean": (
        "You are cleaning a raw speech-to-text transcript. Fix punctuation, "
        "capitalization, obvious recognition errors, and paragraph structure, and "
        "remove repeated filler fragments. Preserve the original meaning, wording, "
        "and language. Do not summarize, translate, or add facts. Return only the "
        "corrected transcript as Markdown (paragraphs separated by blank lines), "
        "with no preamble."
    ),
    "summarize": (
        "You produce a detailed, well-structured Markdown summary from a cleaned "
        "transcript. Preserve concrete facts: dates, names, places, numbers, "
        "definitions, and short direct quotes. Do not generalize away specifics or "
        "invent facts; mark anything unclear inline as (unclear: ...). Organize the "
        "summary by topic with headings. Write the output in this language: "
        "{target_output_language}. Return only the Markdown summary, with no preamble."
    ),
}


@dataclass(frozen=True)
class Prompts:
    clean: str
    summarize: str


def default_prompt(name: str) -> str:
    """Built-in default for `name`. Raises KeyError for an unknown name."""
    return _DEFAULTS[name]


def resolve_prompt(name: str, override_dir: Path | None) -> tuple[str, str]:
    """Return (content, source) where source is "override" or "default".

    An override is a file `<override_dir>/<name>.md`; if present it wins.
    """
    if name not in _DEFAULTS:
        raise KeyError(name)
    if override_dir is not None:
        candidate = override_dir / f"{name}.md"
        if candidate.is_file():
            return candidate.read_text(encoding="utf-8"), "override"
    return _DEFAULTS[name], "default"


def load_prompts(override_dir: Path | None) -> Prompts:
    """Resolve every prompt into a `Prompts` bundle for the stages."""
    resolved = {name: resolve_prompt(name, override_dir)[0] for name in PROMPT_NAMES}
    return Prompts(**resolved)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && uv run pytest tests/lib/test_prompts.py -v`
Expected: PASS (9 tests).

- [ ] **Step 5: Commit**

```bash
git add backend/src/steno10k/lib/prompts.py backend/tests/lib/test_prompts.py
git commit -m "feat(lib): English domain-neutral prompt registry with override loader"
```

---

## Task 8: `lib/llm.py` — `OpenAICompatibleClient` (implements the F1 protocol)

Port the transport + retry core; expose a single `complete(system, user) -> str` that satisfies `contracts.llm.LLMClient`. No domain methods, no vendor-specific code. Retry/timeout are hardcoded M1 constants (§ ADR).

**Files:**
- Create: `backend/src/steno10k/lib/llm.py`
- Test: `backend/tests/lib/test_llm.py`

- [ ] **Step 1: Write the failing test**

```python
from __future__ import annotations

import httpx
import pytest
from openai import OpenAIError

from steno10k.contracts.config import LLMConfig
from steno10k.contracts.llm import LLMClient
from steno10k.lib.llm import OpenAICompatibleClient


class _Msg:
    def __init__(self, content):
        self.content = content


class _Choice:
    def __init__(self, content):
        self.message = _Msg(content)


class _Resp:
    def __init__(self, content):
        self.choices = [_Choice(content)]


class _Completions:
    def __init__(self, behaviors):
        self._behaviors = list(behaviors)
        self.calls = 0

    def create(self, **kwargs):
        b = self._behaviors[self.calls]
        self.calls += 1
        if isinstance(b, Exception):
            raise b
        return _Resp(b)


class _Chat:
    def __init__(self, behaviors):
        self.completions = _Completions(behaviors)


class FakeOpenAI:
    """Stands in for `openai.OpenAI`; `behaviors` is a list of str|Exception."""

    def __init__(self, behaviors):
        self.chat = _Chat(behaviors)


def _cfg() -> LLMConfig:
    return LLMConfig(model="test-model", base_url="http://local", temperature=0.2, max_tokens=100)


def test_satisfies_llmclient_protocol():
    client: LLMClient = OpenAICompatibleClient(_cfg(), client=FakeOpenAI(["hi"]))
    assert client.complete("sys", "user") == "hi"


def test_content_is_stripped():
    c = OpenAICompatibleClient(_cfg(), client=FakeOpenAI(["  padded \n"]))
    assert c.complete("s", "u") == "padded"


def test_none_content_becomes_empty_string():
    c = OpenAICompatibleClient(_cfg(), client=FakeOpenAI([None]))
    assert c.complete("s", "u") == ""


def test_retries_then_succeeds(monkeypatch):
    import steno10k.lib.llm as llmmod

    monkeypatch.setattr(llmmod.time, "sleep", lambda _s: None)  # no real waiting
    fake = FakeOpenAI([OpenAIError("boom"), "recovered"])
    c = OpenAICompatibleClient(_cfg(), client=fake)
    assert c.complete("s", "u") == "recovered"
    assert fake.chat.completions.calls == 2


def test_raises_after_max_retries(monkeypatch):
    import steno10k.lib.llm as llmmod

    monkeypatch.setattr(llmmod.time, "sleep", lambda _s: None)
    fake = FakeOpenAI([OpenAIError("e1"), OpenAIError("e2"), OpenAIError("e3")])
    c = OpenAICompatibleClient(_cfg(), client=fake)
    with pytest.raises(RuntimeError, match="failed after 3 attempts"):
        c.complete("s", "u")
    assert fake.chat.completions.calls == 3


def test_missing_api_key_raises(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="Missing API key"):
        OpenAICompatibleClient(_cfg())  # no injected client -> tries to build real one


def test_no_vendor_names_in_source():
    from pathlib import Path

    src = (Path(__file__).resolve().parents[2] / "src" / "steno10k" / "lib" / "llm.py").read_text()
    lowered = src.lower()
    for vendor in ("gemini", "anthropic", "claude", "google"):
        assert vendor not in lowered
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/lib/test_llm.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'steno10k.lib.llm'`.

- [ ] **Step 3: Write the implementation**

Create `backend/src/steno10k/lib/llm.py`:

```python
from __future__ import annotations

import logging
import os
import time

import httpx
from openai import APIStatusError, OpenAI, OpenAIError, RateLimitError

from steno10k.contracts.config import LLMConfig
from steno10k.lib.retry import compute_backoff_wait, extract_retry_after_seconds

log = logging.getLogger("steno10k.llm")

# Retry/timeout policy is a hardcoded M1 constant set — not a user knob. Deferred
# to M2; see docs/adr/0001-defer-llm-and-whisper-config-knobs.md.
_TIMEOUT_SECONDS = 120
_MAX_RETRIES = 3
_RETRY_INITIAL_WAIT = 2.0
_RETRY_BACKOFF_BASE = 2.0
_RETRY_MAX_WAIT = 60.0
_RETRY_RATE_LIMIT_WAIT = 60.0


class OpenAICompatibleClient:
    """`contracts.llm.LLMClient` over any OpenAI-compatible chat-completions endpoint.

    Provider-neutral: base URL + model come from `LLMConfig`; rate-limit backoff
    uses the standard `Retry-After` header (via `lib.retry`). No vendor-specific code.
    """

    def __init__(self, config: LLMConfig, *, client: OpenAI | None = None) -> None:
        self.config = config
        if client is not None:
            self.client = client
            return
        api_key = os.environ.get(config.api_key_env)
        if not api_key:
            raise RuntimeError(f"Missing API key. Set env var {config.api_key_env}.")
        kwargs: dict[str, object] = {"api_key": api_key, "timeout": _TIMEOUT_SECONDS}
        if config.base_url:
            kwargs["base_url"] = config.base_url
        self.client = OpenAI(**kwargs)

    def _compute_wait(self, attempt: int, err: Exception) -> float:
        is_rate_limit = isinstance(err, RateLimitError) or (
            isinstance(err, APIStatusError) and getattr(err, "status_code", None) == 429
        )
        return compute_backoff_wait(
            attempt,
            initial=_RETRY_INITIAL_WAIT,
            base=_RETRY_BACKOFF_BASE,
            max_wait=_RETRY_MAX_WAIT,
            rate_limit_floor=_RETRY_RATE_LIMIT_WAIT,
            is_rate_limit=is_rate_limit,
            server_hint=extract_retry_after_seconds(err),
        )

    def complete(self, system: str, user: str) -> str:
        last_err: Exception | None = None
        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                resp = self.client.chat.completions.create(
                    model=self.config.model,
                    temperature=self.config.temperature,
                    max_tokens=self.config.max_tokens,
                    messages=[
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                )
                return (resp.choices[0].message.content or "").strip()
            except (OpenAIError, httpx.HTTPError) as e:
                last_err = e
                if attempt >= _MAX_RETRIES:
                    break
                log.warning(
                    "LLM call failed (attempt %s/%s): %s. Retrying.",
                    attempt, _MAX_RETRIES, e,
                )
                time.sleep(self._compute_wait(attempt, e))
        raise RuntimeError(f"LLM call failed after {_MAX_RETRIES} attempts: {last_err}")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && uv run pytest tests/lib/test_llm.py -v`
Expected: PASS (7 tests). `test_missing_api_key_raises` relies on `OPENAI_API_KEY` being unset in the test env (the monkeypatch removes it).

- [ ] **Step 5: Commit**

```bash
git add backend/src/steno10k/lib/llm.py backend/tests/lib/test_llm.py
git commit -m "feat(lib): OpenAI-compatible LLM client implementing the F1 protocol"
```

---

## Task 9: `lib/transcriber.py` — faster-whisper worker

Port near-intact. `TranscribeJob`/`TranscribeSettings` are L-owned dataclasses (the transcribe stage maps `TranscriptionConfig` → settings and supplies the M1 default decode knobs). Empty-jobs path is pure-tested; the real transcription path is model-gated.

**Files:**
- Create: `backend/src/steno10k/lib/transcriber.py`
- Test: `backend/tests/lib/test_transcriber.py`

- [ ] **Step 1: Write the failing test**

```python
from __future__ import annotations

import os

import pytest

from steno10k.lib.transcriber import TranscribeJob, TranscribeSettings, transcribe_chunks

_RUN_WHISPER = os.environ.get("STENO10K_RUN_WHISPER") == "1"


def _settings() -> TranscribeSettings:
    return TranscribeSettings(
        model="tiny", device="cpu", compute_type="int8", language="en",
        beam_size=1, vad_filter=False, min_silence_duration_ms=500, cpu_threads=1,
    )


def test_empty_jobs_returns_empty_list():
    assert transcribe_chunks([], _settings(), max_workers=1) == []


@pytest.mark.skipif(not _RUN_WHISPER, reason="set STENO10K_RUN_WHISPER=1 to run the real model")
def test_transcribes_a_generated_tone(tmp_path):
    import subprocess

    wav = tmp_path / "clip.wav"
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi",
         "-i", "sine=frequency=440:duration=1", str(wav)],
        check=True, capture_output=True,
    )
    out = tmp_path / "clip.txt"
    results = transcribe_chunks([TranscribeJob(wav, out)], _settings(), max_workers=1)
    assert results == [(out, None)]
    assert out.exists()  # a (possibly empty) transcript file was written
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/lib/test_transcriber.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'steno10k.lib.transcriber'`.

- [ ] **Step 3: Write the implementation**

Create `backend/src/steno10k/lib/transcriber.py`:

```python
from __future__ import annotations

import logging
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path

log = logging.getLogger("steno10k.transcriber")


@dataclass
class TranscribeJob:
    chunk_path: Path
    output_path: Path


@dataclass
class TranscribeSettings:
    model: str
    device: str
    compute_type: str
    language: str
    beam_size: int
    vad_filter: bool
    min_silence_duration_ms: int
    cpu_threads: int


# Per-process cached WhisperModel. Loading the model is expensive, so each worker
# process loads it once on its first job and reuses it. ProcessPoolExecutor gives
# each worker its own interpreter, so these globals are per-process state — no
# cross-worker sharing and no locking. The settings are cached alongside so a job
# with different settings rebuilds the model.
_WORKER_MODEL = None
_WORKER_SETTINGS: TranscribeSettings | None = None


def _ensure_model(settings: TranscribeSettings):
    global _WORKER_MODEL, _WORKER_SETTINGS
    if _WORKER_MODEL is not None and _WORKER_SETTINGS == settings:
        return _WORKER_MODEL
    from faster_whisper import WhisperModel

    _WORKER_MODEL = WhisperModel(
        settings.model,
        device=settings.device,
        compute_type=settings.compute_type,
        cpu_threads=settings.cpu_threads,
    )
    _WORKER_SETTINGS = settings
    return _WORKER_MODEL


def _transcribe_one(job: TranscribeJob, settings: TranscribeSettings) -> tuple[Path, str | None]:
    """Runs inside a worker process. Returns (output_path, error_or_None)."""
    try:
        model = _ensure_model(settings)
        vad_params = (
            {"min_silence_duration_ms": settings.min_silence_duration_ms}
            if settings.vad_filter
            else None
        )
        segments, _info = model.transcribe(
            str(job.chunk_path),
            language=settings.language,
            beam_size=settings.beam_size,
            vad_filter=settings.vad_filter,
            vad_parameters=vad_params,
        )
        text = "\n".join(p for p in (seg.text.strip() for seg in segments) if p).strip()
        job.output_path.parent.mkdir(parents=True, exist_ok=True)
        job.output_path.write_text(text, encoding="utf-8")
        return job.output_path, None
    except Exception as e:  # isolation: return the error to the parent process
        return job.output_path, f"{type(e).__name__}: {e}"


def transcribe_chunks(
    jobs: list[TranscribeJob],
    settings: TranscribeSettings,
    max_workers: int,
) -> list[tuple[Path, str | None]]:
    if not jobs:
        return []
    if max_workers <= 1:
        return [_transcribe_one(j, settings) for j in jobs]
    results: list[tuple[Path, str | None]] = []
    with ProcessPoolExecutor(max_workers=max_workers) as ex:
        futures = {ex.submit(_transcribe_one, j, settings): j for j in jobs}
        for fut in as_completed(futures):
            results.append(fut.result())
    return results
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && uv run pytest tests/lib/test_transcriber.py -v`
Expected: PASS — `test_empty_jobs_returns_empty_list` passes; `test_transcribes_a_generated_tone` SKIPPED (unless `STENO10K_RUN_WHISPER=1`).

- [ ] **Step 5: Commit**

```bash
git add backend/src/steno10k/lib/transcriber.py backend/tests/lib/test_transcriber.py
git commit -m "feat(lib): faster-whisper transcription worker"
```

---

## Task 10: Deferred-config ADR

Record the §3 decision durably in `docs/` (per review feedback).

**Files:**
- Create: `docs/adr/0001-defer-llm-and-whisper-config-knobs.md`

- [ ] **Step 1: Write the ADR**

Create `docs/adr/0001-defer-llm-and-whisper-config-knobs.md`:

```markdown
# 0001 — Defer LLM retry/timeout and Whisper decode knobs to M2

Status: Accepted · Date: 2026-07-11 · Milestone: M1·L

## Context

The utilities ported from `lecturemate10k` read config fields that the frozen F1
contracts do not define:

- `LLMConfig` (F1) has no `timeout_seconds`, `max_retries`, `retry_initial_wait`,
  `retry_backoff_base`, `retry_max_wait`, `retry_rate_limit_wait`, no direct
  `api_key`, and no `output_language`.
- `TranscriptionConfig` (F1) has no `beam_size`, `vad_filter`, or
  `min_silence_duration_ms`.

F1 is a frozen contract; adding fields is a coordinated change (AGENTS.md lock
protocol). M1's value is a working pipeline, not exhaustive configurability.

## Decision

- LLM **retry/timeout policy is hardcoded** as M1 constants in `lib/llm`
  (`_TIMEOUT_SECONDS=120`, `_MAX_RETRIES=3`, backoff 2·2ⁿ capped at 60s, rate-limit
  floor 60s). Not a user knob in M1.
- Whisper `beam_size`/`vad_filter`/`min_silence_duration_ms` are supplied as **M1
  defaults by the transcribe stage** when it builds `TranscribeSettings`.
- Direct `api_key` stays **dropped** — F1 is env-only by secrets policy; `lib/llm`
  reads `api_key_env` only.
- `output_language` is **not** an LLM-client concern — it lives in
  `PromptsConfig.target_output_language` and is threaded into the summarize prompt
  by the stage.

Net: L adds **zero** fields to F1/F2. No contract-change lock is needed for L.

## Consequences

- Simpler M1, no contract churn, `lib` stays provider-neutral and config-light.
- Users cannot tune retry/decode behavior in M1.
- **M2 ("configurability polish")** revisits this: if these become user knobs, that
  is a coordinated `LLMConfig`/`TranscriptionConfig` change then, surfaced in config
  and the UI.
```

- [ ] **Step 2: Commit**

```bash
git add docs/adr/0001-defer-llm-and-whisper-config-knobs.md
git commit -m "docs(adr): defer LLM retry and Whisper decode knobs to M2"
```

---

## Task 11: Full-suite verification

- [ ] **Step 1: Run the entire backend suite**

Run: `cd backend && uv run pytest -q`
Expected: PASS. New `tests/lib/*` pass; binary/model-gated tests skip when ffmpeg/whisper are absent; all pre-existing tests still pass.

- [ ] **Step 2: Typecheck**

Run: `cd backend && uv run mypy`
Expected: `Success: no issues found`. Confirms `OpenAICompatibleClient` satisfies `contracts.llm.LLMClient` (the `client: LLMClient = OpenAICompatibleClient(...)` assignment in `test_llm.py` typechecks under strict mode) and the `faster_whisper.*`/`docx.*` overrides suppress missing-stub errors.

- [ ] **Step 3: Lint + format check**

Run: `cd backend && uv run ruff check . && uv run ruff format --check .`
Expected: `All checks passed!` (fix with `uv run ruff format .` if needed, then re-commit).

- [ ] **Step 4: Pre-commit (repo-wide gate)**

Run: `pre-commit run --all-files`
Expected: all hooks pass.

- [ ] **Step 5: Final commit (only if formatting/fixups were needed)**

```bash
git add -A
git commit -m "chore(lib): lint/format fixups"
```

---

## Self-Review notes (author)

- **Spec coverage:** §2 table → Tasks 2–9 (retry/names/ffmpeg/docx-render/bundle/prompts/llm/transcriber); §3 config-gap + ADR → Tasks 8, 9, 10; §3a provider-neutrality → Task 2 (`test_provider_specific_body_is_ignored`) + Task 8 (`test_no_vendor_names_in_source`); §4 deps → Task 0; §5 testing (ported vs new, pure-CI, binary-gated) → Tasks 4/9 skips + Task 1 boundary; §7 acceptance → Task 11 (mypy proves protocol conformance; import guard; empty vendor grep). `filenames.py` not ported → Task 3 reuses `contracts.slug`.
- **Placeholder scan:** none — every code step is complete.
- **Type consistency:** `TranscribeSettings` fields, `build_bundle(pairs, force, err_log)`, `resolve_prompt(name, override_dir) -> (content, source)`, and `complete(system, user)` names are identical across tasks and match the spec.
```
