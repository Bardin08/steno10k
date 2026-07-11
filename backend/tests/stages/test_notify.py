from __future__ import annotations

from steno10k.contracts.events import EventKind
from steno10k.contracts.status import StageStatus
from steno10k.stages.notify import NotifyStage
from tests.stages.support import RecordingBus, make_ctx


def _touch(path, text="x"):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_name_and_deps():
    stage = NotifyStage()
    assert stage.name == "notify"
    assert stage.depends_on == ["bundle"]


def test_emits_artifact_list_and_counts(set_dir):
    _touch(set_dir / "merged" / "clean_transcript.md")
    _touch(set_dir / "summary.md")
    _touch(set_dir / "bundle" / "transcript.docx")
    _touch(set_dir / "bundle" / "summary.docx")
    bus = RecordingBus()
    ctx = make_ctx(set_dir, events=bus)

    result = NotifyStage().run(ctx)

    assert result.status == StageStatus.OK
    assert result.stats["artifacts"] == 4
    progress = [e for e in bus.events if e.kind == EventKind.STAGE_PROGRESS]
    assert len(progress) == 1
    payload = progress[0].payload
    assert payload["stage"] == "notify"
    assert set(payload["artifacts"]) == {
        "merged/clean_transcript.md",
        "summary.md",
        "bundle/transcript.docx",
        "bundle/summary.docx",
    }


def test_only_lists_existing_artifacts(set_dir):
    _touch(set_dir / "summary.md")  # nothing else produced
    bus = RecordingBus()
    ctx = make_ctx(set_dir, events=bus)

    result = NotifyStage().run(ctx)

    assert result.stats["artifacts"] == 1
    payload = next(e for e in bus.events if e.kind == EventKind.STAGE_PROGRESS).payload
    assert payload["artifacts"] == ["summary.md"]


def test_honors_custom_summary_filename(set_dir):
    _touch(set_dir / "notes.md")
    bus = RecordingBus()
    ctx = make_ctx(set_dir, events=bus)
    ctx.cfg.output.summary_filename = "notes.md"

    NotifyStage().run(ctx)

    payload = next(e for e in bus.events if e.kind == EventKind.STAGE_PROGRESS).payload
    assert "notes.md" in payload["artifacts"]
